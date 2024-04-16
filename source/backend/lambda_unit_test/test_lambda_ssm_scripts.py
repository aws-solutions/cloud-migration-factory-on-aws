#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import base64
import os
import unittest
import zipfile
from unittest.mock import patch

import boto3
from unittest import mock

import botocore
from boto3.dynamodb.conditions import Key
from moto import mock_aws
import test_common_utils
from test_common_utils import logger

mock_os_environ = {
    **test_common_utils.default_mock_os_environ,
    'scripts_bucket_name': 'test_bucket_ssm_scripts',
    'scripts_table': 'test_table_ssm_scripts'
}


def mock_get_user_resource_creation_policy_allow(obj, event, schema):
    logger.debug(f'mock_get_user_resource_creation_policy_allow({obj}, {event}, {schema})')
    return {'action': 'allow', 'user': 'testuser@example.com'}


def mock_get_user_resource_creation_policy_default_deny(obj, event, schema):
    logger.debug(f'mock_get_user_resource_creation_policy_default_deny({obj}, {event}, {schema})')
    return {'action': 'deny', 'cause': 'Request is not Authenticated'}


CONST_SCRIPT_FILE_NAME = 'hello_world.py'


def mock_aws_invoke_factory(kind=0):

    def mock_aws_invoke(FunctionName, InvocationType, Payload, ClientContext=None):
        logger.debug(f'mock_aws_invoke({FunctionName}, {InvocationType}, {Payload}, {ClientContext})')

        if kind == 1:
            payload = {
                'statusCode': 200,
                'body': json.dumps({
                    'ResponseMetadata': {
                        'HTTPStatusCode': 500,
                        'Message': 'Internal Error'
                    }
                })
            }
        elif kind == 2:
            payload = {
                'statusCode': 500,
                'body': json.dumps({
                    'ResponseMetadata': {
                        'HTTPStatusCode': 500,
                        'Message': 'Internal Error'
                    }
                })
            }
        elif kind == 3:
            payload = {
                'statusCode': 500,
                'body': json.dumps({
                    'ResponseMetadata': {
                        'HTTPStatusCode': 500,
                        'Message': 'already exist'
                    }
                })
            }
        else:
            payload = {
                'statusCode': 200,
                'body': json.dumps({
                    'ResponseMetadata': {
                        'HTTPStatusCode': 200,
                        'Message': 'Successfully invoked'
                    }
                })
            }

        class LambdaPayload:
            def read(self):
                return json.dumps(payload)

        return {
            'Payload': LambdaPayload()
        }

    return mock_aws_invoke


