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

# Version: 17MAY2021.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import subprocess
import time
import boto3
import botocore.exceptions
import mfcommon

linuxpkg = __import__("1-Uninstall-Linux")

with open('FactoryEndpoints.json') as json_file:
  endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

def assume_role(account_id, region):

  sts_client = boto3.client('sts')
  role_arn = 'arn:aws:iam::' + account_id + ':role/CMF-AutomationServer'
  # Call the assume_role method of the STSConnection object and pass the role
  # ARN and a role session name.
  try:
    user = sts_client.get_caller_identity()['Arn']
    sessionname = user.split('/')[1]
    response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName=sessionname)
    credentials = response['Credentials']
    session = boto3.Session(
      region_name = region,
      aws_access_key_id=credentials['AccessKeyId'],
      aws_secret_access_key=credentials['SecretAccessKey'],
      aws_session_token=credentials['SessionToken']
    )
    return session
  except botocore.exceptions.ClientError as e:
    print(str(e))
    return None

def uninstall_ads_agents(get_servers, windows_user_name, windows_password, linux_user_name, linux_pass_key, linux_key_exist, linux_secret_name = None, windows_secret_name = None, no_user_prompts = False , hard_uninstall = False):
  print(hard_uninstall)
  hard_uninstall_str = 'No'
  agent_windows_download_url = ''
  if hard_uninstall:
      hard_uninstall_str = 'Yes'
      agent_windows_download_url = "https://s3.us-west-2.amazonaws.com/aws-discovery-agent.us-west-2/windows/latest/AWSDiscoveryAgentInstaller.exe"
  print(hard_uninstall_str)

  try:
    for account in get_servers:
      print("######################################################")
      print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
      print("######################################################")

      # Uninstalling agent on Windows servers
      server_string = ""
      if len(account['servers_windows']) > 0:
        #Get all servers FQDNs into csv for trusted hosts update.
        for server in account['servers_windows']:
          server_string = server_string + server['server_fqdn'] + ','
        server_string = server_string[:-1]
        #Add servers to local trusted hosts to allow authentication if different domain.
        p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + server_string + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for server in account['servers_windows']:
          windows_credentials = mfcommon.getServerCredentials(windows_user_name, windows_password, server, windows_secret_name, no_user_prompts)
          if windows_credentials['username'] != "":
            if "\\" not in windows_credentials['username'] and "@" not in windows_credentials['username']:
              #Assume local account provided, prepend server name to user ID.
              server_name_only = server["server_fqdn"].split(".")[0]
              windows_credentials['username'] = server_name_only + "\\" + windows_credentials['username']
              print("INFO: Using local account to connect: " + windows_credentials['username'])
            else:
              print("INFO: Using domain account to connect: " + windows_credentials['username'])

            p = subprocess.Popen(["powershell.exe",
                    ".\\1-Uninstall-Windows.ps1", server['server_fqdn'], "'" + windows_credentials['username'] + "'", "'" + windows_credentials['password'] + "'", hard_uninstall_str, agent_windows_download_url],
                    stdout=sys.stdout)
          else:
            # User credentials of user executing the script (from remote execution jobs this will be localsystem account and so will not be able to access remote servers)
            p = subprocess.Popen(["powershell.exe",
                    ".\\1-Uninstall-Windows.ps1", server['server_fqdn']],
                    stdout=sys.stdout)
          p.communicate()
      # Uninstalling agent on Linux servers
      if len(account['servers_linux']) > 0:
        for server in account['servers_linux']:
          linux_credentials = mfcommon.getServerCredentials(linux_user_name, linux_pass_key, server, linux_secret_name, no_user_prompts)

          uninstall_linux = linuxpkg.uninstall_ads(server['server_fqdn'], linux_credentials['username'], linux_credentials['password'], linux_credentials['private_key'])
      print("")

  except botocore.exceptions.ClientError as error:
    if ":" in str(error):
      err = ''
      msgs = str(error).split(":")[1:]
      for msg in msgs:
        err = err + msg
      msg = "ERROR: " + err
      print(msg)
      sys.exit()
    else:
      msg = "ERROR: " + str(error)
      print(msg)
      sys.exit()

def main(arguments):
  parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--Waveid', required=True)
  parser.add_argument('--NoPrompts', default=False, type=bool, help='Specify if user prompts for passwords are allowed. Default = False')
  parser.add_argument('--SecretWindows', default=None)
  parser.add_argument('--SecretLinux', default=None)
  parser.add_argument('--HardUninstall', default=False, type=bool)


  args = parser.parse_args(arguments)

  UserHOST = ""
  region = ""
  # Get MF endpoints from FactoryEndpoints.json file
  if 'UserApiUrl' in endpoints:
    UserHOST = endpoints['UserApiUrl']
  else:
    print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
    sys.exit()

  # Get region value from FactoryEndpoint.json file if migration execution server is on prem

  if 'Region' in endpoints:
    region = endpoints['Region']
  else:
    print("ERROR: Invalid FactoryEndpoints.json file, please update region")
    sys.exit()
  print("Factory region: " + region)

  print("")
  print("****************************")
  print("*Login to Migration factory*")
  print("****************************")
  token = mfcommon.Factorylogin()

  print("****************************")
  print("*** Getting Server List ***")
  print("****************************")
  get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST)
  linux_user_name = ''
  linux_pass_key = ''
  linux_key_exist = False

  print("****************************")
  print("****Uninstalling Agents *****")
  print("****************************")
  print("")
  install_agents = uninstall_ads_agents(get_servers, "", "", linux_user_name, linux_pass_key, linux_key_exist, args.SecretLinux, args.SecretWindows, args.NoPrompts, args.HardUninstall)

  time.sleep(5)
  print("All servers have had ADS Agent uninstallation run. Check logs for details.")
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
