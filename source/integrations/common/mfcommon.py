#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


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

if not sys.warnoptions:
    import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=Warning)
    import paramiko

ts = calendar.timegm(time.gmtime())
# Constants referenced from other modules.
api_stage = 'prod'

serverendpoint = '/user/server'
databaseendpoint = '/user/database'
appendpoint = '/user/app'
waveendpoint = '/user/wave'
REQUESTS_DEFAULT_TIMEOUT = 60

PREFIX_CREDENTIALS_STORE = 'cached_secret:'
credentials_store = {}

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s',
                    level=logging.ERROR)  # //NOSONAR Basic configuration doesn't pose security risk
logger = logging.getLogger()
logger.setLevel(logging.ERROR)

with open('FactoryEndpoints.json') as json_file:
    mf_config = json.load(json_file)


# start of the external interface / functions to be called by clients ###############

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


def get_api_endpoint_headers(token):
    return {"Authorization": token}


def get_api_endpoint_url(api_id, api_endpoint):
    if 'VpceId' in mf_config and mf_config['VpceId'] != '':
        return f'https://{api_id}-{mf_config["VpceId"]}.execute-api.{mf_config["Region"]}.amazonaws.com/{api_stage}{api_endpoint}'
    else:
        return f'https://{api_id}.execute-api.{mf_config["Region"]}.amazonaws.com/{api_stage}{api_endpoint}'


def build_requests_parameters(token, api_id, api_path):
    return {
        "url": get_api_endpoint_url(api_id, api_path),
        "headers": get_api_endpoint_headers(token),
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


def factory_login(silent=False):
    login_data, username, using_secret = get_cmf_user_login_data(mf_config)
    token = validate_cmf_user_login(mf_config, login_data, username, using_secret, silent=silent)

    return token


def get_server_credentials(
    local_username, local_password, server, secret_override=None, no_user_prompts=False):
    secret_name = ""

    # Local account details passed, do not get from secrets manager.
    if local_username != "" and local_password != "":
        return {'username': local_username, 'password': local_password}

    ##  If secret has been provided then use this instead of checking server record.
    if secret_override is not None:
        secret_name = secret_override
    elif "secret_name" in server and server['secret_name'] != "":
        secret_name = server['secret_name']
        print("Server specific secret configured, using: " + secret_name)

    if secret_name != "":

        # Check if already read secret, and if so return cached.
        cached_credential = return_cached_secret(secret_name)
        if cached_credential is not None:
            return cached_credential

        mfauth = get_server_credentials_with_secret(
            secret_name, server, no_user_prompts, mf_config)
        return mfauth

    if server['server_os_family'].lower() == "windows":
        credential = get_windows_server_credentials(no_user_prompts)
        if credential is not None:
            return credential

    if server['server_os_family'].lower() == "linux":
        credential = get_linux_server_credentials(no_user_prompts)
        if credential is not None:
            return credential

    if no_user_prompts == True:
        print(
            "No credentials supplied by user or specified in Migration "
            "Factory server secret attribute. Returning blank username and password")
        return {'username': '', 'password': '', 'private_key': False}


def get_credentials(secret_name, no_user_prompts=True, not_found_response=None):
    if secret_name != "":

        # Check if already read secret, and if so return cached.
        cached_credential = return_cached_secret(secret_name)
        if cached_credential is not None:
            return cached_credential

        return get_credentials_with_secret(secret_name, no_user_prompts, mf_config)

    # return default not found response.
    return not_found_response


# Function is used with new MGN capabiltiy to get servers based on the AWS account they are targeted to.
def get_factory_servers(waveid, token, os_split=True, rtype=None):
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
        aws_accounts, sys_exit = \
            get_aws_account_region(apps, waveid, os_split)
        if sys_exit:
            sys.exit()

        # Get server list
        for account in aws_accounts:
            print(f"### Servers in Target Account: {account['aws_accountid']}, "
                  f"region: {account['aws_region']} ###")
            account, sys_exit = iterate_app_list(
                apps, servers, account, waveid, os_split, rtype)
            if sys_exit:
                sys.exit()

            print("")
            linux_exist, windows_exist = \
                verify_windows_and_linux_server(
                    os_split, account, waveid)

        if os_split:
            return aws_accounts, linux_exist, windows_exist
        else:
            return aws_accounts
    except botocore.exceptions.ClientError as error:
        sys_exit = handle_client_error(error)
        if sys_exit:
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


def get_mgn_source_server(cmf_server, mgn_source_servers):
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
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
            ssh.connect(hostname=host, username=username, pkey=private_key)
        else:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
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
        "Set-Item WSMan:\\localhost\\Client\\TrustedHosts",
        "-Value '" + trusted_hosts_server_csv + "'",
        "-Concatenate",
        "-Force"],
        check=True)


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
        aws_accounts = factory_database_accounts_from_apps(apps, waveid)
        # Get database list
        factory_database_extract_databases(aws_accounts, databases, apps, waveid, rtype)
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


