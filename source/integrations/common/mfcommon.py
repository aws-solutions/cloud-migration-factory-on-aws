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

api_stage = 'prod'

serverendpoint = '/user/server'
databaseendpoint = '/user/database'
appendpoint = '/user/app'
waveendpoint = '/user/wave'

REQUESTS_DEFAULT_TIMEOUT = 60

PREFIX_CREDENTIALS_STORE = 'cached_secret:'

credentials_store = {}

with open('FactoryEndpoints.json') as json_file:
    mf_config = json.load(json_file)


def get_mf_config_user_api_id():
    # Function required to maintain backward compatibility with pre-3.3.1 CMF deployments,
    # allowing newer scripts to work on older versions.
    if "UserApi" in mf_config:
        return mf_config["UserApi"]
    elif "UserApiUrl" in mf_config:
        return extract_api_id_from_url(mf_config["UserApiUrl"])
    else:
        print("ERROR: Invalid FactoryEndpoints.json file. UserApi or UserApiUrl not present.")
        sys.exit()


def extract_api_id_from_url(api_url):
    if api_url:
        return api_url[8:18]


def get_api_endpoint_headers(token, api_id):
    if 'VpceId' in mf_config and mf_config['VpceId'] != '':
        auth = {
            "Authorization": token
        }
    else:
        auth = {"Authorization": token}

    return auth


def get_api_endpoint_url(api_id, api_endpoint):
    if 'VpceId' in mf_config and mf_config['VpceId'] != '':
        return f'https://{api_id}-{mf_config["VpceId"]}.execute-api.{mf_config["Region"]}.amazonaws.com/{api_stage}{api_endpoint}'
    else:
        return f'https://{api_id}.execute-api.{mf_config["Region"]}.amazonaws.com/{api_stage}{api_endpoint}'


def build_requests_parameters(token, api_id, api_path):
    return {
        "url": get_api_endpoint_url(api_id, api_path),
        "headers": get_api_endpoint_headers(token, api_id),
        "timeout": REQUESTS_DEFAULT_TIMEOUT
    }


def get_data_from_api(token, api_id, api_path):
    request_parameters = build_requests_parameters(token, api_id, api_path)

    try:
        requests_response = requests.get(**request_parameters)  # nosec B113
    except requests.exceptions.ConnectionError:
        msg = f'ERROR: Could not connect to API endpoint {request_parameters["url"]}{api_path}.'
        print(msg)
        sys.exit()

    if requests_response.status_code != 200:
        msg = f'ERROR: Bad response from API {request_parameters["url"]}{api_path}. {requests_response.text}'
        print(msg)
        sys.exit()

    return requests_response


def put_data_to_api(token, api_id, api_path, payload):
    request_parameters = build_requests_parameters(token, api_id, api_path)
    request_parameters['data'] = json.dumps(payload)

    try:
        requests_response = requests.put(**request_parameters)  # nosec B113

    except requests.exceptions.ConnectionError:
        msg = f'ERROR: Could not connect to API endpoint {request_parameters["url"]}{api_path}.'
        print(msg)
        sys.exit()

    if requests_response.status_code != 200:
        msg = f'ERROR: Bad response from API {request_parameters["url"]}{api_path}. {requests_response.text}'
        print(msg)

    return requests_response


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
            mf_service_account = secretsmanager_client.get_secret_value(
                SecretId='MFServiceAccount-' + mf_config['UserPoolId'])
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
                    default_user = mf_config['DefaultUser']
                else:
                    default_user = ''
                username = input("Factory Username [" + default_user + "]: ") or default_user
                password = getpass.getpass('Factory Password: ')
    else:
        if 'DefaultUser' in mf_config:
            default_user = mf_config['DefaultUser']
        else:
            default_user = ""
        username = input("Factory Username [" + default_user + "]: ") or default_user
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
                except EOFError:
                    print("", flush=True)
                    print("ERROR: MFA is enabled for the service account; this is not supported when used with "
                          "CMF automation, if MFA is required, scripts must be run from the command line of the "
                          "automation server.", flush=True)
                    sys.exit(1)
                mfa_challenge_data = {'username': username, 'mfacode': one_time_code, 'session': r_content['Session']}
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
        if PREFIX_CREDENTIALS_STORE + secret_name in credentials_store:
            return credentials_store[PREFIX_CREDENTIALS_STORE + secret_name]

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

            # Cache secret for next server.
            credentials_store[PREFIX_CREDENTIALS_STORE + secret_name] = mfauth

            return mfauth
        except botocore.exceptions.ClientError as e:
            print(e)
            if e.response['Error']['Code'] == 'ResourceNotFoundException' or e.response['Error'][
                'Code'] == 'AccessDeniedException':
                if no_user_prompts == True:
                    print(f"Secret not found [{server['secret_name']}] doesn't exist or access is denied to Secret.")
                else:
                    print(f"Secret not found [{server['secret_name']}] doesn't exist or access is denied to Secret, "
                          f"please enter username and password")
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
        if PREFIX_CREDENTIALS_STORE + secret_name in credentials_store:
            return credentials_store[PREFIX_CREDENTIALS_STORE + secret_name]

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
            credentials_store[PREFIX_CREDENTIALS_STORE + secret_name] = mfauth

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


