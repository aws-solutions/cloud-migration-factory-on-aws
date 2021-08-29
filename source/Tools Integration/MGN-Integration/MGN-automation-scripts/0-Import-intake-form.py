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

# Version: 08APR2021.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import csv
import boto3
import botocore.exceptions
import mfcommon

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint
waveendpoint = mfcommon.waveendpoint

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

def get_reader(file):
    ordered_dict_list = []
    input_file = csv.DictReader(open(file))
    for row in input_file:
        ordered_dict_list.append(row)
    # return input_file
    return ordered_dict_list

def convert_string_to_list(row_str):
    row_list = []
    row_list = row_str.split(';')
    return row_list

def data_validation(data, app_list_csv):
    # Validate app attribute
    for app in app_list_csv:
        match = True
        attr = ""
        app_list_validation = []
        for row in data:
            if app['app_name'].strip() == row['app_name'].strip():
               app_list_validation.append(row)
        for app_validation in app_list_validation:
            wave_name = "Wave " + app_validation['wave_id'].strip()
            if wave_name != app['wave_name'].strip():
                match = False
                attr = 'wave_id'
            elif app_validation['aws_region'].strip() != app['aws_region'].strip():
                match = False
                attr = 'aws_region'
            elif app_validation['aws_accountid'] != app['aws_accountid']:
                match = False
                attr = 'aws_accountid'
        if (match == False):
            print("Error: App attributes " + attr + " doesn't match, please validate app: " + app['app_name'])
            sys.exit(1)

