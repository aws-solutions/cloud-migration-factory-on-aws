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

import sys
import argparse
import requests
import json
import getpass
import boto3
import botocore

# Constants referenced from other modules.
ce_endpoint = '/api/latest/{}'
ce_address = 'https://console.cloudendure.com'
ce_headers = {'Content-Type': 'application/json'}

serverendpoint = '/prod/user/servers'
appendpoint = '/prod/user/apps'
waveendpoint = '/prod/user/waves'

with open('FactoryEndpoints.json') as json_file:
    mf_config = json.load(json_file)

# common functions
def GetWindowsPassword():
    pass_first = getpass.getpass("Windows User Password: ")
    pass_second = getpass.getpass("Re-enter Password: ")
    while(pass_first != pass_second):
        print("Password mismatch, please try again!")
        pass_first = getpass.getpass("Windows User Password: ")
        pass_second = getpass.getpass("Re-enter Password: ")
    return pass_second

def get_linux_password():
    print("******************************************")
    print("* Enter Linux Sudo username and password *")
    print("******************************************")
    user_name = ''
    pass_key = ''
    has_key = ''
    key_exist = False
    user_name = input("Linux Username: ")
    has_key = input("If you use a private key to login, press [Y] or if use password press [N]: ")
    if 'y' in has_key.lower():
        pass_key = input('Private Key file name: ')
        key_exist = True
    else:
        pass_key_first = getpass.getpass('Linux Password: ')
        pass_key_second = getpass.getpass('Re-enter Password: ')
        while(pass_key_first != pass_key_second):
            print("Password mismatch, please try again!")
            pass_key_first = getpass.getpass('Linux Password: ')
            pass_key_second = getpass.getpass('Re-enter Password: ')
        pass_key = pass_key_second
    print("")
    return user_name, pass_key, key_exist

def Factorylogin():
    username = ""
    password = ""
    using_secret = False
    if 'UserPoolId' in mf_config and 'Region' in mf_config:
        try:
            secretsmanager_client = boto3.client('secretsmanager', mf_config['Region'])
            # mf_service_account_details = secretsmanager_client.describe_secret(SecretId='MFServiceAccount-' + mf_config['UserPoolId'])
            mf_service_account = secretsmanager_client.get_secret_value(SecretId='MFServiceAccount-' + mf_config['UserPoolId'])
            #username = mf_service_account_details['Description']
            mfauth = json.loads(mf_service_account['SecretString'])
            username = mfauth['username']
            password = mfauth['password']
            using_secret = True
        except botocore.exceptions.ClientError as e:
            print(e)
            if e.response['Error']['Code'] == 'ResourceNotFoundException' or e.response['Error']['Code'] == 'AccessDeniedException':
                print("Service Account doesn't exist or access is denied to Secret, please enter username and password")
                if 'DefaultUser' in mf_config:
                    DefaultUser = mf_config['DefaultUser']
                else:
                    DefaultUser = ''
                username = input("Factory Username [" + DefaultUser + "]: ") or DefaultUser
                password = getpass.getpass('Factory Password: ')
    else:
        if 'DefaultUser' in mf_config:
            DefaultUser = mf_config['DefaultUser']
        else:
            DefaultUser = ""
        username = input("Factory Username [" + DefaultUser + "]: ") or DefaultUser
        password = getpass.getpass('Factory Password: ')
    login_data = {'username': username, 'password': password}
    try:
        r = requests.post(mf_config['LoginApiUrl'] + '/prod/login',
                    data=json.dumps(login_data))
        if r.status_code == 200:
            print("Migration Factory : You have successfully logged in")
            print("")
            token = str(json.loads(r.text))
            return token
        if r.status_code == 502 or r.status_code == 400:
            if using_secret:
                print("ERROR: Incorrect username or password stored in Secrets Manager [MFServiceAccount-" + mf_config['UserPoolId'] + "] in region " + mf_config['Region'] + ".")
            else:
                print("ERROR: Incorrect username or password....")
            sys.exit()
        else:
            print(r.text)
            sys.exit()
    except requests.ConnectionError as e:
           raise SystemExit("ERROR: Connecting to the Login API failed, please check Login API in FactoryEndpoints.json file. "
                            "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")

