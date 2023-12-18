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

# Version: 1SEP2023.00

from __future__ import print_function
import sys
import argparse
import json
import subprocess

if not sys.warnoptions:
    import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=Warning)
    import paramiko
import mfcommon
import threading
import os

from queue import Queue

MSG_SSH_SOURCE = 'SSH 22 to source server'
MSG_SSH_UNABLE_TO_CONNECT = 'Unable to connect! SSH is null'
MSG_SUDO_PERMISSION = 'SUDO permission'

OUTPUT_ERROR_KEY = 'final_result'


def is_winrm_accessible(s_result, winrm_use_ssl=False):
    messages = []

    command_wsman = "Test-WSMan -ComputerName " + s_result["server_name"]
    if winrm_use_ssl:
        command_wsman += " -UseSSL"

    p_wsman = subprocess.Popen(["powershell.exe", command_wsman], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in p_wsman.stdout.readlines():
        messages.append(line)

    for line in p_wsman.stderr.readlines():
        messages.append(line)
    retval = p_wsman.wait()
    p_wsman.communicate()

    for message in messages:
        # Ignore certificate errors if present.
        if 'unknown certificate authority' in str(message):
            retval = 0

    if retval != 0:
        s_result['test_results'].append({'test': "WinRM Accessible", 'result': "Fail", 'error': messages})
        s_result['success'] = False
        return False
    else:
        s_result['test_results'].append({'test': "WinRM Accessible", 'result': "Pass"})
        s_result['success'] = True
        return True


def check_windows(parameters):
    mgn_endpoint = parameters["MGNEndpoint"]
    s3_endpoint = parameters["S3Endpoint"]
    s = parameters["s"]
    mgn_server_ip = parameters["MGNServerIP"]
    domain_user = parameters["user_name"]
    domain_password = parameters["windows_password"]
    secret_name = parameters["secret_name"]
    no_user_prompts = parameters["no_user_prompts"]

    windows_fail = False
    print("")

    s_result = {
        "server_id": s["server_id"],
        "server_name": s["server_fqdn"],
        "test_results": [],
        "success": True
    }

    if not is_winrm_accessible(s_result, parameters["winrm_use_ssl"]):
        s_result['success'] = False
        windows_fail = True
        return s_result, windows_fail

    credentials = mfcommon.get_server_credentials(
        domain_user, domain_password, s, secret_name, no_user_prompts)

    command = "Invoke-Command -ComputerName " + s["server_fqdn"] + \
              " -FilePath 0-Prerequisites-Windows.ps1 -ArgumentList " + \
              mgn_server_ip + "," + mgn_endpoint + "," + s3_endpoint
    if credentials['username'] != "":
        if "\\" not in credentials['username'] and "@" not in credentials['username']:
            # Assume local account provided, prepend server name to user ID.
            server_name_only = s["server_fqdn"].split(".")[0]
            credentials['username'] = server_name_only + "\\" + credentials['username']
            # logger.debug("INFO: Using local account to connect: " + credentials['username'])
        else:
            print("INFO: Using domain account to connect: " + credentials['username'])
        command += " -Credential (New-Object System.Management.Automation.PSCredential('" + credentials[
            'username'] + "', (ConvertTo-SecureString '" + credentials['password'] + "' -AsPlainText -Force)))"
    p = subprocess.Popen(["powershell.exe", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = p.communicate()
    if output != "":
        returnlist = output.decode('utf8').split("\n")
        for r in returnlist:
            if r.strip() != "":
                result = r.split(":")

                if "Pass" not in result[1]:
                    s_result['test_results'].append(
                        {
                            'test': result[0],
                            'result': result[1],
                            'error': result[2].replace("\r", "")
                        }
                    )
                    s_result['success'] = False
                    windows_fail = True
                else:
                    s_result['test_results'].append({'test': result[0], 'result': result[1].replace("\r", "")})

    if len(error) > 0:
        s_result['test_results'].append({'test': "Powershell test script", 'result': error})
        s_result['success'] = False
        windows_fail = True

    return s_result, windows_fail


def check_ssh_connectivity(ip, user_name, pass_key, is_key, s_result):
    ssh, error = mfcommon.open_ssh(ip, user_name, pass_key, is_key)
    if ssh is None or len(error) > 0:
        s_result['test_results'].append({'test': MSG_SSH_SOURCE, 'result': "Fail", 'error': error})
        s_result['success'] = False
        return None
    else:
        s_result['test_results'].append({'test': MSG_SSH_SOURCE, 'result': "Pass"})
        return ssh


def check_sudo_permissions(ssh, s_result):
    stderr = None
    ssh_err = ''
    if ssh is not None:
        try:
            _, _, stderr = ssh.exec_command("sudo -n -l")  # nosec B601
        except paramiko.SSHException as e:
            s_result['test_results'].append(
                {'test': MSG_SUDO_PERMISSION, 'result': "Fail", 'error': str(e)}
            )
            s_result['success'] = False
            return
    else:
        s_result['test_results'].append(
            {'test': MSG_SUDO_PERMISSION, 'result': "Fail", 'error': MSG_SSH_UNABLE_TO_CONNECT}
        )
        s_result['success'] = False
        return

    if stderr:
        for err in stderr.readlines():
            ssh_err = ssh_err + err
    if 'password is required' in ssh_err:
        s_result['test_results'].append({'test': MSG_SUDO_PERMISSION, 'result': "Fail", 'error': 'password is required'})
        s_result['success'] = False
    else:
        s_result['test_results'].append({'test': MSG_SUDO_PERMISSION, 'result': "Pass"})


def check_tcp_connectivity(ssh, host, port, s_result, friendly_name=None):
    if friendly_name:
        check = "%s-%s" % (friendly_name, str(port))
    else:
        if port == '1500':
            check = " TCP 1500 to MGN Rep Server"
        elif port == '443':
            check = " TCP 443 to Endpoint"
        else:
            check = " TCP " + str(port)

    if ssh is not None:
        cmd = "sudo timeout 2 bash -c '</dev/tcp/" + host + "/" + port + " && echo port is open || echo port is closed' || echo connection timeout"
        try:
            _, stdout, stderr = ssh.exec_command(cmd)  # nosec B601
            str_output = ''
            for output in stdout.readlines():
                str_output = str_output + output

            str_stderr = ''
            for err in stderr.readlines():
                str_stderr = str_stderr + err

            if len(str_output) > 0:
                str_output = str_output.strip()
                if "open" in str(str_output):
                    s_result['test_results'].append({'test': check, 'result': "Pass"})
                else:
                    s_result['test_results'].append({'test': check, 'result': "Fail", 'error': str_output})
                    s_result['success'] = False
                    return
            else:
                s_result['test_results'].append({'test': check, 'result': "Pass"})
                s_result['success'] = False

            if len(str_stderr) > 0:
                if "refused" in str_stderr:
                    s_result['test_results'].append({'test': check, 'result': "Pass"})
                else:
                    s_result['test_results'].append({'test': check, 'result': "Fail", 'error': str_stderr})
                    s_result['success'] = False

        except paramiko.SSHException as e:
            ssh_err = f"Got exception! while executing the command {cmd}  due to {str(e)}"
            s_result['test_results'].append({'test': check, 'result': "Fail", 'error': ssh_err})
            s_result['success'] = False
    else:
        s_result['test_results'].append({'test': check, 'result': "Fail", 'error': MSG_SSH_UNABLE_TO_CONNECT})
        s_result['success'] = False


def check_freespace(ssh, dir, min, s_result):
    stderr = None
    stdout = None
    ssh_err = ''
    if ssh is not None:
        cmd = "df -h " + dir + " | tail -1 | tr -s ' ' | cut -d' ' -f4"
        try:
            _, stdout, stderr = ssh.exec_command(cmd)  # nosec B601
            str_output = ''
            for output in stdout.readlines():
                str_output = str_output + output
            value = 0
            if len(str_output) > 0:
                str_output = str_output.strip()
                try:
                    if str_output[-1].lower() == 'g':
                        value = float(str_output[:-1])
                    else:
                        value = float(str_output)
                except ValueError as ve:
                    ssh_err = "Got exception! for the command " + cmd + \
                              ". The output is " + str(ve)
            if value <= min:
                ssh_err = dir + " directory should have a minimum of " + str(
                    min) + " GB free space, but got " + str(value)
        except paramiko.SSHException as e:
            ssh_err = f"Got exception! while executing the command {cmd}  due to {str(e)}"
    else:
        ssh_err = MSG_SSH_UNABLE_TO_CONNECT

    if stderr:
        for err in stderr.readlines():
            ssh_err = ssh_err + err

    check = str(min) + " GB " + dir + " FreeSpace"
    if len(ssh_err) > 0:
        s_result['test_results'].append({'test': check, 'result': "Fail", 'error': ssh_err})
        s_result['success'] = False
    else:
        s_result['test_results'].append({'test': check, 'result': "Pass"})


def check_dhclient(ssh, s_result):
    stderr = None
    ssh_err = ''
    check = "DHCLIENT Package"
    if ssh is not None:
        try:
            _, _, stderr = ssh.exec_command("sudo dhclient -v")  # nosec B601
        except paramiko.SSHException as e:
            s_result['test_results'].append(
                {'test': check, 'result': "Fail", 'error': str(e)}
            )
            s_result['success'] = False
            return
    else:
        s_result['test_results'].append(
            {'test': check, 'result': "Fail", 'error': MSG_SSH_UNABLE_TO_CONNECT}
        )
        s_result['success'] = False
        return

    if stderr:
        for err in stderr.readlines():
            ssh_err = ssh_err + err
    if len(ssh_err) > 0 and 'not found' in ssh_err:
        s_result['test_results'].append({'test': check, 'result': "Fail", 'error': ssh_err})
        s_result['success'] = False
    else:
        s_result['test_results'].append({'test': check, 'result': "Pass", 'error': ssh_err})


def check_linux(parameters):
    mgn_endpoint = parameters["MGNEndpoint"]
    s3_endpoint = parameters["S3Endpoint"]
    mgn_server_ip = parameters["MGNServerIP"]
    user_name = parameters["user_name"]
    pass_key = parameters["pass_key"]
    s = parameters["s"]
    secret_name = parameters["secret_name"]
    no_user_prompts = parameters["no_user_prompts"]

    linux_fail = False

    s_result = {
        "server_id": s["server_id"],
        "server_name": s["server_fqdn"],
        "test_results": [],
        "success": True
    }

    credentials = mfcommon.get_server_credentials(
        user_name, pass_key, s, secret_name, no_user_prompts)

    # This checks network connectivity, if we can SSH to the source machine
    ssh = check_ssh_connectivity(s["server_fqdn"], credentials['username'], credentials['password'],
                                 credentials['private_key'], s_result)
    if OUTPUT_ERROR_KEY not in s_result:
        # Check if the given user has sudo permissions
        check_sudo_permissions(ssh, s_result)
        if OUTPUT_ERROR_KEY not in s_result:
            # Check if user is able to access Internet and
            # connect to MGN Service Endpoint, or private endpoint
            check_tcp_connectivity(ssh, mgn_endpoint, '443', s_result, "MGNEndpoint")

            # Check if user is able to access Internet and
            # connect to S3 Endpoint, or private endpoint
            check_tcp_connectivity(ssh, s3_endpoint, '443', s_result, "S3Endpoint")

            # Check if user is able to connect to TCP 1500
            # for a specific IP (user provide IP address)
            check_tcp_connectivity(ssh, mgn_server_ip, '1500', s_result)

            # Check if root directory have more than 3GB free space
            check_freespace(ssh, '/', 2.0, s_result)

            # Check if /tmp directory have more than 500MB free space
            check_freespace(ssh, '/tmp', 0.5, s_result)  # //NOSONAR nosec B108

            # Check if dhclient package is installed.
            check_dhclient(ssh, s_result)
    if not s_result['success']:
        linux_fail = True
    # Closing ssh connection
    if ssh is not None:
        ssh.close()
        ssh = None
    if OUTPUT_ERROR_KEY in s_result:
        final_result = s_result[OUTPUT_ERROR_KEY]
        if len(final_result) > 1 and final_result[-1] == ',':
            final_result = final_result[:-1]
            s_result[OUTPUT_ERROR_KEY] = final_result
            linux_fail = True

    if os.path.isfile(credentials['password']):
        os.remove(credentials['password'])
    return s_result, linux_fail


def print_results(label, results, token, status):
    # Print all the execution output to the console
    for result in results:
        print("")
        print("---------------------------------------------------------")
        print("-- " + label + " Server result for " + result['server_name'] + " --")
        print("---------------------------------------------------------")
        print("")
        if result['success']:
            output = "ALL TESTS PASSED"
        else:
            output = "SOME TESTS FAILED"

        for test_result in result['test_results']:
            if test_result['result'] == 'Fail':
                output += f"\n [x] {test_result['test']}: {test_result['result']}"
            else:
                output += f"\n{test_result['test']}: {test_result['result']}"
        print(output, flush=True)

    print("")
    print("")
    print("")
    print("------------------------------------------------------------")
    print("-- " + label + " server passed all Pre-requisites checks --")
    print("------------------------------------------------------------")
    is_empty = 0
    for result in results:
        if result['success']:
            print("     " + result['server_name'])
            mfcommon.update_server_migration_status(
                token,
                result['server_id'],
                "Pre-requisites check : Passed"
            )
        else:
            is_empty = is_empty + 1
    if len(results) == is_empty:
        print(" [x]   No servers passed all checks.")
    print("", flush=True)

    if status:
        print("")
        print("-------------------------------------------------------------")
        print("-- " + label + " servers failed one or more pre-requisites checks --")
        print("-------------------------------------------------------------")
        print("", flush=True)
        for result in results:
            if not result['success']:
                failure_output = [
                    f"{test_result['test']}: {test_result['error']}"
                    for test_result in result['test_results']
                    if test_result['result'] == 'Fail'
                ]

                print(f"     {result['server_name']} : Pre-requisites checks : Failed - {failure_output}")

                mfcommon.update_server_migration_status(
                    token,
                    result['server_id'],
                    f"Pre-requisites checks : Failed - {failure_output}"
                )

    print("", flush=True)


def parse_boolean(value):
    value = value.lower()

    if value in ["true", "yes", "y", "1", "t"]:
        return True
    elif value in ["false", "no", "n", "0", "f"]:
        return False

    return False


def parse_arguments(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--ReplicationServerIP', required=True)
    # Removed as new credentials function deals with this parser.add_argument('--WindowsUser', default="")
    parser.add_argument('--NoPrompts', default=False, type=parse_boolean,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretWindows', default=None)
    parser.add_argument('--SecretLinux', default=None)
    parser.add_argument('--S3Endpoint', default=None)
    parser.add_argument('--MGNEndpoint', default=None)
    parser.add_argument('--UseSSL', default=False, type=parse_boolean)
    # parser.add_argument('--Verbose', default=False, type=bool, help='For detailed logging, use True')
    args = parser.parse_args(arguments)
    return args


def get_install_endpoint_parameters(account, args):
    parameters = {}
    if args.MGNEndpoint:
        parameters["MGNEndpoint"] = args.MGNEndpoint
    else:
        parameters["MGNEndpoint"] = "mgn.{}.amazonaws.com".format(account['aws_region'])
    if args.S3Endpoint:
        parameters["S3Endpoint"] = args.S3Endpoint
    else:
        parameters["S3Endpoint"] = "aws-application-migration-service-{}.s3.amazonaws.com" \
            .format(account['aws_region'])

    return parameters


def main(args):

    print("")
    print("Login to Migration factory")
    print("", flush=True)
    token = mfcommon.factory_login()

    print("****************************")
    print("*** Getting Server List ****")
    print("****************************")
    print("", flush=True)
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(
        args.Waveid, token, os_split=True, rtype='Rehost'
    )
    user_name = ''
    pass_key = ''
    key_exist = False

    windows_results = []
    linux_results = []
    windows_status_failed = False
    linux_status_failed = False
    windows_fail = False
    linux_fail = False

    if windows_exist:
        print("")
        print("*********************************************")
        print("*Checking Pre-requisites for Windows servers*")
        print("*********************************************")
        print("", flush=True)

        thread_list = list()
        que = Queue()

        for account in get_servers:
            if len(account["servers_windows"]) > 0:
                # Parameters to be passed to the thread
                parameters = get_install_endpoint_parameters(account, args)
                parameters["servers_windows"] = account["servers_windows"]
                parameters["MGNServerIP"] = args.ReplicationServerIP
                parameters["user_name"] = ""
                parameters["windows_password"] = ""
                parameters["secret_name"] = args.SecretWindows
                parameters["no_user_prompts"] = args.NoPrompts
                parameters["winrm_use_ssl"] = args.UseSSL

                mfcommon.add_windows_servers_to_trusted_hosts(account["servers_windows"])

                # Creating multiple threads to connect to source servers in parallel
                for s in account["servers_windows"]:
                    parameters["s"] = s
                    x = threading.Thread(target=lambda q, parameters: q.put(check_windows(parameters)),
                                         args=(que, parameters), name=s["server_fqdn"])
                    x.start()
                    thread_list.append(x)

        print("Waiting for all threads to finish...")
        print("", flush=True)
        for thread in thread_list:
            thread.join()

        while not que.empty():
            # Get the results from all the threads and save it in windows_results
            result, windows_fail = que.get()
            windows_results.append(result)

            if windows_fail:
                windows_status_failed = True

    if linux_exist:
        print("")
        print("*Checking Pre-requisites for Linux servers*")
        print("", flush=True)

        count = 0  # For counting number of threads
        thread_list = list()  # for storing the details of each thread
        que = Queue()  # for storing the output messages from each thread

        for account in get_servers:
            if len(account["servers_linux"]) > 0:
                parameters = get_install_endpoint_parameters(account, args)
                parameters["Servers_Linux"] = account["servers_linux"]
                parameters["MGNServerIP"] = args.ReplicationServerIP
                parameters["user_name"] = user_name
                parameters["pass_key"] = pass_key
                parameters["key_exist"] = key_exist
                parameters["secret_name"] = args.SecretLinux
                parameters["no_user_prompts"] = args.NoPrompts

                for s in account["servers_linux"]:
                    parameters["s"] = s
                    x = threading.Thread(target=lambda q, parameters: q.put(check_linux(parameters)),
                                         args=(que, parameters), name=s["server_fqdn"])
                    x.start()
                    count = count + 1
                    thread_list.append(x)

        print("Waiting for all checks to finish...")
        print("", flush=True)
        for thread in thread_list:
            thread.join()

        while not que.empty():
            result, linux_fail = que.get()
            linux_results.append(result)

            if linux_fail:
                linux_status_failed = True

    print("")
    print("********************************************")
    print("***** Final results for all servers *****")
    print("********************************************")
    print("", flush=True)
    if windows_exist:
        print_results("Windows", windows_results, token, windows_status_failed)
    if linux_exist:
        print_results("Linux", linux_results, token, linux_status_failed)

    if linux_fail or windows_fail:
        print("A number of servers failed pre-requisites checks, see logs for details.")
        return 1
    else:
        print("All servers passed pre-requisites checks.")
        return 0


if __name__ == '__main__':
    args = parse_arguments(sys.argv[1:])
    sys.exit(main(args))
