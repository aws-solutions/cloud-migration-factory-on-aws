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

# Version: 17NOV2021.01

import sys
import requests
import json
import getpass
import boto3
import botocore
import base64
import calendar
import time
import subprocess
import csv
import logging

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=logging.ERROR)
logger = logging.getLogger()
logger.setLevel(logging.ERROR)

if not sys.warnoptions:
    import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=Warning)
    import paramiko

ts = calendar.timegm(time.gmtime())
# Constants referenced from other modules.
ce_endpoint = '/api/latest/{}'
ce_address = 'https://console.cloudendure.com'
ce_headers = {'Content-Type': 'application/json'}

serverendpoint = '/prod/user/server'
appendpoint = '/prod/user/app'
waveendpoint = '/prod/user/wave'

credentials_store = {}

with open('FactoryEndpoints.json') as json_file:
    mf_config = json.load(json_file)


# common functions
def GetWindowsPassword():
    pass_first = getpass.getpass("Windows User Password: ")
    pass_second = getpass.getpass("Re-enter Password: ")
    while (pass_first != pass_second):
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
        while (pass_key_first != pass_key_second):
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
            mf_service_account = secretsmanager_client.get_secret_value(
                SecretId='MFServiceAccount-' + mf_config['UserPoolId'])
            # username = mf_service_account_details['Description']
            mfauth = json.loads(mf_service_account['SecretString'])
            username = mfauth['username']
            password = mfauth['password']
            using_secret = True
        except botocore.exceptions.ClientError as e:
            print(e)
            if e.response['Error']['Code'] == 'ResourceNotFoundException' or e.response['Error'][
                'Code'] == 'AccessDeniedException':
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
        r = factory_login(login_data)

        if 'body' in r:
            r_content = json.loads(r['body'])
        else:
            r_content = ''

        if r['statusCode'] == 200 and 'ChallengeName' in r_content:
            if 'ChallengeName' in r_content and r_content['ChallengeName'] == 'SMS_MFA':
                try:
                    one_time_code = input("Please provide MFA One Time Code: ")
                except EOFError as MFA_input_error:
                    print("", flush=True)
                    print("ERROR: MFA is enabled for the service account; this is not supported when used with "
                          "CMF automation, if MFA is required, scripts must be run from the command line of the "
                          "automation server.", flush=True)
                    sys.exit(1)
                mfa_challenge_data = {'username': username, 'mfacode': one_time_code, 'session': r_content['Session']}
                # r_mfa = requests.post(mf_config['LoginApiUrl'] + '/prod/login',
                #                       data=json.dumps(mfa_challenge_data))
                r_mfa = factory_login(mfa_challenge_data)
                if r_mfa['statusCode'] == 200:
                    print("Migration Factory : You have successfully logged in")
                    print("")
                    token = str(json.loads(r_mfa['body']))
                    return token
                if r_mfa['statusCode'] == 502 or r_mfa['statusCode'] == 400:
                    print("ERROR: Incorrect MFA One Time Code provided....")
                    sys.exit(1)
        elif r['statusCode'] == 200:
            print("Migration Factory : You have successfully logged in")
            print("")
            token = str(r_content)
            return token

        if r['statusCode'] == 502 or r['statusCode'] == 400:
            if using_secret:
                print("ERROR: Incorrect username or password stored in Secrets Manager [MFServiceAccount-" + mf_config[
                    'UserPoolId'] + "] in region " + mf_config['Region'] + ".")
            else:
                print("ERROR: Incorrect username or password....")
            sys.exit(1)
        else:
            print(r['text'])
            sys.exit()
    except requests.ConnectionError as e:
        raise SystemExit(
            "ERROR: Connecting to the Login API failed, please check Login API in FactoryEndpoints.json file. "
            "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")


