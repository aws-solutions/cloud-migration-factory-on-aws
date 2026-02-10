#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest import TestCase, mock

mock_os_environ = {"application": "cmf", "environment": "unittest", "AWS_DEFAULT_REGION": "us-east-1"}

ddb_apps = [
    {"app_id": "1", "app_name": "app1", "wave_ids": ["1"]},
    {"app_id": "2", "app_name": "app2", "wave_ids": ["1", "2"]},
    {"app_id": "3", "app_name": "app3", "wave_ids": ["3"]},
    {"app_id": "4", "app_name": "app4", "wave_ids": ["4"]},
]

ddb_scan_waves_page1 = {
    "Items": [
        {"wave_id": "1", "app_ids": ["1", "2"], "wave_status": "Completed"},
        {"wave_id": "2", "app_ids": ["2"], "wave_status": "In progress"},
    ],
    "LastEvaluatedKey": "LastEvaluatedKey",
}

ddb_scan_waves_page2 = {
    "Items": [
        {"wave_id": "3", "app_ids": ["3"], "wave_status": "Unknown"},
        {"wave_id": "4", "app_ids": ["4"], "wave_status": "Not started"},
    ],
}


def mock_boto(obj, operation_name, kwarg):
    # MGH and ADS integration removed - only DynamoDB operations remain
    if operation_name == "Scan":
        for k in kwarg:
            if isinstance(kwarg[k], str) and "LastEvaluatedKey" in kwarg[k]:
                return ddb_scan_waves_page2
        return ddb_scan_waves_page1
    if operation_name == "BatchGetItem":
        # Filter waves based on requested app_ids
        requested_keys = kwarg.get("RequestItems", {}).get("cmf-unittest-apps", {}).get("Keys", [])
        requested_app_ids = [key["app_id"] for key in requested_keys]
        filtered_apps = [app for app in ddb_apps if app["app_id"] in requested_app_ids]
        return {"Responses": {"cmf-unittest-apps": filtered_apps}}
    return {}


def get_event(wave_status, wave_id):
    # Find app_ids from test data
    all_waves = ddb_scan_waves_page1["Items"] + ddb_scan_waves_page2["Items"]
    wave_data = next((w for w in all_waves if w["wave_id"] == wave_id), {})
    app_ids = wave_data.get("app_ids", [])

    return {
        "Records": [
            {
                "eventID": "1",
                "eventName": "MODIFY",
                "eventVersion": "1.1",
                "eventSource": "aws:dynamodb",
                "awsRegion": "us-west-2",
                "dynamodb": {
                    "ApproximateCreationDateTime": 1706910205.0,
                    "Keys": {"wave_id": {"S": wave_id}},
                    "NewImage": {
                        "wave_id": {"S": wave_id},
                        "app_ids": {"L": [{"S": app_id} for app_id in app_ids]} if app_ids else {},
                        "wave_status": {"S": wave_status},
                    },
                    "OldImage": {
                        "wave_id": {"S": wave_id},
                        "wave_name": {"S": "Test"},
                        "wave_status": {"S": "In progress"},
                    },
                },
            }
        ]
    }


def get_calls_by_operation(mock_client, operation_name):
    return [call for call in mock_client.call_args_list if call[0][0] == operation_name]


