#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import unittest
from unittest import TestCase
from unittest.mock import patch

from models import PipelineTemplate
from test_common_utils import default_mock_os_environ as mock_os_environ


@patch('cmf_boto.client')
@patch.dict('os.environ', mock_os_environ)
class LambdaImportTemplatesTest(TestCase):

    @unittest.skip("Mocking the lambda call doesnt work when running multiple tests. skipping the test for now")
    def test_post_default_pipelines(self, mock_cmf_boto_client):
        from lambda_import_export_pipeline_templates import lambda_handler

        # GIVEN
        # Lambda items returns new Pipeline Template
        expected_template: PipelineTemplate = {
            "pipeline_template_id": "1",
            "pipeline_template_name": "Migration Hub Import",
            "pipeline_template_description": "foo",
            "_history": {
                "created_by": "foo",
                "created_timestamp": "foo",
                "last_updated_by": "foo",
                "last_updated_timestamp": "foo"
            },
            "pipeline_template_tasks": []
        }
        expected_response = {
            "statusCode": 200,
            "body": json.dumps({"newItems": [expected_template]}),
            'requestContext': {}
        }
        mock_lambda_client = mock_cmf_boto_client.return_value
        mock_lambda_client.invoke.return_value = expected_response

        with open(os.path.dirname(
                os.path.realpath(__file__)) + '/sample_data/' + 'pipeline_templates_import.json') as json_file:
            sample_items = json.load(json_file)

        # WHEN
        response = lambda_handler({
            'httpMethod': 'POST',
            'body': json.dumps(sample_items),
            'requestContext': {}
        })

        # THEN
        self.assertEqual(201, response['statusCode'])

    def test_post_empty_list(self, _):
        from lambda_import_export_pipeline_templates import lambda_handler

        # WHEN
        response = lambda_handler({
            'httpMethod': 'POST',
            'body': json.dumps([]),
            'requestContext': {}
        })

        # THEN
        self.assertEqual(201, response['statusCode'])

    def test_error_on_lambda_invoke(self, mock_cmf_boto_client):
        from lambda_import_export_pipeline_templates import lambda_handler

        # GIVEN
        # Lambda Items returns error
        expected_response = {
            "statusCode": 400,
            "body": json.dumps({"errors": "['foo']"})
        }
        mock_lambda_client = mock_cmf_boto_client.return_value
        mock_lambda_client.invoke.return_value = expected_response

        with open(os.path.dirname(
                os.path.realpath(__file__)) + '/sample_data/' + 'pipeline_templates_import.json') as json_file:
            sample_items = json.load(json_file)

        # WHEN
        response = lambda_handler({
            'httpMethod': 'POST',
            'body': json.dumps(sample_items),
            'requestContext': {}
        })

        # THEN
        self.assertEqual(500, response['statusCode'])