def getServerCredentials(local_username, local_password, server, secret_overide=None, no_user_prompts=False):
    username = ""
    password = ""
    secret_name = ""
    using_secret = False

    # Local account details passed, do not get from secrets manager.
    if local_username != "" and local_password != "":
        return {'username': local_username, 'password': local_password}

    ##  If secret has been provided then use this instead of checking server record.
    if secret_overide is not None:
        secret_name = secret_overide
    elif "secret_name" in server and server['secret_name'] != "":
        secret_name = server['secret_name']
        print("Server specific secret configured, using: " + secret_name)

    if secret_name != "":

        # Check if already read secret, and if so return cached.
        if 'cached_secret:' + secret_name in credentials_store:
            return credentials_store['cached_secret:' + secret_name]

        try:
            secretsmanager_client = boto3.client('secretsmanager', mf_config['Region'])
            mf_service_account = secretsmanager_client.get_secret_value(SecretId=secret_name)

            secret_data_raw = mf_service_account['SecretString']

            secret_data = None
            mfauth = None

            if secret_data_raw[0] != "{":
                # Secret could be encoded, perform decode.
                secret_data_tmp = base64.b64decode(secret_data_raw.encode("utf-8")).decode("ascii")
                secret_data_tmp_json = json.loads(secret_data_tmp)
            else:
                secret_data_tmp_json = json.loads(secret_data_raw)

            secret_data = {}
            if "USERNAME" in secret_data_tmp_json:
                secret_data['username'] = secret_data_tmp_json['USERNAME']
            else:
                secret_data['username'] = ""
            if "PASSWORD" in secret_data_tmp_json:
                if "IS_SSH_KEY" in secret_data_tmp_json and secret_data_tmp_json['IS_SSH_KEY'].lower() == 'true':
                    secret_data['password'] = base64.b64decode(secret_data_tmp_json['PASSWORD'].encode("utf-8")) \
                        .decode("ascii")
                    secret_data['password'] = secret_data['password'].replace('\\n', '\n')
                    secret_data['private_key'] = True
                else:
                    secret_data['password'] = secret_data_tmp_json['PASSWORD']
                    secret_data['private_key'] = False
            else:
                secret_data['password'] = ""
            if "SECRET_TYPE" in secret_data_tmp_json:
                secret_data['secret_type'] = secret_data_tmp_json['SECRET_TYPE']
            else:
                secret_data['secret_type'] = ""
            if "OS_TYPE" in secret_data_tmp_json:
                secret_data['os_type'] = secret_data_tmp_json['OS_TYPE']
            else:
                secret_data['os_type'] = ""

            mfauth = secret_data

            using_secret = True

            # Cache secret for next server.
            credentials_store['cached_secret:' + secret_name] = mfauth

            return mfauth
        except botocore.exceptions.ClientError as e:
            print(e)
            if e.response['Error']['Code'] == 'ResourceNotFoundException' or e.response['Error'][
                'Code'] == 'AccessDeniedException':
                if no_user_prompts == True:
                    print(
                        "Secret not found [" + server['secret_name'] + "] doesn't exist or access is denied to Secret.")
                else:
                    print("Secret not found [" + server[
                        'secret_name'] + "] doesn't exist or access is denied to Secret, please enter username and password")
            else:
                # Unknown error returned when getting secret.
                print(e.response['Error'])

    if server['server_os_family'].lower() == "windows":
        if 'windows' in credentials_store:
            return credentials_store['windows']
        if no_user_prompts == False:
            print(
                "No Windows credentials supplied by user or specified in Migration Factory server secret attribute. Please enter credentials now.")
            username = input("Windows Username (leave blank to use current logged on user): ")
            if username != "":
                password = GetWindowsPassword()
            else:
                password = ""
            store_cred = input(
                "Do you wish to use the same credentials for all Windows servers in the job?, press [Y] or if you wish to be prompted per server [N]: ")
            credentials = {'username': username, 'password': password}
            if 'y' in store_cred.lower():
                credentials_store['windows'] = credentials
            return credentials
    if server['server_os_family'].lower() == "linux":
        if 'linux' in credentials_store:
            return credentials_store['linux']
        if no_user_prompts == False:
            print(
                "No Linux credentials supplied by user or specified in Migration Factory server secret attribute. Please enter credentials now.")
            username, password, key_exist = get_linux_password()
            store_cred = input(
                "Do you wish to use the same credentials for all Linux servers in the job?, press [Y] or if you wish to be prompted per server [N]: ")
            credentials = {'username': username, 'password': password, 'private_key': key_exist}
            if 'y' in store_cred.lower():
                credentials_store['linux'] = credentials
            return credentials

    if no_user_prompts == True:
        print(
            "No credentials supplied by user or specified in Migration Factory server secret attribute. Returning blank username and password")
        return {'username': '', 'password': ''}


