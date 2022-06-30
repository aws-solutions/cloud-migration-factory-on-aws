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

# Version: 13MAY2022.01

from __future__ import print_function

import sys
import json
import subprocess
import boto3
import threading
import argparse
import io
import base64
from re import search
from botocore.exceptions import ClientError
import mfcommon
import os

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)

# Get region value from FactoryEndpoint.json file if migration execution server is on prem

if 'Region' in endpoints:
    region = endpoints['Region']
else:
    print("ERROR: Invalid FactoryEndpoints.json file, please update region")
    sys.exit()
print("Factory region: " + region)

serverendpoint = mfcommon.serverendpoint
appendpoint = mfcommon.appendpoint

# Global Variables
user_name = ''
pass_key = ''
has_key = 'False'
Domain_User= ''
Domain_Password = ''

# for storing the response from each thread
ll = []

global finalReport

win_failed_servers = []
win_success_servers = []
lin_failed_servers = []
lin_success_servers = []

output_bucket_name = "cmf-post-migration-report"

if "CMF_SCRIPTS_BUCKET" in os.environ:
    scripts_bucket = os.environ["CMF_SCRIPTS_BUCKET"]
    output_bucket_name = scripts_bucket.replace('-ssm-scripts', '-ssm-outputs')

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

def GetInstanceId(serverlist):
    error = False
    for account in serverlist:
        target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
        print("")
        print("Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'])
        mgn_client = target_account_session.client("mgn", account['aws_region'])
        mgn_sourceservers = get_mgn_source_servers(mgn_client)
        for factoryserver in account['servers']:
            if 'server_fqdn' not in factoryserver:
                print("ERROR: server_fqdn does not exist for server: " + factoryserver['server_name'])
                error = True
            else:
                sourceserver = mfcommon.get_MGN_Source_Server(factoryserver, mgn_sourceservers)
                if sourceserver is not None:
                    # Get target instance Id for the source server in Application Migration Service
                    if sourceserver['isArchived'] == False:
                        if 'launchedInstance' in sourceserver:
                            if 'ec2InstanceID' in sourceserver['launchedInstance']:
                                factoryserver['target_ec2InstanceID'] = sourceserver['launchedInstance']['ec2InstanceID']
                                print(factoryserver['server_name'] + " : " + factoryserver['target_ec2InstanceID'])
                            else:
                                factoryserver['target_ec2InstanceID'] = ''
                                print("ERROR: target instance Id does not exist for server: " + factoryserver['server_name'] + ", please wait for a few minutes")
                                error = True
                        else:
                            factoryserver['target_ec2InstanceID'] = ''
                            print("ERROR: target instance does not exist for server: " + factoryserver['server_name'] + ", please wait for a few minutes")
                            error = True
                    else:
                        print("ERROR: Server: " + factoryserver['server_name'] + " is archived in Application Migration Service (Account: " + account['aws_accountid'] + ", Region: " + account['aws_region'] + "), Please install the agent")
                        error = True
                else:
                    print("ERROR: Server: " + factoryserver['server_name'] + " is not yet cutover.")
                    error = True
    return serverlist,error

def get_win_service_val_status(server, p, report):
    #logger.debug("Checking Windows Validation Status")

    global finalReport
    stdout,stderr = p.communicate()
    output = stdout.decode('utf8')
    error = stderr.decode('utf8')
    if error != "":
        print(error)

    #report,console_output = get_win_service_val_status(server, output, report, console_output)

    for type in output.split("\n"):
        if type.strip() != "":
            for categories in type.split("|"):
                if categories == "validationStatus":
                    print("\n")
                    if report["validationStatus"] == "Fail":
                        report[categories] = "Fail"
                    else:
                        report[categories] = type.split("|")[1]
                    print("**** Overall Validation Status: " + report[categories] +" ****\n" )
                    break
                else:
                    if categories.strip() != "":
                        app = categories.split(",")
                        report[app[0]] = app[0]
                        if len(app) == 1:
                            print("")
                            print("*** "+app[0]+" ***" )

                        else:
                            report[app[0]] = app[1]
                            while len(app[0]) < 35:
                                app[0] = app[0] + "."
                            print(app[0] +":"+app[1])


    if "validationStatus" not in report or report["validationStatus"] == "Fail":
        win_failed_servers.append(server)
    else:
        win_success_servers.append(server)
    return report

def get_validations_list():
    software_validations=""
    if args.BootupStatusCheck:
        software_validations = "instance_bootup_status,instance_bootup_screenshot,"
    software_validations = software_validations + "termination_protection_enabled,mandatory_tags,"
    software_validations = software_validations + "Linux_Apps," + args.ServiceList
    if args.HostFileEntryCheck:
        software_validations = software_validations + ",host_file_entry_status,"
    software_validations = software_validations + ",host_ip_check_status,"
    software_validations = software_validations + ",host_ip,"
    if args.DnsEntryCheck:
        software_validations = software_validations + ",dns_entry_check,"
    if args.SyslogEntryCheck:
        software_validations = software_validations + ",syslog_entry_check,"

    software_validations = software_validations +  "Windows_Apps," \
                           + "Win_Wanted_Apps" +","+ args.wantedApplications + "," \
                           + "Win_UnWanted_Apps" +","+ args.unwantedApplications + "," \
                           + "Win_Running_Apps" +","+ args.runningApplications

    report = {"waveId": "NA","serverName": "NA", "serverType": "NA", "validationStatus": "NA"}
    software_validations_list = software_validations.split(",")

    software_validations_list_dict = dict.fromkeys(software_validations_list, "NA")

    # Combine 2 dictionaries
    reportList = {**report, **software_validations_list_dict}
    return reportList

def validate_windows_servers(parameters):

    server = parameters["server"]
    command = parameters["command"]

    try:

        # Irrespective of server tier, all servers would be validated
        p = subprocess.Popen(["powershell.exe", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return server, p
    except Exception as e:
        print("Unable to connect or Error while parsing the report "+server+" \n " +e)

def validate_linux_servers(parameters):

    try:
        server = parameters["server"]

        server_ip = parameters["server_ip"]
        report = parameters["report"]
        LinuxUser = parameters["LinuxUser"]
        LinuxPassword = parameters["LinuxPassword"]
        has_key = parameters["has_key"]
        console_output = ""

        cmd = 'ps -ef'
        # Irrespective of server tier, all servers would be validated
        stdout, stderr = mfcommon.execute_cmd(server, LinuxUser, LinuxPassword, cmd, has_key.lower() in 'y')
        if stderr == "":
            cmd2 = 'hostname'
            stdout1, stderr1 = mfcommon.execute_cmd(server, LinuxUser, LinuxPassword, cmd2, has_key.lower() in 'y')
            print("Hostname...........................: " + stdout1.strip())

            host_ip_check(server, server_ip,LinuxUser ,LinuxPassword, has_key, report, console_output)
            if args.HostFileEntryCheck:
                host_file_entry_check(server, server_ip,LinuxUser ,LinuxPassword, has_key, report, console_output)
            if args.DnsEntryCheck:
                dns_entry_check(server, LinuxUser ,LinuxPassword, has_key, report, args, console_output)
            if args.SyslogEntryCheck:
                syslog_entry_check(server, LinuxUser ,LinuxPassword, has_key, report, console_output)

            serverVerification = "Pass"
            console_output = console_output + "\n" + "*****  Service Validation\n"
            if ServiceList != "":
                for service in ServiceList.split(","):
                    if 'aws-cli' in service:
                        aws_cmd = 'aws --version'
                        stdout2, stderr2 = mfcommon.execute_cmd(server, LinuxUser, LinuxPassword, aws_cmd, has_key.lower() in 'y')
                        if (search('aws-cli', stdout2)) or (search('aws-cli/', stderr2) and search('Python/', stderr2) and search('botocore/', stderr2)):
                            serverVerification = "Pass"
                            console_output = console_output + "\n" + "Service "+service+" : Pass"
                            #logger.debug('%s: Service %s : Pass' % (server,service))
                            report[service] = "Pass"
                        else:
                            console_output = console_output + "\n" + "Service "+service+" : Fail"
                            #logger.debug('%s: Service %s : Fail' % (server, service))
                            serverVerification = "Fail"
                            report[service] = "Fail"
                    elif "vmtoolsd" in service:
                        if search("vmtoolsd", stdout):
                            console_output = console_output + "\n" + "Service "+service+" : Fail"
                            #logger.debug('%s: Service %s : Fail' % (server, service))
                            report[service] = "Fail"
                            serverVerification = "Fail"
                        else:
                            console_output = console_output + "\n" + "Service "+service+" : Pass"
                            #logger.debug('%s: Service %s : Pass' % (server,service))
                            serverVerification = "Pass"
                            report[service] = "Pass"
                    elif search(service, stdout):
                        console_output = console_output + "\n" + "Service "+service+" : Pass"
                        #logger.debug('%s: Service %s : Pass' % (server,service))
                        report[service] = "Pass"
                    else:
                        console_output = console_output + "\n" + "Service "+service+" : Fail"
                        #logger.debug('%s: Service %s : Fail' % (server, service))
                        serverVerification = "Fail"
                        report[service] = "Fail"
        else:
            serverVerification = "Fail"

        #logger.debug("%s: ##################################\n" % server)

        if serverVerification == "Fail":
            lin_failed_servers.append(server)
            report["validationStatus"] = "Fail"
        elif report["validationStatus"] == "Fail":
            lin_failed_servers.append(server)
            report["validationStatus"] = "Fail"
        else:
            lin_success_servers.append(server)
            report["validationStatus"] = "Pass"
        console_output = console_output + "\n\n" + "**** Overall Validation Status: "+report["validationStatus"]+" ****"

        return server, console_output

    except TimeoutError:
        print(server+" Unable to connect\n")

def validate_software_services(args, server_details, report):

    global ServiceList, wantedApplications, unwantedApplications, runningApplications
    server = server_details['server_fqdn']

    parameters = {}
    parameters["server"] = server


    report["waveId"] = args.Waveid
    report["serverName"] = server

    if server_details["server_os_family"] == "windows":
        if args.wantedApplications:
            wantedApplications = args.wantedApplications
        if args.unwantedApplications:
            unwantedApplications = args.unwantedApplications
        if args.runningApplications:
            runningApplications = args.runningApplications

        try:

            credentials = mfcommon.getServerCredentials(Domain_User, Domain_Password, server_details["server_name"],
                                                        args.SecretWindows, args.NoPrompts)
            #creds = " -Credential (New-Object System.Management.Automation.PSCredential(\"" + credentials['username'] + \
            #        "\", (ConvertTo-SecureString \"" + credentials['password'] + "\" -AsPlainText -Force)))"


            report["serverType"] = "Windows"
            report["Windows_Apps"] = "Windows_Apps"
            report["Win_Wanted_Apps"] = "Win_Wanted_Apps ->"
            report["Win_UnWanted_Apps"] = "Win_UnWanted_Apps ->"
            report["Win_Running_Apps"] = "Win_Running_Apps ->"

            # Add the target host to the trusted list
            subprocess.Popen(["powershell.exe", "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" +
                              server + "' -Concatenate -Force"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            command = "./Run-Remote-Validation.ps1 -Username " + \
                      credentials['username'] + " -Password " + "'" + credentials['password'] + "'" + " -Server " + server \
                      + " -wantedApplications " + "'" + wantedApplications + "'" + " -unwantedApplications " + "'" + \
                      unwantedApplications+ "'" + " -runningApplications " + runningApplications #+ creds
            parameters["command"] = command
            return(validate_windows_servers(parameters))

        except Exception as e:
            print("Unable to connect or Error while parsing the report "+ server +  "\n" + e)
    else:
        if args.ServiceList:
            ServiceList = args.ServiceList

        try:
            credentials = mfcommon.getServerCredentials(user_name, pass_key, server_details["server_name"],
                                                        args.SecretLinux, args.NoPrompts)
            server_tier = server_details['server_tier']
            server_ip = server_details.get("private_ip", None)

            report["serverType"] = "Linux"
            report["Linux_Apps"] = "Linux_Apps"

            parameters["server_ip"] = server_ip
            parameters["report"] = report
            parameters["LinuxUser"] = credentials['username']
            parameters["LinuxPassword"] = credentials['password']
            parameters["has_key"] = has_key
            #validate_linux_servers(parameters)
            return(validate_linux_servers(parameters))
        except TimeoutError:
            print("Unable to connect "+server+"\n")

def host_ip_check(server, server_ip,LinuxUser ,LinuxPassword, has_key, report, console_output):
    cmd2 = "hostname -I | awk '{print $1}'"
    stdout1, stderr1 = mfcommon.execute_cmd(server, LinuxUser, LinuxPassword, cmd2, has_key.lower() in 'y')
    report["host_ip"] = stdout1.strip()
    print("IP(s) of Instance..................: " + report["host_ip"])

    if server_ip:
        print("IP(s) from Launch Template.........: " + server_ip)
        if server_ip in stdout1:
            report["host_ip_check_status"] = "Pass"
        else:
            report["host_ip_check_status"] = "Fail"

        print("Host IP match Launch Template : " + report["host_ip_check_status"])
    else:
        # Private IP not assigned in Launch Template
        print("** Skipping Private IP check...")
        report["host_ip_check_status"] = "NA"

def host_file_entry_check(server, server_ip, LinuxUser, LinuxPassword, has_key, report, console_output):
    cmd2 = "hostname -I | awk '{print $1}'"
    stdout1, stderr1 = mfcommon.execute_cmd(server, LinuxUser, LinuxPassword, cmd2, has_key.lower() in 'y')
    report["host_ip"] = stdout1.strip()

    ## NEW CHECK FOR HOST FILE VALIDATION ##
    if report["host_ip"]:
        cmd2 = 'grep ' + report["host_ip"] + ' /etc/hosts'
        stdout3, stderr3 = mfcommon.execute_cmd(server, LinuxUser, LinuxPassword, cmd2, has_key.lower() in 'y')
        if report["host_ip"] in stdout3:
            report["host_file_entry_status"] = "Pass"
        else:
            report["host_file_entry_status"] = "Fail"
            report["validationStatus"] = "Fail"

    #logger.debug("%s: Checking Host Entry: %s" %( server, report["host_file_entry_status"]))
    print("Checking Host Entry................: " + report["host_file_entry_status"])

def dns_entry_check(server, LinuxUser ,LinuxPassword, has_key, report, args, console_output):

    if args.dnsIps:
        cmd2 = "grep -E '"+ args.dnsIps + "' /etc/resolv.conf"
        stdout1, stderr1 = mfcommon.execute_cmd(server, LinuxUser, LinuxPassword, cmd2, has_key.lower() in 'y')

        report["dns_entry_check"] = "Fail"
        for ip in args.dnsIps.split("|"):
            if ip in stdout1:
                report["dns_entry_check"] = "Pass"
                break

        if report["dns_entry_check"] == "Fail":
            report["validationStatus"] = "Fail"

        print("Checking DNS Entry.................: " + report["dns_entry_check"])
    else:
        print("*** Skipping DNS Check")

def syslog_entry_check(server, LinuxUser ,LinuxPassword, has_key, report, console_output):

    cmd2 = "grep linuxsyslogaws /etc/rsyslog.conf"
    stdout1, stderr1 = mfcommon.execute_cmd(server, LinuxUser, LinuxPassword, cmd2, has_key.lower() in 'y')

    if "linuxsyslogaws" in stdout1:
        report["syslog_entry_check"] = "Pass"
    else:
        report["syslog_entry_check"] = "Fail"
        report["validationStatus"] = "Fail"

    print("Checking Syslog Entry..............: " + report["syslog_entry_check"])

def recognize_ec2_instance_screenshot(rekognition_client, image_bytes, instance, report):
    server_id = instance['target_ec2InstanceID']


    response = rekognition_client.detect_text(
        Image={
            'Bytes' : image_bytes
        }

    )

    responseStatus = "Fail"

    # Any additional checks for the login page may be added below
    #print("***** Bootup Status ****")
    if len(response["TextDetections"]) > 0:
        for text in response["TextDetections"]:
            if text["Type"] == "LINE":
                #print(text["DetectedText"])
                if "Press" in text["DetectedText"] and "Alt" in text["DetectedText"] and "Delete" in text["DetectedText"]:
                    #print("Detected Text: "+ text["DetectedText"])
                    responseStatus = "Pass"
                    break
                elif "login:" in text["DetectedText"] or "login :" in text["DetectedText"]:
                    #print("Detected Text: "+ text["DetectedText"])
                    responseStatus = "Pass"
                    break
    print("Instance Bootup Status.............:" + responseStatus)
    report["instance_bootup_status"] = responseStatus

    return responseStatus

def get_instance_screenshot(ec2_client, rekognition_client, instance, args, bucket_name, report):
    instanceId = instance['target_ec2InstanceID']
    instanceName = instance['server_name']

    #logger.debug("Validating the Instance screenshot. Instance Name: %s" % instanceName )
    screenshot_path =  "screenshots/Wave"+args.Waveid
    try:
        screenshot = ec2_client.get_console_screenshot(InstanceId=instanceId)
        screenshot_in_bytes = str.encode(screenshot["ImageData"])
        image_bytes = base64.decodebytes(screenshot_in_bytes)

        # ************** Using Amazon Rekognition to read the text in instance screenshot ********
        instanceStatus = recognize_ec2_instance_screenshot(rekognition_client, image_bytes, instance, report)
        # ****************************************************************************************
        screenshot_status_wise_path = screenshot_path + "/" + instanceStatus + "/"
        key = instanceName+"_"+instanceId+".jpg"
        screenshot_file_name = screenshot_status_wise_path + key

        s3_resource.Bucket(bucket_name).upload_fileobj(io.BytesIO(image_bytes), screenshot_file_name)

        s3_url = "s3://"+bucket_name+"/"+key
        report["instance_bootup_screenshot"] = s3_url

    except Exception as e:
        print("Error: Error while trying to save the screenshot for instance: " + instanceId)
        print(e)

def get_instance_termination_protection(ec2_client, instance, args, report):
    instanceId = instance['target_ec2InstanceID']

    try:
        instance_attribute = ec2_client.describe_instance_attribute(Attribute='disableApiTermination', InstanceId=instanceId)

        if instance_attribute["DisableApiTermination"]["Value"] == False:
            termination_protection = "Fail"
        else:
            termination_protection = "Pass"

        print("Termination Protection Enabled.....:" + termination_protection)

        #logger.debug("Termination protection to be enabled? (Y/N): %s" % args.EnableTerminationProtection)

        if instance_attribute["DisableApiTermination"]["Value"] == False and args.EnableTerminationProtection:
            print("*** ----")
            print("** Enabling Termination Protection on instance: " + instanceId)
            response = ec2_client.modify_instance_attribute(
                InstanceId=instanceId,
                DisableApiTermination={
                    'Value': True
                },
            )
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                print("Successfully enabled termination protection")
                print("*** ----")
                termination_protection = "Pass"
            else:
                print("Failed while enabling termination protection")
                print("*** ----")
                termination_protection = "Fail"
                report["validationStatus"] = "Fail"
        report["termination_protection_enabled"] = termination_protection
    except Exception as e:
        print("Error: Error while trying to get the termination protection status of instance: " + instanceId)
        print(e)

def get_instance_tag_details(instance, report):
    if args.Tags:
        TagList = args.Tags
    instance_tag_list = []

    for instancetag in instance.tags:
        instance_tag_list.append(instancetag)

    tags_found = 0
    for tag in TagList.split(","):
        for instancetag in instance_tag_list:
            if instancetag["Key"] == tag.strip() and instancetag["Value"] != "":
                tags_found = tags_found + 1

    if tags_found == len(TagList.split(",")):
        tag_validation = "Pass"
    else:
        tag_validation = "Fail"
        report["validationStatus"] = "Fail"

    print("Tag validation Status..............:" + tag_validation)
    report["mandatory_tags"] = tag_validation

def verify_instance_details(account_servers_list, args):

    global finalReport

    get_servers,error = GetInstanceId(account_servers_list)

    if not error:
        for account in get_servers:

            #logger.debug("Project Name: %s" % project['ProjectName'])
            rekognition_client = boto3.client("rekognition", region)

            target_account_session = assume_role(str(account['aws_accountid']), account['aws_region'])
            ec2_client = target_account_session.client("ec2", region_name=account['aws_region'])
            ec2_resource = target_account_session.resource("ec2", region_name=account['aws_region'])
            #rekognition_client = target_account_session.client("rekognition", region_name=account['aws_region'])


            resp = ec2_resource.instances.filter(Filters=[{
                'Name': 'instance-state-name',
                'Values': ['running', 'stopped', 'pending']}])

            for instance in resp:
                for target_instance in account["servers"]:
                    if instance.id == target_instance['target_ec2InstanceID']:
                        # Create Server report from the template
                        report_dict = get_validations_list()
                        report = report_dict.copy()

                        print("")
                        print("*****************************************************************")
                        print("***** Validating Instance : "+target_instance["server_name"] + "*****")
                        print("*****************************************************************")
                        print("")

                        # ********* Validating the Login Screen by fetching the screenshot ********
                        if args.BootupStatusCheck:
                            get_instance_screenshot(ec2_client, rekognition_client, target_instance, args, bucket_name,
                                                    report)
                        # *************************************************************************

                        # ********* Validating the Termination protection of the instance ********
                        get_instance_termination_protection(ec2_client, target_instance, args, report)
                        # *************************************************************************

                        # *********  Validating the Mandatory tags of the instance  ********
                        get_instance_tag_details(instance, report)
                        # *************************************************************************

                        # *********  Validating the Mandatory Softwares/Services in Instance  ********
                        host,result = validate_software_services(args, target_instance, report)
                        if 'subprocess.Popen' in str(type(result)):
                            get_win_service_val_status(host, result, report)
                        else:
                            print(result)
                        # *************************************************************************
                        if "Fail" in report.values():
                            report["validationStatus"] = "Fail"
                        else:
                            report["validationStatus"] = "Pass"
                        finalReport.append(report)
    else:
        sys.exit()

def parse_args(argv):
    """parse arguments/options"""
    parser = argparse.ArgumentParser(description='CEMF : Automated Post Agent Install Validations')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        default=False, help='verbose output.')
    parser.add_argument('--Waveid', '-w', required=True, help='Wave ID from Migration factory')
    parser.add_argument('--SecretWindows', default=None)
    parser.add_argument('--SecretLinux', default=None)
    parser.add_argument('--Tags', '-t', default="Name", help='Comma separated list of Mandatory tags')
    parser.add_argument('--ServiceList', '-sl', default="amazon-ssm-agent",
                        help='Comma separated list of services to be validated in Linux server')
    parser.add_argument('--wantedApplications', '-wa',default = "Amazon SSM Agent",
                        help='Comma separated list of wanted applications'
                        ' to be validated in windows server')
    parser.add_argument('--unwantedApplications', '-uwa', default="McAfee,Norton,Symantec,VMWare Tools,AVG,Qualys",
                        help='Comma separated list of unwanted applications'
                                                               ' to be validated in windows server')
    parser.add_argument('--runningApplications', '-ra', default="AmazonSSMAgent",
                        help='Comma separated list of running applications'
                                                             ' to be validated in windows server')
    parser.add_argument('--NoPrompts', default=False, type=bool, help='Specify if user prompts for Passwords are '
                                                                      'allowed. Default = False')
    parser.add_argument('--EnableTerminationProtection', '-etp', default=False, type=bool, help='Whether to enable termination '
                                                                               'protection in the migrated instance')
    parser.add_argument('--EnableAllValidations', '-eav', default=False, type=bool, help='Whether to execute all validations')
    parser.add_argument('--HostFileEntryCheck', '-hfec', default=False, type=bool, help='Whether to execute Host file entry check')
    parser.add_argument('--DnsEntryCheck', '-dec', default=False, type=bool, help='Whether to execute DNS validations')
    parser.add_argument('--dnsIps', '-di', default=None, help='Pipe separated list of IPs. eg: "1.1.1.1|2.2.2.2"')
    parser.add_argument('--SyslogEntryCheck', '-sec', default=False, type=bool, help='Whether to execute Syslog validations')
    parser.add_argument('--BootupStatusCheck', '-bsc', default=False, type=bool, help='Whether to execute Bootup status check validations')

    args = parser.parse_args(argv)
    return args

def main(args):
    # These are global variables, its values are set during pre-requisites check itself.
    global user_name, pass_key, has_key, finalReport
    finalReport = []
    #try :

    # Get MF endpoints from FactoryEndpoints.json file
    if 'UserApiUrl' in endpoints:
        UserHOST = endpoints['UserApiUrl']
    else:
        print("ERROR: Invalid FactoryEndpoints.json file, please update UserApiUrl")
        sys.exit()

    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************", flush=True)
    token = mfcommon.Factorylogin()

    print("****************************")
    print("*** Getting Server List ****")
    print("****************************", flush = True)
    account_servers_list = mfcommon.get_factory_servers(args.Waveid, token, UserHOST, False, 'Rehost')
    linux_user_name = ''
    linux_pass_key = ''
    linux_key_exist = False

    # TO-DO
    #     * Verify disk usage (with drive letter checks)
    #     * Verify RDP and SSH access
    #     * ValidateCloudWatch custom metrics


    # Check Service Status and Installed Softwares

    verify_instance_details(account_servers_list, args)

    final_report_name_csv = mfcommon.create_csv_report("validationReport", finalReport, args.Waveid)
    key = "report/"+final_report_name_csv

    s3_resource.Bucket(bucket_name).upload_file(final_report_name_csv, key)

    s3_url = "s3://"+bucket_name+"/"+key
    print("Report is made available in the S3 bucket \n\n\n" + s3_url)

if __name__ == '__main__':

    s3_resource = boto3.resource("s3")
    bucket_name = output_bucket_name

    args = parse_args(sys.argv[1:])
    if args.EnableAllValidations:
        args.HostFileEntryCheck = True
        args.DnsEntryCheck = True
        args.SyslogEntryCheck = True
        args.BootupStatusCheck = True
    sys.exit(main(args))