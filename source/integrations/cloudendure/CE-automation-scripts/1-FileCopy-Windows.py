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