@mock.patch.dict("os.environ", mock_os_environ)
class LambdaWaveStreamTest(TestCase):
    @mock.patch("botocore.client.BaseClient._make_api_call")
    def test_lambda_handler_logs_deprecation_message(self, mock_boto_client):
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        lambda_handler(get_event("Completed", "1"), {})

        # Only DynamoDB operations should be called (Scan and BatchGetItem)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "Scan")), 2)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "BatchGetItem")), 1)
        # No deprecated API calls should be made
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "GetHomeRegion")), 0)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "ListConfigurations")), 0)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "NotifyApplicationState")), 0)

    @mock.patch("botocore.client.BaseClient._make_api_call")
    def test_lambda_handler_with_no_new_image_logs_only(self, mock_boto_client):
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        event = get_event("Completed", "1")
        del event["Records"][0]["dynamodb"]["NewImage"]

        lambda_handler(event, {})

        # Should still scan waves for logging (2 scans due to pagination)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "Scan")), 2)
        # No MGH operations should be called
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "NotifyApplicationState")), 0)

    @mock.patch("botocore.client.BaseClient._make_api_call")
    def test_lambda_handler_with_no_wave_status_logs_only(self, mock_boto_client):
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        event = get_event("Completed", "1")
        del event["Records"][0]["dynamodb"]["NewImage"]["wave_status"]

        lambda_handler(event, {})

        # Should still scan waves for logging (2 scans due to pagination)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "Scan")), 2)
        # No MGH operations should be called
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "NotifyApplicationState")), 0)

    @mock.patch("botocore.client.BaseClient._make_api_call")
    def test_lambda_handler_with_unsupported_wave_status_logs_only(self, mock_boto_client):
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        event = get_event("unknown", "3")

        lambda_handler(event, {})

        # Should scan waves and batch get apps for logging (2 scans due to pagination)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "Scan")), 2)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "BatchGetItem")), 1)
        # No MGH operations should be called
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "NotifyApplicationState")), 0)

    @mock.patch("botocore.client.BaseClient._make_api_call")
    def test_lambda_handler_with_same_wave_status_logs_only(self, mock_boto_client):
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        event = get_event("In progress", "1")

        lambda_handler(event, {})

        # Should scan waves for logging (2 scans due to pagination)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "Scan")), 2)
        # No batch get or MGH operations should be called since status unchanged
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "BatchGetItem")), 0)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "NotifyApplicationState")), 0)

    @mock.patch("botocore.client.BaseClient._make_api_call")
    def test_lambda_handler_with_no_app_ids_logs_only(self, mock_boto_client):
        mock_boto_client.side_effect = lambda operation_name, kwargs: mock_boto(self, operation_name, kwargs)
        from lambda_wave_stream import lambda_handler

        event = get_event("Completed", "1")
        del event["Records"][0]["dynamodb"]["NewImage"]["app_ids"]

        lambda_handler(event, {})

        # Should scan waves for logging (2 scans due to pagination)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "Scan")), 2)
        # No batch get or MGH operations should be called
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "BatchGetItem")), 0)
        self.assertEqual(len(get_calls_by_operation(mock_boto_client, "NotifyApplicationState")), 0)

    def test_calculate_mgh_status_with_empty_waves(self):
        from lambda_wave_stream import calculate_mgh_status

        self.assertEqual(calculate_mgh_status([]), None)

    def test_calculate_mgh_status_in_progress(self):
        from lambda_wave_stream import calculate_mgh_status

        self.assertEqual(
            calculate_mgh_status(
                [
                    {"wave_status": "Completed"},
                    {"wave_status": "In progress"},
                    {"wave_status": "Unknown"},
                    {"wave_status": "Not started"},
                ]
            ),
            "IN_PROGRESS",
        )

    def test_calculate_mgh_status_not_started(self):
        from lambda_wave_stream import calculate_mgh_status

        self.assertEqual(
            calculate_mgh_status(
                [
                    {"wave_status": "Not started"},
                    {"wave_status": "Not started"},
                    {"wave_status": "Not started"},
                    {"wave_status": "Not started"},
                ]
            ),
            "NOT_STARTED",
        )

    def test_calculate_mgh_status_completed(self):
        from lambda_wave_stream import calculate_mgh_status

        self.assertEqual(
            calculate_mgh_status(
                [
                    {"wave_status": "Completed"},
                    {"wave_status": "Completed"},
                    {"wave_status": "Completed"},
                    {"wave_status": "Completed"},
                ]
            ),
            "COMPLETED",
        )

    def test_calculate_mgh_status_none(self):
        from lambda_wave_stream import calculate_mgh_status

        self.assertEqual(
            calculate_mgh_status(
                [
                    {"wave_status": "Completed"},
                    {"wave_status": "Unknown"},
                ]
            ),
            None,
        )