def factory_database_accounts_from_apps(apps, waveid):
    aws_accounts = []
    for app in apps:
        if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
            if str(app['wave_id']) == str(waveid):
                factory_database_update_accounts(app, aws_accounts)
    if len(aws_accounts) == 0:
        msg = "ERROR: Target accounts for wave " + waveid + " is empty...."
        print(msg)
        sys.exit()

    return aws_accounts


def factory_database_update_accounts(app, aws_accounts):
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


def factory_database_extract_databases(aws_accounts, databases, apps, waveid, rtype):
    for account in aws_accounts:
        print("### Databases in Target Account: " + account['aws_accountid'] + " , region: " + account[
            'aws_region'] + " ###")
        for app in apps:
            if 'wave_id' in app and 'aws_accountid' in app and 'aws_region' in app:
                factory_database_match_databases_apps(app, waveid, account, rtype, databases)
        print("")
        if len(account['databases']) == 0:
            msg = "ERROR: Database list for wave " + waveid + " and account: " + account[
                'aws_accountid'] + " region: " + account['aws_region'] + " is empty...."
            print(msg)


def factory_database_match_databases_apps(app, waveid, account ,rtype, databases):
    if str(app['wave_id']) == str(waveid):
        if str(app['aws_accountid']).strip() == str(account['aws_accountid']):
            if app['aws_region'].lower().strip() == account['aws_region']:
                for database in databases:
                    factory_database_update_db_attrs(database, account, app, rtype)


def factory_database_update_db_attrs(database, account, app, rtype):
    if (rtype is None) or ('r_type' in database and database['r_type'] == rtype):
        if 'app_id' in database:
            if database['app_id'] == app['app_id']:
                account['databases'].append(database)
                print(database['database_name'])


# end of the external interface / functions to be called by clients ###############

# start of credential related functions ###############

def get_server_credentials_with_secret(secret_name, server, no_user_prompts, mf_config):
    try:
        secret_data = None
        mfauth = None

        secret_data_raw = get_raw_secret_data(mf_config, secret_name)
        secret_data_tmp_json = get_secret_data_tmp_json(secret_data_raw)

        secret_data = {}
        secret_data = get_data_field_from_secret_data_tmp_json(
            "USERNAME", secret_data_tmp_json, secret_data)
        secret_data = get_password_in_secret_data(
            secret_data_tmp_json, secret_data)
        secret_data = get_data_field_from_secret_data_tmp_json(
            "SECRET_TYPE", secret_data_tmp_json, secret_data)
        secret_data = get_data_field_from_secret_data_tmp_json(
            "OS_TYPE", secret_data_tmp_json, secret_data)

        mfauth = get_secret_data(secret_data, secret_name)
        return mfauth
    except botocore.exceptions.ClientError as e:
        print(e)
        handle_credentials_client_error(e, server['secret_name'], no_user_prompts)


def get_credentials_with_secret(secret_name, no_user_prompts, mf_config):
    try:
        secret_data = None
        mfauth = None

        secret_data_raw = get_raw_secret_data(mf_config, secret_name)
        secret_data_tmp_json = get_secret_data_tmp_json(secret_data_raw)

        secret_data = {}
        secret_data = get_data_field_from_secret_data_tmp_json(
            "USERNAME", secret_data_tmp_json, secret_data)
        secret_data = get_password_in_secret_data(
            secret_data_tmp_json, secret_data)
        secret_data = get_data_field_from_secret_data_tmp_json(
            "SECRET_TYPE", secret_data_tmp_json, secret_data)
        secret_data = get_data_field_from_secret_data_tmp_json(
            "SECRET_KEY", secret_data_tmp_json, secret_data)
        secret_data = get_data_field_from_secret_data_tmp_json(
            "SECRET_VALUE", secret_data_tmp_json, secret_data)
        secret_data = get_data_field_from_secret_data_tmp_json(
            "APIKEY", secret_data_tmp_json, secret_data)
        secret_data = get_data_field_from_secret_data_tmp_json(
            "SECRET_STRING", secret_data_tmp_json, secret_data)
        secret_data = get_data_field_from_secret_data_tmp_json(
            "OS_TYPE", secret_data_tmp_json, secret_data)

        mfauth = get_secret_data(secret_data, secret_name)
        return mfauth
    except botocore.exceptions.ClientError as e:
        handle_credentials_client_error(e, secret_name, no_user_prompts)


