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

# Version: 15APR2021.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import subprocess
import paramiko
import socket
import boto3
import botocore.exceptions
import mfcommon

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

def get_factory_servers(waveid, token, UserHOST):
    try:
        linux_exist = False
        windows_exist = False
        auth = {"Authorization": token}
        # Get all Apps and servers from migration factory
        getservers = json.loads(requests.get(UserHOST + serverendpoint, headers=auth).text)
        #print(servers)
        getapps = json.loads(requests.get(UserHOST + appendpoint, headers=auth).text)
        #print(apps)
        servers = sorted(getservers, key = lambda i: i['server_name'])
        apps = sorted(getapps, key = lambda i: i['app_name'])

        # Get Unique target AWS account and region
        aws_accounts = []
        for app in apps:
            if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                if str(app['wave_id']) == str(waveid):
                    if len(str(app['aws_accountid']).strip()) == 12:
                        target_account = {}
                        target_account['aws_accountid'] = str(app['aws_accountid']).strip()
                        target_account['aws_region'] = app['aws_region'].lower().strip()
                        target_account['servers_windows'] = []
                        target_account['servers_linux'] = []
                        if target_account not in aws_accounts:
                            aws_accounts.append(target_account)
                    else:
                        msg = "ERROR: Incorrect AWS Account Id Length for app: " + app['app_name']
                        print(msg)
                        sys.exit()
        if len(aws_accounts) == 0:
            msg = "ERROR: Server list for wave " + waveid + " is empty...."
            print(msg)
            sys.exit()

        # Get server list
        for account in aws_accounts:
            print("### Servers in Target Account: " + account['aws_accountid'] + " , region: " + account['aws_region'] + " ###")
            for app in apps:
                if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                    if str(app['wave_id']) == str(waveid):
                        if str(app['aws_accountid']).strip() == str(account['aws_accountid']):
                            if app['aws_region'].lower().strip() == account['aws_region']:
                                for server in servers:
                                    if 'app_id' in server:
                                        if server['app_id'] == app['app_id']:
                                            # verify server_os_family attribute, only accepts Windows or Linux
                                            if 'server_os_family' in server:
                                                # Verify server_fqdn, this is mandatory attribute
                                                if 'server_fqdn' in server:
                                                    if server['server_os_family'].lower() == 'windows':
                                                        account['servers_windows'].append(server)
                                                    elif server['server_os_family'].lower() == 'linux':
                                                        account['servers_linux'].append(server)
                                                    else:
                                                        print("ERROR: Invalid server_os_family for: " + server['server_name'] + ", please select either Windows or Linux")
                                                        sys.exit()
                                                    print(server['server_fqdn'])
                                                else:
                                                    print("ERROR: server_fqdn for server: " + server['server_name'] + " doesn't exist")
                                                    sys.exit()
                                            else:
                                                print("ERROR: server_os_family does not exist for: " + server['server_name'])
                                                sys.exit()
            print("")
            # Check if the server list is empty for both Windows and Linux
            if len(account['servers_windows']) == 0 and len(account['servers_linux']) == 0:
                msg = "ERROR: Server list for wave " + waveid + " and account: " + account['aws_accountid'] + " region: " + account['aws_region'] + " is empty...."
                print(msg)
                sys.exit()
            if len(account['servers_linux']) > 0:
               linux_exist = True
            if len(account['servers_windows']) > 0:
               windows_exist = True
        return aws_accounts, linux_exist, windows_exist
    except botocore.exceptions.ClientError as error:
        if ":" in str(error):
            err = ''
            msgs = str(error).split(":")[1:]
            for msg in msgs:
                err = err + msg
            msg = "ERROR: " + err
            print(msg)
            sys.exit()
        else:
            msg = "ERROR: " + str(error)
            print(msg)
            sys.exit()