def getCredentials(secret_name, no_user_prompts=True):
    if secret_name != "":

        # Check if already read secret, and if so return cached.
        if 'cached_secret:' + secret_name in credentials_store:
            return credentials_store['cached_secret:' + secret_name]

        try:
            secretsmanager_client = boto3.client('secretsmanager', mf_config['Region'])
            mf_service_account = secretsmanager_client.get_secret_value(SecretId=secret_name)

            secret_data_raw = mf_service_account['SecretString']

            secret_data = None
            mfauth = None

            if secret_data_raw[0] != "{":
                # Secret could be encoded, perform decode.
                secret_data_tmp = base64.b64decode(secret_data_raw.encode("utf-8")).decode("ascii")
                secret_data_tmp_json = json.loads(secret_data_tmp)
            else:
                secret_data_tmp_json = json.loads(secret_data_raw)

            secret_data = {}
            if "USERNAME" in secret_data_tmp_json:
                secret_data['username'] = secret_data_tmp_json['USERNAME']
            else:
                secret_data['username'] = ""
            if "PASSWORD" in secret_data_tmp_json:
                if "IS_SSH_KEY" in secret_data_tmp_json and secret_data_tmp_json['IS_SSH_KEY'].lower() == 'true':
                    secret_data['password'] = base64.b64decode(secret_data_tmp_json['PASSWORD'].encode("utf-8")) \
                        .decode("ascii")
                    secret_data['password'] = secret_data['password'].replace('\\n', '\n')
                    secret_data['private_key'] = True
                else:
                    secret_data['password'] = secret_data_tmp_json['PASSWORD']
                    secret_data['private_key'] = False
            else:
                secret_data['password'] = ""
            if "SECRET_TYPE" in secret_data_tmp_json:
                secret_data['secret_type'] = secret_data_tmp_json['SECRET_TYPE']
            else:
                secret_data['secret_type'] = ""
            if "SECRET_KEY" in secret_data_tmp_json:
                secret_data['secret_key'] = secret_data_tmp_json['SECRET_KEY']
            else:
                secret_data['secret_key'] = ""
            if "SECRET_VALUE" in secret_data_tmp_json:
                secret_data['secret_value'] = secret_data_tmp_json['SECRET_VALUE']
            else:
                secret_data['secret_value'] = ""
            if "APIKEY" in secret_data_tmp_json:
                secret_data['api_key'] = secret_data_tmp_json['APIKEY']
            else:
                secret_data['api_key'] = ""
            if "SECRET_STRING" in secret_data_tmp_json:
                secret_data['secret_string'] = secret_data_tmp_json['SECRET_STRING']
            else:
                secret_data['secret_string'] = ""
            if "OS_TYPE" in secret_data_tmp_json:
                secret_data['os_type'] = secret_data_tmp_json['OS_TYPE']
            else:
                secret_data['os_type'] = ""

            mfauth = secret_data

            # Cache secret for next server.
            credentials_store['cached_secret:' + secret_name] = mfauth

            return mfauth
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException' or e.response['Error'][
                'Code'] == 'AccessDeniedException':
                if no_user_prompts:
                    print(
                        "Secret not found [" + secret_name + "] doesn't exist or access is denied to Secret.")
                else:
                    print("Secret not found [" + secret_name +
                          "] doesn't exist or access is denied to Secret, please enter username and password")
            else:
                # Unknown error returned when getting secret.
                print(e.response['Error'])

    if no_user_prompts:
        print("No secret specified. Returning blank username and password")
        return {'username': '', 'password': ''}


def ServerList(waveid, token, UserHOST, Projectname):
    # Get all Apps and servers from migration factory
    auth = {"Authorization": token}
    servers = json.loads(requests.get(UserHOST + serverendpoint, headers=auth).text)
    # print(servers)
    apps = json.loads(requests.get(UserHOST + appendpoint, headers=auth).text)

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

    # print(apps)
    # print(servers)
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
                    print('server_os_family attribute does not exist for server: ' + server[
                        'server_name'] + ", please update this attribute")
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
            print(
                'ERROR: CloudEndure Authentication failure limit has been reached. The service will become available for additional requests after a timeout....')
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
    rep = requests.get(ce_address + ce_endpoint.format('projects/{}/replicationConfigurations').format(project_id),
                       headers=ce_headers, cookies=ce_session)
    for item in json.loads(rep.text)['items']:
        region = requests.get(
            ce_address + ce_endpoint.format('cloudCredentials/{}/regions/{}').format(item['cloudCredentials'],
                                                                                     item['region']),
            headers=ce_headers, cookies=ce_session)
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