def ServerList(waveid, token, UserHOST, Projectname):
# Get all Apps and servers from migration factory
    auth = {"Authorization": token}
    servers = json.loads(requests.get(UserHOST + serverendpoint, headers=auth).text)
    #print(servers)
    apps = json.loads(requests.get(UserHOST + appendpoint, headers=auth).text)
    #print(apps)

    # Get App list
    applist = []
    for app in apps:
        if 'wave_id' in app:
            if str(app['wave_id']) == str(waveid):
                if Projectname != "":
                    if str(app['cloudendure_projectname']) == str(Projectname):
                        applist.append(app['app_id'])
                else:
                    applist.append(app['app_id'])

    #print(apps)
    #print(servers)
    # Get Server List
    servers_Windows = []
    servers_Linux = []
    for app in applist:
        for server in servers:
            if app == server['app_id']:
                if 'server_os_family' in server:
                    if 'server_fqdn' in server:
                        if server['server_os_family'].lower() == "windows":
                            servers_Windows.append(server)
                        if server['server_os_family'].lower() == "linux":
                            servers_Linux.append(server)
                    else:
                        print("ERROR: server_fqdn for server: " + server['server_name'] + " doesn't exist")
                        sys.exit(4)
                else:
                    print ('server_os_family attribute does not exist for server: ' + server['server_name'] + ", please update this attribute")
                    sys.exit(2)
    if len(servers_Windows) == 0 and len(servers_Linux) == 0:
        print("ERROR: Serverlist for wave: " + waveid + " in CE Project " + Projectname + " is empty....")
        print("")
    else:
        print("successfully retrieved server list")
        print("")
        if len(servers_Windows) > 0:
            print("*** Windows Server List")
            for server in servers_Windows:
                print(server['server_name'])
        else:
            print("*** No Windows Servers")
        print("")
        if len(servers_Linux) > 0:
            print("*** Linux Server List ***")
            print("")
            for server in servers_Linux:
                print(server['server_name'])
        else:
            print("*** No Linux Servers")
        return servers_Windows, servers_Linux

def CElogin(userapitoken):
    login_data = {'userApiToken': userapitoken}
    r = requests.post(ce_address + ce_endpoint.format('login'),
                  data=json.dumps(login_data), headers=ce_headers)
    if r.status_code == 200:
        print("CloudEndure : You have successfully logged in")
        print("")
    if r.status_code != 200 and r.status_code != 307:
        if r.status_code == 401 or r.status_code == 403:
            print('ERROR: The CloudEndure login credentials provided cannot be authenticated....')
            return None, None
        elif r.status_code == 402:
            print('ERROR: There is no active license configured for this CloudEndure account....')
            return None, None
        elif r.status_code == 429:
            print('ERROR: CloudEndure Authentication failure limit has been reached. The service will become available for additional requests after a timeout....')
            return None, None

    # check if need to use a different API entry point
    if r.history:
        endpointnew = '/' + '/'.join(r.url.split('/')[3:-1]) + '/{}'
        r = requests.post(ce_address + endpointnew.format('login'),
                      data=json.dumps(login_data), headers=ce_headers)
    try:
       ce_headers['X-XSRF-TOKEN'] = r.cookies['XSRF-TOKEN']
       return r.cookies['session'], ce_headers['X-XSRF-TOKEN']
    except:
       pass

    return r.cookies['session'], None

def GetCERegion(project_id, ce_session, ce_headers):
    region_ids = []
    rep = requests.get(ce_address + ce_endpoint.format('projects/{}/replicationConfigurations').format(project_id), headers=ce_headers, cookies=ce_session)
    for item in json.loads(rep.text)['items']:
        region = requests.get(ce_address + ce_endpoint.format('cloudCredentials/{}/regions/{}').format(item['cloudCredentials'], item['region']), headers=ce_headers, cookies=ce_session)
        name = json.loads(region.text)['name']
        region_code = ""
        if "Northern Virginia" in name:
            region_code = 'us-east-1'
        elif "Frankfurt" in name:
            region_code = 'eu-central-1'
        elif "Paris" in name:
            region_code = 'eu-west-3'
        elif "Stockholm" in name:
            region_code = 'eu-north-1'
        elif "Northern California" in name:
            region_code = 'us-west-1'
        elif "Oregon" in name:
            region_code = 'us-west-2'
        elif "AWS GovCloud (US)" in name:
            region_code = 'us-gov-west-1'
        elif "Bahrain" in name:
            region_code = 'me-south-1'
        elif "Hong Kong" in name:
            region_code = 'ap-east-1'
        elif "Tokyo" in name:
            region_code = 'ap-northeast-1'
        elif "Singapore" in name:
            region_code = 'ap-southeast-1'
        elif "AWS GovCloud (US-East)" in name:
            region_code = 'us-gov-east-1'
        elif "Mumbai" in name:
            region_code = 'ap-south-1'
        elif "South America" in name:
            region_code = 'sa-east-1'
        elif "Sydney" in name:
            region_code = 'ap-southeast-2'
        elif "London" in name:
            region_code = 'eu-west-2'
        elif "Central" in name:
            region_code = 'ca-central-1'
        elif "Ireland" in name:
            region_code = 'eu-west-1'
        elif "Seoul" in name:
            region_code = 'ap-northeast-2'
        elif "Ohio" in name:
            region_code = 'us-east-2'
        else:
            print("Incorrect Region Name")
        region_ids.append(region_code)
    return region_ids

