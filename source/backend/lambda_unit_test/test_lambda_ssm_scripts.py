#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0



import unittest
import boto3
import logging
import json
import os
from unittest import TestCase, mock
from moto import mock_dynamodb, mock_s3

# This is to get around the relative path import issue.
# Absolute paths are being used in this file after setting the root directory
import sys
from pathlib import Path

file = Path(__file__).resolve()
package_root_directory = file.parents[1]
sys.path.append(str(package_root_directory))
sys.path.append(str(package_root_directory) + '/lambda_layers/lambda_layer_policy/python/')

# Set log level
loglevel = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger(__name__)

default_http_headers = {
    'Access-Control-Allow-Origin': '*',
    'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
    'Content-Security-Policy': "base-uri 'self'; upgrade-insecure-requests; default-src 'none'; object-src 'none'; connect-src none; img-src 'self' data:; script-src blob: 'self'; style-src 'self'; font-src 'self' data:; form-action 'self';"
}

test_script_records = [
    {
        "package_uuid": {
            "S": "9bd96f83-8510-44a9-be5e-d34f20982143"
        },
        "version": {
            "N": "0"
        },
        "default": {
            "N": "1"
        },
        "latest": {
            "N": "1"
        },
        "script_arguments": {
            "L": [
                {
                    "M": {
                        "description": {
                            "S": "Argument 1"
                        },
                        "group_order": {
                            "S": "1"
                        },
                        "long_desc": {
                            "S": "Argument 1 long description."
                        },
                        "name": {
                            "S": "argument1"
                        },
                        "required": {
                            "BOOL": True
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                }
            ]
        },
        "script_dependencies": {
            "NULL": True
        },
        "script_description": {
            "S": "This is a test script."
        },
        "script_group": {
            "S": "Test"
        },
        "script_masterfile": {
            "S": "test-masterfile.py"
        },
        "script_name": {
            "S": "test"
        },
        "script_update_url": {
            "NULL": True
        },
        "version_id": {
            "S": "YWOD5U3Wn4XO4e8ApSSetwmtq0I_4maw"
        },
        "_history": {
            "M": {
                "createdBy": {
                    "M": {
                        "email": {
                            "S": "someone@example.com"
                        },
                        "userRef": {
                            "S": "someone"
                        }
                    }
                },
                "createdTimestamp": {
                    "S": "2023-05-26T07:50:06.396959"
                },
                "lastModifiedBy": {
                    "M": {
                        "email": {
                            "S": "someone@example.com"
                        },
                        "userRef": {
                            "S": "someone"
                        }
                    }
                },
                "lastModifiedTimestamp": {
                    "S": "2023-05-26T08:01:35.441261"
                }
            }
        }
    }
    , {
        "package_uuid": {
            "S": "9bd96f83-8510-44a9-be5e-d34f20982143"
        },
        "version": {
            "N": "1"
        },
        "script_arguments": {
            "L": [
                {
                    "M": {
                        "description": {
                            "S": "Argument 1"
                        },
                        "group_order": {
                            "S": "1"
                        },
                        "long_desc": {
                            "S": "Argument 1 long description."
                        },
                        "name": {
                            "S": "argument1"
                        },
                        "required": {
                            "BOOL": True
                        },
                        "type": {
                            "S": "string"
                        }
                    }
                }
            ]
        },
        "script_dependencies": {
            "NULL": True
        },
        "script_description": {
            "S": "This is a test script."
        },
        "script_group": {
            "S": "Cutover"
        },
        "script_masterfile": {
            "S": "test-masterfile.py"
        },
        "script_name": {
            "S": "test"
        },
        "script_update_url": {
            "NULL": True
        },
        "version_id": {
            "S": "YWOD5U3Wn4XO4e8ApSSetwmtq0I_4maw"
        },
        "_history": {
            "M": {
                "createdBy": {
                    "M": {
                        "email": {
                            "S": "someone@example.com"
                        },
                        "userRef": {
                            "S": "someone"
                        }
                    }
                },
                "createdTimestamp": {
                    "S": "2023-05-26T07:50:06.396959"
                }
            }
        }
    }
]

test_script_base64 = "data:application/zip;base64,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"


@mock.patch('lambda_ssm_scripts.item_validation')
def mock_item_validation():
    return {'action': 'allow'}





scripts_table_name = '{}-{}-'.format('cmf', 'unittest') + 'ssm-scripts'
scripts_s3_bucket_name = 'scripts_s3_bucket'

# Setting the default AWS region environment variable required by the Python SDK boto3
@mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1', 'region': 'us-east-1', 'application': 'cmf',
                              'environment': 'unittest', 'scripts_bucket_name': scripts_s3_bucket_name,
                              'scripts_table': scripts_table_name})
