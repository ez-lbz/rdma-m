import util

def refresh_gcov(ssh_client):
    try:
        util.run_cmd('sudo rm -rf templates/kernel/*')
        util.run_cmd('sudo rm -rf templates/user/*')
        util.run_remote_cmd(ssh_client, 'rm -rf /tmp/coverage')
        util.run_remote_cmd(ssh_client, 'mkdir -p /tmp/coverage')


        print("[STEP 1] Collecting Kernel GCOV with LCOV")
        # 使用 lcov 从内核 debugfs 收集覆盖率数据
        kernel_base_dir = '/sys/kernel/debug/gcov/usr/src/linux-source-6.8.0/linux-source-6.8.0/drivers/infiniband'
        
        # 收集 core 模块覆盖率
        util.run_remote_cmd(ssh_client, f'lcov --capture --directory {kernel_base_dir}/core --output-file /tmp/coverage/kernel_core.info --ignore-errors source,gcov')
        
        # 收集 rxe 模块覆盖率
        util.run_remote_cmd(ssh_client, f'lcov --capture --directory {kernel_base_dir}/sw/rxe --output-file /tmp/coverage/kernel_rxe.info --ignore-errors source,gcov')
        
        # 收集 mlx5 模块覆盖率
        util.run_remote_cmd(ssh_client, f'lcov --capture --directory {kernel_base_dir}/hw/mlx5 --output-file /tmp/coverage/kernel_mlx5.info --ignore-errors source,gcov')
        
        # 合并所有内核覆盖率文件
        util.run_remote_cmd(ssh_client, 'lcov --add-tracefile /tmp/coverage/kernel_core.info --add-tracefile /tmp/coverage/kernel_rxe.info --add-tracefile /tmp/coverage/kernel_mlx5.info --output-file /home/kernel_coverage.info')
        
        if not util.ssh_retry_until_file_exist(ssh_client, "/home/kernel_coverage.info"):
            return False

        print("[STEP 2] Generating Kernel HTML Report")
        if not util.run_remote_cmd(ssh_client, 'genhtml /home/kernel_coverage.info --output-directory /tmp/coverage/kernel_html_report --ignore-errors source,empty'):
            return False
        if not util.ssh_retry_until_file_exist(ssh_client, "/tmp/coverage/kernel_html_report"):
            return False

        print("[STEP 3] Downloading Kernel Report via SCP")
        if not util.scp_download_directory(ssh_client, "/tmp/coverage/kernel_html_report", "templates/kernel"):
            return False

        print("[STEP 4] Collecting User GCOV with LCOV")
        # 使用 lcov 收集用户态覆盖率 - 只收集 libibverbs 和 librdmacm
        user_build_dir = '/home/rdma-core-master/build'
        
        # 收集 libibverbs 覆盖率
        util.run_remote_cmd(ssh_client, f'lcov --capture --directory {user_build_dir}/libibverbs/CMakeFiles/ibverbs.dir --output-file /tmp/coverage/user_ibverbs.info --ignore-errors source,gcov')
        
        # 收集 librdmacm 覆盖率
        util.run_remote_cmd(ssh_client, f'lcov --capture --directory {user_build_dir}/librdmacm/CMakeFiles/rdmacm.dir --output-file /tmp/coverage/user_rdmacm.info --ignore-errors source,gcov')
        
        # 合并两个用户态覆盖率文件
        util.run_remote_cmd(ssh_client, 'lcov --add-tracefile /tmp/coverage/user_ibverbs.info --add-tracefile /tmp/coverage/user_rdmacm.info --output-file /tmp/coverage/user_combined.info')
        
        # 排除不需要的文件：build/include, tests, examples 等
        util.run_remote_cmd(ssh_client, f'lcov --remove /tmp/coverage/user_combined.info "{user_build_dir}/include/*" "*/tests/*" "*/test/*" "*/examples/*" --output-file /home/user_coverage.info --ignore-errors unused')
        
        if not util.ssh_retry_until_file_exist(ssh_client, "/home/user_coverage.info"):
            return False

        print("[STEP 5] Generating User HTML Report")
        if not util.run_remote_cmd(ssh_client, 'genhtml /home/user_coverage.info --output-directory /tmp/coverage/user_html_report --ignore-errors source,empty'):
            return False
        if not util.ssh_retry_until_file_exist(ssh_client, "/tmp/coverage/user_html_report"):
            return False

        print("[STEP 6] Downloading User Report via SCP")
        if not util.scp_download_directory(ssh_client, "/tmp/coverage/user_html_report", "templates/user"):
            return False

        if not util.retry_until_file_exist("templates/kernel/index.html"):
            return False
        if not util.retry_until_file_exist("templates/user/index.html"):
            return False


        print("[STEP 7] Removing Remote Temp Files")
        if not util.run_remote_cmd(ssh_client, 'rm -rf /tmp/coverage /home/kernel_coverage.info /home/user_coverage.info'):
            return False

        print("[INFO] refresh_gcov finished successfully")
        return True

    except Exception as e:
        print(f"[EXCEPTION] Unexpected error in refresh_gcov: {e}")
        return False