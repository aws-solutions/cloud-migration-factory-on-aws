#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import io
import json
from unittest import mock
from unittest.mock import patch
from moto import mock_aws

import test_common_utils
from test_common_utils import default_mock_os_environ as mock_os_environ
from test_lambda_item_common import LambdaItemCommonTest


@mock.patch.dict('os.environ', mock_os_environ)
@mock_aws
class LambdaExportTemplatesTest(LambdaItemCommonTest):
    @mock.patch.dict('os.environ', mock_os_environ)
    def setUp(self) -> None:
        super().setUp()

    def test_invalid_http_method(self):
        from lambda_import_export_pipeline_templates import lambda_handler

        # WHEN
        response = lambda_handler({
            'httpMethod': 'PUT',
        })

        # THEN
        self.assertEqual(405, response['statusCode'])

    @patch('lambda_import_export_pipeline_templates.lambda_client')
    def test_get_empty_list(self, mock_lambda_client):
        from lambda_import_export_pipeline_templates import lambda_handler

        mock_lambda_client.invoke.return_value = {'Payload': io.StringIO('{"body": "[]"}')}

        # GIVEN
        test_common_utils.create_and_populate_pipeline_templates(self.ddb_client, self.pipeline_templates_table_name)
        test_common_utils.create_and_populate_pipeline_template_tasks(self.ddb_client,
                                                                      self.pipeline_template_tasks_table_name)

        # WHEN
        response = lambda_handler({
            'httpMethod': 'GET',
        })

        # THEN
        self.assertEqual(200, response['statusCode'])
        self.assertEqual([], json.loads(response['body']))

    @patch('lambda_import_export_pipeline_templates.lambda_client')
    def test_get_default_pipeline_templates(self, mock_lambda_client):
        from lambda_import_export_pipeline_templates import lambda_handler

        mock_lambda_client.invoke.return_value = {'Payload': io.StringIO('{"body": "[]"}')}
        # GIVEN
        test_common_utils.create_and_populate_pipeline_templates(
            self.ddb_client,
            self.pipeline_templates_table_name,
            'pipeline_templates.json'
        )

        test_common_utils.create_and_populate_pipeline_template_tasks(
            self.ddb_client,
            self.pipeline_template_tasks_table_name,
            'pipeline_template_tasks.json'
        )

        # WHEN
        response = lambda_handler({
            'httpMethod': 'GET',
        })

        # THEN
        self.assertEqual(200, response['statusCode'])
        pipeline_templates = json.loads(response['body'])
        self.assertEqual(2, len(pipeline_templates))

        migration_hub_import_template = next(
            (template for template in pipeline_templates if
             template['pipeline_template_name'] == "Migration Hub Import"),
            None
        )
        self.assertEqual(2, len(migration_hub_import_template['pipeline_template_tasks']))

    @patch('lambda_import_export_pipeline_templates.lambda_client')
    def test_filters_by_pipeline_id(self, mock_lambda_client):
        from lambda_import_export_pipeline_templates import lambda_handler

        mock_lambda_client.invoke.return_value = {'Payload': io.StringIO('{"body": "[]"}')}

        # GIVEN
        test_common_utils.create_and_populate_pipeline_templates(
            self.ddb_client,
            self.pipeline_templates_table_name,
            'pipeline_templates.json'
        )

        test_common_utils.create_and_populate_pipeline_template_tasks(
            self.ddb_client,
            self.pipeline_template_tasks_table_name,
            'pipeline_template_tasks.json'
        )

        # WHEN
        response = lambda_handler({
            'httpMethod': 'GET',
            'multiValueQueryStringParameters': {
                'pipeline_template_id': ['2', '1']
            }
        })

        # THEN
        self.assertEqual(200, response['statusCode'])
        pipeline_templates = json.loads(response['body'])
        self.assertEqual(2, len(pipeline_templates))

        migration_hub_import_template = pipeline_templates[0]

        self.assertEqual("Migration Hub Import", migration_hub_import_template['pipeline_template_name'])
        self.assertEqual(2, len(migration_hub_import_template['pipeline_template_tasks']))