def return_cached_secret(secret_name):
    # Check if already read secret, and if so return cached.
    if PREFIX_CREDENTIALS_STORE + secret_name in credentials_store:
        return credentials_store[PREFIX_CREDENTIALS_STORE + secret_name]
    return None


def get_raw_secret_data(mf_config, secret_name):
    secretsmanager_client = boto3.client('secretsmanager', mf_config['Region'])
    mf_service_account = secretsmanager_client.get_secret_value(SecretId=secret_name)
    secret_data_raw = mf_service_account['SecretString']

    return secret_data_raw


def get_secret_data_tmp_json(secret_data_raw):
    if secret_data_raw[0] != "{":
        # Secret could be encoded, perform decode.
        secret_data_tmp = base64.b64decode(secret_data_raw.encode("utf-8")).decode("ascii")
        secret_data_tmp_json = json.loads(secret_data_tmp)
    else:
        secret_data_tmp_json = json.loads(secret_data_raw)

    return secret_data_tmp_json


def get_data_field_from_secret_data_tmp_json(
    field_name, secret_data_tmp_json, secret_data):
    field_name_lower_case = field_name.lower()
    secret_data[field_name_lower_case] = ""
    if field_name in secret_data_tmp_json:
        secret_data[field_name_lower_case] = secret_data_tmp_json[field_name]

    return secret_data


def get_password_in_secret_data(secret_data_tmp_json, secret_data):
    secret_data['password'] = ""
    if "PASSWORD" in secret_data_tmp_json:
        if "IS_SSH_KEY" in secret_data_tmp_json and secret_data_tmp_json['IS_SSH_KEY'].lower() == 'true':
            secret_data['password'] = base64.b64decode(secret_data_tmp_json['PASSWORD'].encode("utf-8")) \
                .decode("ascii")
            secret_data['password'] = secret_data['password'].replace('\\n', '\n')
            secret_data['private_key'] = True
        else:
            secret_data['password'] = secret_data_tmp_json['PASSWORD']
            secret_data['private_key'] = False

    return secret_data


def get_secret_data(secret_data, secret_name):
    mfauth = secret_data

    # Cache secret for next server.
    credentials_store[PREFIX_CREDENTIALS_STORE + secret_name] = mfauth

    return mfauth


def handle_credentials_client_error(e, secret_name, no_user_prompts):
    if e.response['Error']['Code'] == 'ResourceNotFoundException' or e.response['Error'][
        'Code'] == 'AccessDeniedException':
        if no_user_prompts:
            print(f"Secret not found [{secret_name}] doesn't exist or access is denied to Secret.")
        else:
            print(f"Secret not found [{secret_name}] doesn't exist or access is denied to Secret, "
                  f"please enter username and password")
    else:
        # Unknown error returned when getting secret.
        print(e.response['Error'])


def get_windows_server_credentials(no_user_prompts):
    if 'windows' in credentials_store:
        return credentials_store['windows']
    if no_user_prompts == False:
        print(get_prompt_message_for_credentials("Windows"))
        username = input("Windows Username (leave blank to use current logged on user): ")
        if username != "":
            password = get_windows_password()
        else:
            password = ""
        store_cred = input(get_input_message_for_credentials("Windows"))
        credentials = {'username': username, 'password': password}
        if 'y' in store_cred.lower():
            credentials_store['windows'] = credentials
        return credentials
    return None


def get_linux_server_credentials(no_user_prompts):
    if 'linux' in credentials_store:
        return credentials_store['linux']
    if no_user_prompts == False:
        print(get_prompt_message_for_credentials("Linux"))
        username, password, key_exist = get_linux_password()
        store_cred = input(get_input_message_for_credentials("Linux"))
        credentials = {'username': username, 'password': password, 'private_key': key_exist}
        if 'y' in store_cred.lower():
            credentials_store['linux'] = credentials
        return credentials
    return None


