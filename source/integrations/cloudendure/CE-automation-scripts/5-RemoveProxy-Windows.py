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
import mfcommon

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--WindowsUser', default="")
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

    if args.WindowsUser != "":
        Windows_Password = mfcommon.GetWindowsPassword()

    if len(Servers_Windows) > 0:
        print("")
        print("****************************************")
        print("* Disabling proxy on the source server *")
        print("****************************************")

        for server in Servers_Windows:
            command1 = "Invoke-Command -ComputerName " + server["server_fqdn"] + " -ScriptBlock {Set-ItemProperty -path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' ProxyEnable -value 0}"
            command2 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {[Environment]::SetEnvironmentVariable('https_proxy', '', 'Machine')}"

            if args.WindowsUser != "":
                command1 += " -Credential (New-Object System.Management.Automation.PSCredential('" + args.WindowsUser + "', (ConvertTo-SecureString '" + Windows_Password + "' -AsPlainText -Force)))"
                command2 += " -Credential (New-Object System.Management.Automation.PSCredential('" + args.WindowsUser + "', (ConvertTo-SecureString '" + Windows_Password + "' -AsPlainText -Force)))"
                p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + server["server_fqdn"] + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            p1 = subprocess.Popen(["powershell.exe", command1], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = p1.communicate()
            p2 = subprocess.Popen(["powershell.exe", command2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = p2.communicate()
            if len(error) > 0:
                print("Proxy server failed to be updated for server: " + server["server_name"] + " using address " + server["server_fqdn"])
                print(error)
            else:
                print("Proxy server disabled for server: " + server["server_name"])
    else:
        print("")
        print("INFO: No Windows servers configured for Waveid: " + args.Waveid)
if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
