#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


# Version: 23MAR2021.01

from __future__ import print_function
import sys
import argparse
import requests
import json
import subprocess
import getpass
import time

linuxpkg = __import__("1-Install-Linux")
import mfcommon

HOST = mfcommon.ce_address
headers = {'Content-Type': 'application/json'}
session = {}
endpoint = mfcommon.ce_endpoint

with open('FactoryEndpoints.json') as json_file:
    endpoints = json.load(json_file)


def CElogin(userapitoken, endpoint):
    login_data = {'userApiToken': userapitoken}
    r = requests.post(HOST + endpoint.format('login'),
                      data=json.dumps(login_data),
                      headers=headers,
                      timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
    if r.status_code == 200:
        print("CloudEndure : You have successfully logged in")
        print("")
    if r.status_code != 200 and r.status_code != 307:
        if r.status_code == 401 or r.status_code == 403:
            print('ERROR: The CloudEndure login credentials provided cannot be authenticated....')
        elif r.status_code == 402:
            print('ERROR: There is no active license configured for this CloudEndure account....')
        elif r.status_code == 429:
            print(
                'ERROR: CloudEndure Authentication failure limit has been reached. The service will become available for additional requests after a timeout....')

    # check if need to use a different API entry point
    if r.history:
        endpoint = '/' + '/'.join(r.url.split('/')[3:-1]) + '/{}'
        r = requests.post(HOST + endpoint.format('login'),
                          data=json.dumps(login_data),
                          headers=headers,
                          timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)

    session['session'] = r.cookies['session']
    try:
        headers['X-XSRF-TOKEN'] = r.cookies['XSRF-TOKEN']
    except:
        pass


def GetCEProject(projectname):
    r = requests.get(HOST + endpoint.format('projects'),
                     headers=headers,
                     cookies=session,
                     timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
    if r.status_code != 200:
        print("ERROR: Failed to fetch the project....")
        sys.exit(2)
    try:
        # Get Project ID
        project_id = ""
        projects = json.loads(r.text)["items"]
        project_exist = False
        for project in projects:
            if project["name"] == projectname:
                project_id = project["id"]
                project_exist = True
        if project_exist == False:
            print("ERROR: Project Name: " + projectname + " does not exist in CloudEndure....")
            sys.exit(3)
        return project_id
    except:
        print("ERROR: Failed to fetch the project....")
        sys.exit(4)


def GetInstallToken(project_id):
    # Get Machine List from CloudEndure
    project = requests.get(HOST + endpoint.format('projects/{}').format(project_id),
                           headers=headers,
                           cookies=session,
                           timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
    InstallToken = json.loads(project.text)['agentInstallationToken']
    return InstallToken


def ProjectList(waveid, token, UserHOST, serverendpoint, appendpoint):
    # Get all Apps and servers from migration factory
    auth = {"Authorization": token}
    servers = json.loads(requests.get(UserHOST + serverendpoint,
                                      headers=auth,
                                      timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT).text)
    # print(servers)
    apps = json.loads(requests.get(UserHOST + appendpoint,
                                   headers=auth,
                                   timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT).text)
    # print(apps)
    newapps = []

    CEProjects = []
    # Check project names in CloudEndure
    for app in apps:
        Project = {}
        if 'wave_id' in app:
            if str(app['wave_id']) == str(waveid):
                newapps.append(app)
                if 'cloudendure_projectname' in app:
                    Project['ProjectName'] = app['cloudendure_projectname']
                    project_id = GetCEProject(Project['ProjectName'])
                    Project['ProjectId'] = project_id
                    install_token = GetInstallToken(project_id)
                    Project['InstallToken'] = install_token
                    if Project not in CEProjects:
                        CEProjects.append(Project)
                else:
                    print("ERROR: App " + app['app_name'] + " is not linked to any CloudEndure project....")
                    sys.exit(5)
    Projects = ServerList(newapps, servers, CEProjects, waveid)
    return Projects


def ServerList(apps, servers, CEProjects, waveid):
    servercount = 0
    Projects = CEProjects
    for Project in Projects:
        Windows = []
        Linux = []
        for app in apps:
            if str(app['cloudendure_projectname']) == Project['ProjectName']:
                for server in servers:
                    if app['app_id'] == server['app_id']:
                        if 'server_os_family' in server:
                            if 'server_fqdn' in server:
                                if server['server_os_family'].lower() == "windows":
                                    Windows.append(server)
                                elif server['server_os_family'].lower() == "linux":
                                    Linux.append(server)
                            else:
                                print("ERROR: server_fqdn for server: " + server['server_name'] + " doesn't exist")
                                sys.exit(4)
                        else:
                            print('server_os_family attribute does not exist for server: ' + server[
                                'server_name'] + ", please update this attribute")
                            sys.exit(2)
        Project['Windows'] = Windows
        Project['Linux'] = Linux
        # print(Project)
        servercount = servercount + len(Windows) + len(Linux)
    if servercount == 0:
        print("ERROR: Serverlist for wave: " + waveid + " is empty....")
        sys.exit(3)
    else:
        return Projects


def AgentCheck(projects, token, UserHOST):
    auth = {"Authorization": token}
    success_servers = []
    failed_servers = []
    for project in projects:
        project_id = GetCEProject(project['ProjectName'])
        m = requests.get(HOST + endpoint.format('projects/{}/machines').format(project_id),
                         headers=headers,
                         cookies=session,
                         timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
        if len(project['Windows']) > 0:
            for w in project['Windows']:
                machine_exist = False
                serverattr = {}
                for machine in json.loads(m.text)["items"]:
                    if w["server_name"].lower() == machine['sourceProperties']['name'].lower() or w[
                        "server_fqdn"].lower() == machine['sourceProperties']['name'].lower():
                        machine_exist = True
                if machine_exist == True:
                    success_servers.append(w['server_fqdn'])
                    serverattr = {"migration_status": "CE Agent Install - Success"}
                else:
                    failed_servers.append(w['server_fqdn'])
                    serverattr = {"migration_status": "CE Agent Install - Failed"}
                update_w = requests.put(UserHOST + mfcommon.serverendpoint + '/' + w['server_id'],
                                        headers=auth,
                                        data=json.dumps(serverattr),
                                        timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
        if len(project['Linux']) > 0:
            for li in project['Linux']:
                serverattr = {}
                machine_exist = False
                serverattr = {}
                for machine in json.loads(m.text)["items"]:
                    if li["server_name"].lower() == machine['sourceProperties']['name'].lower() or li[
                        "server_fqdn"].lower() == machine['sourceProperties']['name'].lower():
                        machine_exist = True
                if machine_exist == True:
                    success_servers.append(li['server_fqdn'])
                    serverattr = {"migration_status": "CE Agent Install - Success"}
                else:
                    failed_servers.append(li['server_fqdn'])
                    serverattr = {"migration_status": "CE Agent Install - Failed"}
                update_l = requests.put(UserHOST + mfcommon.serverendpoint + '/' + li['server_id'],
                                        headers=auth,
                                        data=json.dumps(serverattr),
                                        timeout=mfcommon.REQUESTS_DEFAULT_TIMEOUT)
    if len(success_servers) > 0:
        print("***** CE Agent installed successfully on the following servers *****")
        for s in success_servers:
            print("  " + s)
        print("")
    if len(failed_servers) > 0:
        print("##### CE Agent install failed on the following servers #####")
        for s in failed_servers:
            print("  " + s)


def main(arguments):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--Waveid', required=True)
    parser.add_argument('--WindowsUser', default="")
    args = parser.parse_args(arguments)
    UserHOST = endpoints['UserApiUrl']
    print("")
    print("****************************")
    print("*Login to Migration factory*")
    print("****************************")
    token = mfcommon.Factorylogin()

    print("")
    print("************************")
    print("* Login to CloudEndure *")
    print("************************")
    r = CElogin(input('CE API Token: '), endpoint)
    if r is not None and "ERROR" in r:
        print(r)

    print("****************************")
    print("*** Getting Server List ***")
    print("****************************")
    Projects = ProjectList(args.Waveid, token, UserHOST, mfcommon.serverendpoint, mfcommon.appendpoint)
    linux_machines = False
    for project in Projects:
        if (len(project['Windows']) + len(project['Linux']) == 0):
            print("* CE Project " + project['ProjectName'] + " server list is empty *")
        else:
            print("* CE Project " + project['ProjectName'] + " *")
            if len(project['Windows']) > 0:
                print("   # Windows Server List #: ")
                for s in project['Windows']:
                    print("       " + s['server_fqdn'])
            if len(project['Linux']) > 0:
                linux_machines = True
                try:
                    print("   # Linux Server List #: ")
                    for s in project['Linux']:
                        print("       " + s['server_fqdn'])
                except Exception as error:
                    print('ERROR', error)
                    sys.exit(4)
        print("")

    print("******************************************")
    print("* Enter Linux Sudo username and password *")
    print("******************************************")
    user_name = ''
    pass_key = ''
    has_key = ''

    if linux_machines:
        user_name = input("Linux Username: ")
        has_key = input("If you use a private key to login, press [Y] or if use password press [N]: ")
        if has_key.lower() in 'y':
            pass_key = input('Private Key file name: ')
        else:
            pass_key_first = getpass.getpass('Linux Password: ')
            pass_key_second = getpass.getpass('Re-enter Password: ')
            while (pass_key_first != pass_key_second):
                print("Password mismatch, please try again!")
                pass_key_first = getpass.getpass('Linux Password: ')
                pass_key_second = getpass.getpass('Re-enter Password: ')
            pass_key = pass_key_second

    # Pass parameters to PowerShell
    # First Parameter - $reinstall - "Yes" or "No"
    # Second Parameter - $API_token - CloudEndure Install token
    # Third Parameter - $Servername - Server name that matchs Wave Id and CloudEndure project name
    print("")
    print("*********************************")
    print("* Installing CloudEndure Agents *")
    print("*********************************")
    print("")
    server_status = {}
    for project in Projects:
        server_string = ""
        if len(project['Windows']) > 0:
            if args.WindowsUser != "":
                windows_password = mfcommon.GetWindowsPassword()
            for server in project['Windows']:
                server_string = server_string + server['server_fqdn'] + ','
            server_string = server_string[:-1]

            if args.WindowsUser != "":
                p_trustedhosts = subprocess.Popen(["powershell.exe",
                                                   "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '" + server[
                                                       'server_fqdn'] + "' -Concatenate -Force"],
                                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p = subprocess.Popen(["powershell.exe",
                                      ".\\1-Install-Windows.ps1", "No", project['InstallToken'], server_string,
                                      args.WindowsUser, windows_password],
                                     stdout=sys.stdout)
            else:
                p = subprocess.Popen(["powershell.exe",
                                      ".\\1-Install-Windows.ps1", "No", project['InstallToken'], server_string],
                                     stdout=sys.stdout)
            p.communicate()
        if len(project['Linux']) > 0:
            for server in project['Linux']:
                status = linuxpkg.install_cloud_endure(server['server_fqdn'], user_name,
                                                       pass_key,
                                                       has_key.lower() in 'y', project['InstallToken'])
                server_status.update({server['server_fqdn']: status})
        print("")

    print("")
    print("********************************")
    print("*Checking Agent install results*")
    print("********************************")
    print("")

    time.sleep(5)
    AgentCheck(Projects, token, UserHOST)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
