#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
import json
import os
import sys
from pathlib import Path


file = Path(__file__).resolve()
sys.path.append(str(file.parents[0]))
integrations_directory = str(file.parents[2])
sys.path.append(integrations_directory)
sys.path.append(integrations_directory + '/credential_manager/lambdas')
source_directory = file.parents[3]
for directory in os.listdir(str(source_directory) + '/backend/lambda_layers/'):
    sys.path.append(str(source_directory) + '/backend/lambda_layers/' + directory + '/python')

from cmf_logger import logger
logger.debug(f'sys.path: {list(sys.path)}')


class CredentialManagerTestBase(unittest.TestCase):

    def setUp(self):
        os.environ['region'] = 'us-east-1'
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

        self.init_event_vars()

    def init_event_vars(self):
        self.create_os_secret_event = {
            'body': json.dumps({
                'user': 'testUser',
                'password': 'testPassword',
                'secretName': 'secretName',
                'osType': 'osType',
                'secretType': 'OS',
                'description': 'description',
                'isSSHKey': 'MySSHKey',
            })
        }
        self.create_os_secret_event_2 = {
            'body': json.dumps({
                'secretName': 'secretName',
                'osType': 'osTypeUpdated',
                'secretType': 'OS',
            })
        }
        self.create_os_secret_event_updated = {
            'body': json.dumps({
                'user': 'testUserUpdated',
                'password': 'testPassword',
                'secretName': 'secretName',
                'osType': 'osType',
                'secretType': 'OS',
                'isSSHKey': 'MySSHKey',
            })
        }
        self.create_key_value_secret_event = {
            'body': json.dumps({
                'secretName': 'secretName',
                'secretKey': 'secretKey',
                'secretValue': 'secretValue',
                'secretType': 'keyValue',
                'description': 'description',
            })
        }
        self.create_key_value_secret_event_updated = {
            'body': json.dumps({
                'secretName': 'secretName',
                'secretKey': 'secretKeyUpdated',
                'secretValue': 'secretValue',
                'secretType': 'keyValue',
                'description': 'description',
            })
        }
        self.create_plain_text_secret_event = {
            'body': json.dumps({
                'secretName': 'secretName',
                'secretString': 'secretString',
                'secretType': 'plainText',
                'description': 'description',
            })
        }
        self.create_plain_text_secret_event_updated = {
            'body': json.dumps({
                'secretName': 'secretName',
                'secretString': 'secretStringUpdated',
                'secretType': 'plainText',
                'description': 'description',
            })
        }
        self.get_secret_event = {
            'queryStringParameters': {
                'Name': 'secretName',
            }
        }

        self.lambda_get_event = {
            'httpMethod': 'GET',
        }

        self.lambda_put_event = {
            'httpMethod': 'PUT',
            'body': json.dumps({
                'secretType': 'OS',
            }),
        }

        self.lambda_delete_event = {
            'httpMethod': 'DELETE',
            'body': json.dumps({
                'secretType': 'OS',
            }),
        }

        self.lambda_post_OS_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'secretType': 'OS',
            }),
        }

        self.lambda_post_keyValue_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'secretType': 'keyValue',
            }),
        }

        self.lambda_post_plainText_event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'secretType': 'plainText',
            }),
        }

    def tearDown(self):
        pass
