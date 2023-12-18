#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 01SEP2023.01

from __future__ import print_function
import sys
import argparse
import subprocess
import os
import time
import mfcommon


def upload_files(host, username, key_pwd, using_key, local_file_path):
    error = ''
    file_path = local_file_path
    ssh = None
    ftp = None
    try:
        ssh, error = mfcommon.open_ssh(host, username, key_pwd, using_key)
        if ssh is None:
            return error
        ssh.exec_command(
            "[ -d /tmp/copy_ce_files ] && echo 'Directory exists' || mkdir /tmp/copy_ce_files")  # nosec B601 B108
        ssh.exec_command(
            "[ -d '/boot/post_launch' ] && echo 'Directory exists' || sudo mkdir /boot/post_launch")  # nosec B601
        ftp = ssh.open_sftp()
        if os.path.isfile(file_path):
            filename = file_path.split("/")
            filename = filename[-1]
            ftp.put(file_path, '/tmp/copy_ce_files/' + filename)  # //NOSONAR nosec B108
        else:
            for file in os.listdir(local_file_path):
                file_path = os.path.join(local_file_path, file)
                if os.path.isfile(file_path):
                    ftp.put(file_path, '/tmp/copy_ce_files/' + file)  # //NOSONAR nosec B108
                else:
                    print('ignoring the subdirectories... ' + file_path)
        ssh.exec_command(
            "sudo cp /tmp/copy_ce_files/* /boot/post_launch && sudo chown aws-replication /boot/post_launch/* && sudo chmod +x /boot/post_launch/*")  # nosec B601 B108
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
    parser.add_argument('--NoPrompts', default=False, type=bool,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--WindowsSource', default="")
    parser.add_argument('--LinuxSource', default="")
    parser.add_argument('--SecretWindows', default="")
    parser.add_argument('--SecretLinux', default="")

    args = parser.parse_args(arguments)
    if args.WindowsSource == "" and args.LinuxSource == "":
        print("ERROR:--WindowsSource or --LinuxSource is required, provide both if you want to push files to both OS")
        sys.exit()

    print("")
    print("*Login to Migration factory*")
    token = mfcommon.factory_login()

    print("*Getting Server List*")
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(
        args.Waveid, token, True, 'Rehost')

    print("")
    print("*************************************")
    print("*Copying files to post_launch folder*")
    print("*************************************")

    linux_user_name = ''
    linux_pass_key = ''
    failures = False

    if args.WindowsSource != "":
        if windows_exist:
            for account in get_servers:
                if len(account["servers_windows"]) > 0:
                    for server in account["servers_windows"]:
                        windows_credentials = mfcommon.get_server_credentials('', '', server, args.SecretWindows,
                                                                              args.NoPrompts)
                        if windows_credentials['username'] != "":
                            if "\\" not in windows_credentials['username'] and "@" not in windows_credentials[
                                'username']:
                                # Assume local account provided, prepend server name to user ID.
                                server_name_only = server["server_fqdn"].split(".")[0]
                                windows_credentials['username'] = server_name_only + "\\" + windows_credentials[
                                    'username']
                                print("INFO: Using local account to connect: " + windows_credentials['username'])
                        else:
                            print("INFO: Using domain account to connect: " + windows_credentials['username'])
                        creds = " -Credential (New-Object System.Management.Automation.PSCredential('" + \
                                windows_credentials['username'] + "', (ConvertTo-SecureString '" + windows_credentials[
                                    'password'] + "' -AsPlainText -Force)))"
                        destpath = "'c:\\Program Files (x86)\\AWS Replication Agent\\post_launch\\'"
                        sourcepath = "'" + args.WindowsSource + "\\*'"
                        command1 = "Invoke-Command -ComputerName " + server[
                            'server_fqdn'] + " -ScriptBlock {if (!(Test-Path -Path " + destpath + ")) {New-Item -Path " + destpath + " -ItemType directory}}" + creds
                        command2 = "$Session = New-PSSession -ComputerName " + server[
                            'server_fqdn'] + creds + "\rCopy-Item -Path " + sourcepath + " -Destination " + destpath + " -ToSession $Session"
                        p1 = subprocess.Popen(["powershell.exe", command1], stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
                        p1.communicate()
                        p2 = subprocess.Popen(["powershell.exe", command2], stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
                        _, stderr = p2.communicate()
                        if 'ErrorId' in str(stderr):
                            print(str(stderr))
                            failures = True
                        else:
                            print("Task completed for server: " + server['server_fqdn'])
        else:
            print("WARN:There is no Windows server in Wave " + str(args.Waveid))

    if args.LinuxSource != "":
        if linux_exist:
            for account in get_servers:
                if len(account["servers_linux"]) > 0:
                    for server in account["servers_linux"]:
                        linux_credentials = mfcommon.get_server_credentials(linux_user_name, linux_pass_key, server,
                                                                            args.SecretLinux, args.NoPrompts)
                        err_reason = upload_files(server['server_fqdn'], linux_credentials['username'],
                                                  linux_credentials['password'], linux_credentials['private_key'],
                                                  args.LinuxSource)
                        if not err_reason:
                            print("Task completed for server: " + server['server_fqdn'])
                        else:
                            print("Unable to copy files to " + server['server_fqdn'] + " due to " + err_reason)
                            failures = True
        else:
            print("WARN:There is no Linux server in Wave " + str(args.Waveid))

    time.sleep(2)

    if failures:
        print("One or more servers failed to copy scripts. Check log for details.")
        return 1
    else:
        print("All servers have had scripts copied successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