def get_cmf_application_ids_for_wave(cmf_api_token, wave_id, ce_project_name=''):
    app_ids = []

    apps_api_response = get_data_from_api(cmf_api_token, get_mf_config_user_api_id(), appendpoint)

    apps = json.loads(apps_api_response.text)

    for app in apps:
        if 'wave_id' in app and str(app['wave_id']) == str(wave_id):
            if ce_project_name != "":
                if str(app['cloudendure_projectname']) == str(ce_project_name):
                    app_ids.append(app['app_id'])
            else:
                app_ids.append(app['app_id'])

    return app_ids


def get_cmf_servers_for_all_apps(cmf_api_token, cmf_application_ids):
    servers_api_response = get_data_from_api(cmf_api_token, get_mf_config_user_api_id(), serverendpoint)

    servers = json.loads(servers_api_response.text)

    servers_windows = []
    servers_linux = []
    for app_id in cmf_application_ids:
        for server in servers:
            if app_id == server['app_id']:
                if 'server_os_family' in server:
                    if 'server_fqdn' in server:
                        if server['server_os_family'].lower() == "windows":
                            servers_windows.append(server)
                        if server['server_os_family'].lower() == "linux":
                            servers_linux.append(server)
                    else:
                        print("ERROR: server_fqdn for server: " + server['server_name'] + " doesn't exist")
                        sys.exit(4)
                else:
                    print('server_os_family attribute does not exist for server: ' + server[
                        'server_name'] + ", please update this attribute")
                    sys.exit(2)

    return servers_windows, servers_linux


def ServerList(waveid, token, _, Projectname=''):
    # Get App list
    applist = get_cmf_application_ids_for_wave(token, waveid, Projectname)

    # Get Server Lists
    servers_windows, servers_linux = get_cmf_servers_for_all_apps(token, applist)

    if len(servers_windows) == 0 and len(servers_linux) == 0:
        print(f"ERROR: Serverlist for wave: {waveid} in CE Project {Projectname} is empty....")
        print("")
    else:
        print("successfully retrieved server list")
        print("")
        if len(servers_windows) > 0:
            print("*** Windows Server List")
            for server in servers_windows:
                print(server['server_name'])
        else:
            print("*** No Windows Servers")
        print("")
        if len(servers_linux) > 0:
            print("*** Linux Server List ***")
            print("")
            for server in servers_linux:
                print(server['server_name'])
        else:
            print("*** No Linux Servers")
        return servers_windows, servers_linux


