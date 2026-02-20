#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the lambda layer path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lambda_layers/lambda_layer_items/python'))

# Import the functions to test
from item_custom_assets import fetch_shard_items, query_custom_assets, adapt_item_to_schema, revert_item_from_schema, get_shard_number, MAX_SHARD

class TestItemCustomAssets(unittest.TestCase):
    
    def setUp(self):
        # Mock logger to avoid actual logging during tests
        self.logger_patch = patch('item_custom_assets.logger')
        self.mock_logger = self.logger_patch.start()
        
    def tearDown(self):
        self.logger_patch.stop()
    
    def test_adapt_item_to_schema_custom(self):
        """Test adapt_item_to_schema for custom schema type"""
        item = {
            'asset_type#shard': 'application#1',
            'asset_id': '123',
            'asset_name': 'TestApp',
            'description': 'Test application',
            'status': 'active'
        }
        
        result = adapt_item_to_schema(item, 'application', 'custom')
        
        self.assertEqual(result['application_id'], '123')
        self.assertEqual(result['application_name'], 'TestApp')
        self.assertEqual(result['description'], 'Test application')
        self.assertEqual(result['status'], 'active')
        self.assertNotIn('asset_type#shard', result)
        self.assertNotIn('asset_id', result)
        self.assertNotIn('asset_name', result)
    
    def test_adapt_item_to_schema_non_custom(self):
        """Test adapt_item_to_schema for non-custom schema type"""
        item = {
            'asset_type#shard': 'application#1',
            'asset_id': '123',
            'asset_name': 'TestApp'
        }
        
        result = adapt_item_to_schema(item, 'application', 'standard')
        
        # Should return the item unchanged for non-custom types
        self.assertEqual(result, item)
    
    def test_fetch_shard_items_single_page(self):
        """Test fetch_shard_items with a single page of results"""
        # Create mock data table
        mock_data_table = MagicMock()
        
        # Set up the mock response for a single page query
        mock_data_table.query.return_value = {
            'Items': [
                {'asset_id': '1', 'asset_name': 'Item1'},
                {'asset_id': '2', 'asset_name': 'Item2'}
            ]
            # No LastEvaluatedKey means no more pages
        }
        
        # Call the function
        result = fetch_shard_items(mock_data_table, 'application', 0)
        
        # Verify the query was called with correct parameters
        mock_data_table.query.assert_called_once_with(
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": "asset_type#shard"},
            ExpressionAttributeValues={":pk": "application#0"}
        )
        
        # Verify the result contains the expected items
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['asset_id'], '1')
        self.assertEqual(result[1]['asset_name'], 'Item2')
    
    def test_fetch_shard_items_multiple_pages(self):
        """Test fetch_shard_items with multiple pages of results"""
        # Create mock data table
        mock_data_table = MagicMock()
        
        # Set up the mock responses for paginated queries
        mock_data_table.query.side_effect = [
            {
                'Items': [{'asset_id': '1', 'asset_name': 'Item1'}],
                'LastEvaluatedKey': {'asset_type#shard': 'application#0', 'asset_id': '1'}
            },
            {
                'Items': [{'asset_id': '2', 'asset_name': 'Item2'}]
                # No LastEvaluatedKey means no more pages
            }
        ]
        
        # Call the function
        result = fetch_shard_items(mock_data_table, 'application', 0)
        
        # Verify the query was called twice with correct parameters
        self.assertEqual(mock_data_table.query.call_count, 2)
        
        # First call should not have ExclusiveStartKey
        mock_data_table.query.assert_any_call(
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": "asset_type#shard"},
            ExpressionAttributeValues={":pk": "application#0"}
        )
        
        # Second call should have ExclusiveStartKey
        mock_data_table.query.assert_any_call(
            KeyConditionExpression="#pk = :pk",
            ExpressionAttributeNames={"#pk": "asset_type#shard"},
            ExpressionAttributeValues={":pk": "application#0"},
            ExclusiveStartKey={'asset_type#shard': 'application#0', 'asset_id': '1'}
        )
        
        # Verify the result contains the expected items
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['asset_id'], '1')
        self.assertEqual(result[1]['asset_id'], '2')
    
    @patch('item_custom_assets.fetch_shard_items')
    def test_query_custom_assets(self, mock_fetch_shard_items):
        """Test query_custom_assets function"""
        # Set up mock return values for each shard
        mock_fetch_shard_items.side_effect = [
            [{'asset_id': f'{i}1', 'asset_name': f'Item{i}1'}] for i in range(MAX_SHARD)
        ]
        
        # Create mock data table
        mock_data_table = MagicMock()
        
        # Call the function
        result = query_custom_assets(mock_data_table, 'application')
        
        # Verify fetch_shard_items was called for each shard
        self.assertEqual(mock_fetch_shard_items.call_count, MAX_SHARD)
        
        # Verify the result contains all items from all shards
        self.assertEqual(len(result), MAX_SHARD)
        
        # Check that we have items from each shard
        asset_ids = [item['asset_id'] for item in result]
        for i in range(MAX_SHARD):
            self.assertIn(f'{i}1', asset_ids)
    
    @patch('item_custom_assets.ThreadPoolExecutor')
    def test_query_custom_assets_with_exception(self, mock_executor_class):
        """Test query_custom_assets function when a shard query raises an exception"""
        # Create mock executor and futures
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Create mock futures
        mock_futures = []
        for i in range(MAX_SHARD):
            future = MagicMock()
            if i == 5:  # Make shard 5 raise an exception
                future.result.side_effect = Exception("Test exception")
            else:
                future.result.return_value = [{'asset_id': f'{i}1', 'asset_name': f'Item{i}1'}]
            mock_futures.append(future)
        
        mock_executor.submit.side_effect = mock_futures
        
        # Mock as_completed to return futures in order
        with patch('item_custom_assets.as_completed', return_value=mock_futures):
            # Create mock data table
            mock_data_table = MagicMock()
            
            # Call the function
            result = query_custom_assets(mock_data_table, 'application')
            
            # Verify the result contains items from all successful shards (MAX_SHARD - 1)
            self.assertEqual(len(result), MAX_SHARD - 1)
            
            # Verify the error was logged
            self.mock_logger.error.assert_called_once()
    
    def test_revert_item_from_schema_custom(self):
        """Test revert_item_from_schema for custom schema type"""
        item = {
            'application_id': '123',
            'application_name': 'TestApp',
            'description': 'Test application',
            'status': 'active'
        }
        
        result = revert_item_from_schema(item, 'application', 'custom')
        
        self.assertEqual(result['asset_id'], '123')
        self.assertEqual(result['asset_name'], 'TestApp')
        self.assertEqual(result['description'], 'Test application')
        self.assertEqual(result['status'], 'active')
        self.assertIn('asset_type#shard', result)
        self.assertTrue(result['asset_type#shard'].startswith('application#'))
        self.assertNotIn('application_id', result)
        self.assertNotIn('application_name', result)
    
    def test_revert_item_from_schema_non_custom(self):
        """Test revert_item_from_schema for non-custom schema type"""
        item = {
            'application_id': '123',
            'application_name': 'TestApp'
        }
        
        result = revert_item_from_schema(item, 'application', 'standard')
        
        # Should return the item unchanged for non-custom types
        self.assertEqual(result, item)
    
    def test_get_shard_number(self):
        """Test get_shard_number function"""
        # Test that the same ID always returns the same shard
        shard1 = get_shard_number('test-id-123')
        shard2 = get_shard_number('test-id-123')
        self.assertEqual(shard1, shard2)
        
        # Test that shard number is within valid range
        self.assertGreaterEqual(shard1, 0)
        self.assertLess(shard1, 10)
        
        # Test different IDs can produce different shards
        shard3 = get_shard_number('different-id-456')
        self.assertGreaterEqual(shard3, 0)
        self.assertLess(shard3, 10)

if __name__ == '__main__':
    unittest.main()