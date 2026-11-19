#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""Unit tests for the in-Lambda admin authorization helpers in cmf_utils.

is_admin_request is a defense-in-depth check that re-verifies admin group
membership inside each admin Lambda, so that an API Gateway authorizer
misconfiguration does not by itself expose admin functionality.

The decision it makes has two edges that must both hold:

  - A request that reached API Gateway without authorizer context must fail
    closed. That is exactly the misconfiguration the check exists to contain
    (a route wired with AuthorizationType: NONE, or an authorizer attaching
    no context), so it must not be allowed through.
  - A direct Lambda-to-Lambda invocation must still be allowed, because
    trusted internal callers depend on it. lambda_ssm_scripts invokes
    lambda_schema with {'httpMethod': 'PUT', ...} and no requestContext.
"""

import logging
import os
from unittest import TestCase, mock

import test_common_utils

loglevel = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger(__name__)

mock_os_environ = {**test_common_utils.default_mock_os_environ}


@mock.patch.dict('os.environ', mock_os_environ)
class IsAdminRequestTest(TestCase):

    def _cognito_event(self, groups):
        """API Gateway event carrying COGNITO_USER_POOLS authorizer claims."""
        return {
            'httpMethod': 'GET',
            'requestContext': {
                'requestId': 'req-1',
                'authorizer': {'claims': {'cognito:groups': groups}},
            },
        }

    def _custom_authorizer_event(self, groups):
        """API Gateway event carrying CUSTOM authorizer context."""
        return {
            'httpMethod': 'GET',
            'requestContext': {
                'requestId': 'req-1',
                'authorizer': {'cognito:groups': groups},
            },
        }

    # --- allowed cases ------------------------------------------------------

    def test_admin_via_custom_authorizer_context(self):
        import cmf_utils
        self.assertTrue(cmf_utils.is_admin_request(
            self._custom_authorizer_event('admin,user')))

    def test_admin_via_cognito_claims(self):
        import cmf_utils
        self.assertTrue(cmf_utils.is_admin_request(
            self._cognito_event('admin,readonly')))

    def test_admin_via_cognito_claims_bracketed_space_separated(self):
        """API Gateway renders a multi-valued COGNITO_USER_POOLS claim as a
        bracketed, space-separated string (e.g. '[admin readonly]'), not a
        comma-separated one. This must still be recognized.
        """
        import cmf_utils
        self.assertTrue(cmf_utils.is_admin_request(
            self._cognito_event('[readonly admin]')))

    def test_admin_via_cognito_claims_bracketed_single_group(self):
        import cmf_utils
        self.assertTrue(cmf_utils.is_admin_request(
            self._cognito_event('[admin]')))

    def test_admin_claims_as_list(self):
        import cmf_utils
        self.assertTrue(cmf_utils.is_admin_request(
            self._cognito_event(['user', 'admin'])))

    def test_internal_lambda_invocation_is_allowed(self):
        """No requestContext: a direct Lambda-to-Lambda call. Must be allowed.

        This is the exact payload lambda_ssm_scripts sends to lambda_schema.
        """
        import cmf_utils
        event = {'httpMethod': 'PUT', 'body': '{}',
                 'pathParameters': {'schema_name': 'server'}}
        self.assertTrue(cmf_utils.is_admin_request(event))

    def test_non_http_invocation_is_allowed(self):
        import cmf_utils
        self.assertTrue(cmf_utils.is_admin_request({}))
        self.assertTrue(cmf_utils.is_admin_request({'payload': {'some': 'data'}}))

    # --- denied cases -------------------------------------------------------

    def test_non_admin_group_is_denied(self):
        import cmf_utils
        self.assertFalse(cmf_utils.is_admin_request(
            self._custom_authorizer_event('user,readonly')))
        self.assertFalse(cmf_utils.is_admin_request(
            self._cognito_event('readonly')))
        self.assertFalse(cmf_utils.is_admin_request(
            self._cognito_event('[readonly user]')))

    def test_empty_groups_are_denied(self):
        import cmf_utils
        self.assertFalse(cmf_utils.is_admin_request(
            self._custom_authorizer_event('')))
        self.assertFalse(cmf_utils.is_admin_request(
            self._cognito_event([])))

    def test_api_gateway_request_without_authorizer_fails_closed(self):
        """The misconfiguration this check exists to contain.

        A route wired with AuthorizationType: NONE still produces a
        requestContext, but no authorizer context. It must be denied rather
        than allowed through as an 'internal' call.
        """
        import cmf_utils
        event = {
            'httpMethod': 'GET',
            'requestContext': {'requestId': 'req-1', 'stage': 'prod'},
        }
        self.assertFalse(cmf_utils.is_admin_request(event))

    def test_authorizer_present_but_empty_fails_closed(self):
        import cmf_utils
        event = {
            'httpMethod': 'GET',
            'requestContext': {'requestId': 'req-1', 'authorizer': {}},
        }
        self.assertFalse(cmf_utils.is_admin_request(event))

    def test_iam_authenticated_api_request_fails_closed(self):
        """An AWS_IAM API Gateway request carries identity but no authorizer.

        No admin route is wired this way today, so failing closed is correct;
        it would otherwise be an unauthenticated-by-group path.
        """
        import cmf_utils
        event = {
            'httpMethod': 'GET',
            'requestContext': {
                'requestId': 'req-1',
                'identity': {'userArn': 'arn:aws:iam::123456789012:user/u'},
            },
        }
        self.assertFalse(cmf_utils.is_admin_request(event))

    def test_admin_substring_does_not_match(self):
        """'administrators' must not satisfy a check for the 'admin' group."""
        import cmf_utils
        self.assertFalse(cmf_utils.is_admin_request(
            self._custom_authorizer_event('administrators,superadmin')))


@mock.patch.dict('os.environ', mock_os_environ)
class AdminForbiddenResponseTest(TestCase):

    def test_returns_403_with_headers_and_error_body(self):
        import json
        import cmf_utils
        response = cmf_utils.create_admin_forbidden_response()
        self.assertEqual(403, response['statusCode'])
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        body = json.loads(response['body'])
        self.assertIn('errors', body)
        self.assertEqual(1, len(body['errors']))