def CElogin(userapitoken):
    login_data = {'userApiToken': userapitoken}
    r = requests.post(ce_address + ce_endpoint.format('login'),
                      data=json.dumps(login_data),
                      headers=ce_headers,
                      timeout=REQUESTS_DEFAULT_TIMEOUT)
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
                          data=json.dumps(login_data),
                          headers=ce_headers,
                          timeout=REQUESTS_DEFAULT_TIMEOUT)
    try:
        ce_headers['X-XSRF-TOKEN'] = r.cookies['XSRF-TOKEN']
        return r.cookies['session'], ce_headers['X-XSRF-TOKEN']
    except:
        pass

    return r.cookies['session'], None


def GetCERegion(project_id, ce_session, ce_headers):
    region_ids = []
    rep = requests.get(ce_address + ce_endpoint.format('projects/{}/replicationConfigurations').format(project_id),
                       headers=ce_headers,
                       cookies=ce_session,
                       timeout=REQUESTS_DEFAULT_TIMEOUT)
    for item in json.loads(rep.text)['items']:
        region = requests.get(
            ce_address + ce_endpoint.format('cloudCredentials/{}/regions/{}').format(item['cloudCredentials'],
                                                                                     item['region']),
            headers=ce_headers,
            cookies=ce_session,
            timeout=REQUESTS_DEFAULT_TIMEOUT)
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
def get_factory_servers(waveid, token, osSplit=True, rtype=None):
    try:
        linux_exist = False
        windows_exist = False
        # Get all Apps and servers from migration factory

        servers_api_response = get_data_from_api(token, get_mf_config_user_api_id(), serverendpoint)

        getservers = json.loads(servers_api_response.text)

        apps_api_response = get_data_from_api(token, get_mf_config_user_api_id(), appendpoint)

        getapps = json.loads(apps_api_response.text)

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
            msg = f"ERROR: AWS Account list for wave {waveid} is empty...."
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
                    msg = (f"INFORMATIONAL: Server list for wave {waveid} and account: {account['aws_accountid']} "
                           f"region: {account['aws_region']} is empty....")
                    print(msg)
                if len(account['servers_linux']) > 0:
                    linux_exist = True
                if len(account['servers_windows']) > 0:
                    windows_exist = True
            else:
                if len(account['servers']) == 0:
                    msg = (f"INFORMATIONAL: Server list for wave {waveid} and account: {account['aws_accountid']} "
                           f"region: {account['aws_region']}  is empty....")
                    print(msg)
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


def clean_value(value):
    return value.lower().strip()


def is_cmf_server_match_for_mgn_ip_address(interface, cmf_server):
    cmf_server_name = clean_value(cmf_server['server_name'])
    cmf_server_fqdn = clean_value(cmf_server['server_fqdn'])

    if interface['isPrimary'] is True:
        for ip_address in interface['ips']:
            if cmf_server_name == clean_value(ip_address) or cmf_server_fqdn == clean_value(ip_address):
                return True

    return False


def is_cmf_server_match_for_mgn_hostname(mgn_source_server, cmf_server):
    cmf_server_name = clean_value(cmf_server['server_name'])
    cmf_server_fqdn = clean_value(cmf_server['server_fqdn'])
    mgn_server_hostname = clean_value(mgn_source_server['sourceProperties']['identificationHints']['hostname'])
    mgn_server_fqdn = clean_value(mgn_source_server['sourceProperties']['identificationHints']['fqdn'])

    if cmf_server_name == mgn_server_hostname or cmf_server_name == mgn_server_fqdn \
        or cmf_server_fqdn == mgn_server_hostname or cmf_server_fqdn == mgn_server_fqdn:
        return True

    return False


def is_cmf_server_matching_mgn_source_server(cmf_server, mgn_source_server):
    # Check if any IP addresses in MGN record match with CMF.
    if 'networkInterfaces' in mgn_source_server['sourceProperties']:
        for interface in mgn_source_server['sourceProperties']['networkInterfaces']:
            if is_cmf_server_match_for_mgn_ip_address(interface, cmf_server):
                return True

    if is_cmf_server_match_for_mgn_hostname(mgn_source_server, cmf_server):
        return True

    return False


