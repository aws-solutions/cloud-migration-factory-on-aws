#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import botocore
import contextlib, io
from unittest import TestCase, mock
from common.test_mfcommon_util import default_mock_os_environ, logger, mock_file_open


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock.patch('builtins.open', new=mock_file_open)
class CMFGetServersTestCase(TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_handle_client_error(self):
        logger.info("Testing test_cmf_get_servers: "
                    "test_handle_client_error")
        from mfcommon import handle_client_error
        error = botocore.exceptions.ClientError({
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'An error occurred (ResourceNotFoundException) when calling the testing operation'
            }
        }, 'testing')

        message = f"ERROR:  An error occurred (ResourceNotFoundException) when calling the testing operation\n"

        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io):
            handle_client_error(error)
        response = str_io.getvalue()
        print("Response: ", response)
        expected_response = message
        self.assertEqual(response, expected_response)

    def test_handle_client_error_with_colon_in_error(self):
        logger.info("Testing test_cmf_get_servers: "
                    "test_handle_client_error")
        from mfcommon import handle_client_error
        error = botocore.exceptions.ClientError({
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'An error occurred (ResourceNotFoundException) when calling the testing operation:OOPS'
            }
        }, 'testing')

        message = f"ERROR:  An error occurred (ResourceNotFoundException) when calling the testing operationOOPS\n"

        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io):
            handle_client_error(error)
        response = str_io.getvalue()
        print("Response: ", response)
        expected_response = message
        self.assertEqual(response, expected_response)
