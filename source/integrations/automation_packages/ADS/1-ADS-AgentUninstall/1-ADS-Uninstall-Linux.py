#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import sys
from mfcommon import execute_cmd

if not sys.warnoptions:
    import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=Warning)
    import paramiko


def uninstall_ads(host, username, key_pwd, using_key):
    print("")
    print("--------------------------------------------------------------------")
    print(f"- Uninstalling Application Discovery Service Agent for:  ${host} -")
    print("--------------------------------------------------------------------")
    try:
        output = None
        error = ''
        # Step 1 - run uninstall
        command = "sudo rpm -e --nodeps aws-discovery-agent"
        print(f"Executing ${command}")
        output, error1 = execute_cmd(host=host, username=username, key=key_pwd,
                                     cmd=command, using_key=using_key)
        print(output)
        command = "sudo apt-get remove aws-discovery-agent:i386"
        print(f"Executing ${command}")
        output, error2 = execute_cmd(host=host, username=username, key=key_pwd,
                                     cmd=command, using_key=using_key)
        print(output)

        command = "sudo zypper remove aws-discovery-agent"
        print(f"Executing ${command}")
        output, error3 = execute_cmd(host=host, username=username, key=key_pwd,
                                     cmd=command, using_key=using_key)
        print(output)

    except Exception as e:
        error = f'Got exception! ${str(e)}'

    if ((error == '' or
         error1 == '' or
         error2 == '' or
         error3 == '' or
         'warning: /etc/opt/aws/discovery/config saved as /etc/opt/aws/discovery/config.rpmsave' in error1) and
        'Error: Uninstallation failed' not in output
    ):
        print(f"***** Agent uninstallation completed successfully on ${host} *****")
        return True
    else:
        print(f"An error was returned from the uninstall command on ${host} due to: ")
        print("")
        print(f'unknown: ${error}, rpm: ${error1} , apt-get: ${error2}, zypper: ${error3}')
        return False
