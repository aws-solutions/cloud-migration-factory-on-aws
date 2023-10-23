#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import json
import unittest
import uuid
from datetime import datetime
from datetime import timedelta
import boto3
from unittest import mock

from moto import mock_dynamodb

import test_common_utils


@mock.patch.dict('os.environ', test_common_utils.default_mock_os_environ)
@mock_dynamodb
class LambdaSSMJobsTest(unittest.TestCase):

    @mock.patch.dict('os.environ', test_common_utils.default_mock_os_environ)
    def setUp(self) -> None:
        import lambda_ssm_jobs
        self.ddb_client = boto3.client('dynamodb')
        test_common_utils.create_and_populate_ssm_jobs(self.ddb_client, lambda_ssm_jobs.ssm_jobs_table_name)
        self.put_recent_job(1, 5)
        self.put_recent_job(2, 50)

    def put_recent_job(self, job_id, num_hours):
        import lambda_ssm_jobs
        current_time = datetime.utcnow()
        current_time = current_time + timedelta(hours=-num_hours)
        current_time_str = current_time.isoformat(sep='T')
        ssm_uuid = str(uuid.uuid4())
        instance_id = 'i-00000000000000000'
        ssm_id = instance_id + '+' + ssm_uuid + '+' + current_time_str
        item = {
            'SSMId': ssm_id,
            'jobname': 'Test job ' + str(job_id),
            'status': 'RUNNING',
            '_history': {
                'createdTimestamp': current_time_str
            }
        }
        lambda_ssm_jobs.table.put_item(Item=item)

    def test_lambda_handler_get_in_range_success(self):
        import lambda_ssm_jobs
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
                'maximumdays': 30
            }
        }
        response = lambda_ssm_jobs.lambda_handler(event, None)
        jobs = json.loads(response['body'])
        jobs = sorted(jobs, key=lambda item: item['jobname'])
        self.assertEqual(2, len(jobs))
        self.assertEqual('Test job 1', jobs[0]['jobname'])
        self.assertEqual('Test job 2', jobs[1]['jobname'])
        self.assertEqual('RUNNING', jobs[0]['status'])
        self.assertEqual('TIMED-OUT', jobs[1]['status'])

    def test_lambda_handler_get_all_success(self):
        import lambda_ssm_jobs
        event = {
            'httpMethod': 'GET',
            'queryStringParameters': {
            }
        }
        lambda_ssm_jobs.default_maximum_days_logs_returned = None
        response = lambda_ssm_jobs.lambda_handler(event, None)
        jobs = json.loads(response['body'])
        self.assertEqual(4, len(jobs))
        jobs_complete = [job for job in jobs if job['status'] == 'COMPLETE']
        self.assertEqual(2, len(jobs_complete))

    def test_lambda_handler_post_success(self):
        import lambda_ssm_jobs
        event = {
            'payload': {
                'httpMethod': 'POST',
                'body': json.dumps({
                    'SSMId': 'test_id',
                    'jobname': 'Test job 3',
                    'status': 'RUNNING',
                    '_history': {
                        'createdTimestamp': '2023-08-03T14:18:29.742147'
                    }
                })
            }
        }
        response = lambda_ssm_jobs.lambda_handler(event, None)
        expected = {
            'headers': lambda_ssm_jobs.default_http_headers,
            'body': '"SSMId: test_id"',
        }
        self.assertEqual(expected, response)
        response = lambda_ssm_jobs.table.get_item(Key={'SSMId': 'test_id'})
        self.assertTrue('Item' in response)
        self.assertEqual('Test job 3', response['Item']['jobname'])

    def test_lambda_handler_delete_success(self):
        import lambda_ssm_jobs
        ssm_id = 'i-0f8671916d904a820+c1f73bdc-f6ae-4341-9311-c29060c15bf9+2023-04-25T19:10:00.892229'
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'jobid': ssm_id
            }
        }
        response = lambda_ssm_jobs.lambda_handler(event, None)
        expected = {
            'headers': lambda_ssm_jobs.default_http_headers,
            'body': ssm_id + ' deleted',
        }
        self.assertEqual(expected, response)
        response = lambda_ssm_jobs.table.get_item(Key={'SSMId': ssm_id})
        self.assertTrue('Item' not in response)

    def test_lambda_handler_delete_not_existing_success(self):
        import lambda_ssm_jobs
        ssm_id = 'NonExistingID$$$$'
        event = {
            'httpMethod': 'DELETE',
            'pathParameters': {
                'jobid': ssm_id
            }
        }
        response = lambda_ssm_jobs.lambda_handler(event, None)
        expected = {
            'headers': lambda_ssm_jobs.default_http_headers,
            'body': ssm_id + ' deleted',
        }
        self.assertEqual(expected, response)
        response = lambda_ssm_jobs.table.scan(Limit=100)
        self.assertEqual(4, len(response['Items']))

    def test_lambda_handler_unexpected_method(self):
        import lambda_ssm_jobs
        event = {
            'httpMethod': 'UNEXPECTED',
        }
        response = lambda_ssm_jobs.lambda_handler(event, None)
        self.assertEqual(None, response)

