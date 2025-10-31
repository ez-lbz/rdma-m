import re
import select
import os
import time
import threading
import subprocess

import paramiko

safe_print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    with safe_print_lock:
        print(*args, **kwargs)

def safe_ssh_client(ssh_client, cmd):
    try:
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        stdout.channel.recv_exit_status()  # Wait for command to complete
        return stdin, stdout, stderr
    except paramiko.ssh_exception.SSHException as e:
        print(f"[!] [SSH ERROR] SSH command execution failed: {e}")
        raise
    except Exception as e:
        print(f"[!] [ERROR] Unknown error occurred: {e}")
        raise

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"[STDOUT] {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {cmd}")
        if e.stderr:
            print(f"[STDERR] {e.stderr.strip()}")
        return False

def run_remote_cmd(ssh_client, cmd):
    try:
        env_vars = {"ASAN_OPTIONS": "verify_asan_link_order=0"}
        stdin, stdout, stderr = safe_ssh_client(ssh_client, cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            return False
        return True
    except Exception as e:
        print(f"[SSH EXCEPTION] Failed to run: {cmd}")
        print(f"[DETAIL] {e}")
        return False

def filter_output(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
    text = re.sub(r'[^\x20-\x7E\n\t]', '', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    lines = text.splitlines()
    filtered_lines = [line.strip() for line in lines if re.search(r'\[.{6,}\]', line)]
    return '\n'.join(filtered_lines).strip()

def handle_pty_output(master_fd, logfile_path):
    with open(logfile_path, "w", encoding="utf-8") as logfile:
        while True:
            ready, _, _ = select.select([master_fd], [], [], 1.0)
            if master_fd in ready:
                try:
                    data = os.read(master_fd, 1024).decode('utf-8', errors='ignore')
                    if not data:
                        break
                    filtered_data = filter_output(data)
                    if filtered_data:
                        logfile.write(filtered_data + '\n')
                        logfile.flush()
                except OSError:
                    break
            time.sleep(0.1)

def retry_until_file_exist(filename):
    for i in range(3):
        if (os.path.exists(filename)):
            print(f"[+] {filename} exists !!!")
            return True
        else:
            print("[!] try" + str(i) + "failed !!!")
            time.sleep(0.3)
    return False

def ssh_retry_until_file_exist(ssh_client, filename):
    for i in range(3):
        stdin, stdout, stderr = ssh_client.exec_command(f'stat {filename}')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print(f"[+] {filename} exists !!!")
            return True
        else:
            print("[!] try" + str(i) + "failed !!!")
            time.sleep(0.3)
    return False

def _sftp_ensure_local_dir(local_path: str) -> None:
    if not os.path.exists(local_path):
        os.makedirs(local_path, exist_ok=True)

def sftp_download_dir(ssh_client: paramiko.SSHClient, remote_dir: str, local_dir: str) -> bool:
    try:
        _sftp_ensure_local_dir(local_dir)
        sftp = ssh_client.open_sftp()
        stack = [(remote_dir, local_dir)]
        while stack:
            current_remote, current_local = stack.pop()
            _sftp_ensure_local_dir(current_local)
            for entry in sftp.listdir_attr(current_remote):
                remote_path = current_remote.rstrip('/') + '/' + entry.filename
                local_path = os.path.join(current_local, entry.filename)
                if paramiko.S_ISDIR(entry.st_mode):
                    stack.append((remote_path, local_path))
                else:
                    _sftp_ensure_local_dir(os.path.dirname(local_path))
                    sftp.get(remote_path, local_path)
        sftp.close()
        return True
    except Exception as e:
        print(f"[SFTP ERROR] Failed to download {remote_dir} -> {local_dir}: {e}")
        return False