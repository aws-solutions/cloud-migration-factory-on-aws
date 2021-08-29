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

# Version: 11APR2021.01

from __future__ import print_function
import paramiko
import sys
import argparse
import json
import subprocess
import os
import boto3
import botocore.exceptions
import mfcommon

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

def open_ssh(host, username, key_pwd, using_key):
    ssh = None
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
        print(error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(ssh_exception)
        print(error)
    return ssh


def upload_files(host, username, key_pwd, using_key, local_file_path):
    error = ''
    file_path = local_file_path
    ssh = None
    ftp = None
    try:
        ssh = open_ssh(host, username, key_pwd, using_key)
        tmp_c_command = ssh.exec_command("[ -d /tmp/copy_ce_files ] && echo 'Directory exists' || mkdir /tmp/copy_ce_files")
        post_launch_command = ssh.exec_command("[ -d '/boot/post_launch' ] && echo 'Directory exists' || sudo mkdir /boot/post_launch")
        ftp = ssh.open_sftp()
        if os.path.isfile(file_path):
            filename = file_path.split("/")
            filename = filename[-1]
            ftp.put(file_path, '/tmp/copy_ce_files/' + filename)
        else:
            for file in os.listdir(local_file_path):
                file_path = os.path.join(local_file_path, file)
                if os.path.isfile(file_path):
                    ftp.put(file_path, '/tmp/copy_ce_files/' + file)
                else:
                    print('ignoring the subdirectories... ' + file_path)
        copy_command = ssh.exec_command("sudo cp /tmp/copy_ce_files/* /boot/post_launch && sudo chown aws-replication /boot/post_launch/* && sudo chmod +x /boot/post_launch/*")
    except Exception as e:
        error = "Copying " + file_path + " to " + \
                "/boot/post_launch" + " on host " + host + " failed due to " + \
                str(e)
        print(error)
    finally:
        if ftp is not None:
            ftp.close()
        if ssh is not None:
            ssh.close()
    return error

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--WindowsSource', default="")
    parser.add_argument('--LinuxSource', default="")
    parser.add_argument('--WindowsUser', default="")
    args = parser.parse_args(arguments)
    if args.WindowsSource == "" and args.LinuxSource == "":
        print("ERROR:--WindowsSource or --LinuxSource is required, provide both if you want to push files to both OS")
        sys.exit()

    UserHOST = ""

    # Get MF endpoints from FactoryEndpoints.json file
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
    print("*Getting Server List*")
    print("****************************")
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST)
    user_name = ''
    pass_key = ''
    key_exist = False

    print("")
    print("*************************************")
    print("*Copying files to post_launch folder*")
    print("*************************************")

    if args.WindowsSource != "":
       if windows_exist:
           if args.WindowsUser != "":
               Windows_Password = mfcommon.GetWindowsPassword()
               creds = " -Credential (New-Object System.Management.Automation.PSCredential(\"" + args.WindowsUser + "\", (ConvertTo-SecureString \"" + Windows_Password + "\" -AsPlainText -Force)))"
           else:
               creds = ""
           for account in get_servers:
               if len(account["servers_windows"]) > 0:
                   for server in account["servers_windows"]:
                        destpath = "'c:\\Program Files (x86)\\AWS Replication Agent\\post_launch\\'"
                        sourcepath = "'" + args.WindowsSource + "\\*'"
                        command1 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {if (!(Test-Path -Path " + destpath + ")) {New-Item -Path " + destpath + " -ItemType directory}}" + creds
                        command2 = "$Session = New-PSSession -ComputerName " + server['server_fqdn'] + creds + "\rCopy-Item -Path " + sourcepath + " -Destination " + destpath + " -ToSession $Session"
                        print("Task completed for server: " + server['server_fqdn'])
                        p1 = subprocess.Popen(["powershell.exe", command1], stdout=sys.stdout)
                        p1.communicate()
                        p2 = subprocess.Popen(["powershell.exe", command2], stdout=sys.stdout)
                        p2.communicate()
       else:
           print("ERROR:There is no Windows server in Wave " + str(args.Waveid))
           sys.exit()

    if args.LinuxSource != "":
       if linux_exist:
            user_name, pass_key, key_exist = mfcommon.get_linux_password()
            for account in get_servers:
               if len(account["servers_linux"]) > 0:
                   for server in account["servers_linux"]:
                        err_reason = upload_files(server['server_fqdn'], user_name, pass_key, key_exist,
                                    args.LinuxSource)
                        if not err_reason:
                            print("Task completed for server: " + server['server_fqdn'])
                        else:
                            print("Unable to copy files to " + server['server_fqdn'] + " due to " + err_reason)
       else:
           print("ERROR:There is no Linux server in Wave " + str(args.Waveid))
           sys.exit()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
