#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest import mock
from unittest.mock import patch, MagicMock
from test_common_utils import default_mock_os_environ

@mock.patch.dict('os.environ', default_mock_os_environ)
class S3ImportEntityProcessorTest(unittest.TestCase):

    def setUp(self):
        self.sample_entity = MagicMock()
        self.sample_entity.entityName = 'app'
        self.sample_entity.schema = MagicMock()
        self.sample_entity.schema.schema_name = 'app'
        self.sample_entity.schema.attributes = [
            {'name': 'app_name', 'type': 'string'},
            {'name': 'server_ids', 'type': 'multivalue-relationship', 'rel_entity': 'server'}
        ]
        self.sample_entity.data = {
            'app1': {'app_name': 'TestApp1', 'server_ids': ['server1', 'server2']}
        }
        
        self.schema_cache = {
            'app': {
                'schema_name': 'app',
                'attributes': [
                    {'name': 'app_name', 'type': 'string'},
                    {'name': 'server_ids', 'type': 'multivalue-relationship', 'rel_entity': 'server'},
                    {'name': 'wave_id', 'type': 'relationship', 'rel_entity': 'wave'}
                ]
            },
            'server': {
                'schema_name': 'server',
                'attributes': [
                    {'name': 'server_name', 'type': 'string'},
                    {'name': 'app_id', 'type': 'relationship', 'rel_entity': 'app'}
                ]
            }
        }

    @patch('s3_import_entity_processor.ULID')
    def test_process_entities_for_import_success(self, mock_ulid):
        import s3_import_entity_processor
        
        mock_ulid.return_value = 'test-ulid-123'
        mock_results = MagicMock()
        
        result = s3_import_entity_processor.process_entities_for_import(
            [self.sample_entity], [], self.schema_cache, mock_results
        )
        
        self.assertIn('entities_to_create', result)
        self.assertIn('entities_to_update', result)
        self.assertIn('name_to_id_map', result)

    @patch('s3_import_entity_processor.ULID')
    def test_prepare_entities_for_creation(self, mock_ulid):
        import s3_import_entity_processor
        
        mock_ulid.return_value = 'test-ulid-123'
        
        result = s3_import_entity_processor.prepare_entities_for_creation([self.sample_entity], self.schema_cache)
        
        self.assertIn('app', result)
        self.assertEqual(len(result['app']), 1)
        self.assertEqual(result['app'][0]['app_id'], 'test-ulid-123')

    def test_normalize_entity_name(self):
        import s3_import_entity_processor
        
        # Test application -> app conversion
        app_entity = MagicMock()
        app_entity.entityName = 'application'
        result = s3_import_entity_processor.normalize_entity_name(app_entity)
        self.assertEqual(result, 'app')
        
        # Test other entity names remain unchanged
        server_entity = MagicMock()
        server_entity.entityName = 'server'
        result = s3_import_entity_processor.normalize_entity_name(server_entity)
        self.assertEqual(result, 'server')

    def test_get_name_field(self):
        import s3_import_entity_processor
        
        self.assertEqual(s3_import_entity_processor.get_name_field('app'), 'app_name')
        self.assertEqual(s3_import_entity_processor.get_name_field('server'), 'server_name')

    def test_get_id_field(self):
        import s3_import_entity_processor
        
        self.assertEqual(s3_import_entity_processor.get_id_field('app'), 'app_id')
        self.assertEqual(s3_import_entity_processor.get_id_field('server'), 'server_id')

    def test_get_name_field_custom_asset(self):
        import s3_import_entity_processor
        
        custom_schema_cache = {
            'database': {'schema_type': 'custom'},
            'server': {'schema_type': 'user'}
        }
        
        self.assertEqual(s3_import_entity_processor.get_name_field('database', custom_schema_cache), 'database_name')
        self.assertEqual(s3_import_entity_processor.get_name_field('server', custom_schema_cache), 'server_name')

    def test_get_id_field_custom_asset(self):
        import s3_import_entity_processor
        
        custom_schema_cache = {
            'database': {'schema_type': 'custom'},
            'server': {'schema_type': 'user'}
        }
        
        self.assertEqual(s3_import_entity_processor.get_id_field('database', custom_schema_cache), 'database_id')
        self.assertEqual(s3_import_entity_processor.get_id_field('server', custom_schema_cache), 'server_id')

    def test_is_custom_asset_type(self):
        import s3_import_entity_processor
        
        custom_schema_cache = {
            'database': {'schema_type': 'custom'},
            'server': {'schema_type': 'user'},
            'app': {'schema_type': 'user'}
        }
        
        self.assertTrue(s3_import_entity_processor.is_custom_asset_type('database', custom_schema_cache))
        self.assertFalse(s3_import_entity_processor.is_custom_asset_type('server', custom_schema_cache))
        self.assertFalse(s3_import_entity_processor.is_custom_asset_type('app', custom_schema_cache))

    def test_get_cross_reference_attributes(self):
        import s3_import_entity_processor
        
        schema = {
            'attributes': [
                {'name': 'app_name', 'type': 'string'},
                {'name': 'server_ids', 'type': 'multivalue-relationship'},
                {'name': 'wave_id', 'type': 'relationship'}
            ]
        }
        
        result = s3_import_entity_processor.get_cross_reference_attributes(schema)
        
        self.assertIn('server_ids', result)
        self.assertIn('wave_id', result)
        self.assertNotIn('app_name', result)

    def test_move_relationships_to_updates(self):
        import s3_import_entity_processor
        
        processed_creates = {
            'app': [{'app_id': 'test-id', 'app_name': 'TestApp', 'server_ids': ['server1']}]
        }
        processed_updates = {}
        
        s3_import_entity_processor.move_relationships_to_updates(
            processed_creates, processed_updates, self.schema_cache
        )
        
        # Cross-reference should be removed from create and added to update
        self.assertNotIn('server_ids', processed_creates['app'][0])
        self.assertIn('app', processed_updates)
        self.assertIn('server_ids', processed_updates['app'][0])

    def test_resolve_cross_reference_value_list(self):
        import s3_import_entity_processor
        
        name_to_id_map = {
            'server': {'server1': 'id-1', 'server2': 'id-2'}
        }
        
        result = s3_import_entity_processor.resolve_cross_reference_value(
            ['server1', 'server2'], name_to_id_map
        )
        
        self.assertEqual(result, ['id-1', 'id-2'])

    def test_resolve_cross_reference_value_single(self):
        import s3_import_entity_processor
        
        name_to_id_map = {
            'server': {'server1': 'id-1'}
        }
        
        result = s3_import_entity_processor.resolve_cross_reference_value(
            'server1', name_to_id_map
        )
        
        self.assertEqual(result, 'id-1')

    def test_find_id_by_name(self):
        import s3_import_entity_processor
        
        name_to_id_map = {
            'app': {'app1': 'app-id-1'},
            'server': {'server1': 'server-id-1'}
        }
        
        result = s3_import_entity_processor.find_id_by_name('server1', name_to_id_map)
        self.assertEqual(result, 'server-id-1')
        
        result = s3_import_entity_processor.find_id_by_name('nonexistent', name_to_id_map)
        self.assertIsNone(result)

    def test_is_valid_id(self):
        import s3_import_entity_processor
        
        # Valid ULID format (26 characters)
        self.assertTrue(s3_import_entity_processor.is_valid_id('01ARZ3NDEKTSV4RRFFQ69G5FAV'))
        
        # Invalid formats
        self.assertFalse(s3_import_entity_processor.is_valid_id('short'))
        self.assertFalse(s3_import_entity_processor.is_valid_id(123))



    def test_get_cross_reference_attributes_with_targets(self):
        import s3_import_entity_processor
        
        schema = {
            'attributes': [
                {'name': 'server_ids', 'type': 'multivalue-relationship', 'rel_entity': 'server'},
                {'name': 'wave_id', 'type': 'relationship', 'rel_entity': 'wave'},
                {'name': 'app_name', 'type': 'string'}
            ]
        }
        
        result = s3_import_entity_processor.get_cross_reference_attributes_with_targets(schema)
        
        self.assertEqual(result['server_ids'], 'server')
        self.assertEqual(result['wave_id'], 'wave')
        self.assertNotIn('app_name', result)

    def test_move_existing_creates_to_updates(self):
        import s3_import_entity_processor
        
        processed_creates = {
            'app': [{'app_id': 'new-id', 'app_name': 'ExistingApp'}]
        }
        processed_updates = {}
        name_to_id_map = {
            'app': {'ExistingApp': 'existing-id'}
        }
        
        s3_import_entity_processor.move_existing_creates_to_updates(
            processed_creates, processed_updates, name_to_id_map, self.schema_cache
        )
        
        self.assertEqual(len(processed_creates['app']), 0)
        self.assertIn('app', processed_updates)
        self.assertEqual(processed_updates['app'][0]['app_id'], 'existing-id')

    def test_remove_non_existing_updates(self):
        import s3_import_entity_processor
        from results import ProcessingResults
        
        processed_updates = {
            'app': [
                {'app_id': 'id1', 'app_name': 'ExistingApp'},
                {'app_id': 'id2', 'app_name': 'NonExistingApp'}
            ]
        }
        name_to_id_map = {
            'app': {'ExistingApp': 'id1'}
        }
        
        results = ProcessingResults('test-upload', 'test-file', 'test-user')
        s3_import_entity_processor.remove_non_existing_updates(processed_updates, results, name_to_id_map, self.schema_cache)
        
        self.assertEqual(len(processed_updates['app']), 1)
        self.assertEqual(processed_updates['app'][0]['app_name'], 'ExistingApp')
        self.assertIn('app', results.update_failures)
        self.assertIn('NonExistingApp', results.update_failures['app'])

    @patch('s3_import_entity_processor.validate_all_cross_references')
    @patch('s3_import_entity_processor.add_new_creates_to_mapping')
    @patch('s3_import_entity_processor.remove_non_existing_updates')
    @patch('s3_import_entity_processor.move_existing_creates_to_updates')
    def test_validate_and_move_entities(self, mock_move_creates, mock_remove_updates, mock_add_creates, mock_validate_refs):
        import s3_import_entity_processor
        from results import ProcessingResults
        
        processed_creates = {'app': []}
        processed_updates = {'app': []}
        results = ProcessingResults('test-upload', 'test-file', 'test-user')
        name_to_id_map = {'app': {}}
        
        s3_import_entity_processor.validate_and_move_entities(
            processed_creates, processed_updates, results, name_to_id_map, self.schema_cache
        )
        
        mock_move_creates.assert_called_once_with(processed_creates, processed_updates, name_to_id_map, self.schema_cache)
        mock_remove_updates.assert_called_once_with(processed_updates, results, name_to_id_map, self.schema_cache)
        mock_add_creates.assert_called_once_with(processed_creates, name_to_id_map, self.schema_cache)
        mock_validate_refs.assert_called_once_with(processed_creates, processed_updates, name_to_id_map, results, self.schema_cache)

    def test_validate_all_cross_references(self):
        import s3_import_entity_processor
        from results import ProcessingResults
        
        processed_creates = {
            'app': [{'app_id': 'id1', 'app_name': 'TestApp', 'server_ids': ['nonexistent']}]
        }
        processed_updates = {
            'app': [{'app_id': 'id2', 'app_name': 'TestApp2', 'server_ids': ['nonexistent']}]
        }
        name_to_id_map = {'server': {}}
        results = ProcessingResults('test-upload', 'test-file', 'test-user')
        
        s3_import_entity_processor.validate_all_cross_references(
            processed_creates, processed_updates, name_to_id_map, results, self.schema_cache
        )
        
        # Both entities should be removed due to invalid references
        self.assertEqual(len(processed_creates['app']), 0)
        self.assertEqual(len(processed_updates['app']), 0)
        # CREATE failure should be in create_failures, UPDATE failure in update_failures
        self.assertIn('app', results.create_failures)
        self.assertIn('app', results.update_failures)

    def test_can_resolve_cross_reference_list(self):
        import s3_import_entity_processor
        
        name_to_id_map = {
            'server': {'server1': 'id-1'}
        }
        
        # Valid reference
        self.assertTrue(s3_import_entity_processor._can_resolve_cross_reference(['server1'], name_to_id_map))
        
        # Invalid reference
        self.assertFalse(s3_import_entity_processor._can_resolve_cross_reference(['nonexistent'], name_to_id_map))
        
        # Mixed references
        self.assertFalse(s3_import_entity_processor._can_resolve_cross_reference(['server1', 'nonexistent'], name_to_id_map))

    def test_can_resolve_cross_reference_single(self):
        import s3_import_entity_processor
        
        name_to_id_map = {
            'server': {'server1': 'id-1'}
        }
        
        # Valid reference
        self.assertTrue(s3_import_entity_processor._can_resolve_cross_reference('server1', name_to_id_map))
        
        # Invalid reference
        self.assertFalse(s3_import_entity_processor._can_resolve_cross_reference('nonexistent', name_to_id_map))
        
        # Valid ID (ULID format)
        self.assertTrue(s3_import_entity_processor._can_resolve_cross_reference('01ARZ3NDEKTSV4RRFFQ69G5FAV', name_to_id_map))

    def test_resolve_cross_references_to_ids(self):
        import s3_import_entity_processor
        
        processed_updates = {
            'app': [{
                'app_id': 'id1',
                'server_ids': ['server1', 'server2'],
                'wave_id': 'wave1'
            }]
        }
        name_to_id_map = {
            'server': {'server1': 'server-id-1', 'server2': 'server-id-2'},
            'wave': {'wave1': 'wave-id-1'}
        }
        
        s3_import_entity_processor.resolve_cross_references_to_ids(processed_updates, name_to_id_map, self.schema_cache)
        
        self.assertEqual(processed_updates['app'][0]['server_ids'], ['server-id-1', 'server-id-2'])
        self.assertEqual(processed_updates['app'][0]['wave_id'], 'wave-id-1')

    def test_resolve_cross_references_preserves_name_fields(self):
        """Test that name fields are not replaced with IDs during cross-reference resolution."""
        import s3_import_entity_processor
        
        # Schema for resource_group with cross-reference to app
        resource_group_schema = {
            'schema_name': 'resource_group',
            'attributes': [
                {'name': 'resource_group_name', 'type': 'string'},
                {'name': 'app_ids', 'type': 'multivalue-relationship', 'rel_entity': 'app'}
            ]
        }
        
        schema_cache = {
            'resource_group': resource_group_schema,
            'app': self.schema_cache['app']
        }
        
        processed_updates = {
            'resource_group': [{
                'resource_group_id': '01K5WXSRNV2RZ03Z9JG1CCQ50J',
                'resource_group_name': 'Name A',  # This should NOT be replaced
                'app_ids': ['MS_app01']  # This SHOULD be replaced
            }]
        }
        
        name_to_id_map = {
            'resource_group': {'Name A': '01K5WXSRNV2RZ03Z9JG1CCQ50J'},
            'app': {'MS_app01': 'app-id-123'}
        }
        
        s3_import_entity_processor.resolve_cross_references_to_ids(processed_updates, name_to_id_map, schema_cache)
        
        # Verify cross-reference was resolved
        self.assertEqual(processed_updates['resource_group'][0]['app_ids'], ['app-id-123'])
        
        # Verify name field was NOT replaced with ID
        self.assertEqual(processed_updates['resource_group'][0]['resource_group_name'], 'Name A')

if __name__ == '__main__':
    unittest.main()