def check_windows(MGNEndpoint, Servers_Windows, MGNServerIP, Domain_User, Domain_Password):
    windows_fail = False
    print("")
    windows_results = []
    for s in Servers_Windows:
        print("---------------------------------------------------------")
        print("-- Windows Server result for " + s['server_name'] + " --")
        print("---------------------------------------------------------")
        print("")
        s_result = {}
        final = ""
        command = "Invoke-Command -ComputerName " + s["server_fqdn"] + " -FilePath 0-Prerequisites-Windows.ps1 -ArgumentList " + MGNServerIP + "," + MGNEndpoint
        if Domain_User != "":
            command += " -Credential (New-Object System.Management.Automation.PSCredential(\"" + Domain_User + "\", (ConvertTo-SecureString \"" + Domain_Password + "\" -AsPlainText -Force)))"
            p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + s["server_fqdn"] + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p = subprocess.Popen(["powershell.exe", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        if output != "":
            returnlist = output.decode('utf8').split("\n")
            for r in returnlist:
                if r.strip() != "":
                    result = r.split(":")
                    s_result[result[0]] = result[1]
                    if "Pass" not in result[1]:
                        windows_fail = True
                        final = final + result[0] + ","
            s_result["final_result"] = final[:-1]
        s_result["server_name"] = s["server_fqdn"]
        s_result["server_id"] = s["server_id"]
        if len(error) > 0:
            s_result["error"] = error
            windows_fail = True
        if 'TCP443' in s_result:
            print(" TCP 443 to MGN Endpoint  : " + s_result['TCP443'])
        if 'TCP1500' in s_result:
            print(" TCP 1500 to Rep Server   : " + s_result['TCP1500'])
        if 'FreeSpace' in s_result:
            print(" 2GB C:\ Free Space       : " + s_result['FreeSpace'])
        print("")
        if "error" in s_result:
            print(s_result['error'])
            windows_fail = True
        windows_results.append(s_result)
    return windows_results, windows_fail

def check_ssh_connectivity(ip, user_name, pass_key, is_key, s_result):
    ssh, error = open_ssh(ip, user_name, pass_key, is_key)
    if ssh is None or len(error) > 0:
        s_result["error"] = error
        s_result["SSH22"] = "Fail"
        if "final_result" in s_result:
            s_result["final_result"] = s_result["final_result"] + "SSH22,"
        else:
            s_result["final_result"] = "SSH22,"
        print(" SSH 22 to source server : Fail")
        return None
    else:
        s_result["SSH22"] = "Pass"
        print(" SSH 22 to source server : Pass")
        return ssh


def check_sudo_permissions(ssh, s_result):
    stderr = None
    stdout = None
    ssh_err = ''
    if ssh is not None:
        try:
            stdin, stdout, stderr = ssh.exec_command("sudo -n -l")
        except paramiko.SSHException as e:
            ssh_err = "Got exception! " + str(e)
    else:
        ssh_err = 'Unable to connect! SSH is null'

    if stderr:
        for err in stderr.readlines():
            ssh_err = ssh_err + err
    if 'password is required' in ssh_err:
            s_result["error"] = ssh_err
            s_result["SUDO"] = "Fail"
            if "final_result" in s_result:
                s_result["final_result"] = s_result["final_result"] + "SUDO,"
            else:
                s_result["final_result"] = "SUDO,"
            print(" SUDO permission         : Fail")
    else:
        s_result["SUDO"] = "Pass"
        print(" SUDO permission         : Pass")

def check_tcp_connectivity(ssh, host, port, s_result):
    stderr = None
    stdout = None
    check = "TCP" + str(port)
    ssh_err = ''
    if ssh is not None:
        cmd = "sudo timeout 2 bash -c '</dev/tcp/" + host + "/" + port + " && echo port is open || echo port is closed' || echo connection timeout"
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            str_output = ''
            for output in stdout.readlines():
                str_output = str_output + output
            if len(str_output) > 0:
                str_output = str_output.strip()
                if "open" in str(str_output):
                    s_result[check] = "Pass"
                else:
                    s_result[check] = "Fail"
            else:
                s_result[check] = "Fail"
        except paramiko.SSHException as e:
            ssh_err = "Got exception! while executing the command " + cmd + \
                      " due to " + str(e)
    else:
        ssh_err = 'Unable to connect! SSH is null'

    if port == '1500':
        message = " TCP 1500 to Rep Server  : "
    elif port == '443':
        message = " TCP 443 to MGN Endpoint : "
    else:
        message = "Incorrect port! "

    if stderr:
        for err in stderr.readlines():
            ssh_err = ssh_err + err
    if "refused" in ssh_err:
        s_result[check] = "Pass"
    if check in s_result:
        print(message + s_result[check])
        if s_result[check] == "Fail":
            if "final_result" in s_result:
                s_result["final_result"] = s_result["final_result"] + check + ","
            else:
                s_result["final_result"] = check + ","
    else:
        if len(ssh_err) > 0:
            s_result["error"] = ssh_err
        s_result[check] = "Fail"
        if "final_result" in s_result:
            s_result["final_result"] = s_result["final_result"] + check + ","
        else:
            s_result["final_result"] = check + ","
        print(message + "Fail")

def check_freespace(ssh, dir, min,  s_result):
    stderr = None
    stdout = None
    ssh_err = ''
    if ssh is not None:
        cmd = "df -h " + dir + " | tail -1 | tr -s ' ' | cut -d' ' -f4"
        try:
            stdin, stdout, stderr = ssh.exec_command(cmd)
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
            ssh_err = "Got exception! while executing the command " + cmd + \
                      " due to " + str(e)
    else:
        ssh_err = 'Unable to connect! SSH is null'

    if stderr:
        for err in stderr.readlines():
            ssh_err = ssh_err + err
    if len(ssh_err) > 0 :
            s_result["error"] = ssh_err
            s_result["FreeSpace"] = "Fail"
            if "final_result" in s_result:
                s_result["final_result"] = s_result["final_result"] + "FreeSpace" + str(min) + ","
            else:
                s_result["final_result"] = "FreeSpace" + str(min) + ","
            if min == 2.0:
                print(" " + str(min) + " GB " + dir + " FreeSpace      : Fail")
            else:
                print(" " + str(min) + " GB " + dir + " FreeSpace   : Fail")
    else:
        s_result["FreeSpace"] = "Pass"
        if min == 2.0:
            print(" " + str(min) + " GB " + dir + " FreeSpace      : Pass")
        else:
            print(" " + str(min) + " GB " + dir + " FreeSpace   : Pass")


def check_dhclient(ssh, s_result):
    stderr = None
    stdout = None
    ssh_err = ''
    if ssh is not None:
        try:
            stdin, stdout, stderr = ssh.exec_command("sudo dhclient -v")
        except paramiko.SSHException as e:
            ssh_err = "Got exception! " + str(e)
    else:
        ssh_err = 'Unable to connect! SSH is null'

    if stderr:
        for err in stderr.readlines():
            ssh_err = ssh_err + err
    if len(ssh_err) > 0 and 'not found' in ssh_err:
            s_result["error"] = ssh_err
            s_result["DHCLIENT"] = "Fail"
            if "final_result" in s_result:
                s_result["final_result"] = s_result["final_result"] + "DHCLIENT,"
            else:
                s_result["final_result"] = "DHCLIENT,"
            print(" DHCLIENT Package        : Fail")
    else:
        s_result["DHCLIENT"] = "Pass"
        print(" DHCLIENT Package        : Pass")


def check_linux(MGNEndpoint, Servers_Linux, MGNServerIP, user_name, pass_key, key_exist):
    linux_fail = False
    linux_results = []
    for s in Servers_Linux:
        print("")
        print("---------------------------------------------------------")
        print("-- Linux Server result for " + s['server_name'] + " --")
        print("---------------------------------------------------------")
        print("")
        s_result = {}
        s_result["server_id"] = s["server_id"]
        s_result["server_name"] = s["server_fqdn"]
        s_result["final_result"] = ""

        # This checks network connectivity, if we can SSH to the source machine
        ssh = check_ssh_connectivity(s["server_fqdn"], user_name, pass_key,
                               key_exist, s_result)
        if "SSH22" not in s_result["final_result"]:
            # Check if the given user has sudo permissions
            check_sudo_permissions(ssh, s_result)
            if "SUDO" not in s_result["final_result"]:
                # Check if user is able to access Internet and
                # connect to MGN Service Endpoint
                check_tcp_connectivity(ssh, MGNEndpoint, '443', s_result)

                # Check if user is able to connect to TCP 1500
                # for a specific IP (user provide IP address)
                check_tcp_connectivity(ssh, MGNServerIP, '1500', s_result)

                # Check if root directory have more than 3GB free space
                check_freespace(ssh, '/', 2.0, s_result)

                # Check if /tmp directory have more than 500MB free space
                check_freespace(ssh, '/tmp', 0.5, s_result)

                # Check if dhclient package is installed.
                check_dhclient(ssh, s_result)
        if "error" in s_result:
            print(s_result['error'])
            linux_fail = True
        # Closing ssh connection
        if ssh is not None:
            ssh.close()
            ssh = None
        if "final_result" in s_result:
            final_result = s_result["final_result"]
            if len(final_result) > 1 and final_result[-1] == ',':
                final_result = final_result[:-1]
                s_result["final_result"] = final_result
                linux_fail = True
        linux_results.append(s_result)
    return linux_results, linux_fail


def open_ssh(host, username, key_pwd, using_key):
    ssh = None
    error = ''
    try:
        if using_key:
            private_key = paramiko.RSAKey.from_private_key_file(key_pwd)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, pkey=private_key)
        else:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, password=key_pwd)
    except IOError as io_error:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(io_error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(ssh_exception)
    return ssh, error


def print_results(label, results, UserHOST, token, status):
    print("------------------------------------------------------------")
    print("-- " + label +" server passed all Pre-requisites checks --")
    print("------------------------------------------------------------")
    print("")
    isEmpty = 0
    for result in results:
        if 'final_result' in result:
            if result['final_result'] == "":
                if 'error' not in result:
                    print("     " + result['server_name'])
                    serverattr = {"migration_status": "Pre-requisites check : Passed"}
                    update = requests.put(UserHOST + serverendpoint + '/' +
                                        result['server_id'], headers={
                        "Authorization": token}, data=json.dumps(serverattr))
            else:
                isEmpty = isEmpty + 1
    if len(results) == isEmpty:
       print("     No Server Passed")

    if status:
        print("")
        print("-------------------------------------------------------------")
        print("-- " + label + " server failed one or more Pre-requisites checks --")
        print("-------------------------------------------------------------")
        print("")
        for result in results:
            if 'final_result' not in result:
                print("     " + result[
                    'server_name'] + " : Unexpected error, please check error details")
                serverattr = {"migration_status": "Pre-requisites check : Failed - Unexpected error"}
                update = requests.put(
                    UserHOST + serverendpoint + '/' + result['server_id'],
                    headers={"Authorization": token},
                    data=json.dumps(serverattr))
            else:
                if 'error' in result and result['final_result'] == "":
                    print("     " + result[
                        'server_name'] + " : Unexpected error, please check error details")
                    serverattr = {"migration_status": "Pre-requisites check : Failed - Unexpected error"}
                    update = requests.put(
                        UserHOST + serverendpoint + '/' + result['server_id'],
                        headers={"Authorization": token},
                        data=json.dumps(serverattr))
                if result['final_result'] != "":
                    print("     " + result['server_name'] + " : " + result['final_result'])
                    serverattr = {
                        "migration_status": "Pre-requisites check : Failed - " + result['final_result']}
                    update = requests.put(
                        UserHOST + serverendpoint + '/' + result['server_id'],
                        headers={"Authorization": token}, data=json.dumps(serverattr))
    print("")

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--ReplicationServerIP', required=True)
    parser.add_argument('--WindowsUser', default="")
    args = parser.parse_args(arguments)

    UserHOST = ""

    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit()

    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ****")
    print("****************************")
    get_servers, linux_exist, windows_exist = get_factory_servers(args.Waveid, token, UserHOST)
    user_name = ''
    pass_key = ''
    key_exist = False
    if linux_exist == True:
        user_name, pass_key, key_exist = mfcommon.get_linux_password()

    windows_results = []
    linux_results = []
    windows_status = False
    linux_status = False
    if windows_exist:
        print("")
        print("*********************************************")
        print("*Checking Pre-requisites for Windows servers*")
        print("*********************************************")
        print("")
        if args.WindowsUser != "":
           windows_password = mfcommon.GetWindowsPassword()
        else:
           windows_password = ''
        for account in get_servers:
            MGNEndpoint = "mgn.{}.amazonaws.com".format(account['aws_region'])
            result = []
            if len(account["servers_windows"]) > 0:
                result, windows_fail = check_windows(MGNEndpoint, account["servers_windows"], args.ReplicationServerIP, args.WindowsUser, windows_password)
                windows_results = windows_results + result
                if windows_fail:
                   windows_status = True

    if linux_exist:
        print("")
        print("********************************************")
        print("*Checking Pre-requisites for Linux servers*")
        print("********************************************")
        print("")
        for account in get_servers:
            MGNEndpoint = "mgn.{}.amazonaws.com".format(account['aws_region'])
            result = []
            if len(account["servers_linux"]) > 0 :
                result, linux_fail = check_linux(MGNEndpoint, account["servers_linux"], args.ReplicationServerIP, user_name, pass_key, key_exist)
                linux_results = linux_results + result
                if linux_fail:
                   linux_status = True

    print("")
    print("********************************************")
    print("***** Final results for all servers *****")
    print("********************************************")
    print("")
    if windows_exist:
       print_results("Windows", windows_results, UserHOST, token, windows_status)
    if linux_exist:
       print_results("Linux", linux_results, UserHOST, token, linux_status)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