# Function is used with new MGN capabiltiy to get servers based on the AWS account they are targeted to.
def get_factory_servers(waveid, token, UserHOST, osSplit=True, rtype=None):
    try:
        linux_exist = False
        windows_exist = False
        auth = {"Authorization": token}
        # Get all Apps and servers from migration factory
        getservers = json.loads(requests.get(UserHOST + serverendpoint, headers=auth).text)
        # print(servers)
        getapps = json.loads(requests.get(UserHOST + appendpoint, headers=auth).text)
        # print(apps)
        servers = sorted(getservers, key=lambda i: i['server_name'])
        apps = sorted(getapps, key=lambda i: i['app_name'])

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
            print("### Servers in Target Account: " + account['aws_accountid'] + " , region: " + account[
                'aws_region'] + " ###")
            for app in apps:
                if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                    if str(app['wave_id']) == str(waveid):
                        if str(app['aws_accountid']).strip() == str(account['aws_accountid']):
                            if app['aws_region'].lower().strip() == account['aws_region']:
                                for server in servers:
                                    if (rtype is None) or ('r_type' in server and server['r_type'] == rtype):
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
                                                                print("ERROR: Invalid server_os_family for: " + server[
                                                                    'server_name'] + ", please select either Windows or Linux")
                                                                sys.exit()
                                                        else:
                                                            account['servers'].append(server)
                                                        print(server['server_fqdn'])
                                                    else:
                                                        print("ERROR: server_fqdn for server: " + server[
                                                            'server_name'] + " doesn't exist")
                                                        sys.exit()
                                                else:
                                                    print("ERROR: server_os_family does not exist for: " + server[
                                                        'server_name'])
                                                    sys.exit()
            print("")
            if osSplit:
                # Check if the server list is empty for both Windows and Linux
                if len(account['servers_windows']) == 0 and len(account['servers_linux']) == 0:
                    msg = "ERROR: Server list for wave " + waveid + " and account: " + account[
                        'aws_accountid'] + " region: " + account['aws_region'] + " is empty...."
                    print(msg)
                    sys.exit()
                if len(account['servers_linux']) > 0:
                    linux_exist = True
                if len(account['servers_windows']) > 0:
                    windows_exist = True
            else:
                if len(account['servers']) == 0:
                    msg = "ERROR: Server list for wave " + waveid + " and account: " + account[
                        'aws_accountid'] + " region: " + account['aws_region'] + " is empty...."
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
            # Check if IP address is matching any on record.
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

            if factoryserver['server_name'].lower().strip() == sourceserver['sourceProperties']['identificationHints'][
                'hostname'].lower().strip():
                lsourceserver = sourceserver
            elif factoryserver['server_name'].lower().strip() == \
                sourceserver['sourceProperties']['identificationHints']['fqdn'].lower().strip():
                lsourceserver = sourceserver
            elif factoryserver['server_fqdn'].lower().strip() == \
                sourceserver['sourceProperties']['identificationHints']['hostname'].lower().strip():
                lsourceserver = sourceserver
            elif factoryserver['server_fqdn'].lower().strip() == \
                sourceserver['sourceProperties']['identificationHints']['fqdn'].lower().strip():
                lsourceserver = sourceserver

    if lsourceserver is not None:
        return lsourceserver
    else:
        return None


def execute_external_script(command):
    print("Executing an external script " + command)
    try:
        result = subprocess.run(
            command, capture_output=True, timeout=120
        )
        output = result.stderr.decode("utf-8")
        error = result.stdout.decode("utf-8")
        if "ERROR" in error or "Error" in error:
            print("Failed to run the external script: " + command)
            print(error)
            return False
        if result.stdout != "":
            print(output)
            return True
    except ValueError as e:
        print("Exception while executing script: " + command)
        return False


