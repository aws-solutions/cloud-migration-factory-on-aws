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

# Version: 23MAR2021.01

from __future__ import print_function
import paramiko
import sys
import argparse
import requests
import json
import getpass
import os
import mfcommon
import tempfile

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

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
        tmp_c_command = ssh.exec_command("[ -d /tmp/copy_ce_files ] && echo 'Directory exists' || mkdir /tmp/copy_ce_files")  # nosec B601 B108
        post_launch_command = ssh.exec_command("[ -d '/boot/post_launch' ] && echo 'Directory exists' || sudo mkdir /boot/post_launch")  # nosec B601
        ftp = ssh.open_sftp()
        if os.path.isfile(file_path):
            filename = file_path.split("/")
            filename = filename[-1]
            ftp.put(file_path, '/tmp/copy_ce_files/' + filename)  # nosec B108
        else:
            for file in os.listdir(local_file_path):
                file_path = os.path.join(local_file_path, file)
                if os.path.isfile(file_path):
                    ftp.put(file_path, '/tmp/copy_ce_files/' + file)  # nosec B108
                else:
                    print('ignoring the subdirectories... ' + file_path)
        copy_command = ssh.exec_command("sudo cp /tmp/copy_ce_files/* /boot/post_launch && sudo chown cloudendure /boot/post_launch/* && sudo chmod +x /boot/post_launch/*")  # nosec B601 B108
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
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--Source', required=True)
    args = parser.parse_args(arguments)

    UserHOST = endpoints['UserApiUrl']
    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*Getting Server List*")
    print("****************************")
    Servers_Windows, Servers_Linux = mfcommon.ServerList(args.Waveid, token, UserHOST, "")

    if len(Servers_Linux) == 0:
        print("ERROR: There are no Linux servers in this Wave")
        sys.exit(1)

    print("*****************************************")
    print("*Provide Linux credentials to copy files*")
    print("*****************************************")
    user_name = input("Linux Username: ")
    has_key = input("If you use a private key to login, press [Y] or if use password press [N]: ")
    has_key = has_key.lower()
    if has_key in 'y':
        pass_key = input('Private Key file name: ')
    else:
        pass_key_first = getpass.getpass('Linux Password: ')
        pass_key_second = getpass.getpass('Re-enter Password: ')
        while(pass_key_first != pass_key_second):
            print("Password mismatch, please try again!")
            pass_key_first = getpass.getpass('Linux Password: ')
            pass_key_second = getpass.getpass('Re-enter Password: ')
        pass_key = pass_key_second

    print("")
    print("*************************************")
    print("*Copying files to post_launch folder*")
    print("*************************************")
    print("")
    for server in Servers_Linux:
        err_reason = upload_files(server["server_fqdn"], user_name, pass_key, has_key in 'y',
                    args.Source)
        if not err_reason:
            print("Successfully copied files to " + server["server_name"])
        else:
            print("Unable to copy files to " + server["server_name"] + " due to " + err_reason)
        print("")


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
