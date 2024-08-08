#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 01SEP2023.01

from __future__ import print_function
import sys
import argparse
import subprocess
import mfcommon

windows_fail = 0
linux_fail = 0


def check_linux(linux_servers, secret_name, ssh_port, no_prompts=True):
    user_name = ''
    pass_key = ''
    key_exist = False
    failure_count = 0

    if len(linux_servers) > 0:
        for server in linux_servers:
            linux_credentials = mfcommon.get_server_credentials(user_name, pass_key, server, secret_name,
                                                                no_prompts)
            failure_count += check_ssh_connectivity(
                server["server_fqdn"],
                linux_credentials['username'],
                linux_credentials['password'],
                key_exist,
                ssh_port
            )
    return failure_count


def check_windows(servers_windows, rdp_port):
    failure_count = 0
    if len(servers_windows) > 0:
        for s in servers_windows:
            command = "(Test-NetConnection -ComputerName " + s[
                "server_fqdn"] + " -Port " + rdp_port + ").TcpTestSucceeded"
            p = subprocess.Popen(["powershell.exe", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, _ = p.communicate()
            if output:
                print(" RDP test to Server " + s["server_fqdn"] + " : Pass", flush=True)
            else:
                print(" RDP test to Server " + s["server_fqdn"] + " : Fail", flush=True)
                failure_count += 1

    return failure_count


def check_ssh_connectivity(ip, user_name, pass_key, is_key, ssh_port):
    failure = 0
    ssh, error = mfcommon.open_ssh(ip, user_name, pass_key, is_key, ssh_port)
    if ssh is None or len(error) > 0:
        print(" SSH test to server " + ip + " : Fail", flush=True)
        failure = 1
    else:
        print(" SSH test to server " + ip + " : Pass", flush=True)

    return failure


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--AppIds', default=None)
    parser.add_argument('--ServerIds', default=None)
    parser.add_argument('--SSHPort', default="22")
    parser.add_argument('--RDPPort', default="3389")
    parser.add_argument('--NoPrompts', default=False, type=mfcommon.parse_boolean,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretLinux', default=None)
    args = parser.parse_args(arguments)

    print("*Login to Migration factory*", flush=True)
    token = mfcommon.factory_login()

    print("*** Getting Server List ****", flush=True)
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(
        waveid=args.Waveid,
        app_ids=mfcommon.parse_list(args.AppIds),
        server_ids=mfcommon.parse_list(args.ServerIds),
        token=token
    )

    windows_status = 0
    linux_status = 0

    print("")

    if windows_exist:
        print("")
        print("*********************************************")
        print("*Checking RDP Access for Windows servers*")
        print("*********************************************")
        print("", flush=True)
        for account in get_servers:
            windows_status = check_windows(account["servers_windows"], args.RDPPort)

    if linux_exist:
        print("")
        print("********************************************")
        print("*Checking SSH connections for Linux servers*")
        print("********************************************")
        print("", flush=True)
        for account in get_servers:
            linux_status = check_linux(account["servers_linux"], args.SecretLinux, args.SSHPort, args.NoPrompts)

    if windows_status > 0 or linux_status > 0:
        print("One or more servers failed to pass the connection check. Check log for details.")
        return 1
    else:
        print("All servers have had server connection check completed successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
