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
    parser.add_argument('--Source', required=True)
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

    if len(Servers_Windows) == 0:
        print("ERROR: There are no Windows servers in this Wave")
        sys.exit(1)

    if args.WindowsUser != "":
        Windows_Password = mfcommon.GetWindowsPassword()
        creds = " -Credential (New-Object System.Management.Automation.PSCredential('" + args.WindowsUser + "', (ConvertTo-SecureString '" + Windows_Password + "' -AsPlainText -Force)))"
    else:
        creds = ""

    print("")
    print("*************************************")
    print("*Copying files to post_launch folder*")
    print("*************************************")

    for server in Servers_Windows:
        destpath = "'c:\\Program Files (x86)\\CloudEndure\\post_launch\\'"
        sourcepath = "'" + args.Source + "\\*'"
        command1 = "Invoke-Command -ComputerName " + server['server_fqdn'] + " -ScriptBlock {if (!(Test-Path -Path " + destpath + ")) {New-Item -Path " + destpath + " -ItemType directory}}" + creds
        command2 = "$Session = New-PSSession -ComputerName " + server['server_fqdn'] + creds + "\rCopy-Item -Path " + sourcepath + " -Destination " + destpath + " -ToSession $Session"
        print("Copying files to server: " + server['server_fqdn'])
        p1 = subprocess.Popen(["powershell.exe", command1], stdout=sys.stdout)
        p1.communicate()
        p2 = subprocess.Popen(["powershell.exe", command2], stdout=sys.stdout)
        p2.communicate()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
