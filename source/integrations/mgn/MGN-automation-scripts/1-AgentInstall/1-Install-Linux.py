#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################
import multiprocessing
import sys
import mfcommon

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
        ssh = mfcommon.open_ssh(host, username, key_pwd, using_key)
        if distribution == "ubuntu":
            ssh.exec_command("sudo apt-get update")  # nosec B601
            stdin, stdout, stderr = ssh.exec_command(  # nosec B601
                "sudo DEBIAN_FRONTEND=noninteractive apt-get install wget")
        elif distribution == "suse":
            stdin, stdout, stderr = ssh.exec_command("sudo zypper install wget")  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        else:
            # This condition works with centos, fedora and RHEL distributions
            # ssh.exec_command("sudo yum update")
            stdin, stdout, stderr = ssh.exec_command("sudo yum install wget -y")  # nosec B601
        # Check if there is any error while installing wget
        error = ''
        for line in stderr.readlines():
            error = error + line
        if not error:
            final_output['messages'].append("wget got installed successfully")
            # Execute the command wget and check if it got configured correctly
            stdin, stdout, stderr = ssh.exec_command("wget")  # nosec B601
            error = ''
            for line in stderr.readlines():
                error = error + line
            if "not found" in error or "command-not-found" in error:
                final_output['messages'].append("wget is not recognized, unable to proceed! due to " + error)
        else:
            final_output['messages'].append("something went wrong while installing wget ", error)
    finally:
        if ssh is not None:
            ssh.close()


def check_python(host, username, key_pwd, using_key):
    output, error = mfcommon.execute_cmd_via_ssh(host, username, key_pwd, "python --version",
                                                 using_key)
    if error:
        if "Python 2" in error:
            return True
        else:
            return False
    else:
        return True


def check_python3(host, username, key_pwd, using_key):
    output, error = mfcommon.execute_cmd_via_ssh(host, username, key_pwd, "python3 --version",
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
        ssh = mfcommon.open_ssh(host, username, key_pwd, using_key)
        # Find the distribution
        distribution = mfcommon.find_distribution(host, username, key_pwd, using_key)
        if distribution == "ubuntu":
            ssh.exec_command("sudo apt-get update")  # nosec B601
            command = "sudo DEBIAN_FRONTEND=noninteractive apt-get install " \
                      "python3"
            stdin, stdout, stderr = ssh.exec_command(command)  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        elif distribution == 'suse':
            stdin, stdout, stderr = ssh.exec_command("sudo zypper install python3")  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        elif distribution == "fedora":
            stdin, stdout, stderr = ssh.exec_command("sudo dnf install python3")  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        else:  # This installs on centos
            # ssh.exec_command("sudo yum update")  # nosec B601
            ssh.exec_command("sudo yum install centos-release-scl")  # nosec B601
            ssh.exec_command("sudo yum install rh-python36")  # nosec B601
            ssh.exec_command("scl enable rh-python36 bash")  # nosec B601
            stdin, stdout, stderr = ssh.exec_command("python --version")  # nosec B601
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


def install_mgn(agent_linux_download_url, region, host, username, key_pwd, using_key,
                aws_access_key, aws_secret_access_key, session_token=None, s3_endpoint=None, mgn_endpoint=None):
    final_output = {'messages': []}
    pid = multiprocessing.current_process()
    final_output['pid'] = str(pid)
    final_output['host'] = host
    final_output['messages'].append("Installing Application Migration Service Agent on:  " + host)

    output = None
    error = None

    try:
        command = "wget -O ./aws-replication-installer-init.py " + agent_linux_download_url
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
            install_wget(host, username, key_pwd, using_key)
            output, error = mfcommon.execute_cmd_via_ssh(host=host, username=username, key=key_pwd,
                                                         cmd=command, using_key=using_key)
            final_output['messages'].append(output)
        # Check if python is already installed if not install python3
        python_str = "python"
        if not check_python(host, username, key_pwd, using_key):
            if not check_python3(host, username, key_pwd, using_key):
                if not install_python3(host, username, key_pwd, using_key):
                    # Python installation failed cancel agent installation.
                    final_output['return_code'] = 1
                    return final_output
                python_str = "python3"
            else:
                python_str = "python3"
        # Step 2 - execute linux installer
        if session_token:
            command = "sudo " + python_str + " ./aws-replication-installer-init.py --region " + region + \
                      " --aws-access-key-id " + aws_access_key + \
                      " --aws-secret-access-key " + aws_secret_access_key + \
                      " --aws-session-token " + session_token + \
                      " --no-prompt"
            display_command = "sudo " + python_str + " ./aws-replication-installer-init.py --region " + region + \
                              " --aws-access-key-id " + aws_access_key + \
                              " --aws-secret-access-key *****" + \
                              " --aws-session-token *****" + \
                              " --no-prompt"
        else:
            command = "sudo " + python_str + " ./aws-replication-installer-init.py --region " + region + \
                      " --aws-access-key-id " + aws_access_key + \
                      " --aws-secret-access-key " + aws_secret_access_key + \
                      " --no-prompt"
            display_command = "sudo " + python_str + " ./aws-replication-installer-init.py --region " + region + \
                              " --aws-access-key-id " + aws_access_key + \
                              " --aws-secret-access-key *****" + \
                              " --no-prompt"
        # Add s3 endpoint if specified in parameters.
        if s3_endpoint:
            command += " --s3-endpoint " + s3_endpoint
            display_command += " --s3-endpoint " + s3_endpoint

        # Add mgn endpoint if specified in parameters.
        if mgn_endpoint:
            command += " --endpoint " + mgn_endpoint
            display_command += " --endpoint " + mgn_endpoint

        final_output['messages'].append("Executing " + display_command)

        output, error = mfcommon.execute_cmd_via_ssh(host=host, username=username, key=key_pwd,
                                                     cmd=command, using_key=using_key)
        final_output['messages'].append(output)
    except Exception as e:
        error = 'Got exception! ' + str(e)
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
