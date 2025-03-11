#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import multiprocessing
import sys
import mfcommon

NO_PROMPT_ARG = "--no-prompt"
ACCESS_KEY_ARG = "--aws-access-key-id"
ACCESS_SECRET_KEY_ARG = "--aws-secret-access-key"
ACCESS_SESSION_TOKEN_ARG = "--aws-session-token"
INSTALL_SCRIPT_PATH = "./aws-replication-installer-init.py"

if not sys.warnoptions:
    import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=Warning)
    import paramiko


def install_wget(host, username, key_pwd, using_key, final_output):
    ssh = None
    try:
        # Find the distribution
        distribution = mfcommon.find_distribution(host, username, key_pwd, using_key)
        final_output['messages'].append("***** Installing wget *****")
        ssh, _ = mfcommon.open_ssh(host, username, key_pwd, using_key)
        if distribution == "ubuntu":
            ssh.exec_command("sudo apt-get update")  # nosec B601
            stdin, _, stderr = ssh.exec_command(  # nosec B601
                "sudo DEBIAN_FRONTEND=noninteractive apt-get install wget")
        elif distribution == "suse":
            stdin, _, stderr = ssh.exec_command("sudo zypper install wget")  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        else:
            # This condition works with centos, fedora and RHEL distributions
            # ssh.exec_command("sudo yum update")
            stdin, _, stderr = ssh.exec_command("sudo yum install wget -y")  # nosec B601
        # Check if there is any error while installing wget
        error = ''
        for line in stderr.readlines():
            error = error + line
        if not error:
            final_output['messages'].append("wget got installed successfully")
            # Execute the command wget and check if it got configured correctly
            stdin, _, stderr = ssh.exec_command("wget")  # nosec B601
            error = ''
            for line in stderr.readlines():
                error = error + line
            if "not found" in error or "command-not-found" in error:
                final_output['messages'].append("wget is not recognized, unable to proceed! due to " + error)
        else:
            final_output['messages'].append("something went wrong while installing wget " + error)
    finally:
        if ssh is not None:
            ssh.close()


def check_python(host, username, key_pwd, using_key):
    _, error = mfcommon.execute_cmd_via_ssh(host, username, key_pwd, "python --version",
                                                 using_key)
    if error:
        if "Python 2" in error:
            return True
        else:
            return False
    else:
        return True


def check_python3(host, username, key_pwd, using_key):
    _, error = mfcommon.execute_cmd_via_ssh(host, username, key_pwd, "python3 --version",
                                                 using_key)
    if error:
        if "Python 3" in error:
            return True
        else:
            return False
    else:
        return True


def install_python3(host, username, key_pwd, using_key, final_output):
    ssh = None
    try:
        final_output['messages'].append("***** Installing python3 *****")
        ssh, _ = mfcommon.open_ssh(host, username, key_pwd, using_key)
        # Find the distribution
        distribution = mfcommon.find_distribution(host, username, key_pwd, using_key)
        if distribution == "ubuntu":
            ssh.exec_command("sudo apt-get update")  # nosec B601
            command = "sudo DEBIAN_FRONTEND=noninteractive apt-get install " \
                      "python3"
            stdin, _, stderr = ssh.exec_command(command)  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        elif distribution == 'suse':
            stdin, _, stderr = ssh.exec_command("sudo zypper install python3")  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        elif distribution == "fedora":
            stdin, _, stderr = ssh.exec_command("sudo dnf install python3")  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        else:  # This installs on centos
            # ssh.exec_command("sudo yum update")  # nosec B601
            ssh.exec_command("sudo yum install centos-release-scl")  # nosec B601
            ssh.exec_command("sudo yum install rh-python36")  # nosec B601
            ssh.exec_command("scl enable rh-python36 bash")  # nosec B601
            stdin, _, stderr = ssh.exec_command("python --version")  # nosec B601
        error = ''
        for line in stderr.readlines():
            error = error + line
        if not error:
            final_output['messages'].append("python was installed successfully.")
            return True
        else:
            final_output['messages'].append(error)
            return False
    finally:
        if ssh is not None:
            ssh.close()


