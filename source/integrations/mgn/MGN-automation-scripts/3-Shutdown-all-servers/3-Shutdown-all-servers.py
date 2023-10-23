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

# Version: 01SEP2023.01

from __future__ import print_function
import sys
import argparse
import subprocess
import mfcommon


def shutdown_windows_server(server, secret_name, no_prompts):
    success = True
    windows_credentials = mfcommon.getServerCredentials(
        '',
        '',
        server,
        secret_name,
        no_prompts
    )
    if windows_credentials['username'] != "":
        if "\\" not in windows_credentials['username'] and "@" not in windows_credentials['username']:
            # Assume local account provided, prepend server name to user ID.
            server_name_only = server["server_fqdn"].split(".")[0]
            windows_credentials['username'] = server_name_only + "\\" + windows_credentials['username']
            print("INFO: Using local account to connect: " + windows_credentials['username'])
    else:
        print("INFO: Using domain account to connect: " + windows_credentials['username'])
    command = "Stop-Computer -Force"
    print("Shutting down server: " + server['server_fqdn'], flush=True)

    invoke_command = "Invoke-Command -ComputerName %s -ScriptBlock{%s}" % (server['server_fqdn'],
                                                                           command)
    invoke_command += " -Credential (New-Object System.Management.Automation.PSCredential('" + \
                      windows_credentials['username'] + "', (ConvertTo-SecureString '" + \
                      windows_credentials['password'] + "' -AsPlainText -Force)))"

    p = subprocess.Popen(["powershell.exe", invoke_command], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    _, stderr = p.communicate()
    if 'ErrorId' in str(stderr):
        print(str(stderr), flush=True)
        success = False
    else:
        print("Shutdown completed for server: " + server['server_fqdn'], flush=True)

    return success


def process_shutdown_for_linux_servers(cmf_servers, secret_name, no_prompts=True):
    failure_count = 0
    print("")
    print("*Shutting down Linux servers*")
    print("", flush=True)
    for account in cmf_servers:
        if len(account["servers_linux"]) > 0:
            if not secret_name:
                failure_count += len(account["servers_linux"])
                continue
            for server in account["servers_linux"]:
                linux_credentials = mfcommon.getServerCredentials('', '', server, secret_name,
                                                                  no_prompts)
                _, error = mfcommon.execute_cmd_via_ssh(server['server_fqdn'], linux_credentials['username'],
                                                        linux_credentials['password'], "sudo shutdown now",
                                                        linux_credentials['private_key'])
                if not error:
                    print("Shutdown successful on " + server['server_fqdn'], flush=True)
                else:
                    print("unable to shutdown server " + server['server_fqdn'] + " due to " + error, flush=True)
                    failure_count += 1

    return failure_count


def process_shutdown_for_windows_servers(cmf_servers, secret_name, no_prompts=True):
    failure_count = 0

    print("*Shutting down Windows servers*", flush=True)

    for account in cmf_servers:
        if len(account["servers_windows"]) > 0:
            if not secret_name:
                failure_count += len(account["servers_windows"])
                continue

            mfcommon.add_windows_servers_to_trusted_hosts(account["servers_windows"])

            for server in account["servers_windows"]:
                if not shutdown_windows_server(server, secret_name, no_prompts):
                    failure_count += 1

    return failure_count


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--NoPrompts', default=False, type=bool,
                        help='Specify if user prompts for passwords are allowed. Default = False')
    parser.add_argument('--SecretWindows', default=None)
    parser.add_argument('--SecretLinux', default=None)
    args = parser.parse_args(arguments)

    print("*Login to Migration factory*")
    token = mfcommon.Factorylogin()

    print("*Getting Server List*")
    get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token)

    if windows_exist:
        if not args.SecretWindows:
            print('ERROR: SecretWindows not provided and is required.')
        windows_failure_count = process_shutdown_for_windows_servers(get_servers, args.SecretWindows, args.NoPrompts)
    else:
        windows_failure_count = 0

    if linux_exist:
        if not args.SecretLinux:
            print('ERROR: SecretLinux not provided and is required.')
        linux_failure_count = process_shutdown_for_linux_servers(get_servers, args.SecretLinux, args.NoPrompts)
    else:
        linux_failure_count = 0

    if windows_failure_count > 0 or linux_failure_count > 0:
        print(f"{windows_failure_count + linux_failure_count} servers failed to shutdown. Check log for details.")
        return 1
    else:
        print("All servers have had shutdown completed successfully.")
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
