#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import sys
import mfcommon
if not sys.warnoptions:
    import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=Warning)
    import paramiko


def install_wget(host, username, key_pwd, using_key):
    ssh = None
    try:
        # Find the distribution
        distribution = mfcommon.find_distribution(host, username, key_pwd, using_key)
        print("")
        print("***** Installing wget *****")
        ssh, _ = mfcommon.open_ssh(host, username, key_pwd, using_key)
        if distribution == "ubuntu":
            ssh.exec_command("sudo apt-get update")  # nosec B601
            stdin, _, stderr = ssh.exec_command(  # nosec B601
                "sudo DEBIAN_FRONTEND=noninteractive apt-get install wget")  # nosec B601
        elif distribution == "suse":
            stdin, _, stderr = ssh.exec_command("sudo zypper install wget")  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        else:
            # This condition works with centos, fedora and RHEL distributions
            # ssh.exec_command("sudo yum update")  # nosec B601
            stdin, _, stderr = ssh.exec_command("sudo yum install wget -y")  # nosec B601
        # Check if there is any error while installing wget
        error = ''
        for line in stderr.readlines():
            error = error + line
        if not error:
            print("wget got installed successfully")
            # Execute the command wget and check if it got configured correctly
            stdin, _, stderr = ssh.exec_command("wget")  # nosec B601
            error = ''
            for line in stderr.readlines():
                error = error + line
            if "not found" in error or "command-not-found" in error:
                print(
                    "wget is not recognized, unable to proceed! due to " + error)
        else:
            print("something went wrong while installing wget ", error)
    finally:
        if ssh is not None:
            ssh.close()


def install_ads(agent_linux_download_url, region, host, username, key_pwd, using_key, access_key_id, secret_access_key):
    print("")
    print("--------------------------------------------------------------------")
    print("- Installing Application Discovery Service Agent for:  "+ host + " -")
    print("--------------------------------------------------------------------")
    try:
        output = None
        error = None
        # Step 2 - download linux installer
        command = "wget -O ./aws-discovery-agent.tar.gz " + agent_linux_download_url
        output, error = mfcommon.execute_cmd(host=host, username=username, key=key_pwd,
                                cmd=command, using_key=using_key)
        if "not found" in error or "No such file or directory" in error:
            install_wget(host, username, key_pwd, using_key)
            output, error = mfcommon.execute_cmd(host=host, username=username, key=key_pwd,
                                    cmd=command, using_key=using_key)
        # Step 2 - extract linux installer
        command = "tar -xzf aws-discovery-agent.tar.gz"
        display_command = "tar -xzf aws-discovery-agent.tar.gz"
        print("Executing " + display_command)
        output, error = mfcommon.execute_cmd(host=host, username=username, key=key_pwd,
                                cmd=command, using_key=using_key)
        print(output)
        # Step 3 - execute linux installer
        command = "sudo bash install -r " + \
                  region + " -k \"" + access_key_id + "\" -s \"" + secret_access_key + "\""
        display_command = "sudo bash install -r " + \
                          region + " -k " + access_key_id + " -s *************"
        print("Executing " + display_command)
        output, error = mfcommon.execute_cmd(host=host, username=username, key=key_pwd,
                                cmd=command, using_key=using_key)
        print(output)
    except Exception as e:
        error = 'Got exception! ' + str(e)
    if (error == '' or 'Created symlink from' in error) and 'Error: Installation failed' not in output:
        print("***** Agent installation completed successfully on "
              +host+ "*****")
        return True
    else:
        print("Unable to install Agent on "+host+" due to: ")
        print("")
        print(error)
        return False