def get_python_executable(host, username, key_pwd, using_key, final_output):
    python_str = "python"
    python_str_3 = "python3"

    if check_python(host, username, key_pwd, using_key):
        return python_str
    elif check_python3(host, username, key_pwd, using_key):
        return python_str_3
    else:
        if install_python3(host, username, key_pwd, using_key, final_output):
            return python_str_3
        else:
            return None


def get_installation_command(python_executable, session_token, region, aws_access_key,
                             aws_secret_access_key, s3_endpoint, mgn_endpoint):
    if session_token:
        command = f"sudo {python_executable} {INSTALL_SCRIPT_PATH} --region {region}" + \
                  f" {ACCESS_KEY_ARG}  {aws_access_key}" + \
                  f" {ACCESS_SECRET_KEY_ARG} {aws_secret_access_key}" + \
                  f" {ACCESS_SESSION_TOKEN_ARG} {session_token}" + \
                  f" {NO_PROMPT_ARG}"
        display_command = f"sudo {python_executable} {INSTALL_SCRIPT_PATH} --region {region}" + \
                          f" {ACCESS_KEY_ARG}  {aws_access_key}" + \
                          f" {ACCESS_SECRET_KEY_ARG} *****" + \
                          f" {ACCESS_SESSION_TOKEN_ARG} *****" + \
                          f" {NO_PROMPT_ARG}"
    else:
        command = f"sudo {python_executable} {INSTALL_SCRIPT_PATH} --region {region}" + \
                  f" {ACCESS_KEY_ARG}  {aws_access_key}" + \
                  f" {ACCESS_SECRET_KEY_ARG} {aws_secret_access_key}" + \
                  f" {NO_PROMPT_ARG}"
        display_command = f"sudo {python_executable} {INSTALL_SCRIPT_PATH} --region {region}" + \
                          f" {ACCESS_KEY_ARG}  {aws_access_key}" + \
                          f" {ACCESS_SECRET_KEY_ARG} *****" + \
                          f" {NO_PROMPT_ARG}"
    # Add s3 endpoint if specified in parameters.
    if s3_endpoint:
        command += f" --s3-endpoint {s3_endpoint}"
        display_command += f" --s3-endpoint {s3_endpoint}"

    # Add mgn endpoint if specified in parameters.
    if mgn_endpoint:
        command += f" --endpoint {mgn_endpoint}"
        display_command += f" --endpoint {mgn_endpoint}"

    return command, display_command


def add_additional_parameters(s3_endpoint=None, mgn_endpoint=None, no_replication=False, replication_devices=None):
    command = ''
    display_command = ''
    # Add s3 endpoint if specified in parameters.
    if s3_endpoint:
        command += " --s3-endpoint " + s3_endpoint
        display_command += " --s3-endpoint " + s3_endpoint

    # Add mgn endpoint if specified in parameters.
    if mgn_endpoint:
        command += " --endpoint " + mgn_endpoint
        display_command += " --endpoint " + mgn_endpoint

    # If replication devices specified in parameters use these
    if replication_devices:
        command += f' --devices="{replication_devices}"'
        display_command += f' --devices="{replication_devices}"'

    # if no replication is set then set.
    if no_replication:
        command += ' --no-replication'
        display_command += ' --no-replication'

    return command, display_command


