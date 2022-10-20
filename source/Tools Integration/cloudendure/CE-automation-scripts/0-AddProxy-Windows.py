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
    parser.add_argument('--ProxyServer', required=True)
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

    print("")
    print("*************************************")
    print("* Adding proxy on the source server *")
    print("*************************************")

    for server in Servers_Windows:
        command1 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {[Environment]::SetEnvironmentVariable('https_proxy', 'https://" + args.ProxyServer + "/', 'Machine')}"
        command2 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {Set-ItemProperty -path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' ProxyEnable -value 1}"
        command3 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {Set-ItemProperty -path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' ProxyServer -value " + args.ProxyServer + "}"

        if args.WindowsUser != "":
            command1 += " -Credential (New-Object System.Management.Automation.PSCredential('" + args.WindowsUser + "', (ConvertTo-SecureString '" + Windows_Password + "' -AsPlainText -Force)))"
            command2 += " -Credential (New-Object System.Management.Automation.PSCredential('" + args.WindowsUser + "', (ConvertTo-SecureString '" + Windows_Password + "' -AsPlainText -Force)))"
            command3 += " -Credential (New-Object System.Management.Automation.PSCredential('" + args.WindowsUser + "', (ConvertTo-SecureString '" + Windows_Password + "' -AsPlainText -Force)))"
            p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + server['server_fqdn'] + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        p1 = subprocess.Popen(["powershell.exe", command1], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p1.communicate()
        p2 = subprocess.Popen(["powershell.exe", command2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2.communicate()
        p3 = subprocess.Popen(["powershell.exe", command3], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p3.communicate()
        if len(error) > 0:
            print("Proxy server failed to be updated for server: " + server['server_name'] + ", using address: " + server['server_fqdn'])
        else:
            print("Proxy server added for server: " + server['server_name'])

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
