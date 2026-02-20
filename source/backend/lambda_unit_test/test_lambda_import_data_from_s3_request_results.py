#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest import mock
from test_common_utils import default_mock_os_environ

@mock.patch.dict('os.environ', default_mock_os_environ)
class S3ImportRequestResultsTest(unittest.TestCase):

    def setUp(self):
        self.sample_json_data = {
            'entities_to_create': [
                {
                    'entityName': 'app',
                    'schema': {
                        'schema_name': 'app',
                        'attributes': [
                            {'name': 'app_name', 'type': 'string'},
                            {'name': 'app_id', 'type': 'string'}
                        ]
                    },
                    'data': {
                        'app1': {'app_name': 'TestApp1', 'app_id': 'app-1'},
                        'app2': {'app_name': 'TestApp2', 'app_id': 'app-2'}
                    }
                }
            ],
            'entities_to_update': [
                {
                    'entityName': 'server',
                    'schema': {
                        'schema_name': 'server',
                        'attributes': [
                            {'name': 'server_name', 'type': 'string'},
                            {'name': 'server_id', 'type': 'string'}
                        ]
                    },
                    'data': {
                        'server1': {'server_name': 'TestServer1', 'server_id': 'server-1'}
                    }
                }
            ],
            'issues': {
                'deduplicationErrors': [],
                'validationErrors': [{'entityName': 'app', 'message': 'test error'}]
            }
        }

    def test_parse_import_request_success(self):
        from request import parse_import_request
        
        result = parse_import_request(self.sample_json_data)
        
        # Test entities_to_create
        self.assertEqual(len(result.entities_to_create), 1)
        create_entity = result.entities_to_create[0]
        self.assertEqual(create_entity.entityName, 'app')
        self.assertEqual(create_entity.schema.schema_name, 'app')
        self.assertEqual(len(create_entity.schema.attributes), 2)
        self.assertEqual(len(create_entity.data), 2)
        self.assertIn('app1', create_entity.data)
        self.assertIn('app2', create_entity.data)
        
        # Test entities_to_update
        self.assertEqual(len(result.entities_to_update), 1)
        update_entity = result.entities_to_update[0]
        self.assertEqual(update_entity.entityName, 'server')
        self.assertEqual(update_entity.schema.schema_name, 'server')
        self.assertEqual(len(update_entity.data), 1)
        self.assertIn('server1', update_entity.data)
        
        # Test validation issues
        self.assertIsNotNone(result.issues)
        self.assertEqual(len(result.issues.validationErrors), 1)
        self.assertEqual(result.issues.validationErrors[0]['entityName'], 'app')

    def test_parse_import_request_empty_data(self):
        from request import parse_import_request
        
        empty_data = {
            'entities_to_create': [],
            'entities_to_update': []
        }
        
        result = parse_import_request(empty_data)
        
        self.assertEqual(len(result.entities_to_create), 0)
        self.assertEqual(len(result.entities_to_update), 0)
        self.assertIsNone(result.issues)

    def test_parse_import_request_missing_keys(self):
        from request import parse_import_request
        
        # Test with missing entities_to_update
        partial_data = {
            'entities_to_create': self.sample_json_data['entities_to_create']
        }
        
        result = parse_import_request(partial_data)
        
        self.assertEqual(len(result.entities_to_create), 1)
        self.assertEqual(len(result.entities_to_update), 0)

    def test_entity_schema_dataclass(self):
        from request import EntitySchema
        
        schema = EntitySchema(
            schema_name='test_schema',
            attributes=[{'name': 'test_attr', 'type': 'string'}]
        )
        
        self.assertEqual(schema.schema_name, 'test_schema')
        self.assertEqual(len(schema.attributes), 1)
        self.assertEqual(schema.attributes[0]['name'], 'test_attr')

    def test_entity_dataclass(self):
        from request import Entity, EntitySchema
        
        schema = EntitySchema(
            schema_name='test_schema',
            attributes=[{'name': 'test_attr', 'type': 'string'}]
        )
        
        entity = Entity(
            entityName='test_entity',
            schema=schema,
            data={'item1': {'test_attr': 'value1'}}
        )
        
        self.assertEqual(entity.entityName, 'test_entity')
        self.assertEqual(entity.schema.schema_name, 'test_schema')
        self.assertEqual(len(entity.data), 1)
        self.assertIn('item1', entity.data)

    def test_import_request_data_dataclass(self):
        from request import ImportRequestData, Entity, EntitySchema, ValidationIssues
        
        schema = EntitySchema(schema_name='test', attributes=[])
        entity = Entity(entityName='test', schema=schema, data={})
        issues = ValidationIssues(deduplicationErrors=[], validationErrors=[])
        
        import_data = ImportRequestData(
            entities_to_create=[entity],
            entities_to_update=[],
            issues=issues
        )
        
        self.assertEqual(len(import_data.entities_to_create), 1)
        self.assertEqual(len(import_data.entities_to_update), 0)
        self.assertIsNotNone(import_data.issues)

    def test_create_processing_results(self):
        from results import create_processing_results
        from request import ImportRequestData, ValidationIssues
        
        # Create mock import data with issues
        issues = ValidationIssues(deduplicationErrors=[], validationErrors=[])
        import_data = ImportRequestData(entities_to_create=[], entities_to_update=[], issues=issues)
        
        results = create_processing_results(
            upload_id='test-upload-123',
            original_file='test-file.json',
            uploaded_by='test-user',
            import_data=import_data
        )
        
        self.assertEqual(results.upload_id, 'test-upload-123')
        self.assertEqual(results.original_file, 'test-file.json')
        self.assertEqual(results.uploaded_by, 'test-user')
        self.assertEqual(results.get_successful_creates_count(), 0)
        self.assertEqual(results.get_successful_updates_count(), 0)
        self.assertIsNotNone(results.validation_issues)



    def test_failure_details_dataclass(self):
        from results import FailureDetails
        
        failure = FailureDetails(
            data={'test_field': 'test_value'},
            error_message='Test error message'
        )
        
        self.assertEqual(failure.data['test_field'], 'test_value')
        self.assertEqual(failure.error_message, 'Test error message')

    def test_processing_results_dataclass(self):
        from results import ProcessingResults, FailureDetails
        from request import ValidationIssues
        
        failure = FailureDetails(data={}, error_message='test error')
        issues = ValidationIssues(deduplicationErrors=[], validationErrors=[])
        
        results = ProcessingResults(
            upload_id='test-upload',
            original_file='test.json',
            uploaded_by='test-user',
            validation_issues=issues
        )
        
        # Test default values
        self.assertEqual(results.upload_id, 'test-upload')
        self.assertEqual(results.original_file, 'test.json')
        self.assertEqual(results.uploaded_by, 'test-user')
        self.assertEqual(len(results.create_failures), 0)
        self.assertEqual(len(results.update_failures), 0)
        self.assertEqual(len(results.created_items), 0)
        self.assertEqual(len(results.updated_items), 0)
        self.assertEqual(results.get_failed_creates_count(), 0)
        self.assertEqual(results.get_failed_updates_count(), 0)
        self.assertFalse(results.has_failures())
        self.assertIsNotNone(results.validation_issues)
        
        # Test adding failures
        results.create_failures['app'] = {'app1': failure}
        results.update_failures['server'] = {'server1': failure}
        
        self.assertIn('app', results.create_failures)
        self.assertIn('server', results.update_failures)
        self.assertEqual(results.create_failures['app']['app1'].error_message, 'test error')
        self.assertEqual(results.get_failed_creates_count(), 1)
        self.assertEqual(results.get_failed_updates_count(), 1)
        self.assertTrue(results.has_failures())
        
        # Test successful items tracking
        results.created_items['app'] = [{'app_id': 'app-id-1', 'app_name': 'App1'}, {'app_id': 'app-id-2', 'app_name': 'App2'}]
        results.updated_items['server'] = [{'server_id': 'server-id-1', 'server_name': 'Server1'}]
        
        self.assertEqual(results.get_successful_creates_count(), 2)
        self.assertEqual(results.get_successful_updates_count(), 1)

    def test_parse_import_request_with_issues(self):
        from request import parse_import_request
        
        result = parse_import_request(self.sample_json_data)
        
        # Test that issues are parsed correctly
        self.assertIsNotNone(result.issues)
        self.assertEqual(len(result.issues.deduplicationErrors), 0)
        self.assertEqual(len(result.issues.validationErrors), 1)
        self.assertEqual(result.issues.validationErrors[0]['entityName'], 'app')

    def test_validation_issues_dataclass(self):
        from request import ValidationIssues
        
        issues = ValidationIssues(
            deduplicationErrors=[{'test': 'error'}],
            validationErrors=[],
            crossReferenceErrors=[{'ref': 'error'}]
        )
        
        self.assertEqual(len(issues.deduplicationErrors), 1)
        self.assertEqual(len(issues.validationErrors), 0)
        self.assertEqual(len(issues.crossReferenceErrors), 1)

if __name__ == '__main__':
    unittest.main()