#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import unittest
from unittest import TestCase
from unittest.mock import patch

from models import PipelineTemplate
from test_common_utils import default_mock_os_environ as mock_os_environ
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent


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
        
    def test_drawio_format_valid_list(self, _):
        from lambda_import_export_pipeline_templates import lambda_handler

        # WHEN
        sample_drawio = '''
        <mxfile host="drawio.corp.com">
            <diagram1 name="Empty">
                <mxGraphModel>
                    <root>
                        <mxCell id="0"/>
                        <mxCell id="1" parent="0"/>
                    </root>
                </mxGraphModel>
            </diagram1>
        </mxfile>
        '''

        # THEN
        with patch('lambda_import_export_pipeline_templates.DrawIOParser.parse', return_value=[]) as mock_parse:
            response = lambda_handler({
            'httpMethod': 'POST',
            'body': json.dumps({"fileFormat": "drawio", "content": sample_drawio}),
            'requestContext': {}
            })
            # Verify
            mock_parse.assert_called_once_with(sample_drawio)

    def test_lucid_format_valid_list(self, _):
        from lambda_import_export_pipeline_templates import lambda_handler

        # WHEN
        sample_lucid_csv = '''Id,Name,Shape Library,Page ID,Contained By,Group,Line Source,Line Destination,Source Arrow,Destination Arrow,Status,Text Area 1,Comments,automationid,start,tasktype
                1,Document,,,,,,,,,Draft,Lusid-DTR,,,,
                2,Page,,,,,,,,,,LTR2,,,,
                3,Connector,Flowchart Shapes/Containers,2,,,,,,,,Start step,,,Rehost Servers
               '''

        # THEN
        with patch('lambda_import_export_pipeline_templates.LucidCSVParser.parse', return_value=[]) as mock_parse:
            response = lambda_handler({
            'httpMethod': 'POST',
            'body': json.dumps({"fileFormat": "lucid-csv", "content": sample_lucid_csv}),
            'requestContext': {}
            })
            # Verify
            mock_parse.assert_called_once_with(sample_lucid_csv)
    
    def test_content_passed_through_when_cmf_json(self, _):
        """Test DrawIO format with valid list response"""
        # Setup
        from lambda_import_export_pipeline_templates import lambda_handler
    
        # WHEN
        with patch('lambda_import_export_pipeline_templates.DrawIOParser.parse', return_value=[]) as mock_parse:
            response = lambda_handler({
            'httpMethod': 'POST',
            'body': json.dumps([]),
            'requestContext': {}
            })
            # THEN
            mock_parse.assert_not_called()


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
