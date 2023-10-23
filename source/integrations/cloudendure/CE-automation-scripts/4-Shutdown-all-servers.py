#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 23MAR2021.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import subprocess
import getpass
import paramiko
import mfcommon

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


def execute_cmd(host, username, key, cmd, using_key):
    output = ''
    error = ''
    ssh = None
    try:
        ssh = open_ssh(host, username, key, using_key)
        if ssh is None:
            error = "Not able to get the SSH connection for the host " + host
            print(error)
        else:
            stdin, stdout, stderr = ssh.exec_command(cmd)  # nosec B601
            for line in stdout.readlines():
                output = output + line
            for line in stderr.readlines():
                error = error + line
    except IOError as io_error:
        error = "Unable to execute the command " + cmd + " on " +host+ " due to " + \
                str(io_error)
        print(error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to execute the command " + cmd + " on " +host+ " due to " + \
                str(ssh_exception)
        print(error)
    except Exception as e:
        error = "Unable to execute the command " + cmd + " on " +host+ " due to " + str(e)
        print(error)
    finally:
        if ssh is not None:
            ssh.close()
    return output, error

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--WindowsUser', default="")
    args = parser.parse_args(arguments)

    UserHOST = endpoints['UserApiUrl']

    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    winServers, linuxServers = mfcommon.ServerList(args.Waveid, token, UserHOST,
                                   "")
    if len(winServers) > 0:
        print("****************************")
        print("*Shutting down Windows servers*")
        print("****************************")
        if args.WindowsUser != "":
            windows_password = mfcommon.GetWindowsPassword()
        for s in winServers:
            command = "Stop-Computer -ComputerName " + s["server_fqdn"] + " -Force"
            if args.WindowsUser != "":
                command += " -Credential (New-Object System.Management.Automation.PSCredential('" + args.WindowsUser + "', (ConvertTo-SecureString '" + windows_password + "' -AsPlainText -Force)))"
            print("Shutting down server: " + s["server_name"] + " using address " + s["server_fqdn"])
            p = subprocess.Popen(["powershell.exe", command], stdout=sys.stdout)
            p.communicate()
    if len(linuxServers) > 0:
        print("")
        print("****************************")
        print("*Shutting down Linux servers*")
        print("****************************")
        print("")
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
        for s in linuxServers:
            output, error = execute_cmd(s["server_fqdn"], user_name, pass_key, "sudo shutdown now", has_key in 'y')
            if not error:
                print("Shutdown successful on " + s["server_name"])
            else:
                print("unable to shutdown server " + s["server_name"] + " using address " + s["server_fqdn"] + " due to " + error)
            print("")

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
