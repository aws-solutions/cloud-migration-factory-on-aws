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

# Version: 29MAY2022.01

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
import os
import threading

linuxpkg = __import__("1-Install-Linux")

with open('FactoryEndpoints.json') as json_file:
  endpoints = json.load(json_file)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

# for storing the response from each thread
ll = []

# Run multiple agent installations in parallel
def create_parallel_job(parameters):
  th = threading.Thread(target=lambda q, parameters: ll.append(parameters["function_name"](parameters)),
                        args=(ll, parameters), name=parameters["server"]["server_fqdn"])
  th.start()
  return th

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

#Pagination for describe MGN source servers
def get_mgn_source_servers(mgn_client_base):
  token = None
  source_server_data = []
  paginator = mgn_client_base.get_paginator('describe_source_servers')
  while True:
    response = paginator.paginate(filters={},
                                  PaginationConfig={
                                    'StartingToken': token})
    for page in response:
      source_server_data.extend(page['items'])
    try:
      token = page['NextToken']
      print(token)
    except KeyError:
      return source_server_data

def install_mgn_agents_for_windows(parameters):
  windows_user_name = parameters["windows_user_name"]
  windows_password = parameters["windows_password"]
  server = parameters["server"]
  windows_secret_name = parameters["windows_secret_name"]
  no_user_prompts = parameters["no_user_prompts"]
  reinstall = parameters["reinstall"]
  agent_windows_download_url = parameters["agent_windows_download_url"]
  aws_region = parameters["aws_region"]
  agent_install_secrets = parameters["agent_install_secrets"]


  windows_credentials = mfcommon.getServerCredentials(windows_user_name, windows_password, server, windows_secret_name,
                                                      no_user_prompts)

  if windows_credentials['username'] != "":
    if "\\" not in windows_credentials['username'] and "@" not in windows_credentials['username']:
      #Assume local account provided, prepend server name to user ID.
      server_name_only = server["server_fqdn"].split(".")[0]
      windows_credentials['username'] = server_name_only + "\\" + windows_credentials['username']
      print("INFO: Using local account to connect: " + windows_credentials['username'])
    else:
      print("INFO: Using domain account to connect: " + windows_credentials['username'])

    # Added Fix for escaping special characters in password. Error: The ampersand (&) character is not allowed.
    # The & operator is reserved for future use; wrap an ampersand in double quotation marks ("&") to
    # pass it as part of a string.
    p = subprocess.Popen(["powershell.exe",
                          ".\\1-Install-Windows.ps1", reinstall, agent_windows_download_url, aws_region,
                          agent_install_secrets['AccessKeyId'], agent_install_secrets['SecretAccessKey'],
                          server['server_fqdn'], windows_credentials['username'], "\""+windows_credentials['password']+"\""],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
  else:
    # User credentials of user executing the script (from remote execution jobs this will be localsystem account and
    # so will not be able to access remote servers)
    p = subprocess.Popen(["powershell.exe",
                          ".\\1-Install-Windows.ps1", reinstall, agent_windows_download_url, aws_region,
                          agent_install_secrets['AccessKeyId'], agent_install_secrets['SecretAccessKey'],
                          server['server_fqdn']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

  return server['server_fqdn'], p

def install_mgn_agents_for_linux(parameters):
  linux_user_name = parameters["linux_user_name"]
  linux_pass_key = parameters["linux_pass_key"]
  server = parameters["server"]
  linux_secret_name = parameters["linux_secret_name"]
  agent_linux_download_url = parameters["agent_linux_download_url"]
  aws_region = parameters["aws_region"]
  no_user_prompts = parameters["no_user_prompts"]
  agent_install_secrets = parameters["agent_install_secrets"]

  linux_credentials = mfcommon.getServerCredentials(linux_user_name, linux_pass_key, server, linux_secret_name,
                                                    no_user_prompts)
  install_linux_output_queue = linuxpkg.install_mgn(agent_linux_download_url, aws_region, server['server_fqdn'],
                                       linux_credentials['username'], linux_credentials['password'],
                                       linux_credentials['private_key'], agent_install_secrets['AccessKeyId'],
                                       agent_install_secrets['SecretAccessKey'])
  if os.path.isfile(linux_credentials['password']):
    os.remove(linux_credentials['password'])
  print("", flush = True)

  return install_linux_output_queue

def install_mgn_agents(force, get_servers, region, windows_user_name, windows_password, linux_user_name, linux_pass_key,
                       linux_key_exist, linux_secret_name = None, windows_secret_name = None, no_user_prompts = False ):
  try:
    if region != '':
      reinstall = 'No'
      if force == True:
        reinstall = 'Yes'

      #agent installation parameters
      parameters = {
        "windows_user_name"   : windows_user_name,
        "windows_password"    : windows_password,
        "windows_secret_name" : windows_secret_name,
        "linux_user_name"     : linux_user_name,
        "linux_pass_key"      : linux_pass_key,
        "linux_key_exist"     : linux_key_exist,
        "linux_secret_name"   : linux_secret_name,
        "no_user_prompts"     : no_user_prompts,
        "reinstall"           : reinstall,
      }

      # List to store all threads associated with an agent installation
      threadLists = []

      for account in get_servers:
        print("######################################################")
        print("#### In Account: " + account['aws_accountid'], ", region: " + account['aws_region'] + " ####")
        print("######################################################", flush = True)
        target_account_session = assume_role(str(account['aws_accountid']), region)
        if target_account_session is None:
          #Assume role failed continue to next account, as cannot access IAM user for install.
          continue
        secretsmanager_client = target_account_session.client('secretsmanager', region)
        parameters["agent_install_secrets"] = json.loads(secretsmanager_client.get_secret_value
                                                         (SecretId='MGNAgentInstallUser')['SecretString'])
        parameters["aws_region"] = account["aws_region"]

        # Installing agent on Windows servers
        server_string = ""
        if len(account['servers_windows']) > 0:
          parameters["agent_windows_download_url"] = "https://aws-application-migration-service-{}.s3.amazonaws.com/" \
                                                     "latest/windows/AwsReplicationWindowsInstaller." \
                                                     "exe".format(account['aws_region'])


          #Get all servers FQDNs into csv for trusted hosts update.
          for server in account['servers_windows']:
            server_string = server_string + server['server_fqdn'] + ','
          server_string = server_string[:-1]
          #Add servers to local trusted hosts to allow authentication if different domain.
          p_trustedhosts = subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '"
                                             + server_string + "' -Concatenate -Force"], stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)

          for server in account['servers_windows']:
            parameters["function_name"] = install_mgn_agents_for_windows
            parameters["server"] = server
            # Append the thread details to the list
            threadLists.append(create_parallel_job(parameters))

        # Installing agent on Linux servers
        if len(account['servers_linux']) > 0:
          parameters["agent_linux_download_url"] = "https://aws-application-migration-service-{}.s3.amazonaws.com" \
                                                   "/latest/linux/aws-replication-installer-init.py" \
                                                   "".format(account['aws_region'])
          for server in account['servers_linux']:
            parameters["function_name"] = install_mgn_agents_for_linux
            parameters["server"] = server
            # Append the thread details to the list
            threadLists.append(create_parallel_job(parameters))

        # Waiting for all threads to finish
        print("Waiting for agent installation on all servers to finish")
        print("", flush=True)

        #Printing all the responses to console
        total_servers = len(account['servers_linux']) + len(account['servers_windows'])
        total_servers_pending = total_servers
        #List of threads whose output is already pushed to console
        completed_threads = []
        #While there are active threads running
        while total_servers_pending > 0:
          time.sleep(5)
          for thread in threadLists:
            if not thread.is_alive():
              #If this is a newly completed thread, add it to the list and print its output
              if not thread.getName() in completed_threads:
                print("\n", flush=True)
                print("************************************************************")
                print("**** Servers pending Agent Installation: " + str(total_servers_pending) + "/" + str(total_servers)
                      + " ****")
                print("************************************************************")

                for completed_thread_output in ll:
                  host,result=completed_thread_output
                  # If the completed threads name matches with the hostname, print the output on the console.
                  if thread.getName() == host:
                    completed_threads.append(thread.getName())
                    total_servers_pending = total_servers_pending - 1
                    #checks for windows and linux
                    if 'subprocess.Popen' in str(type(result)):
                      stdout,stderr = result.communicate()
                      print(stdout)
                      print(stderr)
                    else:
                      print(result)
                  print("", flush = True)
            else:
              time.sleep(5)
              #print("|", end=' ', flush=True)

        for thread in threadLists:
          thread.join()
    else:
      print("ERROR: Invalid or empty factory region", flush = True)
      sys.exit()

  except botocore.exceptions.ClientError as error:
    if ":" in str(error):
      err = ''
      msgs = str(error).split(":")[1:]
      for msg in msgs:
        err = err + msg
      msg = "ERROR: " + err
      print(msg)
      sys.exit(1)
    else:
      msg = "ERROR: " + str(error)
      print(msg)
      sys.exit(1)

def AgentCheck(get_servers, UserHOST, token):
  try:
    failures = 0
    auth = {"Authorization": token}
    for account in get_servers:
      target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
      mgn_client = target_account_session.client("mgn", account['aws_region'])
      mgn_sourceservers = get_mgn_source_servers(mgn_client)
      all_servers = account['servers_windows'] + account['servers_linux']
      for factoryserver in all_servers:
        serverattr = {}
        isServerExist = False

        sourceserver = mfcommon.get_MGN_Source_Server(factoryserver, mgn_sourceservers)

        if sourceserver is not None:
          print("-- SUCCESS: Agent installed on server: " + factoryserver['server_fqdn'])
          serverattr = {"migration_status": "Agent Install - Success"}
        else:
          print("-- FAILED: Agent install failed on server: " + factoryserver['server_fqdn'])
          serverattr = {"migration_status": "Agent Install - Failed"}
          failures += 1

        update_server_status = requests.put(UserHOST + serverendpoint + '/' + factoryserver['server_id'], headers=auth, data=json.dumps(serverattr))
        print("", flush = True)

    return failures
  except botocore.exceptions.ClientError as error:
    if ":" in str(error):
      err = ''
      msgs = str(error).split(":")[1:]
      for msg in msgs:
        err = err + msg
      msg = "ERROR: " + err
      print(msg)
    else:
      msg = "ERROR: " + str(error)
      print(msg)
    return 1

def main(arguments):
  parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument('--Waveid', required=True)
  parser.add_argument('--Force', default=False)
  parser.add_argument('--NoPrompts', default=False, type=bool, help='Specify if user prompts for passwords are allowed. Default = False')
  parser.add_argument('--SecretWindows', default=None)
  parser.add_argument('--SecretLinux', default=None)
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
  print("****************************", flush=True)
  token = mfcommon.Factorylogin()

  print("****************************")
  print("*** Getting Server List ***")
  print("****************************", flush=True)
  get_servers, linux_exist, windows_exist = mfcommon.get_factory_servers(args.Waveid, token, UserHOST, True, 'Rehost')
  linux_user_name = ''
  linux_pass_key = ''
  linux_key_exist = False

  print("****************************")
  print("**** Installing Agents *****")
  print("****************************")
  print("", flush=True)
  install_agents = install_mgn_agents(args.Force, get_servers, region, "", "", linux_user_name, linux_pass_key, linux_key_exist, args.SecretLinux, args.SecretWindows, args.NoPrompts)

  print("")
  print("********************************")
  print("*Checking Agent install results*")
  print("********************************")
  print("", flush=True)

  time.sleep(5)
  failure_count = AgentCheck(get_servers, UserHOST, token)

  if (failure_count > 0):
    print( str(failure_count) + " servers failed to install MGN agents. Check log for details.")
    return 1
  else:
    print("All servers have had MGN Agents installed successfully.")
    return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