# common functions
def get_windows_password():
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


def get_prompt_message_for_credentials(server_type):
    message = f"No {server_type} credentials supplied by user or specified in Migration Factory server secret attribute. Please enter credentials now."
    return message


def get_input_message_for_credentials(server_type):
    message = f"Do you wish to use the same credentials for all {server_type} servers in the job?, press [Y] or if you wish to be prompted per server [N]: "
    return message


# end of credential related functions ###############


# start of get servers functions ###############

def get_aws_account_region(apps, waveid, os_split):
    aws_accounts = []
    for app in apps:
        if app.get('wave_id') == str(waveid) and \
            'aws_accountid' in app and 'aws_region' in app:
            aws_accounts, sys_exit = \
                extract_aws_account_region(
                    app, os_split, aws_accounts)
            if sys_exit:
                return aws_accounts, sys_exit

    if len(aws_accounts) == 0:
        msg = f"ERROR: AWS Account list for wave {waveid} is empty...."
        print(msg)
        sys_exit = True

    return aws_accounts, sys_exit


def extract_aws_account_region(app, os_split, aws_accounts):
    sys_exit = False
    if len(str(app['aws_accountid']).strip()) == 12:
        target_account = {}
        target_account['aws_accountid'] = str(app['aws_accountid']).strip()
        target_account['aws_region'] = app['aws_region'].lower().strip()
        if os_split:
            target_account['servers_windows'] = []
            target_account['servers_linux'] = []
        else:
            target_account['servers'] = []
        if target_account not in aws_accounts:
            aws_accounts.append(target_account)
    else:
        msg = f"ERROR: Incorrect AWS Account Id Length for app: {app['app_name']}"
        print(msg)
        sys_exit = True

    return aws_accounts, sys_exit


def iterate_app_list(apps, servers, account, waveid, os_split, rtype):
    for app in apps:
        if app.get('wave_id') == str(waveid) and \
            'aws_accountid' in app and 'aws_region' in app and \
            str(app['aws_accountid']).strip() == str(account['aws_accountid']) and \
            app['aws_region'].lower().strip() == account['aws_region']:
            account, sys_exit = iterate_server_list(
                app, servers, account, os_split, rtype)
            if sys_exit:
                return account, sys_exit

    return account, sys_exit


def iterate_server_list(app, servers, account, os_split, rtype):
    sys_exit = False
    for server in servers:
        if ((rtype is None) or (server.get('r_type') == rtype)) and \
            server.get('app_id') == app['app_id']:
            account, sys_exit = verify_server_os_and_fqdn(
                server, os_split, account)
            if sys_exit:
                return account, sys_exit
    return account, sys_exit


def verify_server_os_and_fqdn(server, os_split, account):
    sys_exit = False
    # verify server_os_family attribute, only accepts Windows or Linux
    if 'server_os_family' in server:
        # Verify server_fqdn, this is mandatory attribute
        if 'server_fqdn' in server:
            if os_split:
                if server['server_os_family'].lower() == 'windows':
                    account['servers_windows'].append(server)
                elif server['server_os_family'].lower() == 'linux':
                    account['servers_linux'].append(server)
                else:
                    print(f"ERROR: Invalid server_os_family for: {server['server_name']}, "
                          f"please select either Windows or Linux")
                    sys_exit = True
                    return account, sys_exit
            else:
                account['servers'].append(server)
            print(server['server_fqdn'])
        else:
            print(f"ERROR: server_fqdn for server: {server['server_name']} doesn't exist")
            sys_exit = True
    else:
        print(f"ERROR: server_os_family does not exist for: {server['server_name']}")
        sys_exit = True

    return account, sys_exit


def verify_windows_and_linux_server(os_split, account, waveid):
    linux_exist = False
    windows_exist = False
    msg = (f"INFORMATIONAL: Server list for wave {waveid} and account: {account['aws_accountid']} "
           f"region: {account['aws_region']} is empty....")
    if os_split:
        # Check if the server list is empty for both Windows and Linux
        if len(account['servers_windows']) == 0 and len(account['servers_linux']) == 0:
            print(msg)
        if len(account['servers_linux']) > 0:
            linux_exist = True
        if len(account['servers_windows']) > 0:
            windows_exist = True
    else:
        if len(account['servers']) == 0:
            print(msg)

    return linux_exist, windows_exist