@mock_dynamodb
@mock_s3
class LambdaSSMScriptsTest(TestCase):
    def setUp(self):
        # Setup dynamoDB tables and put items required for test cases
        boto3.setup_default_session()
        self.scripts_table_name = scripts_table_name
        # Creating schema table and creating schema item to test out schema types
        self.ddb_client = boto3.client("dynamodb", region_name='us-east-1')
        self.ddb_client.create_table(
            TableName=self.scripts_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
                {"AttributeName": "package_uuid", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "package_uuid", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "N"},
            ],
            GlobalSecondaryIndexes=[
                {"IndexName": "version-index",
                 "KeySchema": [
                     {"AttributeName": "version", "KeyType": "HASH"}
                 ],
                 "Projection": {
                     "ProjectionType": "ALL"}
                 }
            ]

        )
        for item in test_script_records:
            self.ddb_client.put_item(
                TableName=self.scripts_table_name,
                Item=item)

        self.s3_client = boto3.client("s3", region_name='us-east-1')
        self.s3_client.create_bucket(
            Bucket=scripts_s3_bucket_name,
        )
        self.s3_client.put_bucket_versioning(
            Bucket=scripts_s3_bucket_name,
            VersioningConfiguration={
                'Status': 'Enabled'
            },
        )

    def tearDown(self):
        """
        Delete database resource and mock table
        """
        print("Tearing down")
        self.ddb_client.delete_table(TableName=self.scripts_table_name)
        self.dynamodb = None
        print("Teardown complete")

    def mock_getUserAttributePolicy(self, event, schema):
        return {'action': 'allow'}

    def mock_getUserResourceCreationPolicy(self, event, schema):
        return {'action': 'allow', 'user': 'testuser@testuser'}

    def test_lambda_handler_scripts_get_all_default_versions(self):
        from lambda_functions.lambda_ssm_scripts import lambda_ssm_scripts

        self.event = {"httpMethod": 'GET', "pathParameters": None}
        log.info("Testing lambda_ssm_scripts GET default scripts")
        result = lambda_ssm_scripts.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        expected_result_data = [{"package_uuid": "9bd96f83-8510-44a9-be5e-d34f20982143", "version": "0", "default": "1",
                                 "latest": "1", "script_arguments": [{"description": "Argument 1", "group_order": "1",
                                                                      "long_desc": "Argument 1 long description.",
                                                                      "name": "argument1", "required": True,
                                                                      "type": "string"}],
                                 "script_dependencies": None,
                                 "script_description": "This is a test script.",
                                 "script_group": "Test",
                                 "script_masterfile": "test-masterfile.py",
                                 "script_name": "test", "script_update_url": None,
                                 "version_id": "YWOD5U3Wn4XO4e8ApSSetwmtq0I_4maw",
                                 "_history": {"createdBy": {"email": "someone@example.com", "userRef": "someone"},
                                              "createdTimestamp": "2023-05-26T07:50:06.396959",
                                              "lastModifiedBy": {"email": "someone@example.com", "userRef": "someone"},
                                              "lastModifiedTimestamp": "2023-05-26T08:01:35.441261"}}]
        expected_response = {'headers': {**default_http_headers}, 'body': f"{json.dumps(expected_result_data)}"}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_get_script_by_id_return_all_versions(self):
        from lambda_functions.lambda_ssm_scripts import lambda_ssm_scripts

        self.event = {"httpMethod": 'GET', "pathParameters": {"scriptid": "9bd96f83-8510-44a9-be5e-d34f20982143"}}
        log.info("Testing lambda_ssm_scripts GET specific script by ID and return all versions of the script.")
        result = lambda_ssm_scripts.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        expected_result_data = [{"package_uuid": "9bd96f83-8510-44a9-be5e-d34f20982143", "version": "0", "default": "1",
                                 "latest": "1", "script_arguments": [{"description": "Argument 1", "group_order": "1",
                                                                      "long_desc": "Argument 1 long description.",
                                                                      "name": "argument1", "required": True,
                                                                      "type": "string"}],
                                 "script_dependencies": None,
                                 "script_description": "This is a test script.",
                                 "script_group": "Test",
                                 "script_masterfile": "test-masterfile.py",
                                 "script_name": "test", "script_update_url": None,
                                 "version_id": "YWOD5U3Wn4XO4e8ApSSetwmtq0I_4maw",
                                 "_history": {"createdBy": {"email": "someone@example.com", "userRef": "someone"},
                                              "createdTimestamp": "2023-05-26T07:50:06.396959",
                                              "lastModifiedBy": {"email": "someone@example.com", "userRef": "someone"},
                                              "lastModifiedTimestamp": "2023-05-26T08:01:35.441261"}},
                                {"package_uuid": "9bd96f83-8510-44a9-be5e-d34f20982143",
                                 "version": "1",
                                 "script_arguments": [{"description": "Argument 1",
                                                       "group_order": "1",
                                                       "long_desc": "Argument 1 long description.",
                                                       "name": "argument1", "required": True, "type": "string"}],
                                 "script_dependencies": None,
                                 "script_description": "This is a test script.",
                                 "script_group": "Cutover",
                                 "script_masterfile": "test-masterfile.py",
                                 "script_name": "test", "script_update_url": None,
                                 "version_id": "YWOD5U3Wn4XO4e8ApSSetwmtq0I_4maw",
                                 "_history": {"createdBy": {"email": "someone@example.com", "userRef": "someone"},
                                              "createdTimestamp": "2023-05-26T07:50:06.396959"}}]
        expected_response = {'headers': {**default_http_headers}, 'body': f"{json.dumps(expected_result_data)}"}
        self.assertEqual(data, expected_response)

    def test_lambda_handler_scripts_upload(self):
        from lambda_functions.lambda_ssm_scripts import lambda_ssm_scripts

        self.event = {"httpMethod": 'POST', "body": json.dumps({"script_file": test_script_base64,
                                                                "script_name": "testscriptupload"})}
        log.info("Testing lambda_ssm_scripts PUT upload new script")
        result = lambda_ssm_scripts.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        self.assertEqual(data.get('statusCode'), 200)
        self.assertEqual(data.get('headers'), {**default_http_headers})


    @mock.patch('policy.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_scripts_upload_updated(self):
        from lambda_functions.lambda_ssm_scripts import lambda_ssm_scripts

        self.event = {"httpMethod": 'PUT', "body": json.dumps({"script_file": test_script_base64,
                                                               "script_name": "testscriptupload",
                                                               "action": "update_package"}),
                      "pathParameters": {"scriptid": "9bd96f83-8510-44a9-be5e-d34f20982143"}
                      }
        log.info("Testing lambda_ssm_scripts PUT upload updated script")
        result = lambda_ssm_scripts.lambda_handler(self.event, '')
        data = result
        print("Result data: ", data)
        expected_result_data = [
            {"package_uuid": "9bd96f83-8510-44a9-be5e-d34f20982143",
             "version": "1",
             "script_arguments": [{"description": "Argument 1",
                                   "group_order": "1",
                                   "long_desc": "Argument 1 long descrption.",
                                   "name": "argument1", "required": True, "type": "string"}],
             "script_dependencies": None,
             "script_description": "This is a test script.",
             "script_group": "Cutover",
             "script_masterfile": "test-masterfile.py",
             "script_name": "test", "script_update_url": None,
             "version_id": "YWOD5U3Wn4XO4e8ApSSetwmtq0I_4maw",
             "_history": {"createdBy": {"email": "someone@example.com", "userRef": "someone"},
                          "createdTimestamp": "2023-05-26T07:50:06.396959"}}]
        self.assertEqual(data.get('statusCode'), 200)
        self.assertEqual(data.get('headers'), {**default_http_headers})