def uploading_data(data, token, UserHOST):
    auth = {"Authorization": token}
    try:
        waves = json.loads(requests.get(UserHOST + waveendpoint, headers=auth).text)
        apps = json.loads(requests.get(UserHOST + appendpoint, headers=auth).text)
    except requests.exceptions.ConnectionError as e:
            raise SystemExit("ERROR: Connecting to User API failed, please check User API in FactoryEndpoints.json file. "
                            "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")
    wave_list_csv = []
    app_list_csv = []
    wave_ids = []
    app_list = []
    server_list = []

    for row in data:
        if row['wave_id'].strip() not in wave_list_csv:
            wave_list_csv.append(str(row['wave_id']).strip())
        match = False
        for app in app_list_csv:
            if row['app_name'].lower().strip() == app['app_name'].lower().strip():
                match = True
        if (match == False):
            app_item = {}
            app_item['app_name'] = row['app_name'].strip()
            app_item['wave_name'] = "Wave " + row['wave_id'].strip()
            app_item['aws_region'] = row['aws_region'].strip()
            if len(row['aws_accountid']) == 12 and row['aws_accountid'].isdigit():
               app_item['aws_accountid'] = row['aws_accountid'].strip()
            else:
               print("Error: Invalid AWS Account Id for app: " + row['app_name'].strip())
               sys.exit()

            app_list_csv.append(app_item)

    data_validation(data, app_list_csv)

    # Get Unique new Wave Id, add to the list if Wave Id doesn't exist in the factory
    for wave_id in wave_list_csv:
        match = False
        for wave in waves:
            wave_name = "Wave " + wave_id
            if str(wave_name) == str(wave['wave_name']):
                match = True
        if (match == False):
            wave_ids.append(wave_id)
    if len(wave_ids) != 0:
        wave_ids.sort()
        print("New Waves: ")
        print("")
        for wave in wave_ids:
            print("Wave " + wave)
        print("")
        # Creating new Waves in the migration factory
        for wave in wave_ids:
            wave_name = {}
            wave_name['wave_name'] = "Wave " + wave
            try:
                r = requests.post(UserHOST + waveendpoint, headers=auth, data=json.dumps(wave_name))
                if r.status_code == 200:
                    print("Wave " + wave + " created in the migration factory")
                else:
                    print("Wave " + wave + " failed : " + r.text + ".......")
                    sys.exit()
            except requests.exceptions.ConnectionError as e:
                   raise SystemExit("ERROR: Connecting to User API failed, please check User API in FactoryEndpoints.json file. "
                                    "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")
        print("")
        print("----------------------------------------")
        print("")

    # Get Unique new App Name, add to the resource list if App Name doesn't exist in the factory
    for app_csv in app_list_csv:
        try:
            new_waves = json.loads(requests.get(UserHOST + waveendpoint, headers=auth).text)
        except requests.exceptions.ConnectionError as e:
                raise SystemExit("ERROR: Connecting to User API failed, please check User API in FactoryEndpoints.json file. "
                                "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")
        for wave in new_waves:
            if app_csv['wave_name'] == str(wave['wave_name']):
                app_csv['wave_id'] = wave['wave_id']
                del app_csv['wave_name']
                break
        match = False
        for app in apps:
            if app_csv['app_name'].lower().strip() == app['app_name'].lower().strip():
                match = True
                if app_csv['wave_id'] != app['wave_id']:
                    print("Error: Wave_id for app " + app_csv['app_name'] + " doesn't match the Wave_id for the same app in the factory")
                    sys.exit(2)
                if app_csv['aws_region'] != app['aws_region']:
                    print("Error: aws_region for app " + app_csv['app_name'] + " doesn't match the aws_region for the same app in the factory")
                    sys.exit(3)
                if app_csv['aws_accountid'] != app['aws_accountid']:
                    print("Error: aws_accountid for app " + app_csv['app_name'] + " doesn't match the aws_accountid for the same app in the factory")
                    sys.exit(4)
        if (match == False):
            app_list.append(app_csv)
    if len(app_list) != 0:
        print("New Apps: ")
        print("")
        for app in app_list:
            print(app["app_name"])
        print("")
        # Creating new Apps in the migration factory
        for app in app_list:
            try:
                r = requests.post(UserHOST + appendpoint, headers=auth, data=json.dumps(app))
                if r.status_code == 200:
                    print("App " + app['app_name'] + " created in the migration factory")
                else:
                    print("App " + app['app_name'] + " failed : " + r.text + ".......")
                    sys.exit()
            except requests.exceptions.ConnectionError as e:
                   raise SystemExit("ERROR: Connecting to User API failed, please check User API in FactoryEndpoints.json file. "
                                    "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")
        print("")
        print("----------------------------------------")
        print("")
    # Get Unique server names, add to the resource list if Server Name doesn't exist in the factory
    try:
        newapps = json.loads(requests.get(UserHOST + appendpoint, headers=auth).text)
    except requests.exceptions.ConnectionError as e:
            raise SystemExit("ERROR: Connecting to User API failed, please check User API in FactoryEndpoints.json file. "
                            "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")
    for row in data:
        for app in newapps:
            if row['app_name'].lower().strip() == app['app_name'].lower().strip():
               row['app_id'] = app['app_id']
        tags = []
        tag = {}
        server_item = {}
        server_item['server_name'] = row['server_name'].strip()
        tag['key'] = 'Name'
        tag['value'] = row['server_name'].strip()
        tags.append(tag)
        server_item['tags'] = tags
        server_item['app_id'] = row['app_id'].strip()
        server_item['server_os_family'] = row['server_os_family'].strip()
        server_item['server_os_version'] = row['server_os_version'].strip()
        server_item['server_fqdn'] = row['server_fqdn'].strip()
        server_item['server_tier'] = row['server_tier'].strip()
        server_item['server_environment'] = row['server_environment'].strip()
        server_item['subnet_IDs'] = convert_string_to_list(row['subnet_IDs'].strip())
        server_item['securitygroup_IDs'] = convert_string_to_list(row['securitygroup_IDs'].strip())
        server_item['subnet_IDs_test'] = convert_string_to_list(row['subnet_IDs_test'].strip())
        server_item['securitygroup_IDs_test'] = convert_string_to_list(row['securitygroup_IDs_test'].strip())
        if 'instanceType' in row:
            server_item['instanceType'] = row['instanceType'].strip()
        if 'iamRole' in row:
            server_item['iamRole'] = row['iamRole'].strip()
        if 'private_ip' in row:
            server_item['private_ip'] = row['private_ip'].strip()
        if 'tenancy' in row:
            server_item['tenancy'] = row['tenancy'].strip()
        server_list.append(server_item)
    if len(server_list) != 0:
        print("New Servers: ")
        print("")
        for server in server_list:
            print(server['server_name'])
        print("")
        # Creating new Apps in the migration factory
        for server in server_list:
            try:
                r = requests.post(UserHOST + serverendpoint, headers=auth, data=json.dumps(server))
                if r.status_code == 200:
                    print("Server " + server['server_name'] + " created in the migration factory")
                else:
                    print("ERROR: " + server['server_name'] + " failed : " + r.text + ".......")
            except requests.exceptions.ConnectionError as e:
                   raise SystemExit("ERROR: Connecting to User API failed, please check User API in FactoryEndpoints.json file. "
                                    "If the API endpoint is correct, please close cmd and open a new cmd to run the script again")

def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Intakeform', required=True)
    args = parser.parse_args(arguments)

    UserHOST = ""

    # Get MF endpoints from FactoryEndpoints.json file
    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit()

    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*Reading intake form List*")
    print("****************************")
    data = get_reader(args.Intakeform)
    print("Intake form data loaded for processing....")
    print("")

    print("*********************************************")
    print("*Creating resources in the migration factory*")
    print("*********************************************")

    r = uploading_data(data,token,UserHOST)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