def handle_client_error(error):
    sys_exit = False
    if ":" in str(error):
        err = ''
        msgs = str(error).split(":")[1:]
        for msg in msgs:
            err = err + msg
        msg = "ERROR: " + err
        print(msg)
        sys_exit = True
    else:
        msg = "ERROR: " + str(error)
        print(msg)
        sys_exit = True

    return sys_exit


# end of get servers related functions ###############

# start of user login related functions ###############

def get_login_data_for_user_pool(mf_config):
    try:
        using_secret = False
        secretsmanager_client = boto3.client(
            'secretsmanager', mf_config['Region'])
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
            default_user = ''
            if 'DefaultUser' in mf_config:
                default_user = mf_config['DefaultUser']
            username = input(
                "Factory Username [" + default_user + "]: ") or default_user
            password = getpass.getpass('Factory Password: ')

    return username, password, using_secret


def get_cmf_user_login_data(mf_config):
    username = ""
    password = ""
    using_secret = False
    if 'UserPoolId' in mf_config and 'Region' in mf_config:
        username, password, using_secret = \
            get_login_data_for_user_pool(mf_config)
    else:
        default_user = ""
        if 'DefaultUser' in mf_config:
            default_user = mf_config['DefaultUser']
        username = input(
            "Factory Username [" + default_user + "]: ") or default_user
        password = getpass.getpass('Factory Password: ')

    login_data = {'username': username, 'password': password}

    return login_data, username, using_secret


def factory_login_with_mfa(username, r_content, mf_config):
    if r_content.get('ChallengeName') == 'SMS_MFA':
        try:
            one_time_code = input("Please provide MFA One Time Code: ")
        except EOFError:
            print("", flush=True)
            print("ERROR: MFA is enabled for the service account; this is not supported when used with "
                  "CMF automation, if MFA is required, scripts must be run from the command line of the "
                  "automation server.", flush=True)
            sys.exit(1)
        mfa_challenge_data = {
            'username': username, 'mfacode': one_time_code, 'session': r_content['Session']}
        r_mfa = factory_login_with_cognito_user_pool(
            mfa_challenge_data, mf_config)
        if r_mfa['statusCode'] == 200:
            print("Migration Factory : You have successfully logged in")
            print("")
            token = str(json.loads(r_mfa['body']))
            return token
        if r_mfa['statusCode'] == 502 or r_mfa['statusCode'] == 400:
            print("ERROR: Incorrect MFA One Time Code provided....")
            sys.exit(1)


def validate_cmf_user_login(mf_config, login_data, username, using_secret, silent=False):
    try:
        r = factory_login_with_cognito_user_pool(login_data, mf_config)

        r_content = ''
        if 'body' in r:
            r_content = json.loads(r['body'])

        if r['statusCode'] == 200 and 'ChallengeName' in r_content:
            token = factory_login_with_mfa(username, r_content, mf_config)
        elif r['statusCode'] == 200:
            if not silent:
                print("Migration Factory : You have successfully logged in")
                print("")
            token = str(r_content)
            return token

        if r['statusCode'] == 502 or r['statusCode'] == 400:
            error_message = "ERROR: Incorrect username or password...."
            if using_secret:
                error_message = "ERROR: Incorrect username or password stored in Secrets Manager [MFServiceAccount-" + \
                                mf_config[
                                    'UserPoolId'] + "] in region " + mf_config['Region'] + "."
            print(error_message)
            sys.exit(1)
        else:
            print(r['text'])
            sys.exit()
    except requests.ConnectionError as e:
        logger.error(e)
        raise SystemExit(
            "ERROR: Connecting to the Login API failed, please check Login API in FactoryEndpoints.json file. "
            "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")


def get_login_response(mf_config, auth_data):
    try:
        body = auth_data
        client = boto3.client('cognito-idp', mf_config['Region'])
        response = {}
        userid = body['username']

        if 'mfacode' in body:
            # This is a response to MFA request on previous login attempt.
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
            response = {
                'statusCode': 400,
                'body': 'Incorrect username or password'
            }
        else:
            logger.error(e)

    return response, userid


# Function provides authentication of user credentials to the CMF Cognito user pool directly rather than via the CMF
# /prod/login endpoint. This is required for instances using WAF.
def factory_login_with_cognito_user_pool(auth_data, mf_config):
    if 'UserPoolId' in mf_config and 'Region' in mf_config:
        response, userid = get_login_response(mf_config, auth_data)
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

# end of user login related functions ###############
