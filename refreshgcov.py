import subprocess
import time

import util

def refresh_gcov(ssh_client):
    try:
        util.run_cmd('sudo rm -rf templates/kernel/*')
        util.run_cmd('sudo rm -rf templates/user/*')
        util.run_cmd('sudo rm -rf ../share/coverage/kernel_html_report ../share/coverage/user_html_report')


        print("[STEP 1] Collecting Kernel GCOV")
        util.run_remote_cmd(ssh_client, 'python3 /home/fastcov/fastcov.py -f /sys/kernel/debug/gcov/home/lbz/qemu/noble/drivers/infiniband/core/*.gcda /sys/kernel/debug/gcov/home/lbz/qemu/noble/drivers/infiniband/sw/rxe/*.gcda -i /home/lbz/qemu/noble/drivers/infiniband/ -o /home/kernel_coverage.info -X -l -n')
        if not util.ssh_retry_until_file_exist(ssh_client, "/home/kernel_coverage.info"):
            return False

        print("[STEP 2] Generating Kernel HTML Report")
        if not util.run_remote_cmd(ssh_client, 'genhtml /home/kernel_coverage.info --output-directory /home/share/coverage/kernel_html_report'):
            return False
        if not util.ssh_retry_until_file_exist(ssh_client, "/home/share/coverage/kernel_html_report"):
            return False

        print("[STEP 3] Moving Kernel Report")
        if not util.run_cmd('sudo mv ../share/coverage/kernel_html_report/* templates/kernel'):
            return False

        print("[STEP 4] Collecting User GCOV")
        util.run_remote_cmd(ssh_client, 'python3 /home/fastcov/fastcov.py -f /home/rdma-core-master/build/librdmacm/CMakeFiles/rspreload.dir/*.gcda /home/rdma-core-master/build/libibverbs/CMakeFiles/ibverbs.dir/*.gcda /home/rdma-core-master/build/librdmacm/CMakeFiles/rdmacm.dir/*.gcda -e /home/rdma-core-master/build/include -o /home/user_coverage.info -X -l -n')
        if not util.ssh_retry_until_file_exist(ssh_client, "/home/user_coverage.info"):
            return False

        print("[STEP 5] Generating User HTML Report")
        if not util.run_remote_cmd(ssh_client, 'genhtml /home/user_coverage.info --output-directory /home/share/coverage/user_html_report'):
            return False
        if not util.ssh_retry_until_file_exist(ssh_client, "/home/share/coverage/user_html_report"):
            return False

        print("[STEP 6] Moving User Report")
        if not util.run_cmd('sudo mv ../share/coverage/user_html_report/* templates/user'):
            return False

        if not util.retry_until_file_exist("templates/kernel/index.html"):
            return False
        if not util.retry_until_file_exist("templates/user/index.html"):
            return False


        print("[STEP 7] Removing Temp Files")
        if not util.run_cmd('sudo rm -rf ../share/coverage/kernel_html_report ../share/coverage/user_html_report'):
            return False

        print("[INFO] refresh_gcov finished successfully")
        return True

    except Exception as e:
        print(f"[EXCEPTION] Unexpected error in refresh_gcov: {e}")
        return False