def get_MGN_Source_Server(cmf_server, mgn_source_servers):
    found_matching_source_server = None

    for mgn_source_server in mgn_source_servers:
        if 'isArchived' in mgn_source_server and not mgn_source_server['isArchived']:
            # Check if the factory server exist in Application Migration Service

            if is_cmf_server_matching_mgn_source_server(cmf_server, mgn_source_server):
                found_matching_source_server = mgn_source_server

    if found_matching_source_server is not None:
        return found_matching_source_server
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
        print(f"Exception {e} while executing script: {command}")
        return False


def execute_cmd(host, username, key, cmd, using_key):
    # Function provides backward compatibility with older scripts, new scripts should call execute_cmd_via_ssh directly.
    return execute_cmd_via_ssh(host, username, key, cmd, using_key, False)


def execute_cmd_via_ssh(host, username, key, cmd, using_key, multi_threaded=False):
    # Function provides scripts a standard function to run remote commands against ssh enabled systems.
    output = ''
    error = ''
    ssh = None
    try:
        ssh, error = open_ssh(host, username, key, using_key)
        if ssh:
            _, stdout, stderr = ssh.exec_command(cmd)  # nosec B601
            for line in stdout.readlines():
                output = output + line
            for line in stderr.readlines():
                error = error + line
    except IOError as io_error:
        error = f"Unable to execute the command {cmd} due to {str(io_error)}"
        if not multi_threaded:
            print(error)
    except paramiko.SSHException as ssh_exception:
        error = f"Unable to execute the command {cmd} due to {str(ssh_exception)}"
        if not multi_threaded:
            print(error)
    finally:
        if ssh is not None:
            ssh.close()
    return output, error


def open_ssh(host, username, key_pwd, using_key, multi_threaded=False):
    base_error = f"Unable to connect to host {host} with username {username} due to"
    ssh = None
    error = ''
    try:
        if using_key:
            from io import StringIO
            private_key = paramiko.RSAKey.from_private_key(StringIO(key_pwd.strip()))
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, pkey=private_key)
        else:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=host, username=username, password=key_pwd)
    except IOError as io_error:
        ssh = None
        error = f"{base_error} {str(io_error)}"
        if not multi_threaded:
            print(error)
    except paramiko.SSHException as ssh_exception:
        ssh = None
        error = f"{base_error} {str(ssh_exception)}"
        if not multi_threaded:
            print(error)
    except Exception as all_other:
        ssh = None
        error = f"{base_error} {str(all_other)}"
        if not multi_threaded:
            print(error)

    return ssh, error


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


# Function is used with new database entity to get databases based on the AWS account they are targeted to and wave.
def get_factory_databases(waveid, token, rtype=None):
    try:

        databases_api_response = get_data_from_api(token, get_mf_config_user_api_id(), databaseendpoint)

        databases = json.loads(databases_api_response.text)

        apps_api_response = get_data_from_api(token, get_mf_config_user_api_id(), appendpoint)

        apps = json.loads(apps_api_response.text)

        databases = sorted(databases, key=lambda i: i['database_name'])
        apps = sorted(apps, key=lambda i: i['app_name'])

        # Get Unique target AWS account and region
        aws_accounts = []
        for app in apps:
            if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                if str(app['wave_id']) == str(waveid):
                    if len(str(app['aws_accountid']).strip()) == 12:
                        target_account = {}
                        target_account['aws_accountid'] = str(app['aws_accountid']).strip()
                        target_account['aws_region'] = app['aws_region'].lower().strip()
                        target_account['databases'] = []
                        if target_account not in aws_accounts:
                            aws_accounts.append(target_account)
                    else:
                        msg = "ERROR: Incorrect AWS Account Id Length for app: " + app['app_name']
                        print(msg)
                        sys.exit()
        if len(aws_accounts) == 0:
            msg = "ERROR: Target accounts for wave " + waveid + " is empty...."
            print(msg)
            sys.exit()

        # Get database list
        for account in aws_accounts:
            print("### Databases in Target Account: " + account['aws_accountid'] + " , region: " + account[
                'aws_region'] + " ###")
            for app in apps:
                if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                    if str(app['wave_id']) == str(waveid):
                        if str(app['aws_accountid']).strip() == str(account['aws_accountid']):
                            if app['aws_region'].lower().strip() == account['aws_region']:
                                for database in databases:
                                    if (rtype is None) or ('r_type' in database and database['r_type'] == rtype):
                                        if 'app_id' in database:
                                            if database['app_id'] == app['app_id']:
                                                account['databases'].append(database)
                                                print(database['database_name'])
            print("")
            if len(account['databases']) == 0:
                msg = "ERROR: Database list for wave " + waveid + " and account: " + account[
                    'aws_accountid'] + " region: " + account['aws_region'] + " is empty...."
                print(msg)
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