@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaSSMScriptsTest(unittest.TestCase):

    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
        self.s3_client = boto3.client('s3')
        self.ddb_client = boto3.client('dynamodb')

        self.scripts_table_name = os.getenv('scripts_table')
        test_common_utils.create_and_populate_ssm_scripts(self.ddb_client, self.scripts_table_name)
        self.scripts_table = boto3.resource('dynamodb').Table(self.scripts_table_name)

        self.package_uuid_1 = '11111111-1111-1111-1111-111111111'
        self.package_uuid_2 = '22222222-2222-2222-2222-222222222222'
        self.package_version_1 = 0
        self.package_version_1_updated = 1
        self.package_version_2 = 0

        self.create_bucket()

        self.init_event_objects()

    def tearDown(self) -> None:
        # cleanup zip created in setUp
        for current_zip in ["package_valid",
                            "package_invalid_yaml",
                            "package_no_yaml",
                            "package_incorrect_yaml_contents",
                            "package_no_master_file",
                            "package_valid_with_dependencies",
                            "package_missing_dependencies",
                            "package_invalid_attributes",
                            "package_schema_extensions"]:
            zip_folder = f'{os.path.dirname(os.path.realpath(__file__))}/sample_data/ssm_load_scripts/{current_zip}/'
            os.remove(f"{zip_folder}/{current_zip}.zip")
    def init_event_objects(self):
        self.event_get_default = {
            'httpMethod': 'GET'
        }
        self.event_get_script_id_not_exist = {
            'httpMethod': 'GET',
            'pathParameters': {
                'scriptid': self.package_uuid_1 + 'DOESNT_EXIST',
                'version': self.package_version_1,
                'action': 'NotImportant'
            }
        }
        self.event_get_download = {
            'httpMethod': 'GET',
            'pathParameters': {
                'scriptid': self.package_uuid_1,
                'version': self.package_version_1,
                'action': 'download'
            }
        }

        self.event_get_no_download = {
            'httpMethod': 'GET',
            'pathParameters': {
                'scriptid': self.package_uuid_1,
                'version': self.package_version_1,
                'action': 'no_download'
            }
        }

        self.event_get_single_version = {
            'httpMethod': 'GET',
            'pathParameters': {
                'scriptid': self.package_uuid_2,
                'version': self.package_version_2
            }
        }

        self.event_get_single_version_zero_count = {
            'httpMethod': 'GET',
            'pathParameters': {
                'scriptid': self.package_uuid_2 + 'ZERO_COUNT',
                'version': self.package_version_2
            }
        }

        self.event_get_all_versions = {
            'httpMethod': 'GET',
            'pathParameters': {
                'scriptid': self.package_uuid_1
            }
        }

        self.event_get_all_versions_zero_count = {
            'httpMethod': 'GET',
            'pathParameters': {
                'scriptid': self.package_uuid_1 + 'ZERO_COUNT'
            }
        }

        test_script_base64 = self.zip_and_encode('package_valid')
        self.event_post = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        self.event_post_with_headers = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_script_base64,
                'script_name': 'test_script_uploaded'
            }),
            'headers': 'Something'
        }
        test_script_base64_with_dataurl = 'data:application/zip;base64,' + test_script_base64
        self.event_post_with_dataurl = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_script_base64_with_dataurl,
                'script_name': 'test_script_uploaded'
            })
        }
        test_script_base64_invalid = ','.join(['two', 'commas', 'invalid'])
        self.event_post_invalid_base64_encoded = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_script_base64_invalid,
                'script_name': 'test_script_uploaded'
            })
        }
        test_invalid_zip_script_base64 = self.get_b64_encoded_string(os.path.dirname(os.path.realpath(__file__)) +
                                          '/sample_data/ssm_load_scripts/invalid_zip_file.zip')
        self.event_post_invalid_zip_file = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_invalid_zip_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        test_invalid_yaml_script_base64 = self.zip_and_encode('package_invalid_yaml')
        self.event_post_invalid_yaml = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_invalid_yaml_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        test_no_yaml_script_base64 = self.zip_and_encode('package_no_yaml')
        self.event_post_no_yaml = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_no_yaml_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        test_incorrect_yaml_script_base64 = self.zip_and_encode('package_incorrect_yaml_contents')
        self.event_post_incorrect_yaml = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_incorrect_yaml_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        test_no_master_file_script_base64 = self.zip_and_encode('package_no_master_file')
        self.event_post_no_master_file = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_no_master_file_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        test_valid_with_dependencies_script_base64 = self.zip_and_encode('package_valid_with_dependencies')
        self.event_post_valid_with_dependencies = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_valid_with_dependencies_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        test_package_missing_dependencies_script_base64 = self.zip_and_encode('package_missing_dependencies')
        self.event_post_missing_dependencies = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_package_missing_dependencies_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        self.event_post_empty_script_name = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_script_base64,
                'script_name': ''
            })
        }
        self.event_post_script_name_in_yaml = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_script_base64
            })
        }
        test_package_invalid_attributes_script_base64 = self.zip_and_encode('package_invalid_attributes')
        self.event_post_invalid_attributes = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_package_invalid_attributes_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        self.event_post_name_exists_in_default_scripts = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_script_base64,
                'script_name': 'test'
            })
        }
        self.event_post_make_default = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_script_base64,
                'script_name': 'test_script_uploaded',
                '__make_default': True
            })
        }
        test_package_schema_extensions_script_base64 = self.zip_and_encode('package_schema_extensions')
        self.event_post_schema_extensions = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'script_file': test_package_schema_extensions_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }

        self.event_put_update_package = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'scriptid': self.package_uuid_1
            },
            'body': json.dumps({
                'action': 'update_package',
                'script_file': test_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        self.event_put_invalid_zip_file = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'scriptid': self.package_uuid_1
            },
            'body': json.dumps({
                'action': 'update_package',
                'script_file': test_invalid_zip_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        self.event_put_invalid_yaml = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'scriptid': self.package_uuid_1
            },
            'body': json.dumps({
                'action': 'update_package',
                'script_file': test_invalid_yaml_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        self.event_put_update_default = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'scriptid': self.package_uuid_1
            },
            'body': json.dumps({
                'action': 'update_default',
                'default': 1,
                'script_file': test_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        self.event_put_update_default_item_not_in_db = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'scriptid': self.package_uuid_1 + 'NOT'
            },
            'body': json.dumps({
                'action': 'update_default',
                'default': 1,
                'script_file': test_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }
        self.event_put_action_not_supported = {
            'httpMethod': 'PUT',
            'pathParameters': {
                'scriptid': self.package_uuid_1
            },
            'body': json.dumps({
                'action': 'unknown_action',
                'default': 1,
                'script_file': test_script_base64,
                'script_name': 'test_script_uploaded'
            })
        }

        self.event_delete = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'scriptid': self.package_uuid_1
            }
        }

        self.event_delete_non_existent = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'scriptid': self.package_uuid_1 + '_NOT'
            }
        }

    def zip_and_encode(self, current_zip):
        zip_folder = f'{os.path.dirname(os.path.realpath(__file__))}/sample_data/ssm_load_scripts/{current_zip}/'
        self.create_zip(current_zip, zip_folder)
        zip_file_full_name = f'{zip_folder}{current_zip}.zip'
        return self.get_b64_encoded_string(zip_file_full_name)

    def create_zip(self, current_zip, zip_folder):
        zip_file_name = f'{current_zip}.zip'
        curr_dir = os.getcwd()
        os.chdir(zip_folder)
        if os.path.isfile(zip_file_name):
            os.remove(zip_file_name)
        with zipfile.ZipFile(zip_file_name, 'w') as zipf:
            for file in os.listdir(zip_folder):
                if file != zip_file_name:
                    zipf.write(f'{file}')
        os.chdir(curr_dir)

    def get_b64_encoded_string(self, file_path):
        with open(file_path, 'rb') as f:
            encoded = base64.b64encode(f.read())
        return encoded.decode('ascii')

    def create_bucket(self):
        self.bucket_name = os.getenv('scripts_bucket_name')
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        self.s3_client.put_bucket_versioning(
            Bucket=self.bucket_name,
            VersioningConfiguration={
                'Status': 'Enabled'
            },
        )

    def upload_to_s3_for_get(self):
        s3_key = 'scripts/' + self.package_uuid_1 + '.zip'
        self.s3_client.upload_file(os.path.dirname(os.path.realpath(__file__)) +
                                   '/sample_data/ssm_load_scripts/package_valid/package_valid.zip',
                                   self.bucket_name, s3_key)
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        return response['VersionId']

    def assert_post_success(self, lambda_ssm_scripts, event, assert_history_added=False):
        response = lambda_ssm_scripts.lambda_handler(event, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        package_uuid = self.parse_out_package_uuid(response['body'])
        self.assertTrue(f'package successfully uploaded with uuid: {package_uuid}' in response['body'])

        self.assert_uploaded_to_s3(f'scripts/{package_uuid}.zip')
        self.assert_not_uploaded_to_s3(f'scripts/{self.package_uuid_1}.zip')
        self.assert_saved_in_dynamodb_post(package_uuid)
        if assert_history_added:
            self.assert_history_added_post(package_uuid, 0)

    def assert_uploaded_to_s3(self, s3_key):
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )
        self.assertEqual(200, response['ResponseMetadata']['HTTPStatusCode'])

    def assert_not_uploaded_to_s3(self, s3_key):
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                return
            else:
                raise Exception('Unexpected error')
        raise Exception(f'Unexpected Object found in the bucket {self.bucket_name}')

    def assert_nothing_uploaded_to_s3(self):
        num_objects = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name
        )['KeyCount']
        self.assertEqual(0, num_objects)

    def parse_out_package_uuid(self, response_body):
        # the response_body is in the form of -
        # `test_script_uploaded package successfully uploaded with uuid: 2c311bea-e1e8-48ff-b550-c558d1ec8689`
        # parse the new package_uuid from the response
        # this is brittle, but not changing the response now
        marker_string = 'package successfully uploaded with uuid:'
        return response_body[response_body.find(marker_string) + len(marker_string) + 1:]

    def assert_saved_in_dynamodb_post(self, package_uuid):
        response = self.scripts_table.query(
            KeyConditionExpression=Key('package_uuid').eq(package_uuid)
        )
        items = response['Items']
        item1 = items[0]
        item2 = items[1]

        self.assertEqual(package_uuid, item1['package_uuid'])
        self.assertEqual(0, item1['version'])
        self.assertEqual(1, item1['default'])
        self.assertEqual(1, item1['latest'])
        self.assertEqual(CONST_SCRIPT_FILE_NAME, item1['script_masterfile'])

        self.assertEqual(package_uuid, item2['package_uuid'])
        self.assertEqual(1, item2['version'])
        self.assertEqual(CONST_SCRIPT_FILE_NAME, item2['script_masterfile'])
        self.assertTrue('default' not in item2)
        self.assertTrue('latest' not in item2)

    def assert_saved_in_dynamodb_put(self, package_uuid):
        response = self.scripts_table.query(
            KeyConditionExpression=Key('package_uuid').eq(package_uuid)
        )
        items = response['Items']
        item1 = items[0]
        item2 = items[1]
        item3 = items[2]

        self.assertEqual(package_uuid, item1['package_uuid'])
        self.assertEqual(0, item1['version'])
        self.assertEqual(1, item1['default'])
        self.assertEqual(2, item1['latest'])
        self.assertEqual('test-masterfile.py', item1['script_masterfile'])

        self.assertEqual(package_uuid, item2['package_uuid'])
        self.assertEqual(1, item2['version'])
        self.assertEqual('test-masterfile.py', item2['script_masterfile'])
        self.assertTrue('default' not in item2)
        self.assertTrue('latest' not in item2)

        self.assertEqual(package_uuid, item3['package_uuid'])
        self.assertEqual(2, item3['version'])
        self.assertEqual(CONST_SCRIPT_FILE_NAME, item3['script_masterfile'])
        self.assertTrue('default' not in item3)
        self.assertTrue('latest' not in item3)

        self.assert_history_added_put(package_uuid, 0)

    def assert_saved_in_dynamodb_put_db_not_updated(self, package_uuid):
        response = self.scripts_table.query(
            KeyConditionExpression=Key('package_uuid').eq(package_uuid)
        )
        items = response['Items']
        item1 = items[0]
        item2 = items[1]

        self.assertEqual(package_uuid, item1['package_uuid'])
        self.assertEqual(0, item1['version'])
        self.assertEqual(1, item1['default'])
        self.assertEqual(1, item1['latest'])
        self.assertEqual('test-masterfile.py', item1['script_masterfile'])

        self.assertEqual(package_uuid, item2['package_uuid'])
        self.assertEqual(1, item2['version'])
        self.assertEqual('test-masterfile.py', item2['script_masterfile'])
        self.assertTrue('default' not in item2)
        self.assertTrue('latest' not in item2)

        self.assert_history_added_put(package_uuid, 0)

    def assert_dynamodb_delete(self, package_uuid):
        response = self.scripts_table.query(
            KeyConditionExpression=Key('package_uuid').eq(package_uuid)
        )
        self.assertEqual([], response['Items'])

    def assert_history_added_post(self, package_uuid, version):
        item = self.scripts_table.get_item(
            Key={
                'package_uuid': package_uuid,
                'version': version
            })['Item']
        self.assertEqual(package_uuid, item['package_uuid'])
        self.assertEqual(0, item['version'])
        self.assertEqual(1, item['default'])
        self.assertEqual(CONST_SCRIPT_FILE_NAME, item['script_masterfile'])
        history = item['_history']
        self.assertTrue('lastModifiedTimestamp' in history)
        self.assertTrue('lastModifiedBy' in history)

    def assert_history_added_put(self, package_uuid, version):
        item = self.scripts_table.get_item(
            Key={
                'package_uuid': package_uuid,
                'version': version
            })['Item']
        self.assertEqual(package_uuid, item['package_uuid'])
        self.assertEqual(0, item['version'])
        self.assertEqual(1, item['default'])
        self.assertEqual('test-masterfile.py', item['script_masterfile'])
        history = item['_history']
        self.assertTrue('lastModifiedTimestamp' in history)
        self.assertTrue('lastModifiedBy' in history)

    def assert_post_make_default_side_effects(self):
        bucket_contents = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name
        )['Contents']
        self.assertEqual(1, len(bucket_contents))
        package_uuid = bucket_contents[0]['Key']
        print(package_uuid)
        package_uuid = package_uuid[package_uuid.find('/') + 1:-4]
        self.assert_saved_in_dynamodb_post(package_uuid)

    def assert_post_schema_extensions(self, lambda_ssm_scripts, event):
        response = lambda_ssm_scripts.lambda_handler(event, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(409, response['statusCode'])
        self.assertEqual('Schema extensions failed to be applied, errors are: '
            '["{\\"ResponseMetadata\\": {\\"HTTPStatusCode\\": 500, \\"Message\\": \\"Internal Error\\"}}"]',
                         response['body'])
        # but the package is already uploaded and db updated
        self.assert_post_make_default_side_effects()

    def assert_put_success(self, lambda_ssm_scripts, event):
        response = lambda_ssm_scripts.lambda_handler(event, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        package_uuid = self.package_uuid_1
        self.assertTrue(f'package successfully uploaded with uuid: {package_uuid}' in
                        response['body'])

        self.assert_uploaded_to_s3(f'scripts/{package_uuid}.zip')
        self.assert_saved_in_dynamodb_put(package_uuid)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_get_default_success(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_get_default, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        body = sorted(json.loads(response['body']), key=lambda entry: entry['package_uuid'])
        self.assertEqual(2, len(body))
        self.assertEqual(self.package_uuid_1, body[0]['package_uuid'])
        self.assertEqual(str(self.package_version_1), body[0]['version'])
        self.assertEqual(self.package_uuid_2, body[1]['package_uuid'])
        self.assertEqual(str(self.package_version_2), body[1]['version'])
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_get_default_zero_count_success(self):
        import lambda_ssm_scripts
        # delete all the default entries
        self.scripts_table.delete_item(
            Key={
                'package_uuid': self.package_uuid_1,
                'version': self.package_version_1
            }
        )
        self.scripts_table.delete_item(
            Key={
                'package_uuid': self.package_uuid_2,
                'version': self.package_version_2
            }
        )
        response = lambda_ssm_scripts.lambda_handler(self.event_get_default, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        body = json.loads(response['body'])
        self.assertEqual([], body)
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_get_script_id_not_exist(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_get_script_id_not_exist, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        body = json.loads(response['body'])
        self.assertEqual(200, body['ResponseMetadata']['HTTPStatusCode'])
        self.assertTrue('Item' not in body)
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_get_download_with_version(self):
        import lambda_ssm_scripts
        self.version_id_1 = self.upload_to_s3_for_get()
        # update the item to match the version id of the s3 object uploaded
        self.scripts_table.update_item(
            Key={
                'package_uuid': self.package_uuid_1,
                'version': self.package_version_1
            },
            UpdateExpression='set version_id = :v_id',
            ExpressionAttributeValues={
                ':v_id': self.version_id_1,
            }
        )
        response = lambda_ssm_scripts.lambda_handler(self.event_get_download, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        body = json.loads(response['body'])
        self.assertEqual('test', body['script_name'])
        self.assertEqual(self.package_version_1, body['script_version'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_get_download_no_version(self):
        import lambda_ssm_scripts
        self.version_id_1 = self.upload_to_s3_for_get()
        # update the item by removing the version id attribute
        self.scripts_table.update_item(
            Key={
                'package_uuid': self.package_uuid_1,
                'version': self.package_version_1
            },
            UpdateExpression='remove version_id'
        )
        response = lambda_ssm_scripts.lambda_handler(self.event_get_download, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        body = json.loads(response['body'])
        self.assertEqual('test', body['script_name'])
        self.assertEqual(self.package_version_1, body['script_version'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_get_no_download(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_get_no_download, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        package = json.loads(response['body'])[0]
        self.assertEqual(self.package_uuid_1, package['package_uuid'])
        self.assertEqual(str(self.package_version_1), package['version'])
        self.assertEqual('Argument 1', package['script_arguments'][0]['description'])
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_get_single_version(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_get_single_version, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        package = json.loads(response['body'])[0]
        self.assertEqual(self.package_uuid_2, package['package_uuid'])
        self.assertEqual(str(self.package_version_2), package['version'])
        self.assertEqual('Argument 1 of package 2', package['script_arguments'][0]['description'])
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_get_single_version_zero_count(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_get_single_version_zero_count, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        body = json.loads(response['body'])
        self.assertEqual([], body)
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_get_all_versions(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_get_all_versions, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        body = json.loads(response['body'])
        self.assertEqual(self.package_uuid_1, body[0]['package_uuid'])
        self.assertEqual(str(self.package_version_1), body[0]['version'])
        self.assertEqual('Argument 1', body[0]['script_arguments'][0]['description'])
        self.assertEqual(self.package_uuid_1, body[1]['package_uuid'])
        self.assertEqual(str(self.package_version_1_updated), body[1]['version'])
        self.assertEqual('Argument 1 updated to version 1', body[1]['script_arguments'][0]['description'])
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_get_all_versions_zero_count(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_get_all_versions_zero_count, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        body = json.loads(response['body'])
        self.assertEqual([], body)
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_post_success(self):
        import lambda_ssm_scripts
        self.assert_post_success(lambda_ssm_scripts, self.event_post)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_headers_fail(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_with_headers, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual('Request is not Authenticated', response['body'])
        self.assert_not_uploaded_to_s3(f'scripts/{self.package_uuid_1}.zip')

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_post_with_dataurl(self):
        import lambda_ssm_scripts
        self.assert_post_success(lambda_ssm_scripts, self.event_post_with_dataurl)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_invalid_base64_encoded(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_invalid_base64_encoded, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Zip file is not able to be decoded.', response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    @mock.patch('lambda_ssm_scripts.ZIP_MAX_SIZE', 10)
    def test_lambda_handler_event_post_max_zip_size(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Zip file uncompressed contents exceeds maximum size of 1e-05MBs.', response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_invalid_zip_file(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_invalid_zip_file, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Invalid zip file.', response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_invalid_yaml(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_invalid_yaml, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertTrue(response['body'].startswith('Error reading error YAML Package-Structure.yml'))

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_no_yaml(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_no_yaml, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        print(response['body'])
        self.assertEqual('Package-Structure.yml not found in root of package, this is required.', response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_incorrect_yaml(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_incorrect_yaml, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        print(response['body'])
        self.assertEqual("Missing the following required keys or values in Package-Structure.yml, Attribute 'Name' not "
                         "provided and is required,Attribute 'Description' not provided and is required,Attribute "
                         "'MasterFileName' not provided and is required",
                         response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_no_master_file(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_no_master_file, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        print(response['body'])
        self.assertEqual(f'{CONST_SCRIPT_FILE_NAME} not found in root of package, and is referenced '
                         f'as the MasterFileName.',
                         response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_valid_with_dependencies(self):
        import lambda_ssm_scripts
        self.assert_post_success(lambda_ssm_scripts, self.event_post_valid_with_dependencies)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_missing_dependencies(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_missing_dependencies, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        print(response['body'])
        self.assertEqual("The following dependencies do not exist in the package: lib1.py", response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_empty_script_name(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_empty_script_name, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        print(response['body'])
        self.assertEqual("Script name provided cannot be empty.", response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_script_name_in_yaml(self):
        import lambda_ssm_scripts
        self.assert_post_success(lambda_ssm_scripts, self.event_post_script_name_in_yaml)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_invalid_attributes(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_invalid_attributes, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('{"errors": [[{"attribute 0 errors": ["Attribute key: \'name\' cannot be empty", '
                         '"Attribute \'description\' not provided and is required", '
                         '"Attribute \'type\' not provided and is required"]}, '
                         '{"attribute 1 errors": ["Attribute \'listvalue\' not provided and is required"]}]]}',
                         response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_name_exists_in_default_scripts(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_name_exists_in_default_scripts, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        print(response['body'])
        self.assertEqual('Script name already defined in another package', response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_post_make_default_not_authenticated(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_post_make_default, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual('Request is not Authenticated', response['body'])

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_post_make_default(self):
        import lambda_ssm_scripts
        # the entry with version 0 was already default, the only thing changed was an entry in the history
        self.assert_post_success(lambda_ssm_scripts, self.event_post_make_default, assert_history_added=True)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_event_post_make_default_fail_second_auth(self, mock_get_user_resource_creation_policy):
        import lambda_ssm_scripts
        mock_get_user_resource_creation_policy.side_effect = [
            {'action': 'allow', 'user': 'testuser@example.com'},
            {'action': 'deny', 'user': 'testuser@example.com', 'cause': 'Not authorized'}
            ]
        response = lambda_ssm_scripts.lambda_handler(self.event_post_make_default, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual('Not authorized', response['body'])
        # but the package is already uploaded and db updated
        self.assert_post_make_default_side_effects()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy')
    def test_lambda_handler_event_post_make_default_no_user_second_auth(self, mock_get_user_resource_creation_policy):
        import lambda_ssm_scripts
        mock_get_user_resource_creation_policy.side_effect = [
                {'action': 'allow', 'user': 'testuser@example.com'},
                {'action': 'allow', 'cause': 'Unexpected Error'}
            ]
        response = lambda_ssm_scripts.lambda_handler(self.event_post_make_default, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual('No user details found from auth. Unexpected Error', response['body'])
        # but the package is already uploaded and db updated
        self.assert_post_make_default_side_effects()

    @patch('lambda_ssm_scripts.lambda_client.invoke')
    def test_lambda_handler_event_post_schema_extensions_success(self, mock_aws):
        import lambda_ssm_scripts
        mock_aws.side_effect = mock_aws_invoke_factory()
        self.assert_post_success(lambda_ssm_scripts, self.event_post_schema_extensions)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    @patch('lambda_ssm_scripts.lambda_client.invoke')
    def test_lambda_handler_event_post_schema_extensions_error_1(self, mock_aws):
        import lambda_ssm_scripts
        mock_aws.side_effect = mock_aws_invoke_factory(1)
        self.assert_post_schema_extensions(lambda_ssm_scripts, self.event_post_schema_extensions)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    @patch('lambda_ssm_scripts.lambda_client.invoke')
    def test_lambda_handler_event_post_schema_extensions_error_2(self, mock_aws):
        import lambda_ssm_scripts
        mock_aws.side_effect = mock_aws_invoke_factory(2)
        self.assert_post_schema_extensions(lambda_ssm_scripts, self.event_post_schema_extensions)
        self.assert_not_uploaded_to_s3(f'scripts/{self.package_uuid_1}.zip')

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    @patch('lambda_ssm_scripts.lambda_client.invoke')
    def test_lambda_handler_event_post_schema_extensions_error_3_and_put(self, mock_aws):
        import lambda_ssm_scripts
        mock_aws.side_effect = [mock_aws_invoke_factory(3)(None, None, None),
                                   mock_aws_invoke_factory(0)(None, None, None)]
        self.assert_post_success(lambda_ssm_scripts, self.event_post_schema_extensions)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_put_success(self):
        import lambda_ssm_scripts
        self.assert_put_success(lambda_ssm_scripts, self.event_put_update_package)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_put_not_authorized(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_update_package, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        # self.assertEqual('Request is not Authenticated', response['body'])
        package_uuid = self.package_uuid_1
        self.assert_uploaded_to_s3(f'scripts/{package_uuid}.zip')
        self.assert_saved_in_dynamodb_put(package_uuid)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    @mock.patch('lambda_ssm_scripts.ZIP_MAX_SIZE', 10)
    def test_lambda_handler_event_put_max_zip_size(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_update_package, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Zip file uncompressed contents exceeds maximum size of 1e-05MBs.', response['body'])
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    @mock.patch('lambda_ssm_scripts.ZIP_MAX_SIZE', 10)
    def test_lambda_handler_event_put_invalid_zip_file(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_invalid_zip_file, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Invalid zip file.', response['body'])
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_put_invalid_yaml(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_invalid_yaml, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertTrue(response['body'].startswith('Error reading error YAML Package-Structure.yml'))
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_put_update_default_not_authorized(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_update_default, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual('Request is not Authenticated', response['body'])
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                return_value={'action': 'allow', 'cause': 'No User'})
    def test_lambda_handler_event_put_update_default_no_user(self, _):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_update_default, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual('No user details found from auth. No User', response['body'])
        self.assert_nothing_uploaded_to_s3()

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_put_update_default_success(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_update_default, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual('Default version changed to: 1', response['body'])
        self.assert_nothing_uploaded_to_s3()
        self.assert_saved_in_dynamodb_put_db_not_updated(self.package_uuid_1)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_put_update_default_item_not_in_db(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_update_default_item_not_in_db, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertTrue(response['body'].startswith('The requested version does not exist for the script'))
        self.assert_nothing_uploaded_to_s3()
        self.assert_saved_in_dynamodb_put_db_not_updated(self.package_uuid_1)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_put_action_not_supported(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_put_action_not_supported, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual('Script update action is not supported.', response['body'])
        self.assert_nothing_uploaded_to_s3()
        self.assert_saved_in_dynamodb_put_db_not_updated(self.package_uuid_1)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_default_deny)
    def test_lambda_handler_event_delete_not_authorized(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_delete, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(401, response['statusCode'])
        self.assertEqual('Request is not Authenticated', response['body'])
        self.assert_nothing_uploaded_to_s3()
        self.assert_saved_in_dynamodb_put_db_not_updated(self.package_uuid_1)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_delete_not_success(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_delete, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(200, response['statusCode'])
        self.assertEqual(f'Package {self.package_uuid_1} was successfully deleted', response['body'])
        self.assert_nothing_uploaded_to_s3()
        self.assert_dynamodb_delete(self.package_uuid_1)

    @mock.patch('lambda_ssm_scripts.MFAuth.get_user_resource_creation_policy',
                new=mock_get_user_resource_creation_policy_allow)
    def test_lambda_handler_event_delete_non_existent(self):
        import lambda_ssm_scripts
        response = lambda_ssm_scripts.lambda_handler(self.event_delete_non_existent, None)
        self.assertEqual(lambda_ssm_scripts.default_http_headers, response['headers'])
        self.assertEqual(400, response['statusCode'])
        self.assertEqual(f'Package {self.package_uuid_1}_NOT does not exist', response['body'])
        self.assert_nothing_uploaded_to_s3()
        self.assert_saved_in_dynamodb_put_db_not_updated(self.package_uuid_1)
