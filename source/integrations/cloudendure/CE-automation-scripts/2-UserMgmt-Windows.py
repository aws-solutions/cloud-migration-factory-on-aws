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
import time
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
    choice_flag = True
    choice = 3
    while choice_flag:
        print("1. Create user")
        print("2. Delete user")
        print("3. Exit")
        choice = input("Enter your choice [1-3]: ")
        if choice == '3':
            sys.exit(0)
        elif choice != '1' and choice != '2':
            print("Please provide a valid option [1, 2, 3]")
            print("")
        else:
            choice_flag = False
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()


    print("****************************")
    print("*Getting Server List*")
    print("****************************")
    Servers_Windows, Servers_Linux = mfcommon.ServerList(args.Waveid, token, UserHOST,"")

    if len(Servers_Windows) == 0:
        print("ERROR: There are no Windows servers in this Wave")
        sys.exit(1)

    if args.WindowsUser != "":
        Windows_Password = mfcommon.GetWindowsPassword()
        creds = " -Credential (New-Object System.Management.Automation.PSCredential('" + args.WindowsUser + "', (ConvertTo-SecureString '" + Windows_Password + "' -AsPlainText -Force)))"
    else:
        creds = ""

    print("")
    if choice == '1':
        print("")
        print("************************************")
        print("*Creating local admin on the server*")
        print("************************************")
        LocalAdminUser = input("Enter Local admin username: ")
        localadmin_pass_first = getpass.getpass('Local admin Password: ')
        localadmin_pass_second = getpass.getpass('Re-enter Password: ')
        while(localadmin_pass_first != localadmin_pass_second):
            print("Password mismatch, please try again!")
            localadmin_pass_first = getpass.getpass('Local admin Password: ')
            localadmin_pass_second = getpass.getpass('Re-enter Password: ')
        localadmin_pass = localadmin_pass_second
        print("")
        for s in Servers_Windows:
            command1 = "Invoke-Command -ComputerName " + s['server_fqdn'] + " -ScriptBlock {net user " + LocalAdminUser + " " + localadmin_pass + " /add}" + creds
            print("------------------------------------------------------")
            print("- Creating a local user on: " + s['server_fqdn'] + " -")
            print("------------------------------------------------------")
            p = subprocess.Popen(["powershell.exe", command1], stdout=sys.stdout)
            p.communicate()
            command2 = "Invoke-Command -ComputerName " + s['server_fqdn'] + " -ScriptBlock {net localgroup Administrators " + LocalAdminUser + " /add}" + creds
            print("Adding user to local admin group on server: " + s['server_fqdn'])
            p = subprocess.Popen(["powershell.exe", command2], stdout=sys.stdout)
            p.communicate()
        print("")
    else:
        print("")
        print("*************************************")
        print("*Deleting local admin on the servers*")
        print("*************************************")
        print("")
        LocalAdminUser = input("Enter local admin UserName to be deleted: ")
        print("")
        for s in Servers_Windows:
            command1 = "Invoke-Command -ComputerName " + s['server_fqdn'] + " -ScriptBlock {net user " + LocalAdminUser + " /delete}" + creds
            print("------------------------------------------------------")
            print("- Deleting a local user on: " + s['server_fqdn'] + " -")
            print("------------------------------------------------------")
            p = subprocess.Popen(["powershell.exe", command1], stdout=sys.stdout)
            p.communicate()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
