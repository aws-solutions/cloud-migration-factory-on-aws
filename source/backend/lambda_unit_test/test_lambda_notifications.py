#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import os
import sys
import unittest
from unittest import mock

import boto3
from moto import mock_dynamodb

import test_common_utils


@mock.patch.dict('os.environ', test_common_utils.default_mock_os_environ)
@mock_dynamodb
class LambdaNotificationsTest(unittest.TestCase):

    @mock.patch.dict('os.environ', test_common_utils.default_mock_os_environ)
    def setUp(self) -> None:
        import lambda_notifications
        super().setUp()
        self.schema_table_name = lambda_notifications.schema_table_name
        self.ddb_client = boto3.client('dynamodb')
        self.event_get = {
            'httpMethod': 'GET'
        }
        self.event_unknown = {
            'httpMethod': 'UNKNOWN'
        }

    def test_lambda_handler_uknown_event(self):
        import lambda_notifications
        response = lambda_notifications.lambda_handler(self.event_unknown, None)
        self.assertEqual(None, response)

    def test_lambda_handler_success(self):
        import lambda_notifications
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name)
        response = lambda_notifications.lambda_handler(self.event_get, None)
        body = json.loads(response['body'])
        expected_body = {'lastChangeDate': '2020-01-01T00:00:00',
                         'notifications': [
                             {'type': 'schema',
                              'versions': [
                                  {'schema': 'server',
                                   'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   },
                                  {'schema': 'app',
                                   'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   },
                                  {'schema': 'wave', 'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   }
                              ]
                              }
                         ]
                         }
        self.assertEqual(expected_body, body)

    def test_lambda_handler_success_modified_TS(self):
        if 'cors' in os.environ:
            del os.environ['cors']
        del sys.modules['lambda_notifications']  # to force lambda_notifications to be re-imported with the above os.environ values
        import lambda_notifications
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name, 'schemas_modified_TS.json')
        response = lambda_notifications.lambda_handler(self.event_get, None)
        body = json.loads(response['body'])
        print(body)
        expected_body = {'lastChangeDate': '2023-04-28T15:27:12.991773',
                         'notifications': [
                             {'type': 'schema',
                              'versions': [
                                  {'schema': 'server',
                                   'lastModifiedTimestamp': '2023-04-28T15:27:12.991773'
                                   },
                                  {'schema': 'app',
                                   'lastModifiedTimestamp': '2023-04-25T18:53:25.915746'
                                   },
                                  {'schema': 'wave',
                                   'lastModifiedTimestamp': '2023-04-28T15:27:12.991773'
                                   }
                              ]
                              }
                         ]
                         }
        self.assertEqual(expected_body, body)

    def test_lambda_handler_success_no_server(self):
        import lambda_notifications
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name, 'schemas_no_server.json')
        response = lambda_notifications.lambda_handler(self.event_get, None)
        body = json.loads(response['body'])
        expected_body = {'lastChangeDate': '2020-01-01T00:00:00',
                         'notifications': [
                             {'type': 'schema',
                              'versions': [
                                  {'schema': 'app',
                                   'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   },
                                  {'schema': 'wave', 'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   }
                              ]
                              }
                         ]
                         }
        self.assertEqual(expected_body, body)

    def test_lambda_handler_success_no_app(self):
        import lambda_notifications
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name, 'schemas_no_app.json')
        response = lambda_notifications.lambda_handler(self.event_get, None)
        body = json.loads(response['body'])
        expected_body = {'lastChangeDate': '2020-01-01T00:00:00',
                         'notifications': [
                             {'type': 'schema',
                              'versions': [
                                  {'schema': 'server',
                                   'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   },
                                  {'schema': 'wave', 'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   }
                              ]
                              }
                         ]
                         }
        self.assertEqual(expected_body, body)

    def test_lambda_handler_success_no_wave(self):
        import lambda_notifications
        test_common_utils.create_and_populate_schemas(self.ddb_client, self.schema_table_name, 'schemas_no_wave.json')
        response = lambda_notifications.lambda_handler(self.event_get, None)
        body = json.loads(response['body'])
        expected_body = {'lastChangeDate': '2020-01-01T00:00:00',
                         'notifications': [
                             {'type': 'schema',
                              'versions': [
                                  {'schema': 'server',
                                   'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   },
                                  {'schema': 'app',
                                   'lastModifiedTimestamp': '2020-01-01T00:00:00'
                                   }
                              ]
                              }
                         ]
                         }
        self.assertEqual(expected_body, body)