def execute_cmd(host, username, key, cmd, using_key):
    output = ''
    error = ''
    ssh = None
    try:
        ssh = open_ssh(host, username, key, using_key)
        if ssh is None:
            error = "Not able to get the SSH connection for the host " + host
            print(error, flush=True)
        else:
            stdin, stdout, stderr = ssh.exec_command(cmd)  # nosec B601
            for line in stdout.readlines():
                output = output + line
            for line in stderr.readlines():
                error = error + line
    except IOError as io_error:
        error = "Unable to execute the command " + cmd + " due to " + \
                str(io_error)
        print(error, flush=True)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to execute the command " + cmd + " due to " + \
                str(ssh_exception)
        print(error, flush=True)
    finally:
        if ssh is not None:
            ssh.close()
    return output, error


def open_ssh(host, username, key_pwd, using_key):
    ssh = None
    try:
        if using_key:
            from io import StringIO
            private_key = paramiko.RSAKey.from_private_key(StringIO(key_pwd))
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, pkey=private_key)
        else:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, password=key_pwd)
    except IOError as io_error:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(io_error)
        print(error)
    except paramiko.SSHException as ssh_exception:
        error = "Unable to connect to host " + host + " with username " + \
                username + " due to " + str(ssh_exception)
        print(error)
    return ssh


# Function to print the status in csv format.
def create_csv_report(report_name, agent_installed_server_details, wave_id):
    final_report_name_csv = "cmf-" + report_name + "-report_Wave_" + wave_id + ".csv"

    iterator = map(convert_dictionaries_keys_to_list, agent_installed_server_details)
    fields = list(iterator)[0]
    iterator = map(convert_dictionaries_values_to_list, agent_installed_server_details)
    row = list(iterator)

    # Workaround for software service validation report. First row in this report is an unwanted data. This row was
    # generated just to get the dynamic csv header properly.
    if report_name == "serviceValdationReport":
        row.pop(0)

    with open(final_report_name_csv, 'w', newline="") as f:
        # using csv.writer method from CSV package
        write = csv.writer(f)
        write.writerow(fields)
        write.writerows(row)

    print("")
    print("**************************************************************************************************")
    print("Please check the status in the generated report...")
    print("Validation Overview CSV : " + final_report_name_csv)
    return final_report_name_csv


# Function to convert a dictionaries keys into list format required by csv module
def convert_dictionaries_keys_to_list(var):
    return (list(var.keys()))


# Function to convert a dictionaries values into list format required by csv module
def convert_dictionaries_values_to_list(var):
    return (list(var.values()))


# Function provides authentication of user credentials to the CMF Cognito user pool directly rather than via the CMF
# /prod/login endpoint. This is required for instances using WAF.
def factory_login(auth_data):
    if 'UserPoolId' in mf_config and 'Region' in mf_config:

        try:
            body = auth_data
            client = boto3.client('cognito-idp', mf_config['Region'])

            if 'mfacode' in body:
                # This is a response to MFA request on previous login attempt.
                userid = body['username']
                mfacode = body['mfacode']
                session = body['session']
                response = client.respond_to_auth_challenge(
                    ClientId=mf_config['UserPoolClientId'],
                    ChallengeName='SMS_MFA',
                    Session=session,
                    ChallengeResponses={
                        'SMS_MFA_CODE': mfacode,
                        'USERNAME': userid
                    }
                )
            else:
                userid = body['username']
                password = body['password']
                response = client.initiate_auth(
                    ClientId=mf_config['UserPoolClientId'],
                    AuthFlow='USER_PASSWORD_AUTH',
                    AuthParameters={
                        'USERNAME': userid,
                        'PASSWORD': password
                    }
                )
        except Exception as e:
            if "NotAuthorizedException" in str(e) or "UserNotFoundException" in str(e):
                logger.error('Incorrect username or password: %s', userid)
                return {
                    'statusCode': 400,
                    'body': 'Incorrect username or password'
                }
            else:
                logger.error(e)

        if 'AuthenticationResult' in response:
            logger.debug('User authenticated: %s', userid)
            return {
                'statusCode': 200,
                'body': json.dumps(response['AuthenticationResult']['IdToken'])
            }
        elif 'ChallengeName' in response:
            logger.debug('User challenge requested: %s', userid)
            return {
                'statusCode': 200,
                'body': json.dumps(response)
            }
    else:
        logger.error('Missing Cognito configuration in factory.json.')
        return {
            'statusCode': 200,
            'body': 'Missing Cognito configuration in factory.json.'
        }