def find_distribution(host, username, key_pwd, using_key):
    distribution = "linux"
    output, _ = execute_cmd_via_ssh(host, username, key_pwd, "cat /etc/*release",
                                    using_key)
    if "ubuntu" in output:
        distribution = "ubuntu"
    elif "fedora" in output:
        distribution = "fedora"
    elif "suse" in output:
        distribution = "suse"
    return distribution


def install_wget(host, username, key_pwd, using_key):
    ssh = None
    try:
        # Find the distribution
        distribution = find_distribution(host, username, key_pwd, using_key)
        print("")
        print("***** Installing wget *****")
        ssh = open_ssh(host, username, key_pwd, using_key, True)
        if distribution == "ubuntu":
            ssh.exec_command("sudo apt-get update")  # nosec B601
            stdin, _, stderr = ssh.exec_command("sudo DEBIAN_FRONTEND=noninteractive "  # nosec B601
                                                "apt-get install wget")
        elif distribution == "suse":
            stdin, _, stderr = ssh.exec_command("sudo zypper install wget")  # nosec B601
            stdin.write('Y\n')
            stdin.flush()
        else:
            # This condition works with centos, fedora and RHEL distributions
            stdin, _, stderr = ssh.exec_command("sudo yum install wget -y")  # nosec B601
        # Check if there is any error while installing wget
        error = ''
        for line in stderr.readlines():
            error = error + line
        if not error:
            print("wget got installed successfully")
            # Execute the command wget and check if it got configured correctly
            stdin, _, stderr = ssh.exec_command("wget")  # nosec B601
            error = ''
            for line in stderr.readlines():
                error = error + line
            if "not found" in error or "command-not-found" in error:
                print(
                    "wget is not recognized, unable to proceed! due to " + error)
        else:
            print("something went wrong while installing wget ", error)
    finally:
        if ssh is not None:
            ssh.close()


def update_server_migration_status(token, server_id, new_status):
    status_update_payload = {"migration_status": new_status}
    return put_data_to_api(token, get_mf_config_user_api_id(), f'{serverendpoint}/{server_id}', status_update_payload)


def update_server_replication_status(token, server_id, new_status):
    status_update_payload = {"replication_status": new_status}
    return put_data_to_api(token, get_mf_config_user_api_id(), f'{serverendpoint}/{server_id}', status_update_payload)


def add_windows_servers_to_trusted_hosts(cmf_servers):
    # Get all servers FQDNs into csv for trusted hosts update.
    trusted_hosts_server_csv = ""
    for server in cmf_servers:
        trusted_hosts_server_csv = trusted_hosts_server_csv + server["server_fqdn"] + ','

    trusted_hosts_server_csv = trusted_hosts_server_csv[:-1]
    # Add servers to local trusted hosts to allow authentication if different domain.
    subprocess.run([
        "powershell.exe",
        "Set-Item WSMan:\localhost\Client\TrustedHosts",
        "-Value '" + trusted_hosts_server_csv + "'",
        "-Concatenate",
        "-Force"],
        check=True)