def install_mgn(agent_linux_download_url, region, host, username, key_pwd, using_key,
                aws_access_key, aws_secret_access_key, session_token=None, s3_endpoint=None, mgn_endpoint=None,
                download_attempts=3, wget_timeout=10, no_replication=False, replication_devices=None):
    final_output = {'messages': []}
    pid = multiprocessing.current_process()
    final_output['pid'] = str(pid)
    final_output['host'] = host
    final_output['messages'].append("Installing Application Migration Service Agent on:  " + host)

    output = None
    error = None

    try:
        command = f"wget --timeout={wget_timeout} --tries={download_attempts} -O {INSTALL_SCRIPT_PATH}" \
                  f" {agent_linux_download_url}"
        if s3_endpoint:
            # S3 Endpoints use certificates based on the parent S3 domain excluding the vpc endpoint name, this means
            # the certificate name and the dns name used do not match and causes errors in verification of cert auth
            # we disable wget checks for cert auth when using s3 endpoints only.
            command += "  --no-check-certificate"
        output, error = mfcommon.execute_cmd_via_ssh(host=host, username=username, key=key_pwd,
                                                     cmd=command, using_key=using_key)
        final_output['messages'].append(output)
        final_output['messages'].append(error)
        if "not found" in error or "No such file or directory" in error:
            install_wget(host, username, key_pwd, using_key, final_output)
            output, error = mfcommon.execute_cmd_via_ssh(host=host, username=username, key=key_pwd,
                                                         cmd=command, using_key=using_key)
            final_output['messages'].append(output)

        if "failed" in error:
            raise RuntimeError("An error occurred when attempting to download agent installer to server.")

        # Check if python is already installed if not install python3
        python_executable = get_python_executable(host, username, key_pwd, using_key, final_output)
        if not python_executable:
            # Python not found and install failed.
            final_output['return_code'] = 1
            return final_output

        # Step 2 - execute linux installer
        if session_token:
            command = f"sudo {python_executable} {INSTALL_SCRIPT_PATH} --region {region}" + \
                      f" {ACCESS_KEY_ARG}  {aws_access_key}" + \
                      f" {ACCESS_SECRET_KEY_ARG} {aws_secret_access_key}" + \
                      f" {ACCESS_SESSION_TOKEN_ARG} {session_token}" + \
                      f" {NO_PROMPT_ARG}"
            display_command = f"sudo {python_executable} {INSTALL_SCRIPT_PATH} --region {region}" + \
                              f" {ACCESS_KEY_ARG}  {aws_access_key}" + \
                              f" {ACCESS_SECRET_KEY_ARG} *****" + \
                              f" {ACCESS_SESSION_TOKEN_ARG} *****" + \
                              f" {NO_PROMPT_ARG}"
        else:
            command = f"sudo {python_executable} {INSTALL_SCRIPT_PATH} --region {region}" + \
                      f" {ACCESS_KEY_ARG}  {aws_access_key}" + \
                      f" {ACCESS_SECRET_KEY_ARG} {aws_secret_access_key}" + \
                      f" {NO_PROMPT_ARG}"
            display_command = f"sudo {python_executable} {INSTALL_SCRIPT_PATH} --region {region}" + \
                              f" {ACCESS_KEY_ARG}  {aws_access_key}" + \
                              f" {ACCESS_SECRET_KEY_ARG} *****" + \
                              f" {NO_PROMPT_ARG}"


        additional_params_command, additional_params_command_display = add_additional_parameters(
            s3_endpoint,mgn_endpoint,no_replication, replication_devices
        )

        command += additional_params_command
        display_command += additional_params_command_display

        final_output['messages'].append("Executing " + display_command)

        output, error = mfcommon.execute_cmd_via_ssh(host=host, username=username, key=key_pwd,
                                                     cmd=command, using_key=using_key)
        final_output['messages'].append(output)
    except Exception as e:
        error = 'Exception occurred! ' + str(e)
    if not error and 'Installation failed' not in output and 'Error details:' not in output:
        final_output['messages'].append("***** Agent installation completed successfully on " + host + "*****")
        final_output['return_code'] = 0
        return final_output
    else:
        final_output['messages'].append("Error: Installation Failed. Unable to install Agent on " + host + " due to: ")
        if output:
            final_output['messages'].append(output)
        final_output['messages'].append(error)
        final_output['return_code'] = 1
        return final_output
