#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
from test_common_utils import default_mock_os_environ

@mock.patch.dict('os.environ', default_mock_os_environ)
class S3ImportDynamoDBOperationsTest(unittest.TestCase):

    def setUp(self):
        self.upload_id = 'test-upload-123'
        self.mock_table = MagicMock()

    @patch('s3_import_dynamodb_operations.upload_table')
    def test_check_and_update_upload_status_success(self, mock_upload_table):
        import s3_import_dynamodb_operations
        
        mock_upload_table.get_item.return_value = {
            'Item': {
                'upload_id': self.upload_id,
                'status': 'pending',
                'auth_info': {'user': 'test-user'}
            }
        }
        
        result = s3_import_dynamodb_operations.check_and_update_upload_status(
            self.upload_id, 'in-progress'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['upload_id'], self.upload_id)
        mock_upload_table.get_item.assert_called_once()
        mock_upload_table.update_item.assert_called_once()

    @patch('s3_import_dynamodb_operations.upload_table')
    def test_check_and_update_upload_status_already_processed(self, mock_upload_table):
        import s3_import_dynamodb_operations
        
        mock_upload_table.get_item.return_value = {
            'Item': {
                'upload_id': self.upload_id,
                'status': 'complete'
            }
        }
        
        result = s3_import_dynamodb_operations.check_and_update_upload_status(
            self.upload_id, 'in-progress'
        )
        
        self.assertFalse(result)
        mock_upload_table.update_item.assert_not_called()

    @patch('s3_import_dynamodb_operations.upload_table')
    def test_check_and_update_upload_status_not_found(self, mock_upload_table):
        import s3_import_dynamodb_operations
        
        mock_upload_table.get_item.return_value = {}
        
        with self.assertRaises(Exception):
            s3_import_dynamodb_operations.check_and_update_upload_status(
                self.upload_id, 'in-progress'
            )

    @patch('s3_import_dynamodb_operations.dynamodb')
    def test_fetch_all_schemas_success(self, mock_dynamodb):
        import s3_import_dynamodb_operations
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.scan.return_value = {
            'Items': [
                {'schema_name': 'app', 'attributes': []},
                {'schema_name': 'server', 'attributes': []}
            ]
        }
        
        result = s3_import_dynamodb_operations.fetch_all_schemas()
        
        self.assertEqual(len(result), 2)
        self.assertIn('app', result)
        self.assertIn('server', result)

    @patch('s3_import_dynamodb_operations.dynamodb')
    def test_fetch_all_schemas_exception(self, mock_dynamodb):
        import s3_import_dynamodb_operations
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.scan.side_effect = Exception('DynamoDB Error')
        
        result = s3_import_dynamodb_operations.fetch_all_schemas()
        
        self.assertEqual(result, {})

    @patch('s3_import_dynamodb_operations.scan_dynamodb_table')
    @patch('s3_import_dynamodb_operations.dynamodb')
    def test_fetch_all_entities_for_import_success(self, mock_dynamodb, mock_scan):
        import s3_import_dynamodb_operations
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_scan.return_value = [
            {'app_id': 'id-1', 'app_name': 'App1'},
            {'app_id': 'id-2', 'app_name': 'App2'}
        ]
        
        schema_cache = {
            'app': {'attributes': []},
            'server': {'attributes': []}
        }
        
        result = s3_import_dynamodb_operations.fetch_all_entities_for_import(schema_cache)
        
        self.assertEqual(len(result), 2)
        self.assertIn('app', result)
        self.assertIn('server', result)
        self.assertEqual(len(result['app']), 2)
        self.assertEqual(result['app']['App1'], 'id-1')
        self.assertEqual(result['app']['App2'], 'id-2')

    @patch('s3_import_dynamodb_operations.scan_dynamodb_table')
    @patch('s3_import_dynamodb_operations.dynamodb')
    def test_fetch_all_entities_for_import_exception(self, mock_dynamodb, mock_scan):
        import s3_import_dynamodb_operations
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_scan.side_effect = Exception('Scan Error')
        
        schema_cache = {'app': {'attributes': []}}
        
        result = s3_import_dynamodb_operations.fetch_all_entities_for_import(schema_cache)
        
        self.assertEqual(result['app'], {})

    def test_scan_dynamodb_table_success(self):
        import s3_import_dynamodb_operations
        
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [{'app_id': 'id-1', 'app_name': 'App1'}]
        }
        
        result = s3_import_dynamodb_operations.scan_dynamodb_table(mock_table)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['app_id'], 'id-1')

    def test_scan_dynamodb_table_with_pagination(self):
        import s3_import_dynamodb_operations
        
        mock_table = MagicMock()
        mock_table.scan.side_effect = [
            {
                'Items': [{'app_id': 'id-1', 'app_name': 'App1'}],
                'LastEvaluatedKey': {'app_id': 'id-1'}
            },
            {
                'Items': [{'app_id': 'id-2', 'app_name': 'App2'}]
            }
        ]
        
        result = s3_import_dynamodb_operations.scan_dynamodb_table(mock_table)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(mock_table.scan.call_count, 2)

    @patch('s3_import_dynamodb_operations.upload_table')
    def test_update_upload_status_success(self, mock_upload_table):
        import s3_import_dynamodb_operations
        
        mock_upload_table.update_item.return_value = {
            'Attributes': {'upload_id': self.upload_id, 'status': 'complete'}
        }
        
        s3_import_dynamodb_operations.update_upload_status(
            self.upload_id, 'complete', 's3://bucket/results.json'
        )
        
        mock_upload_table.update_item.assert_called_once()

    @patch('s3_import_dynamodb_operations.upload_table')
    def test_update_upload_status_exception(self, mock_upload_table):
        import s3_import_dynamodb_operations
        
        mock_upload_table.update_item.side_effect = Exception('Update Error')
        
        with self.assertRaises(Exception):
            s3_import_dynamodb_operations.update_upload_status(
                self.upload_id, 'complete'
            )

    @patch('s3_import_dynamodb_operations.update_upload_status')
    def test_safe_update_upload_status_to_failed_success(self, mock_update_status):
        import s3_import_dynamodb_operations
        
        s3_import_dynamodb_operations.safe_update_upload_status_to_failed(self.upload_id)
        
        mock_update_status.assert_called_once_with(self.upload_id, 'failed')

    @patch('s3_import_dynamodb_operations.update_upload_status')
    def test_safe_update_upload_status_to_failed_exception(self, mock_update_status):
        import s3_import_dynamodb_operations
        
        mock_update_status.side_effect = Exception('Update Error')
        
        # Should not raise exception
        s3_import_dynamodb_operations.safe_update_upload_status_to_failed(self.upload_id)

    def test_is_custom_asset_schema(self):
        import s3_import_dynamodb_operations
        
        custom_schema = {'schema_type': 'custom', 'schema_name': 'database'}
        standard_schema = {'schema_type': 'user', 'schema_name': 'app'}
        
        self.assertTrue(s3_import_dynamodb_operations.is_custom_asset_schema(custom_schema))
        self.assertFalse(s3_import_dynamodb_operations.is_custom_asset_schema(standard_schema))

    @patch('s3_import_dynamodb_operations.scan_dynamodb_table')
    @patch('s3_import_dynamodb_operations.dynamodb')
    def test_fetch_custom_assets_for_import(self, mock_dynamodb, mock_scan):
        import s3_import_dynamodb_operations
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_scan.return_value = [
            {'asset_type#shard': 'database#0', 'asset_name': 'DB1', 'asset_id': 'db-id-1'},
            {'asset_type#shard': 'database#1', 'asset_name': 'DB2', 'asset_id': 'db-id-2'},
            {'asset_type#shard': 'storage#0', 'asset_name': 'S3-1', 'asset_id': 's3-id-1'}
        ]
        
        schema_cache = {
            'database': {'schema_type': 'custom'},
            'storage': {'schema_type': 'custom'}
        }
        
        result = s3_import_dynamodb_operations.fetch_custom_assets_for_import(schema_cache)
        
        self.assertEqual(len(result), 2)
        self.assertIn('database', result)
        self.assertIn('storage', result)
        self.assertEqual(result['database']['DB1'], 'db-id-1')
        self.assertEqual(result['database']['DB2'], 'db-id-2')
        self.assertEqual(result['storage']['S3-1'], 's3-id-1')

    def test_group_custom_assets_by_type(self):
        import s3_import_dynamodb_operations
        
        custom_assets = [
            {'asset_type#shard': 'database#0', 'asset_name': 'DB1', 'asset_id': 'db-id-1'},
            {'asset_type#shard': 'database#1', 'asset_name': 'DB2', 'asset_id': 'db-id-2'},
            {'asset_type#shard': 'storage#0', 'asset_name': 'S3-1', 'asset_id': 's3-id-1'},
            {'asset_type#shard': 'unknown#0', 'asset_name': 'Unknown', 'asset_id': 'unknown-id'}
        ]
        
        schema_cache = {
            'database': {'schema_type': 'custom'},
            'storage': {'schema_type': 'custom'}
        }
        
        result = s3_import_dynamodb_operations.group_custom_assets_by_type(custom_assets, schema_cache)
        
        self.assertEqual(len(result), 2)
        self.assertIn('database', result)
        self.assertIn('storage', result)
        self.assertNotIn('unknown', result)  # Not in schema_cache
        self.assertEqual(len(result['database']), 2)
        self.assertEqual(len(result['storage']), 1)

    @patch('s3_import_dynamodb_operations.fetch_custom_assets_for_import')
    @patch('s3_import_dynamodb_operations.scan_dynamodb_table')
    @patch('s3_import_dynamodb_operations.dynamodb')
    def test_fetch_all_entities_for_import_with_custom_assets(self, mock_dynamodb, mock_scan, mock_fetch_custom):
        import s3_import_dynamodb_operations
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_scan.return_value = [
            {'app_id': 'app-1', 'app_name': 'App1'}
        ]
        mock_fetch_custom.return_value = {
            'database': {'DB1': 'db-id-1'}
        }
        
        schema_cache = {
            'app': {'schema_type': 'user'},
            'database': {'schema_type': 'custom'}
        }
        
        result = s3_import_dynamodb_operations.fetch_all_entities_for_import(schema_cache)
        
        self.assertEqual(len(result), 2)
        self.assertIn('app', result)
        self.assertIn('database', result)
        self.assertEqual(result['app']['App1'], 'app-1')
        self.assertEqual(result['database']['DB1'], 'db-id-1')
        mock_fetch_custom.assert_called_once_with(schema_cache)

    @patch('s3_import_dynamodb_operations.upload_table')
    @patch('s3_import_dynamodb_operations.datetime')
    def test_update_status_to_in_progress_removes_record_ttl(self, mock_datetime, mock_upload_table):
        """Test that _update_status_to_in_progress removes the record_ttl attribute to prevent deletion."""
        import s3_import_dynamodb_operations
        from datetime import datetime, timezone
        
        # Mock the current timestamp
        mock_timestamp = '2024-01-15T10:30:00+00:00'
        mock_datetime.now.return_value.isoformat.return_value = mock_timestamp
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        
        # Call the private function directly
        s3_import_dynamodb_operations._update_status_to_in_progress(self.upload_id, 'in-progress')
        
        # Verify the update_item was called with the correct parameters
        mock_upload_table.update_item.assert_called_once_with(
            Key={'upload_id': self.upload_id},
            ConditionExpression='attribute_exists(upload_id)',
            UpdateExpression='SET #status = :status, #history.#lastModifiedTimestamp = :lastModifiedTimestamp REMOVE record_ttl',
            ExpressionAttributeNames={
                '#status': 'status',
                '#history': '_history',
                '#lastModifiedTimestamp': 'lastModifiedTimestamp'
            },
            ExpressionAttributeValues={
                ':status': 'in-progress',
                ':lastModifiedTimestamp': mock_timestamp
            }
        )

    @patch('s3_import_dynamodb_operations._update_status_to_in_progress')
    @patch('s3_import_dynamodb_operations._get_upload_record')
    def test_check_and_update_upload_status_calls_update_with_ttl_removal(self, mock_get_record, mock_update_status):
        """Test that check_and_update_upload_status calls _update_status_to_in_progress which removes TTL."""
        import s3_import_dynamodb_operations
        
        # Mock the upload record
        mock_get_record.return_value = {
            'upload_id': self.upload_id,
            'status': 'pending',
            'record_ttl': 1705312200  # Some TTL timestamp
        }
        
        # Call the function
        result = s3_import_dynamodb_operations.check_and_update_upload_status(
            self.upload_id, 'in-progress'
        )
        
        # Verify that _update_status_to_in_progress was called
        mock_update_status.assert_called_once_with(self.upload_id, 'in-progress')
        
        # Verify the result is the upload record
        self.assertEqual(result['upload_id'], self.upload_id)
        self.assertEqual(result['status'], 'pending')

if __name__ == '__main__':
    unittest.main()