#Function is used with new MGN capabiltiy to get servers based on the AWS account they are targeted to.
def get_factory_servers(waveid, token, UserHOST, osSplit = True):
    try:
        linux_exist = False
        windows_exist = False
        auth = {"Authorization": token}
        # Get all Apps and servers from migration factory
        getservers = json.loads(requests.get(UserHOST + serverendpoint, headers=auth).text)
        #print(servers)
        getapps = json.loads(requests.get(UserHOST + appendpoint, headers=auth).text)
        #print(apps)
        servers = sorted(getservers, key = lambda i: i['server_name'])
        apps = sorted(getapps, key = lambda i: i['app_name'])

        # Get Unique target AWS account and region
        aws_accounts = []
        for app in apps:
            if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                if str(app['wave_id']) == str(waveid):
                    if len(str(app['aws_accountid']).strip()) == 12:
                        target_account = {}
                        target_account['aws_accountid'] = str(app['aws_accountid']).strip()
                        target_account['aws_region'] = app['aws_region'].lower().strip()
                        if osSplit:
                            target_account['servers_windows'] = []
                            target_account['servers_linux'] = []
                        else:
                            target_account['servers'] = []
                        if target_account not in aws_accounts:
                            aws_accounts.append(target_account)
                    else:
                        msg = "ERROR: Incorrect AWS Account Id Length for app: " + app['app_name']
                        print(msg)
                        sys.exit()
        if len(aws_accounts) == 0:
            msg = "ERROR: Server list for wave " + waveid + " is empty...."
            print(msg)
            sys.exit()

        # Get server list
        for account in aws_accounts:
            print("### Servers in Target Account: " + account['aws_accountid'] + " , region: " + account['aws_region'] + " ###")
            for app in apps:
                if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                    if str(app['wave_id']) == str(waveid):
                        if str(app['aws_accountid']).strip() == str(account['aws_accountid']):
                            if app['aws_region'].lower().strip() == account['aws_region']:
                                for server in servers:
                                    if 'app_id' in server:
                                        if server['app_id'] == app['app_id']:
                                            # verify server_os_family attribute, only accepts Windows or Linux
                                            if 'server_os_family' in server:
                                                # Verify server_fqdn, this is mandatory attribute
                                                if 'server_fqdn' in server:
                                                    if osSplit:
                                                        if server['server_os_family'].lower() == 'windows':
                                                            account['servers_windows'].append(server)
                                                        elif server['server_os_family'].lower() == 'linux':
                                                            account['servers_linux'].append(server)
                                                        else:
                                                            print("ERROR: Invalid server_os_family for: " + server['server_name'] + ", please select either Windows or Linux")
                                                            sys.exit()
                                                    else:
                                                        account['servers'].append(server)
                                                    print(server['server_fqdn'])
                                                else:
                                                    print("ERROR: server_fqdn for server: " + server['server_name'] + " doesn't exist")
                                                    sys.exit()
                                            else:
                                                print("ERROR: server_os_family does not exist for: " + server['server_name'])
                                                sys.exit()
            print("")
            if osSplit:
                # Check if the server list is empty for both Windows and Linux
                if len(account['servers_windows']) == 0 and len(account['servers_linux']) == 0:
                    msg = "ERROR: Server list for wave " + waveid + " and account: " + account['aws_accountid'] + " region: " + account['aws_region'] + " is empty...."
                    print(msg)
                    sys.exit()
                if len(account['servers_linux']) > 0:
                   linux_exist = True
                if len(account['servers_windows']) > 0:
                   windows_exist = True
            else:
                if len(account['servers']) == 0:
                    msg = "ERROR: Server list for wave " + waveid + " and account: " + account['aws_accountid'] + " region: " + account['aws_region'] + " is empty...."
                    print(msg)
                    sys.exit()
        if osSplit:
            return aws_accounts, linux_exist, windows_exist
        else:
            return aws_accounts
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

def get_MGN_Source_Server(factoryserver, mgn_sourceservers):
    lsourceserver = None

    for sourceserver in mgn_sourceservers:
        if sourceserver['isArchived'] == False:
            # Check if the factory server exist in Application Migration Service
            #Check if IP address is matching any on record.
            if 'networkInterfaces' in sourceserver['sourceProperties']:
                for interface in sourceserver['sourceProperties']['networkInterfaces']:
                    if interface['isPrimary'] is True:
                        for ips in interface['ips']:
                            if factoryserver['server_name'].lower().strip() == ips.lower().strip():
                                lsourceserver = sourceserver
                                break
                            elif factoryserver['server_fqdn'].lower().strip() == ips.lower().strip():
                                lsourceserver = sourceserver
                                break
                    if lsourceserver is not None:
                        break

            if factoryserver['server_name'].lower().strip() == sourceserver['sourceProperties']['identificationHints']['hostname'].lower().strip():
                lsourceserver = sourceserver
            elif factoryserver['server_name'].lower().strip() == sourceserver['sourceProperties']['identificationHints']['fqdn'].lower().strip():
                lsourceserver = sourceserver
            elif factoryserver['server_fqdn'].lower().strip() == sourceserver['sourceProperties']['identificationHints']['hostname'].lower().strip():
                lsourceserver = sourceserver
            elif factoryserver['server_fqdn'].lower().strip() == sourceserver['sourceProperties']['identificationHints']['fqdn'].lower().strip():
                lsourceserver = sourceserver

    if lsourceserver is not None:
        return lsourceserver
    else:
        return None
