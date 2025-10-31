import paramiko

def ssh_get():
    hostname = "172.19.0.2"
    port = 22
    username = "root"
    key_path = "../id_rsa"

    private_key = paramiko.RSAKey.from_private_key_file(key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(
        hostname=hostname,
        port=port,
        username=username,
        pkey=private_key
    )

    return client
