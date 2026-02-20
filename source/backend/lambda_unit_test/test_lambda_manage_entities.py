import unittest
from unittest import mock
import json
import os

import boto3
from moto import mock_aws
from item_custom_assets import get_shard_number

from test_common_utils import default_mock_os_environ

TABLE_NAME_PREFIX = "migration-factory-test-"

mock_os_environ = {
    **default_mock_os_environ,
    "WPM_JOBS_TABLE_NAME": f"{TABLE_NAME_PREFIX}wpm_jobs",
    "MOVE_GROUPS_TABLE_NAME": f"{TABLE_NAME_PREFIX}move_groups",
    "MOVE_GROUP_REQUESTS_TABLE_NAME": f"{TABLE_NAME_PREFIX}move_group_requests",
    "WAVES_TABLE_NAME": f"{TABLE_NAME_PREFIX}waves",
    "APPS_TABLE_NAME": f"{TABLE_NAME_PREFIX}apps",
    "SERVERS_TABLE_NAME": f"{TABLE_NAME_PREFIX}servers",
    "DATABASES_TABLE_NAME": f"{TABLE_NAME_PREFIX}databases",
    "SCHEMA_TABLE_NAME": f"{TABLE_NAME_PREFIX}schema",
    "CUSTOM_ASSETS_TABLE_NAME": f"{TABLE_NAME_PREFIX}custom-assets",
    "AWS_DEFAULT_REGION": "us-east-1",
}

MAX_BATCH_WRITE_OPERATIONS = 25

USE_MOCK_DATABASE = True

if not USE_MOCK_DATABASE:
    del mock_os_environ['AWS_ACCESS_KEY_ID']
    del mock_os_environ['AWS_SECRET_ACCESS_KEY']
    del mock_os_environ['AWS_SESSION_TOKEN']
    del mock_os_environ['AWS_DEFAULT_REGION']
    del mock_os_environ['AWS_SECURITY_TOKEN']

@mock.patch.dict("os.environ", mock_os_environ)
@mock_aws
@mock.patch('policy.MFAuth.get_user_attribute_policy', return_value={'action': 'allow'})
@mock.patch('policy.MFAuth.get_user_resource_creation_policy', return_value={'action': 'allow'})
class TestLambdaManageEntities(unittest.TestCase):
    """Test cases for lambda_manage_entities function"""

    @mock.patch.dict("os.environ", mock_os_environ)
    def setUp(self):
        """Set up test environment"""
        # Create mock DynamoDB tables
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        if USE_MOCK_DATABASE:
            # Create WPM jobs table
            self.dynamodb.create_table(
                TableName=os.getenv("WPM_JOBS_TABLE_NAME"),
                KeySchema=[{"AttributeName": "wpm_job_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "wpm_job_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create waves table
            self.dynamodb.create_table(
                TableName=os.getenv("WAVES_TABLE_NAME"),
                KeySchema=[{"AttributeName": "wave_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "wave_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create move_groups table
            self.dynamodb.create_table(
                TableName=os.getenv("MOVE_GROUPS_TABLE_NAME"),
                KeySchema=[{"AttributeName": "move_group_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "move_group_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create move_groups table
            self.dynamodb.create_table(
                TableName=os.getenv("MOVE_GROUP_REQUESTS_TABLE_NAME"),
                KeySchema=[{"AttributeName": "move_group_request_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "move_group_request_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create apps table
            self.dynamodb.create_table(
                TableName=os.getenv("APPS_TABLE_NAME"),
                KeySchema=[{"AttributeName": "app_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "app_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create servers table
            self.dynamodb.create_table(
                TableName=os.getenv("SERVERS_TABLE_NAME"),
                KeySchema=[{"AttributeName": "server_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "server_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create databases table
            self.dynamodb.create_table(
                TableName=os.getenv("DATABASES_TABLE_NAME"),
                KeySchema=[{"AttributeName": "database_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "database_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create schemas table
            self.dynamodb.create_table(
                TableName=os.getenv("SCHEMA_TABLE_NAME"),
                KeySchema=[{"AttributeName": "schema_name", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "schema_name", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create custom assets table
            self.dynamodb.create_table(
                TableName=os.getenv("CUSTOM_ASSETS_TABLE_NAME"),
                KeySchema=[
                    {"AttributeName": "asset_type#shard", "KeyType": "HASH"},
                    {"AttributeName": "asset_id", "KeyType": "RANGE"}
                ],
                AttributeDefinitions=[
                    {"AttributeName": "asset_type#shard", "AttributeType": "S"},
                    {"AttributeName": "asset_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

        # Populate test data
        self._populate_test_data()

    def _populate_test_data(self):
        """Populate test data in DynamoDB tables"""
        # Add a test wave
        self.waves_table = self.dynamodb.Table(os.getenv("WAVES_TABLE_NAME"))
        self.waves_table.put_item(
            Item={
                "wave_id": "wave-1",
                "wave_name": "Test Wave 1",
                "move_group_ids": ["mg-1", "mg-2"],
                "app_ids": ["app-1", "app-2"],
                "server_ids": ["server-1"],
                "database_ids": ["db-1"],
            }
        )

        # Add a second test wave
        self.waves_table.put_item(
            Item={
                "wave_id": "wave-2",
                "wave_name": "Test Wave 2",
                "move_group_ids": ["mg-3"],
                "app_ids": ["app-3"],
                "database_ids": ["db-3"],
            }
        )

        # Add test move groups
        self.move_groups_table = self.dynamodb.Table(os.getenv("MOVE_GROUPS_TABLE_NAME"))
        self.move_groups_table.put_item(
            Item={
                "move_group_id": "mg-1",
                "move_group_name": "Test Move Group 1",
                "wave_id": "wave-1",
                "app_ids": ["app-1", "app-2"],
                "server_ids": ["server-1"],
                "database_ids": ["db-1"],
                "server_count": 1,  # Integer value
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": "mg-2",
                "move_group_name": "Test Move Group 2",
                "wave_id": "wave-1",
                "app_ids": ["app-2"],
                "server_ids": [],
                "database_ids": [],
                "server_count": 0,  # Integer value
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": "mg-3",
                "move_group_name": "Test Move Group 3",
                "app_ids": ["app-1", "app-3"],
                "server_ids": [],
                "database_ids": ["db-3"],
                "server_count": 0,  # Integer value
            }
        )

        # Add test move groups
        self.move_group_requests_table = self.dynamodb.Table(os.getenv("MOVE_GROUP_REQUESTS_TABLE_NAME"))
        self.move_group_requests_table.put_item(
            Item={
                "move_group_request_id": "mgr-1",
                "move_group_request_name": "Test Move Group 1",
                "wpm_job_id": "job-1",
            }
        )

        # Add a test WPM job
        self.wpm_jobs_table = self.dynamodb.Table(os.getenv("WPM_JOBS_TABLE_NAME"))
        self.wpm_jobs_table.put_item(
            Item={
                "wpm_job_id": "job-1",
                "wpm_job_name": "Test Job 1",
                "wave_ids": ["wave-1"],
                "move_group_ids": ["mg-1", "mg-2"],
            }
        )

        # Get apps table reference
        self.apps_table = self.dynamodb.Table(os.getenv("APPS_TABLE_NAME"))

        # Add test servers with one-to-many relationships
        self.servers_table = self.dynamodb.Table(os.getenv("SERVERS_TABLE_NAME"))
        self.servers_table.put_item(
            Item={
                "server_id": "server-1",
                "server_name": "Test Server 1",
                "move_group_id": "mg-1",
                "wave_id": "wave-1",
                "app_ids": ["app-1"],
            }
        )

        # Add server that references other apps (should remain)
        self.servers_table.put_item(
            Item={
                "server_id": "server-2",
                "server_name": "Test Server 2",
                "app_ids": ["app-1", "app-2"],
            }
        )

        # Add test database with one-to-many relationships
        self.databases_table = self.dynamodb.Table(os.getenv("DATABASES_TABLE_NAME"))
        self.databases_table.put_item(
            Item={
                "database_id": "db-1",
                "database_name": "Test Database 1",
                "move_group_id": "mg-1",
                "wave_id": "wave-1",
                "app_ids": ["app-1"],
            }
        )

        # Add test database that references other apps (should remain)
        self.databases_table.put_item(
            Item={
                "database_id": "db-2",
                "database_name": "Test Database 2",
                "app_ids": ["app-1", "app-2"],
            }
        )

        self.databases_table.put_item(
            Item={
                "database_id": "db-3",
                "database_name": "Test Database 3",
                "app_ids": ["app-1", "app-3"],
                "move_group_id": "mg-3",
                "wave_id": "wave-2",
            }
        )

        # Add storage schema to schema table
        self.schema_table = self.dynamodb.Table(os.getenv("SCHEMA_TABLE_NAME"))
        storage_schema = {
            "schema_name": "storage",
            "attributes": [
                {"name": "storage_id", "type": "string"},
                {"name": "storage_name", "type": "string"},
                {"name": "storage_type", "type": "list"},
                {
                    "name": "app_ids",
                    "rel_entity": "app",
                    "rel_key": "app_id",
                    "type": "multivalue-relationship"
                }
            ],
            "schema_type": "custom"
        }
        self.schema_table.put_item(Item=storage_schema)

        # Add custom storage assets
        self.custom_assets_table = self.dynamodb.Table(os.getenv("CUSTOM_ASSETS_TABLE_NAME"))

        self.custom_assets_table.put_item(
            Item={
                "asset_type#shard": f"storage#{get_shard_number('storage-1')}",
                "asset_id": "storage-1",
                "storage_name": "Test Storage 1",
                "storage_type": "NAS",
                "app_ids": ["app-1"],
            }
        )

        self.custom_assets_table.put_item(
            Item={
                "asset_type#shard": f"storage#{get_shard_number('storage-2')}",
                "asset_id": "storage-2",
                "storage_name": "Test Storage 2",
                "storage_type": "SAN",
                "app_ids": ["app-1", "app-2"],
            }
        )

        # Add test apps with all relationships
        self.apps_table.put_item(
            Item={
                "app_id": "app-1",
                "app_name": "Test App 1",
                "move_group_ids": ["mg-1", "mg-3"],
                "wave_ids": ["wave-1", "wave-3"],
                "server_ids": ["server-1", "server-2"],
                "database_ids": ["db-1", "db-2"],
                "storage_ids": ["storage-1", "storage-2"],
            }
        )

        self.apps_table.put_item(
            Item={
                "app_id": "app-2",
                "app_name": "Test App 2",
                "move_group_ids": ["mg-2"],
                "wave_ids": ["wave-1", "wave-3"],
                "server_ids": ["server-2"],
                "database_ids": ["db-2"],
                "storage_ids": ["storage-2"],
            }
        )

        self.apps_table.put_item(
            Item={
                "app_id": "app-3",
                "app_name": "Test App 3",
                "move_group_ids": ["mg-3"],
                "wave_ids": ["wave-2"],
                "server_ids": [],
                "database_ids": ["db-3"],
            }
        )

        if USE_MOCK_DATABASE:
            # Add schema information
            self.schemas_table = self.dynamodb.Table(os.getenv("SCHEMA_TABLE_NAME"))
            self.schemas_table.put_item(
                Item={
                    "schema_name": "wpm_job",
                    "attributes": [
                        {
                            "name": "wave_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "wave",
                            "rel_key": "wave_id",
                        },
                        {
                            "name": "move_group_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "move_group",
                            "rel_key": "move_group_id",
                        },
                    ],
                }
            )

            self.schemas_table.put_item(
                Item={
                    "schema_name": "move_group",
                    "attributes": [
                        {
                            "name": "wave_id",
                            "type": "relationship",
                            "rel_entity": "wave",
                            "rel_key": "wave_id",
                        },
                        {
                            "name": "app_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "app",
                            "rel_key": "app_id",
                        },
                        {
                            "name": "server_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "server",
                            "rel_key": "server_id",
                        },
                        {
                            "name": "database_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "database",
                            "rel_key": "database_id",
                        },
                        {
                            "name": "wpm_job_id",
                            "type": "relationship",
                            "rel_entity": "wpm_job",
                            "rel_key": "wpm_job_id",
                        },
                    ],
                }
            )

            self.schemas_table.put_item(
                Item={
                    "schema_name": "wave",
                    "attributes": [
                        {
                            "name": "move_group_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "move_group",
                            "rel_key": "move_group_id",
                        },
                        {
                            "name": "app_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "app",
                            "rel_key": "app_id",
                        },
                        {
                            "name": "server_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "server",
                            "rel_key": "server_id",
                        },
                        {
                            "name": "database_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "database",
                            "rel_key": "database_id",
                        },
                        {
                            "name": "wpm_job_id",
                            "type": "relationship",
                            "rel_entity": "wpm_job",
                            "rel_key": "wpm_job_id",
                        },
                    ],
                }
            )

            # Add app schema
            self.schemas_table.put_item(
                Item={
                    "schema_name": "app",
                    "schema_type": "user",
                    "attributes": [
                        {
                            "name": "wave_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "wave",
                            "rel_key": "wave_id",
                        },
                        {
                            "name": "move_group_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "move_group",
                            "rel_key": "move_group_id",
                        },
                        {
                            "name": "server_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "server",
                            "rel_key": "server_id",
                        },
                        {
                            "name": "database_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "database",
                            "rel_key": "database_id",
                        },
                        {
                            "name": "storage_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "storage",
                            "rel_key": "storage_id",
                        },
                    ],
                }
            )

            # Add server schema
            self.schemas_table.put_item(
                Item={
                    "schema_name": "server",
                    "schema_type": "user",
                    "attributes": [
                        {
                            "name": "wave_id",
                            "type": "relationship",
                            "rel_entity": "wave",
                            "rel_key": "wave_id",
                        },
                        {
                            "name": "move_group_id",
                            "type": "relationship",
                            "rel_entity": "move_group",
                            "rel_key": "move_group_id",
                        },
                        {
                            "name": "app_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "app",
                            "rel_key": "app_id",
                        },
                    ],
                }
            )

            # Add database schema
            self.schemas_table.put_item(
                Item={
                    "schema_name": "database",
                    "schema_type": "user",
                    "attributes": [
                        {
                            "name": "wave_id",
                            "type": "relationship",
                            "rel_entity": "wave",
                            "rel_key": "wave_id",
                        },
                        {
                            "name": "move_group_id",
                            "type": "relationship",
                            "rel_entity": "move_group",
                            "rel_key": "move_group_id",
                        },
                        {
                            "name": "app_ids",
                            "type": "multivalue-relationship",
                            "rel_entity": "app",
                            "rel_key": "app_id",
                        },
                    ],
                }
            )

            # Add move_group_request schema
            self.schemas_table.put_item(
                Item={
                    "schema_name": "move_group_request",
                    "schema_type": "user",
                    "attributes": [
                        {
                            "name": "wpm_job_id",
                            "type": "relationship",
                            "rel_entity": "wpm_job",
                            "rel_key": "wpm_job_id",
                        },
                    ],
                }
            )

    def test_cleanup_permission_denied(self, mock_creation_policy, mock_attribute_policy):
        """Test cleanup operation denied by resource creation policy"""
        import lambda_manage_entities
        
        # Temporarily override the class-level mock to return deny
        mock_creation_policy.return_value = {'action': 'deny'}
        
        event = {
            "body": json.dumps({
                "operation": "cleanup",
                "entity_type": "app",
                "entity_ids": ["app-1"]
            })
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 403)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["error"], "Unauthorized")
        self.assertIn("Delete permission required for app", response_body["message"])
        
        # Reset mock to allow for other tests
        mock_creation_policy.return_value = {'action': 'allow'}

    def test_move_permission_denied(self, mock_creation_policy, mock_attribute_policy):
        """Test move operation denied by attribute policy"""
        import lambda_manage_entities
        
        # Temporarily override the class-level mock to return deny
        mock_attribute_policy.return_value = {'action': 'deny'}
        
        event = {
            "body": json.dumps({
                "operation": "move",
                "source_entity_type": "move_group",
                "source_entity_id": "mg-1",
                "destination_entity_type": "move_group", 
                "destination_entity_id": "mg-2",
                "target_entities": [
                    {"entity_type": "server", "entity_id": "server-1"}
                ]
            })
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 403)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["error"], "Unauthorized")
        self.assertIn("Update permission required for server.move_group_id", response_body["message"])
        
        # Reset mock to allow for other tests
        mock_attribute_policy.return_value = {'action': 'allow'}

    def test_cleanup_validation_missing_parameters(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation validation"""
        # Create the event
        event = {
            "body": json.dumps(
                {
                    "operation": "cleanup",
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 400)
        response_body = json.loads(response["body"])
        self.assertIn("Missing required parameter: entity_type", response_body["message"])

    def test_cleanup_validation_too_many_entity_ids(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation validation"""
        # Create the event
        event = {
            "body": json.dumps(
                {
                    "operation": "cleanup",
                    "entity_type": "app",
                    "entity_ids": [f"app_{i}" for i in range(lambda_manage_entities.CLEANUP_MAX_ENTITY_SIZE + 1)],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 400)
        response_body = json.loads(response["body"])
        self.assertIn(f"Too many entity_ids. Maximum allowed is {lambda_manage_entities.CLEANUP_MAX_ENTITY_SIZE}", response_body["message"])

    def test_cleanup_move_group(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for a move group"""
        # Create the event
        event = {
            "body": json.dumps(
                {
                    "operation": "cleanup",
                    "entity_type": "move_group",
                    "entity_ids": ["mg-1"],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify the move group was deleted
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertNotIn("Item", response)

        # Verify references were updated in apps
        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_ids"], ["mg-3"])

        # Verify references were updated in servers
        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])

        # Verify references were updated in databases
        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])

        # Verify references were updated in waves
        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_ids"], ["mg-2"])
        self.assertEqual(response["Item"]["app_ids"], ["app-2"])
        self.assertEqual(response["Item"]["database_ids"], [])
        self.assertEqual(response["Item"]["server_ids"], [])

        # Verify references were updated in WPM jobs
        response = self.wpm_jobs_table.get_item(Key={"wpm_job_id": "job-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_ids"], ["mg-2"])

    def test_cleanup_move_groups(self, mock_creation_policy, mock_attribute_policy):
        """Test cleanup of multiple move groups"""
        wave_id = "mgs-wave-1"
        for i in range(10):
            id = f"mgs-{i}"
            self.apps_table.put_item(
                Item={
                    "app_id": id,
                    "app_name": f"App for multiple groups {i}",
                    "move_group_ids": [id],
                    "wave_ids": [wave_id],
                    "server_ids": [id],
                }
            )
            self.servers_table.put_item(
                Item={
                    "server_id": id,
                    "server_name": f"Server for multiple groups {i}",
                    "move_group_id": id,
                    "wave_id": wave_id,
                    "app_ids": [id],
                }
            )
            self.move_groups_table.put_item(
                Item={
                    "move_group_id": id,
                    "move_group_name": f"Move Group for multiple groups {i}",
                    "wave_id": wave_id,
                    "app_ids": [id],
                    "server_ids": [id],
                }
            )

        all_ids = [f"mgs-{i}" for i in range(10)]
        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Wave for multiple groups 1",
                "move_group_ids": all_ids,
                "app_ids": all_ids,
                "server_ids": all_ids,
                "server_count": len(all_ids),
            }
        )
        
        delete_ids = ["mgs-0", "mgs-1", "mgs-2"]

        import lambda_manage_entities
        event = {
            "body": json.dumps({
                "operation": "cleanup",
                "entity_type": "move_group",
                "entity_ids": delete_ids
            })
        }
        response = lambda_manage_entities.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        
        for delete_id in delete_ids:
            response = self.move_groups_table.get_item(Key={"move_group_id": delete_id})
            self.assertNotIn("Item", response)

        expected_ids = ["mgs-3", "mgs-4", "mgs-5", "mgs-6", "mgs-7", "mgs-8", "mgs-9"]
        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        
        self.assertEqual(response["Item"]["move_group_ids"], expected_ids)
        self.assertEqual(response["Item"]["app_ids"], expected_ids)
        self.assertEqual(response["Item"]["server_ids"], expected_ids)
        self.assertEqual(response["Item"]["server_count"], len(expected_ids))    

    def test_cleanup_wave(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for a wave"""
        # Create the event
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "wave", "entity_ids": ["wave-1"]}
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify the wave was deleted
        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertNotIn("Item", response)

        # Verify all move groups in the wave were deleted
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertNotIn("Item", response)
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-2"})
        self.assertNotIn("Item", response)

        # Verify references were updated in apps
        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["wave_ids"], ["wave-3"])

        # Verify references were updated in servers
        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertIn("Item", response)
        self.assertNotIn("wave_id", response["Item"])

        # Verify references were updated in databases
        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertIn("Item", response)
        self.assertNotIn("wave_id", response["Item"])

        # Verify references were updated in WPM jobs
        response = self.wpm_jobs_table.get_item(Key={"wpm_job_id": "job-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["wave_ids"], [])

    def test_cleanup_wpm_job(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for a WPM job"""
        # Create the event
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "wpm_job", "entity_ids": ["job-1"]}
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify the WPM job was deleted
        response = self.wpm_jobs_table.get_item(Key={"wpm_job_id": "job-1"})
        self.assertNotIn("Item", response)

        # Verify the move group request was deleted
        response = self.move_group_requests_table.get_item(
            Key={"move_group_request_id": "mgr-1"}
        )
        self.assertNotIn("Item", response)

        # Verify all waves in the job were deleted
        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertNotIn("Item", response)

        # Verify all move groups were deleted
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertNotIn("Item", response)
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-2"})
        self.assertNotIn("Item", response)

        # Check specific assets that were in the job's waves/move groups
        # Check app
        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        if "move_group_ids" in response["Item"]:
            self.assertNotIn("mg-1", response["Item"]["move_group_ids"])
            self.assertNotIn("mg-2", response["Item"]["move_group_ids"])
        if "wave_ids" in response["Item"]:
            self.assertNotIn("wave-1", response["Item"]["wave_ids"])

        # Check server
        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])
        self.assertNotIn("wave_id", response["Item"])

        # Check database
        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])
        self.assertNotIn("wave_id", response["Item"])

    def test_move_move_group_between_waves(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test move operation for a move group between waves"""
        # Create the event
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "wave",
                    "source_entity_id": "wave-1",
                    "destination_entity_type": "wave",
                    "destination_entity_id": "wave-2",
                    "target_entities": [
                        {"entity_type": "move_group", "entity_id": "mg-1"}
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify the move group was moved to the new wave
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["wave_id"], "wave-2")
        self.assertEqual(
            response["Item"]["server_count"], 1
        )  # Verify server count is preserved

        # Verify the source wave's references were updated
        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_ids"], ["mg-2"])
        self.assertNotIn("app-1", response["Item"]["app_ids"])
        self.assertNotIn("server-1", response["Item"]["server_ids"])
        self.assertNotIn("db-1", response["Item"]["database_ids"])

        # Verify the destination wave's move_group_ids was updated
        response = self.waves_table.get_item(Key={"wave_id": "wave-2"})
        self.assertIn("Item", response)
        self.assertIn("mg-1", response["Item"]["move_group_ids"])
        self.assertIn("app-1", response["Item"]["app_ids"])
        self.assertIn("server-1", response["Item"]["server_ids"])
        self.assertIn("db-1", response["Item"]["database_ids"])

        # Verify assets' wave references were updated
        # Check apps
        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertIn("wave-2", response["Item"]["wave_ids"])
        self.assertNotIn("wave-1", response["Item"]["wave_ids"])

        # Check servers
        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["wave_id"], "wave-2")

        # Check databases
        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["wave_id"], "wave-2")

    def test_add_group_to_wave_updates_unassigned_entities(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test adding a group to a wave when servers and apps didn't have parent_id or parent_ids before"""
        # Setup: Create a move group with servers and apps that have no wave assignment
        wave_id = "wave-new"
        mg_id = "mg-unassigned-to-wave"
        app_id = "app-unassigned-to-wave"
        server_id = "server-unassigned-to-wave"

        # Create wave (initially empty)
        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "New Wave",
                "move_group_ids": [],
                "app_ids": [],
                "server_ids": [],
            }
        )

        # Create move group with no wave assignment initially
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Unassigned Move Group",
                "app_ids": [app_id],
                "server_ids": [server_id],
                "server_count": 1,
                # Note: no wave_id initially
            }
        )

        # Create app with no wave assignment initially
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Unassigned App",
                "move_group_ids": [mg_id],
                # Note: no wave_ids initially
            }
        )

        # Create server with no wave assignment initially
        self.servers_table.put_item(
            Item={
                "server_id": server_id,
                "server_name": "Unassigned Server",
                "move_group_id": mg_id,
                "app_ids": [app_id],
                # Note: no wave_id initially
            }
        )

        # Add move group to wave (this should update all child entities)
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "wave",
                    "destination_entity_id": wave_id,
                    "target_entities": [
                        {"entity_type": "move_group", "entity_id": mg_id}
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify move group now has wave_id
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id})
        self.assertIn("Item", response)
        mg_item = response["Item"]
        self.assertEqual(mg_item["wave_id"], wave_id)

        # THE KEY TEST: Verify app now has wave_ids (even though it didn't have this field before)
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]
        self.assertIn("wave_ids", app_item, "App should now have wave_ids field")
        self.assertIn(wave_id, app_item["wave_ids"], "App should be assigned to the wave")

        # THE KEY TEST: Verify server now has wave_id (even though it didn't have this field before)
        response = self.servers_table.get_item(Key={"server_id": server_id})
        self.assertIn("Item", response)
        server_item = response["Item"]
        self.assertIn("wave_id", server_item, "Server should now have wave_id field")
        self.assertEqual(server_item["wave_id"], wave_id, "Server should be assigned to the wave")

        # Verify wave now contains the move group, app, and server
        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        wave_item = response["Item"]
        self.assertIn(mg_id, wave_item["move_group_ids"])
        self.assertIn(app_id, wave_item["app_ids"])
        self.assertIn(server_id, wave_item["server_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave_id})


    def test_cleanup_app(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for an app"""
        # Create the event
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "app", "entity_ids": ["app-1"]}
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify the app was deleted
        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertNotIn("Item", response)

        # Verify references were removed from move groups
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertNotIn("app-1", response["Item"].get("app_ids", []))

        # Verify references were removed from waves
        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertNotIn("app-1", response["Item"].get("app_ids", []))

        # Verify servers with only this app reference were deleted
        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertNotIn("Item", response)

        # Verify databases with only this app reference were deleted
        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertNotIn("Item", response)

        # Verify servers with other app references remain
        response = self.servers_table.get_item(Key={"server_id": "server-2"})
        self.assertIn("Item", response)
        self.assertNotIn("app-1", response["Item"].get("app_ids", []))

        # Verify databases with other app references remain
        response = self.databases_table.get_item(Key={"database_id": "db-2"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("app_ids"), ["app-2"])

        # Verify custom asset (storage-1) with only this app reference was deleted
        storage1_response = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-1')}", "asset_id": "storage-1"}
        )
        self.assertNotIn("Item", storage1_response)

        # Verify custom asset (storage-2) with other app references remains but app-1 reference removed
        storage2_response = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-2')}", "asset_id": "storage-2"}
        )
        self.assertIn("Item", storage2_response)
        storage2 = storage2_response["Item"]
        self.assertNotIn("app-1", storage2.get("app_ids", []))
        self.assertIn("app-2", storage2.get("app_ids", []))

    def test_cleanup_apps(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for multiple apps"""
        # Create the event
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "app", "entity_ids": ["app-1", "app-2"]}
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertNotIn("Item", response)
        response = self.apps_table.get_item(Key={"app_id": "app-2"})
        self.assertNotIn("Item", response)
        response = self.apps_table.get_item(Key={"app_id": "app-3"})
        self.assertIn("Item", response)
        self.assertEqual(["db-3"], response["Item"].get("database_ids", []))

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-2"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("app_ids", []))

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-3"})
        self.assertIn("Item", response)
        self.assertEqual(["app-3"], response["Item"].get("app_ids", []))
        self.assertEqual(["db-3"], response["Item"].get("database_ids", []))

        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("app_ids", []))

        response = self.waves_table.get_item(Key={"wave_id": "wave-2"})
        self.assertIn("Item", response)
        self.assertEqual(["app-3"], response["Item"].get("app_ids", []))
        self.assertEqual(["db-3"], response["Item"].get("database_ids", []))

        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertNotIn("Item", response)

        response = self.servers_table.get_item(Key={"server_id": "server-2"})
        self.assertNotIn("Item", response)

        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertNotIn("Item", response)

        response = self.databases_table.get_item(Key={"database_id": "db-2"})
        self.assertNotIn("Item", response)

        response = self.databases_table.get_item(Key={"database_id": "db-3"})
        self.assertIn("Item", response)
        self.assertEqual(["app-3"], response["Item"].get("app_ids", []))
        self.assertEqual("mg-3", response["Item"].get("move_group_id", []))
        self.assertEqual("wave-2", response["Item"].get("wave_id", ""))

        storage1_response = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-1')}", "asset_id": "storage-1"}
        )
        self.assertNotIn("Item", storage1_response)

        storage2_response = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-2')}", "asset_id": "storage-2"}
        )
        self.assertNotIn("Item", storage2_response)

    def test_cleanup_server(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for a server"""
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "server", "entity_ids": ["server-1"]}
            )
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        # Verify server was deleted
        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertNotIn("Item", response)

        # Verify references removed from move group
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertNotIn("server-1", response["Item"].get("server_ids", []))

        # Verify references removed from apps
        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertNotIn("server-1", response["Item"].get("server_ids", []))

        # Verify references removed from waves
        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertNotIn("server-1", response["Item"].get("server_ids", []))


    def test_cleanup_servers(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for multiple servers"""
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "server", "entity_ids": ["server-1", "server-2"]}
            )
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertNotIn("Item", response)

        response = self.servers_table.get_item(Key={"server_id": "server-2"})
        self.assertNotIn("Item", response)

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("server_ids", []))
        self.assertEqual(["app-1", "app-2"], response["Item"].get("app_ids", []))

        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("server_ids", []))

        response = self.apps_table.get_item(Key={"app_id": "app-2"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("server_ids", []))

        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("server_ids", []))
        self.assertEqual(["app-1", "app-2"], response["Item"].get("app_ids", []))

    def test_cleanup_database(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for a database"""
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "database", "entity_ids": ["db-1"]}
            )
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        # Verify database was deleted
        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertNotIn("Item", response)

        # Verify references removed from move group
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertNotIn("db-1", response["Item"].get("database_ids", []))

        # Verify references removed from apps
        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertNotIn("db-1", response["Item"].get("database_ids", []))

        # Verify references removed from waves
        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertNotIn("db-1", response["Item"].get("database_ids", []))

    def test_cleanup_databases(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for multiple databases"""
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "database", "entity_ids": ["db-1", "db-2"]}
            )
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertNotIn("Item", response)

        response = self.databases_table.get_item(Key={"database_id": "db-2"})
        self.assertNotIn("Item", response)

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual(["server-1"], response["Item"].get("server_ids", []))
        self.assertEqual(["app-1", "app-2"], response["Item"].get("app_ids", []))

        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual(["server-1", "server-2"], response["Item"].get("server_ids", []))

        response = self.apps_table.get_item(Key={"app_id": "app-2"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual(["server-2"], response["Item"].get("server_ids", []))

        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual(["server-1"], response["Item"].get("server_ids", []))
        self.assertEqual(["app-1", "app-2"], response["Item"].get("app_ids", []))

    def test_cleanup_all_databases(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup operation for all databases"""
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "database", "entity_ids": ["db-1", "db-2", "db-3"]}
            )
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        response = self.databases_table.get_item(Key={"database_id": "db-1"})
        self.assertNotIn("Item", response)

        response = self.databases_table.get_item(Key={"database_id": "db-2"})
        self.assertNotIn("Item", response)

        response = self.databases_table.get_item(Key={"database_id": "db-3"})
        self.assertNotIn("Item", response)

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual(["server-1"], response["Item"].get("server_ids", []))
        self.assertEqual(["app-1", "app-2"], response["Item"].get("app_ids", []))

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-2"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual([], response["Item"].get("server_ids", []))
        self.assertEqual(["app-2"], response["Item"].get("app_ids", []))

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-3"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual([], response["Item"].get("server_ids", []))
        self.assertEqual([], response["Item"].get("app_ids", []))

        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual(["server-1", "server-2"], response["Item"].get("server_ids", []))

        response = self.apps_table.get_item(Key={"app_id": "app-2"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual(["server-2"], response["Item"].get("server_ids", []))

        response = self.apps_table.get_item(Key={"app_id": "app-3"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual([], response["Item"].get("server_ids", []))

        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual(["server-1"], response["Item"].get("server_ids", []))
        self.assertEqual(["app-1", "app-2"], response["Item"].get("app_ids", []))

        response = self.waves_table.get_item(Key={"wave_id": "wave-2"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("database_ids", []))
        self.assertEqual([], response["Item"].get("server_ids", []))
        self.assertEqual([], response["Item"].get("app_ids", []))

    def test_cleanup_custom_asset(self, mock_creation_policy, mock_attribute_policy):
        """Test cleanup of a custom asset (storage) that removes references and the asset itself"""
        import lambda_manage_entities
        # Create cleanup request for storage-1 (only referenced by app-1)
        event = {
            "body": json.dumps({
                "operation": "cleanup",
                "entity_type": "storage",
                "entity_ids": ["storage-1"]
            })
        }

        response = lambda_manage_entities.lambda_handler(event, None)

        # Verify successful response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertIn("Successfully tracked deletion", response_body["message"])

        # Verify storage asset was deleted from custom_assets table
        item = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-1')}", "asset_id": "storage-1"}
        )
        self.assertNotIn("Item", item)  # Should not exist

        # Verify app-1 no longer references storage-1
        app1 = self.apps_table.get_item(Key={"app_id": "app-1"})["Item"]
        self.assertNotIn("storage-1", app1.get("storage_ids", []))

        # Verify storage-2 still exists (referenced by multiple apps)
        storage2 = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-2')}", "asset_id": "storage-2"}
        )
        self.assertIn("Item", storage2)

        # Verify app-2 still references storage-2
        app2 = self.apps_table.get_item(Key={"app_id": "app-2"})["Item"]
        self.assertIn("storage-2", app2.get("storage_ids", []))

    def test_cleanup_custom_assets(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test cleanup of multiple custom assets (storage) that removes references and the assets themselves"""
        event = {
            "body": json.dumps(
                {"operation": "cleanup", "entity_type": "storage", "entity_ids": ["storage-1", "storage-2"]}
            )
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        response = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-1')}", "asset_id": "storage-1"}
        )
        self.assertNotIn("Item", response)

        response = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-2')}", "asset_id": "storage-2"}
        )
        self.assertNotIn("Item", response)

        response = self.apps_table.get_item(Key={"app_id": "app-1"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("storage_ids", []))

        response = self.apps_table.get_item(Key={"app_id": "app-2"})
        self.assertIn("Item", response)
        self.assertEqual([], response["Item"].get("storage_ids", []))
    
    def test_cleanup_multivalue_relationship(self, mock_creation_policy, mock_attribute_policy):
        """Test cleanup of multiple servers with move groups and wave associated"""
        wave_id = "mvr-wave-1"
        for i in range(10):
            id = f"mvr-{i}"
            self.apps_table.put_item(
                Item={
                    "app_id": id,
                    "app_name": f"App multivalue_relationship {i}",
                    "move_group_ids": [id],
                    "wave_ids": [wave_id],
                    "server_ids": [id],
                }
            )
            self.servers_table.put_item(
                Item={
                    "server_id": id,
                    "server_name": f"Server multivalue_relationship {i}",
                    "move_group_id": id,
                    "wave_id": wave_id,
                    "app_ids": [id],
                }
            )
            self.move_groups_table.put_item(
                Item={
                    "move_group_id": id,
                    "move_group_name": f"Move Group multivalue_relationship {i}",
                    "wave_id": wave_id,
                    "app_ids": [id],
                    "server_ids": [id],
                }
            )

        all_ids = [f"mvr-{i}" for i in range(10)]
        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Wave multivalue_relationship 1",
                "move_group_ids": all_ids,
                "app_ids": all_ids,
                "server_ids": all_ids,
                "server_count": len(all_ids),
            }
        )

        delete_ids = ["mvr-0", "mvr-1", "mvr-2"]
        import lambda_manage_entities
        event = {
            "body": json.dumps({
                "operation": "cleanup",
                "entity_type": "server",
                "entity_ids": delete_ids,
            })
        }
        response = lambda_manage_entities.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)

        for delete_id in delete_ids:
            response = self.servers_table.get_item(Key={"server_id": delete_id})
            self.assertNotIn("Item", response)

        expected_ids = ["mvr-3", "mvr-4", "mvr-5", "mvr-6", "mvr-7", "mvr-8", "mvr-9"]
        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        
        self.assertEqual(response["Item"]["move_group_ids"], all_ids)
        self.assertEqual(response["Item"]["app_ids"], expected_ids)
        self.assertEqual(response["Item"]["server_ids"], expected_ids)
        self.assertEqual(response["Item"]["server_count"], len(expected_ids))    

    def test_remove_server_from_move_group(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test removing a server from a move group when destination_entity_id is not specified"""
        # Create the event to remove server-1 from move_group mg-1
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": "mg-1",
                    "target_entities": [
                        {"entity_type": "server", "entity_id": "server-1"},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify server was removed from the move group
        response = self.servers_table.get_item(Key={"server_id": "server-1"})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])

        # Verify the move group's server_count was updated
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 0)

    def test_move_database_with_different_apps(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving a database with different app list - removed and added apps should get move_group_id and wave_id"""
        # Setup test data
        db_id = "db-different-apps"
        mg_id = "mg-same"
        wave_id = "wave-same"
        old_app_id = "app-removed"
        new_app_id = "app-added"
        common_app_id = "app-common"

        # Create move group and wave
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Same Move Group",
                "wave_id": wave_id,
                "app_ids": [old_app_id, common_app_id],
                "database_ids": [db_id],
                "server_count": 0,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Same Wave",
                "move_group_ids": [mg_id],
                "app_ids": [old_app_id, common_app_id],
                "database_ids": [db_id],
            }
        )

        # Create apps
        self.apps_table.put_item(
            Item={
                "app_id": old_app_id,
                "app_name": "App to be removed",
                "move_group_ids": [mg_id],
                "wave_ids": [wave_id],
                "database_ids": [db_id],
            }
        )

        self.apps_table.put_item(
            Item={
                "app_id": new_app_id,
                "app_name": "App to be added",
                "database_ids": [db_id],
            }
        )

        self.apps_table.put_item(
            Item={
                "app_id": common_app_id,
                "app_name": "Common app",
                "move_group_ids": [mg_id],
                "wave_ids": [wave_id],
                "database_ids": [db_id],
            }
        )

        # Create database with old app list
        self.databases_table.put_item(
            Item={
                "database_id": db_id,
                "database_name": "Database with different apps",
                "move_group_id": mg_id,
                "wave_id": wave_id,
                "app_ids": [old_app_id, common_app_id],
            }
        )

        # Move database with new app list (same move group and wave)
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg_id,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {
                            "entity_type": "database",
                            "entity_id": db_id,
                            "app_ids": [new_app_id, common_app_id]  # Different app list
                        }
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify database app_ids were updated
        response = self.databases_table.get_item(Key={"database_id": db_id})
        self.assertIn("Item", response)
        db_item = response["Item"]
        self.assertEqual(set(db_item["app_ids"]), {new_app_id, common_app_id})

        # Verify removed app (old_app_id) no longer has move_group_id and wave_id
        response = self.apps_table.get_item(Key={"app_id": old_app_id})
        self.assertIn("Item", response)
        old_app_item = response["Item"]
        self.assertNotIn(mg_id, old_app_item.get("move_group_ids", []))
        self.assertNotIn(wave_id, old_app_item.get("wave_ids", []))

        # Verify added app (new_app_id) now has move_group_id and wave_id
        response = self.apps_table.get_item(Key={"app_id": new_app_id})
        self.assertIn("Item", response)
        new_app_item = response["Item"]
        self.assertIn(mg_id, new_app_item.get("move_group_ids", []))
        self.assertIn(wave_id, new_app_item.get("wave_ids", []))

        # Verify common app still has move_group_id and wave_id
        response = self.apps_table.get_item(Key={"app_id": common_app_id})
        self.assertIn("Item", response)
        common_app_item = response["Item"]
        self.assertIn(mg_id, common_app_item.get("move_group_ids", []))
        self.assertIn(wave_id, common_app_item.get("wave_ids", []))

        # Verify wave is updated with correct app references
        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        wave_item = response["Item"]
        self.assertEqual(set(wave_item["app_ids"]), {new_app_id, common_app_id})
        self.assertNotIn(old_app_id, wave_item["app_ids"])

    def test_move_database_from_unassigned_to_move_group(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving a database from unassigned to a move group - apps should get move_group_id and wave_id"""
        # Setup test data
        db_id = "db-unassigned"
        mg_id = "mg-target"
        wave_id = "wave-target"
        app_id = "app-unassigned"

        # Create move group and wave
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Target Move Group",
                "wave_id": wave_id,
                "app_ids": [],
                "database_ids": [],
                "server_count": 0,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Target Wave",
                "move_group_ids": [mg_id],
                "app_ids": [],
                "database_ids": [],
            }
        )

        # Create unassigned app
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Unassigned App",
                "database_ids": [db_id],
            }
        )

        # Create unassigned database
        self.databases_table.put_item(
            Item={
                "database_id": db_id,
                "database_name": "Unassigned Database",
                "app_ids": [app_id],
            }
        )

        # Move database from unassigned to move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "unassigned",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {
                            "entity_type": "database",
                            "entity_id": db_id,
                            "app_ids": [app_id]
                        }
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify database now has move_group_id and wave_id
        response = self.databases_table.get_item(Key={"database_id": db_id})
        self.assertIn("Item", response)
        db_item = response["Item"]
        self.assertEqual(db_item["move_group_id"], mg_id)
        self.assertEqual(db_item["wave_id"], wave_id)

        # Verify app now has move_group_id and wave_id
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]
        self.assertIn(mg_id, app_item.get("move_group_ids", []))
        self.assertIn(wave_id, app_item.get("wave_ids", []))

        # Verify move group is updated with app and database references
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id})
        self.assertIn("Item", response)
        mg_item = response["Item"]
        self.assertIn(app_id, mg_item["app_ids"])
        self.assertIn(db_id, mg_item["database_ids"])

        # Verify wave is updated with app and database references
        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        wave_item = response["Item"]
        self.assertIn(app_id, wave_item["app_ids"])
        self.assertIn(db_id, wave_item["database_ids"])
        self.assertIn(mg_id, wave_item["move_group_ids"])

        # Verify move group app_ids were updated
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id})
        self.assertIn("Item", response)
        mg_item = response["Item"]
        self.assertIn(app_id, mg_item.get("app_ids", []))

        # Clean up test data
        self.databases_table.delete_item(Key={"database_id": db_id})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave_id})

    def test_invalid_operation(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test invalid operation"""
        # Create the event with an invalid operation
        event = {
            "body": json.dumps(
                {
                    "operation": "invalid_operation",
                    "entity_type": "move_group",
                    "entity_id": "mg-1",
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Unsupported operation", json.loads(response["body"])["message"])

    def test_remove_multiple_entities_from_wave(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test removing multiple move groups from a wave when destination_entity_id is not specified"""
        # Create the event to remove move groups mg-1 and mg-2 from wave-1
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "wave",
                    "source_entity_id": "wave-1",
                    "target_entities": [
                        {"entity_type": "move_group", "entity_id": "mg-1"},
                        {"entity_type": "move_group", "entity_id": "mg-2"},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify move groups were removed from the wave
        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-1"})
        self.assertIn("Item", response)
        self.assertNotIn("wave_id", response["Item"])

        response = self.move_groups_table.get_item(Key={"move_group_id": "mg-2"})
        self.assertIn("Item", response)
        self.assertNotIn("wave_id", response["Item"])

        # Verify the source wave's move_group_ids was updated
        response = self.waves_table.get_item(Key={"wave_id": "wave-1"})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_ids"], [])

    def test_entity_not_found(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test entity not found"""
        # Create the event with a non-existent entity
        event = {
            "body": json.dumps(
                {
                    "operation": "cleanup",
                    "entity_type": "move_group",
                    "entity_ids": ["non-existent-id"],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 404)
        self.assertIn("not found", json.loads(response["body"])["message"])

    def test_partial_server_move_app_copy(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test that when only some servers of an app are moved, the app is copied to the destination"""
        # Setup: Create a new app with multiple servers
        app_id = "app-partial-move"
        server_id1 = "server-partial-1"
        server_id2 = "server-partial-2"
        source_mg = "mg-source"
        dest_mg = "mg-dest"

        # Create source and destination move groups
        self.move_groups_table.put_item(
            Item={
                "move_group_id": source_mg,
                "move_group_name": "Source Move Group",
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,  # Integer value
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": dest_mg,
                "move_group_name": "Destination Move Group",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,  # Integer value
            }
        )

        # Create app with two servers
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App for Partial Move Test",
                "move_group_ids": [source_mg],
            }
        )

        # Create two servers for the app
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 for Partial Move",
                "move_group_id": source_mg,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 for Partial Move",
                "move_group_id": source_mg,
                "app_ids": [app_id],
            }
        )

        # Move only one server to the destination move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": source_mg,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": dest_mg,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify server1 was moved to the destination move group
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], dest_mg)

        # Verify server2 remains in the source move group
        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], source_mg)

        # Verify server counts were updated in both move groups
        response = self.move_groups_table.get_item(Key={"move_group_id": source_mg})
        self.assertIn("Item", response)
        self.assertEqual(int(response["Item"]["server_count"]), 1)

        response = self.move_groups_table.get_item(Key={"move_group_id": dest_mg})
        self.assertIn("Item", response)
        self.assertEqual(int(response["Item"]["server_count"]), 1)

        # Verify app was COPIED (not moved) - it should be in both move groups
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertIn(source_mg, response["Item"]["move_group_ids"])
        self.assertIn(dest_mg, response["Item"]["move_group_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": source_mg})
        self.move_groups_table.delete_item(Key={"move_group_id": dest_mg})

    def test_all_servers_move_app_move(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test that when all servers of an app are moved, the app is moved to the destination"""
        # Setup: Create a new app with multiple servers
        app_id = "app-full-move"
        server_id1 = "server-full-1"
        server_id2 = "server-full-2"
        source_mg = "mg-source-full"
        dest_mg = "mg-dest-full"

        # Create source and destination move groups
        self.move_groups_table.put_item(
            Item={
                "move_group_id": source_mg,
                "move_group_name": "Source Move Group Full",
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,  # Integer value
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": dest_mg,
                "move_group_name": "Destination Move Group Full",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,  # Integer value
            }
        )

        # Create app with two servers
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App for Full Move Test",
                "move_group_ids": [source_mg],
            }
        )

        # Create two servers for the app
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 for Full Move",
                "move_group_id": source_mg,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 for Full Move",
                "move_group_id": source_mg,
                "app_ids": [app_id],
            }
        )

        # Move both servers to the destination move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": source_mg,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": dest_mg,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify both servers were moved to the destination move group
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], dest_mg)

        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], dest_mg)

        # Verify app was MOVED (not copied) - it should only be in the destination move group
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertNotIn(source_mg, response["Item"]["move_group_ids"])
        self.assertIn(dest_mg, response["Item"]["move_group_ids"])

        # Verify server counts were updated in both move groups
        response = self.move_groups_table.get_item(Key={"move_group_id": source_mg})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 0)

        response = self.move_groups_table.get_item(Key={"move_group_id": dest_mg})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 2)

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": source_mg})
        self.move_groups_table.delete_item(Key={"move_group_id": dest_mg})

    def test_app_status_partial_to_completed(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app planning_status update from PARTIAL to COMPLETED"""
        # Setup: Create app with some assets grouped, some not
        app_id = "app-partial-to-completed"
        server_id1 = "server-partial-to-completed-1"
        server_id2 = "server-partial-to-completed-2"
        mg_id = "mg-partial-to-completed"

        # Create move group with one server
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Move Group Partial to Completed",
                "app_ids": [app_id],
                "server_ids": [server_id1],
                "server_count": 1,
            }
        )

        # Create app with PARTIAL status
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App Partial to Completed",
                "move_group_ids": [mg_id],
                "server_ids": [server_id1, server_id2],
                "planning_status": "PARTIAL"
            }
        )

        # Create servers - one in move group, one not
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 - In Move Group",
                "move_group_id": mg_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        # Move the second server to the move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to COMPLETED
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "COMPLETED")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})

    def test_app_status_completed_to_partial(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app planning_status update from COMPLETED to PARTIAL"""
        # Setup: Create app with all assets grouped
        app_id = "app-completed-to-partial"
        server_id1 = "server-completed-to-partial-1"
        server_id2 = "server-completed-to-partial-2"
        mg_id = "mg-completed-to-partial"

        # Create move group with both servers
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Move Group Completed to Partial",
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,
            }
        )

        # Create app with COMPLETED status
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App Completed to Partial",
                "move_group_ids": [mg_id],
                "server_ids": [server_id1, server_id2],
                "planning_status": "COMPLETED"
            }
        )

        # Create servers - both in move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 - In Move Group",
                "move_group_id": mg_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 - In Move Group",
                "move_group_id": mg_id,
                "app_ids": [app_id],
            }
        )

        # Remove one server from the move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to PARTIAL
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "PARTIAL")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})

    def test_app_status_not_started_to_partial(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app planning_status update from NOT_STARTED to PARTIAL"""
        # Setup: Create app with no assets grouped
        app_id = "app-not-started-to-partial"
        server_id1 = "server-not-started-to-partial-1"
        server_id2 = "server-not-started-to-partial-2"
        mg_id = "mg-not-started-to-partial"

        # Create empty move group
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Move Group Not Started to Partial",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app with NOT_STARTED status
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App Not Started to Partial",
                "move_group_ids": [],
                "server_ids": [server_id1, server_id2],
                "planning_status": "NOT_STARTED"
            }
        )

        # Create servers - none in move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        # Move one server to the move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to PARTIAL
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "PARTIAL")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})

    def test_app_status_partial_to_not_started(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app planning_status update from PARTIAL to NOT_STARTED"""
        # Setup: Create app with some assets grouped
        app_id = "app-partial-to-not-started"
        server_id1 = "server-partial-to-not-started-1"
        server_id2 = "server-partial-to-not-started-2"
        mg_id = "mg-partial-to-not-started"

        # Create move group with one server
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Move Group Partial to Not Started",
                "app_ids": [app_id],
                "server_ids": [server_id1],
                "server_count": 1,
            }
        )

        # Create app with PARTIAL status
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App Partial to Not Started",
                "move_group_ids": [mg_id],
                "server_ids": [server_id1, server_id2],
                "planning_status": "PARTIAL"
            }
        )

        # Create servers - one in move group, one not
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 - In Move Group",
                "move_group_id": mg_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        # Remove the only server from the move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to NOT_STARTED
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "NOT_STARTED")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})

    def test_app_status_not_started_to_completed(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app planning_status update from NOT_STARTED to COMPLETED"""
        # Setup: Create app with no assets grouped
        app_id = "app-not-started-to-completed"
        server_id1 = "server-not-started-to-completed-1"
        server_id2 = "server-not-started-to-completed-2"
        mg_id = "mg-not-started-to-completed"

        # Create empty move group
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Move Group Not Started to Completed",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app with NOT_STARTED status
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App Not Started to Completed",
                "move_group_ids": [],
                "server_ids": [server_id1, server_id2],
                "planning_status": "NOT_STARTED"
            }
        )

        # Create servers - none in move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        # Move both servers to the move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to COMPLETED
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "COMPLETED")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})

    def test_app_status_completed_to_not_started(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app planning_status update from COMPLETED to NOT_STARTED"""
        # Setup: Create app with all assets grouped
        app_id = "app-completed-to-not-started"
        server_id1 = "server-completed-to-not-started-1"
        server_id2 = "server-completed-to-not-started-2"
        mg_id = "mg-completed-to-not-started"

        # Create move group with both servers
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Move Group Completed to Not Started",
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,
            }
        )

        # Create app with COMPLETED status
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App Completed to Not Started",
                "move_group_ids": [mg_id],
                "server_ids": [server_id1, server_id2],
                "planning_status": "COMPLETED"
            }
        )

        # Create servers - both in move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 - In Move Group",
                "move_group_id": mg_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 - In Move Group",
                "move_group_id": mg_id,
                "app_ids": [app_id],
            }
        )

        # Remove both servers from the move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to NOT_STARTED
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "NOT_STARTED")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})

    def test_app_status_with_database_assets(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app planning_status updates with database assets"""
        # Setup: Create app with server and database
        app_id = "app-status-with-db"
        server_id = "server-status-with-db"
        db_id = "db-status-with-db"
        mg_id = "mg-status-with-db"

        # Create empty move group
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Move Group Status With DB",
                "app_ids": [],
                "server_ids": [],
                "database_ids": [],
                "server_count": 0,
            }
        )

        # Create app with NOT_STARTED status
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App Status With DB",
                "move_group_ids": [],
                "server_ids": [server_id],
                "database_ids": [db_id],
                "planning_status": "NOT_STARTED"
            }
        )

        # Create server - not in move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id,
                "server_name": "Server - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        # Create database - not in move group
        self.databases_table.put_item(
            Item={
                "database_id": db_id,
                "database_name": "Database - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        # Move only the database to the move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "database", "entity_id": db_id},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to PARTIAL
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "PARTIAL")

        # Now move the server to the move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to COMPLETED
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "COMPLETED")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id})
        self.databases_table.delete_item(Key={"database_id": db_id})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})

    def test_app_status_with_multiple_move_groups(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app planning_status with assets spread across multiple move groups"""
        # Setup: Create app with servers in different move groups
        app_id = "app-status-multi-mg"
        server_id1 = "server-status-multi-mg-1"
        server_id2 = "server-status-multi-mg-2"
        mg_id1 = "mg-status-multi-1"
        mg_id2 = "mg-status-multi-2"

        # Create move groups
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id1,
                "move_group_name": "Move Group Status Multi 1",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id2,
                "move_group_name": "Move Group Status Multi 2",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app with NOT_STARTED status
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App Status Multi MG",
                "move_group_ids": [],
                "server_ids": [server_id1, server_id2],
                "planning_status": "NOT_STARTED"
            }
        )

        # Create servers - not in move groups
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 - Not In Move Group",
                "app_ids": [app_id],
            }
        )

        # Move server 1 to move group 1
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id1,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to PARTIAL
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "PARTIAL")

        # Move server 2 to move group 2
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id2,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify app planning_status was updated to COMPLETED even with servers in different move groups
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"].get("planning_status"), "COMPLETED")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id1})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id2})

    def test_database_move_app_relationship(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test app relationship when databases are moved"""
        # Setup: Create a new app with a server and database
        app_id = "app-db-move"
        server_id = "server-db-test"
        db_id = "db-move-test"
        source_mg = "mg-source-db"
        dest_mg = "mg-dest-db"

        # Create source and destination move groups
        self.move_groups_table.put_item(
            Item={
                "move_group_id": source_mg,
                "move_group_name": "Source Move Group DB",
                "app_ids": [app_id],
                "server_ids": [server_id],
                "database_ids": [db_id],
                "server_count": 1,  # Integer value
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": dest_mg,
                "move_group_name": "Destination Move Group DB",
                "app_ids": [],
                "server_ids": [],
                "database_ids": [],
                "server_count": 0,  # Integer value
            }
        )

        # Create app with a server and database
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App for Database Move Test",
                "move_group_ids": [source_mg],
            }
        )

        # Create server for the app
        self.servers_table.put_item(
            Item={
                "server_id": server_id,
                "server_name": "Server for DB Test",
                "move_group_id": source_mg,
                "app_ids": [app_id],
            }
        )

        # Create database for the app
        self.databases_table.put_item(
            Item={
                "database_id": db_id,
                "database_name": "Database for Move Test",
                "move_group_id": source_mg,
                "app_ids": [app_id],
            }
        )

        # Move only the database to the destination move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": source_mg,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": dest_mg,
                    "target_entities": [
                        {"entity_type": "database", "entity_id": db_id},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify database was moved to the destination move group
        response = self.databases_table.get_item(Key={"database_id": db_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], dest_mg)

        # Verify server remains in the source move group
        response = self.servers_table.get_item(Key={"server_id": server_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], source_mg)

        # Verify app was COPIED (not moved) - it should be in both move groups
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertIn(source_mg, response["Item"]["move_group_ids"])
        self.assertIn(dest_mg, response["Item"]["move_group_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id})
        self.databases_table.delete_item(Key={"database_id": db_id})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": source_mg})
        self.move_groups_table.delete_item(Key={"move_group_id": dest_mg})

    def test_add_server_to_move_group(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test adding a server to a move group when source_entity_id is not specified"""
        # Create a new server for testing
        server_id = "server-add-test"
        dest_mg = "mg-1"

        # Create the server
        self.servers_table.put_item(
            Item={
                "server_id": server_id,
                "server_name": "Server for Add Test",
            }
        )

        # Create the event to add the server to move_group mg-1
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": dest_mg,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify server was added to the move group
        response = self.servers_table.get_item(Key={"server_id": server_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], dest_mg)

        # Verify the move group's server_ids was updated
        response = self.move_groups_table.get_item(Key={"move_group_id": dest_mg})
        self.assertIn("Item", response)
        self.assertIn(server_id, response["Item"]["server_ids"])
        self.assertEqual(
            response["Item"]["server_count"], 2
        )  # Original server + new one

        # Clean up
        self.servers_table.delete_item(Key={"server_id": server_id})

    def test_move_server_from_unassigned_to_move_group_with_app(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving a server from unassigned to a move group when the server belongs to an ungrouped app"""
        # Setup: Create a new app with an unassigned server
        app_id = "app-unassigned"
        server_id = "server-unassigned"
        dest_mg = "mg-destination"

        # Create destination move group
        self.move_groups_table.put_item(
            Item={
                "move_group_id": dest_mg,
                "move_group_name": "Destination Move Group",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,  # Integer value
            }
        )

        # Create app with no move group assignment
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Ungrouped App",
                "move_group_ids": [],
                "server_ids": [server_id],
            }
        )

        # Create server for the app with no move group assignment
        self.servers_table.put_item(
            Item={
                "server_id": server_id,
                "server_name": "Unassigned Server",
                "app_ids": [app_id],
            }
        )

        # Move the server to the destination move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": dest_mg,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify server was moved to the destination move group
        response = self.servers_table.get_item(Key={"server_id": server_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], dest_mg)

        # Verify the move group's server_ids was updated
        response = self.move_groups_table.get_item(Key={"move_group_id": dest_mg})
        self.assertIn("Item", response)
        self.assertIn(server_id, response["Item"]["server_ids"])
        self.assertEqual(
            response["Item"]["server_count"], 1
        )  # Verify server count is updated

        # Verify app was COPIED to the move group (not moved)
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertIn(dest_mg, response["Item"]["move_group_ids"])

        # Verify the move group's app_ids was updated
        response = self.move_groups_table.get_item(Key={"move_group_id": dest_mg})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": dest_mg})

    def test_move_server_from_move_group_to_unassigned(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving a server from a move group to unassigned when the server is part of an app with multiple servers"""
        # Setup: Create a move group with an app that has multiple servers
        app_id = "app-with-servers"
        server_id1 = "server-to-unassign"
        server_id2 = "server-stays-in-group"
        source_mg = "mg-source-group"

        # Create source move group
        self.move_groups_table.put_item(
            Item={
                "move_group_id": source_mg,
                "move_group_name": "Source Move Group",
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,  # Integer value
            }
        )

        # Create app assigned to the move group
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App With Multiple Servers",
                "move_group_ids": [source_mg],
                "server_ids": [server_id1, server_id2],
            }
        )

        # Create servers for the app, both assigned to the move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server To Unassign",
                "move_group_id": source_mg,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server Stays In Group",
                "move_group_id": source_mg,
                "app_ids": [app_id],
            }
        )

        # Move the first server to unassigned (no destination_entity_id)
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": source_mg,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify server1 was removed from the move group
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])

        # Verify server2 remains in the move group
        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], source_mg)

        # Verify app still remains in the move group
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        self.assertIn(source_mg, response["Item"]["move_group_ids"])

        # Verify the move group's server_ids was updated
        response = self.move_groups_table.get_item(Key={"move_group_id": source_mg})
        self.assertIn("Item", response)
        self.assertNotIn(server_id1, response["Item"]["server_ids"])
        self.assertIn(server_id2, response["Item"]["server_ids"])
        self.assertIn(app_id, response["Item"]["app_ids"])
        self.assertEqual(
            response["Item"]["server_count"], 1
        )  # Verify server count decreased

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": source_mg})

    def test_add_multiple_servers_to_wave(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test adding multiple servers to a wave when source_entity_id is not specified"""
        # Create new servers for testing
        server_id1 = "server-add-wave-1"
        server_id2 = "server-add-wave-2"
        dest_wave = "wave-2"

        # Create the servers
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 1 for Wave Add Test",
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 2 for Wave Add Test",
            }
        )

        # Create the event to add the servers to wave-2
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "wave",
                    "destination_entity_id": dest_wave,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify servers were added to the wave
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["wave_id"], dest_wave)

        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["wave_id"], dest_wave)

        # Verify the wave's server_ids was updated
        response = self.waves_table.get_item(Key={"wave_id": dest_wave})
        self.assertIn("Item", response)
        self.assertIn(server_id1, response["Item"]["server_ids"])
        self.assertIn(server_id2, response["Item"]["server_ids"])

        # Clean up
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})

    def test_move_validation_empty_string_fields(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test move operation validation with empty string fields"""
        # Test the validation function directly
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": "mg-1",
                    "destination_entity_type": "", # Empty string should be ignored
                    "destination_entity_id": "", # Empty string should be ignored
                    "target_entities": [
                        {"entity_type": "server", "entity_id": "server-1"}
                    ],
                }
            )
        }

        # Call the validation function directly
        validation_result = lambda_manage_entities.validate_request_body(event)
        # Should pass validation because empty strings are ignored
        self.assertTrue(validation_result["valid"])


    def test_large_move_group_scaling(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities
        import time

        """Test moving a move group with more than 100 assets between waves to check scaling"""
        # Define IDs
        large_move_group_id = "mg-large"
        wave_source_id = "wave-source"
        wave_dest_id = "wave-dest"

        server_ids = []
        app_ids = []

        # Create 200 servers first
        for i in range(1, 201):
            server_id = f"server-{i}"
            self.servers_table.put_item(
                Item={
                    "server_id": server_id,
                    "move_group_id": large_move_group_id,
                    "wave_id": wave_source_id,
                    "name": f"Server {i}",
                }
            )
            server_ids.append(server_id)

        # Create 150 apps
        for i in range(1, 151):
            app_id = f"app-{i}"
            self.apps_table.put_item(
                Item={
                    "app_id": app_id,
                    "move_group_ids": [large_move_group_id],
                    "wave_ids": [wave_source_id],
                    "name": f"App {i}",
                }
            )
            app_ids.append(app_id)

        # Create the move group in the source wave with asset IDs
        self.move_groups_table.put_item(
            Item={
                "move_group_id": large_move_group_id,
                "wave_id": wave_source_id,
                "name": "Large Move Group",
                "server_ids": server_ids,
                "app_ids": app_ids,
                "server_count": 200,
            }
        )

        # Create source and destination waves
        self.waves_table.put_item(
            Item={
                "wave_id": wave_source_id,
                "move_group_ids": [large_move_group_id],
                "name": "Source Wave",
                "server_ids": server_ids,
                "app_ids": app_ids,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave_dest_id,
                "move_group_ids": [],
                "name": "Destination Wave",
            }
        )

        # Create the event to move the large move group between waves
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "wave",
                    "source_entity_id": wave_source_id,
                    "destination_entity_type": "wave",
                    "destination_entity_id": wave_dest_id,
                    "target_entities": [
                        {"entity_type": "move_group", "entity_id": large_move_group_id}
                    ],
                }
            )
        }

        # Measure execution time
        start_time = time.time()

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        execution_time = time.time() - start_time
        print(f"Large move group operation took {execution_time:.2f} seconds")

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify the move group was moved to the new wave
        response = self.move_groups_table.get_item(
            Key={"move_group_id": large_move_group_id}
        )
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["wave_id"], wave_dest_id)
        self.assertEqual(
            response["Item"]["server_count"], 200
        )  # Verify server count is preserved

        # Verify the source wave's move_group_ids was updated
        response = self.waves_table.get_item(Key={"wave_id": wave_source_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_ids"], [])

        # Verify the destination wave's move_group_ids was updated
        response = self.waves_table.get_item(Key={"wave_id": wave_dest_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_ids"], [large_move_group_id])

        # Check all servers using scan
        from boto3.dynamodb.conditions import Attr

        # Scan all servers with the move_group_id
        server_items = scan_table(
            self.servers_table,
            Attr("move_group_id").eq(large_move_group_id),
        )

        # Verify all servers have the correct wave_id
        self.assertEqual(len(server_items), 200, "Should have found 100 servers")
        for server in server_items:
            self.assertEqual(
                server["wave_id"],
                wave_dest_id,
                f"Server {server['server_id']} has incorrect wave_id",
            )

        # Scan all apps with the move_group_id in move_group_ids
        app_items = scan_table(
            self.apps_table,
            Attr("move_group_ids").contains(large_move_group_id),
        )

        # Verify all apps have the correct wave_ids
        self.assertEqual(len(app_items), 150, "Should have found 50 apps")
        for app in app_items:
            self.assertIn(
                wave_dest_id,
                app["wave_ids"],
                f"App {app['app_id']} missing destination wave_id",
            )
            self.assertNotIn(
                wave_source_id,
                app["wave_ids"],
                f"App {app['app_id']} still has source wave_id",
            )

        # Clean up test data
        # Delete servers and apps using batch operations
        server_ids = [f"server-{i}" for i in range(1, 201)]
        app_ids = [f"app-{i}" for i in range(1, 151)]

        # Delete in batches to avoid overwhelming DynamoDB
        for i in range(0, len(server_ids), MAX_BATCH_WRITE_OPERATIONS):
            batch = server_ids[i : i + MAX_BATCH_WRITE_OPERATIONS]
            with self.servers_table.batch_writer() as batch_writer:
                for server_id in batch:
                    batch_writer.delete_item(Key={"server_id": server_id})

        for i in range(0, len(app_ids), MAX_BATCH_WRITE_OPERATIONS):
            batch = app_ids[i : i + MAX_BATCH_WRITE_OPERATIONS]
            with self.apps_table.batch_writer() as batch_writer:
                for app_id in batch:
                    batch_writer.delete_item(Key={"app_id": app_id})

        # Delete the move group and waves
        self.move_groups_table.delete_item(Key={"move_group_id": large_move_group_id})
        self.waves_table.delete_item(Key={"wave_id": wave_source_id})
        self.waves_table.delete_item(Key={"wave_id": wave_dest_id})

    def test_remove_server_no_null_in_app_move_group_ids(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test bug fix: removing a server from move group should not add null to app's move_group_ids"""
        # Setup: Create app with two servers in a move group
        app_id = "app-bug-test"
        server_id1 = "server-bug-1"
        server_id2 = "server-bug-2"
        mg_id = "mg-bug-test"

        # Create move group with both servers
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Bug Test Move Group",
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,
            }
        )

        # Create app with both servers
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Bug Test App",
                "move_group_ids": [mg_id],
                "server_ids": [server_id1, server_id2],
            }
        )

        # Create servers - both in move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Bug Test Server 1",
                "move_group_id": mg_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Bug Test Server 2",
                "move_group_id": mg_id,
                "app_ids": [app_id],
            }
        )

        # Remove only one server from the move group (no destination specified)
        # This is the scenario that was causing the bug
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify server1 was removed from the move group
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])

        # Verify server2 remains in the move group
        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg_id)

        # THE KEY TEST: Verify app's move_group_ids does NOT contain null values
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]

        # App should still be in the move group since server2 is still there
        self.assertIn("move_group_ids", app_item)
        move_group_ids = app_item["move_group_ids"]

        # Ensure no null values are present in the list
        self.assertIsInstance(move_group_ids, list)
        for mg_id_value in move_group_ids:
            self.assertIsNotNone(mg_id_value, "move_group_ids should not contain null values")
            self.assertNotEqual(mg_id_value, "", "move_group_ids should not contain empty strings")

        # App should still contain the original move group ID
        self.assertIn(mg_id, move_group_ids)

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})

    def test_add_server_to_new_group_app_copied_not_moved(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test bug: adding server to new group should copy app, not move it"""
        # Setup: Create app41 with servers 81 and 82 in Group1
        app_id = "app41"
        server_id1 = "81"
        server_id2 = "82"
        group1_id = "1"  # Group1
        group2_id = "2"  # Group2

        # Create Group1 with app41 and both servers
        self.move_groups_table.put_item(
            Item={
                "move_group_id": group1_id,
                "move_group_name": "Group1",
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,
            }
        )

        # Create Group2 (empty initially)
        self.move_groups_table.put_item(
            Item={
                "move_group_id": group2_id,
                "move_group_name": "Group2",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app41 initially in Group1 only
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App 41",
                "move_group_ids": [group1_id],
                "server_ids": [server_id1, server_id2],
            }
        )

        # Create server 81 in Group1
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 81",
                "move_group_id": group1_id,
                "app_ids": [app_id],
            }
        )

        # Create server 82 in Group1
        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 82",
                "move_group_id": group1_id,
                "app_ids": [app_id],
            }
        )

        # Move server 81 from Group1 to Group2
        # This should COPY app41 to Group2, not MOVE it
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": group1_id,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": group2_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify server 81 was moved to Group2
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], group2_id)

        # Verify server 82 remains in Group1
        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], group1_id)

        # THE CRITICAL TEST: App should be in BOTH groups (copied, not moved)
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]

        move_group_ids = app_item["move_group_ids"]

        # App should be in both Group1 and Group2
        self.assertIn(group1_id, move_group_ids,
            f"App should still be in Group1. Current move_group_ids: {move_group_ids}")
        self.assertIn(group2_id, move_group_ids,
            f"App should be copied to Group2. Current move_group_ids: {move_group_ids}")

        # Verify both move groups contain the app
        response = self.move_groups_table.get_item(Key={"move_group_id": group1_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"], "Group1 should still contain app41")

        response = self.move_groups_table.get_item(Key={"move_group_id": group2_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"], "Group2 should now contain app41")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": group1_id})
        self.move_groups_table.delete_item(Key={"move_group_id": group2_id})


    def test_remove_server_and_add_to_new_group(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test bug: adding server to new group should copy app, not move it"""
        # Setup: Create app41 with servers 81 and 82 in Group1
        app_id = "app41"
        server_id1 = "81"
        server_id2 = "82"
        group1_id = "1"  # Group1
        group2_id = "2"  # Group2

        # Create Group1 with app41 and both servers
        self.move_groups_table.put_item(
            Item={
                "move_group_id": group1_id,
                "move_group_name": "Group1",
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,
            }
        )

        # Create Group2 (empty initially)
        self.move_groups_table.put_item(
            Item={
                "move_group_id": group2_id,
                "move_group_name": "Group2",
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app41 initially in Group1 only
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "App 41",
                "move_group_ids": [group1_id],
            }
        )

        # Create server 81 in Group1
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Server 81",
                "move_group_id": group1_id,
                "app_ids": [app_id],
            }
        )

        # Create server 82 in Group1
        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Server 82",
                "move_group_id": group1_id,
                "app_ids": [app_id],
            }
        )

        # First, remove server 81 from Group1
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": group1_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Second, add server 81 from Group2
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": group2_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify server 81 was moved to Group2
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], group2_id)

        # Verify server 82 remains in Group1
        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], group1_id)

        # THE CRITICAL TEST: App should be in BOTH groups (copied, not moved)
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]

        move_group_ids = app_item["move_group_ids"]

        # App should be in both Group1 and Group2
        self.assertIn(group1_id, move_group_ids,
            f"App should still be in Group1. Current move_group_ids: {move_group_ids}")
        self.assertIn(group2_id, move_group_ids,
            f"App should be copied to Group2. Current move_group_ids: {move_group_ids}")

        # Verify both move groups contain the app
        response = self.move_groups_table.get_item(Key={"move_group_id": group1_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"], "Group1 should still contain app41")

        response = self.move_groups_table.get_item(Key={"move_group_id": group2_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"], "Group2 should now contain app41")

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": group1_id})
        self.move_groups_table.delete_item(Key={"move_group_id": group2_id})

    def test_move_servers_between_waves(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving servers between move groups in different waves"""
        # Setup: Create two waves with move groups and servers
        wave1_id = "wave-cross-1"
        wave2_id = "wave-cross-2"
        mg1_id = "mg-cross-1"
        mg2_id = "mg-cross-2"
        app_id = "app-cross-wave"
        server_id1 = "server-cross-1"
        server_id2 = "server-cross-2"

        # Create waves
        self.waves_table.put_item(
            Item={
                "wave_id": wave1_id,
                "wave_name": "Cross Wave 1",
                "move_group_ids": [mg1_id],
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave2_id,
                "wave_name": "Cross Wave 2",
                "move_group_ids": [mg2_id],
                "app_ids": [],
                "server_ids": [],
            }
        )

        # Create move groups in different waves
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg1_id,
                "move_group_name": "Cross Move Group 1",
                "wave_id": wave1_id,
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg2_id,
                "move_group_name": "Cross Move Group 2",
                "wave_id": wave2_id,
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app in first wave/move group
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Cross Wave App",
                "move_group_ids": [mg1_id],
                "wave_ids": [wave1_id],
            }
        )

        # Create servers in first move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Cross Server 1",
                "move_group_id": mg1_id,
                "wave_id": wave1_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Cross Server 2",
                "move_group_id": mg1_id,
                "wave_id": wave1_id,
                "app_ids": [app_id],
            }
        )

        # Move all servers from mg1 to mg2 (different waves)
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg1_id,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg2_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify servers moved to new move group and wave
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg2_id)
        self.assertEqual(response["Item"]["wave_id"], wave2_id)

        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg2_id)
        self.assertEqual(response["Item"]["wave_id"], wave2_id)

        # Verify app moved to new move group and wave
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]
        self.assertNotIn(mg1_id, app_item["move_group_ids"])
        self.assertIn(mg2_id, app_item["move_group_ids"])
        self.assertNotIn(wave1_id, app_item["wave_ids"])
        self.assertIn(wave2_id, app_item["wave_ids"])

        # Verify move group relationships
        response = self.move_groups_table.get_item(Key={"move_group_id": mg1_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 0)
        self.assertNotIn(app_id, response["Item"]["app_ids"])

        response = self.move_groups_table.get_item(Key={"move_group_id": mg2_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 2)
        self.assertIn(app_id, response["Item"]["app_ids"])

        # Verify wave relationships
        response = self.waves_table.get_item(Key={"wave_id": wave1_id})
        self.assertIn("Item", response)
        self.assertNotIn(app_id, response["Item"]["app_ids"])

        response = self.waves_table.get_item(Key={"wave_id": wave2_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg1_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg2_id})
        self.waves_table.delete_item(Key={"wave_id": wave1_id})
        self.waves_table.delete_item(Key={"wave_id": wave2_id})

    def test_partial_servers_move_between_waves(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving some servers between move groups in different waves - app should be copied"""
        # Setup: Create two waves with move groups and servers
        wave1_id = "wave-partial-1"
        wave2_id = "wave-partial-2"
        mg1_id = "mg-partial-1"
        mg2_id = "mg-partial-2"
        app_id = "app-partial-wave"
        server_id1 = "server-partial-1"
        server_id2 = "server-partial-2"
        server_id3 = "server-partial-3"

        # Create waves
        self.waves_table.put_item(
            Item={
                "wave_id": wave1_id,
                "wave_name": "Partial Wave 1",
                "move_group_ids": [mg1_id],
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2, server_id3],
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave2_id,
                "wave_name": "Partial Wave 2",
                "move_group_ids": [mg2_id],
                "app_ids": [],
                "server_ids": [],
            }
        )

        # Create move groups in different waves
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg1_id,
                "move_group_name": "Partial Move Group 1",
                "wave_id": wave1_id,
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2, server_id3],
                "server_count": 3,
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg2_id,
                "move_group_name": "Partial Move Group 2",
                "wave_id": wave2_id,
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app in first wave/move group
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Partial Wave App",
                "move_group_ids": [mg1_id],
                "wave_ids": [wave1_id],
            }
        )

        # Create servers in first move group
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Partial Server 1",
                "move_group_id": mg1_id,
                "wave_id": wave1_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Partial Server 2",
                "move_group_id": mg1_id,
                "wave_id": wave1_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id3,
                "server_name": "Partial Server 3",
                "move_group_id": mg1_id,
                "wave_id": wave1_id,
                "app_ids": [app_id],
            }
        )

        # Move only some servers from mg1 to mg2 (different waves)
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg1_id,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg2_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify moved servers are in new move group and wave
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg2_id)
        self.assertEqual(response["Item"]["wave_id"], wave2_id)

        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg2_id)
        self.assertEqual(response["Item"]["wave_id"], wave2_id)

        # Verify remaining server stays in original move group and wave
        response = self.servers_table.get_item(Key={"server_id": server_id3})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg1_id)
        self.assertEqual(response["Item"]["wave_id"], wave1_id)

        # Verify app is COPIED to both move groups and waves
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]
        self.assertIn(mg1_id, app_item["move_group_ids"])
        self.assertIn(mg2_id, app_item["move_group_ids"])
        self.assertIn(wave1_id, app_item["wave_ids"])
        self.assertIn(wave2_id, app_item["wave_ids"])

        # Verify move group relationships
        response = self.move_groups_table.get_item(Key={"move_group_id": mg1_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 1)
        self.assertIn(app_id, response["Item"]["app_ids"])

        response = self.move_groups_table.get_item(Key={"move_group_id": mg2_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 2)
        self.assertIn(app_id, response["Item"]["app_ids"])

        # Verify wave relationships - app should be in both waves
        response = self.waves_table.get_item(Key={"wave_id": wave1_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"])

        response = self.waves_table.get_item(Key={"wave_id": wave2_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.servers_table.delete_item(Key={"server_id": server_id3})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg1_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg2_id})
        self.waves_table.delete_item(Key={"wave_id": wave1_id})
        self.waves_table.delete_item(Key={"wave_id": wave2_id})

    def test_all_servers_move_to_unassigned(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving all servers to unassigned - app should be removed from move group and wave"""
        wave_id = "wave-unassign-all"
        mg_id = "mg-unassign-all"
        app_id = "app-unassign-all"
        server_id1 = "server-unassign-all-1"
        server_id2 = "server-unassign-all-2"

        # Create wave and move group
        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Unassign All Wave",
                "move_group_ids": [mg_id],
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Unassign All Move Group",
                "wave_id": wave_id,
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2],
                "server_count": 2,
            }
        )

        # Create app
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Unassign All App",
                "move_group_ids": [mg_id],
                "wave_ids": [wave_id],
            }
        )

        # Create servers
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Unassign All Server 1",
                "move_group_id": mg_id,
                "wave_id": wave_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Unassign All Server 2",
                "move_group_id": mg_id,
                "wave_id": wave_id,
                "app_ids": [app_id],
            }
        )

        # Move all servers to unassigned
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify servers are unassigned
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])
        self.assertNotIn("wave_id", response["Item"])

        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])
        self.assertNotIn("wave_id", response["Item"])

        # Verify app is removed from move group and wave
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]
        self.assertNotIn(mg_id, app_item.get("move_group_ids", []))
        self.assertNotIn(wave_id, app_item.get("wave_ids", []))

        # Verify move group and wave no longer contain app
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 0)
        self.assertNotIn(app_id, response["Item"]["app_ids"])

        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        self.assertNotIn(app_id, response["Item"]["app_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave_id})

    def test_partial_servers_move_to_unassigned(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving some servers to unassigned - app should remain in move group and wave"""
        wave_id = "wave-unassign-partial"
        mg_id = "mg-unassign-partial"
        app_id = "app-unassign-partial"
        server_id1 = "server-unassign-partial-1"
        server_id2 = "server-unassign-partial-2"
        server_id3 = "server-unassign-partial-3"

        # Create wave and move group
        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Unassign Partial Wave",
                "move_group_ids": [mg_id],
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2, server_id3],
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Unassign Partial Move Group",
                "wave_id": wave_id,
                "app_ids": [app_id],
                "server_ids": [server_id1, server_id2, server_id3],
                "server_count": 3,
            }
        )

        # Create app
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Unassign Partial App",
                "move_group_ids": [mg_id],
                "wave_ids": [wave_id],
            }
        )

        # Create servers
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Unassign Partial Server 1",
                "move_group_id": mg_id,
                "wave_id": wave_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Unassign Partial Server 2",
                "move_group_id": mg_id,
                "wave_id": wave_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id3,
                "server_name": "Unassign Partial Server 3",
                "move_group_id": mg_id,
                "wave_id": wave_id,
                "app_ids": [app_id],
            }
        )

        # Move only some servers to unassigned
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify moved servers are unassigned
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])
        self.assertNotIn("wave_id", response["Item"])

        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertNotIn("move_group_id", response["Item"])
        self.assertNotIn("wave_id", response["Item"])

        # Verify remaining server stays assigned
        response = self.servers_table.get_item(Key={"server_id": server_id3})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg_id)
        self.assertEqual(response["Item"]["wave_id"], wave_id)

        # Verify app remains in move group and wave
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]
        self.assertIn(mg_id, app_item["move_group_ids"])
        self.assertIn(wave_id, app_item["wave_ids"])

        # Verify move group and wave still contain app
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 1)
        self.assertIn(app_id, response["Item"]["app_ids"])

        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.servers_table.delete_item(Key={"server_id": server_id3})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave_id})

    def test_move_unassigned_servers_to_move_group(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving unassigned servers to a move group - should assign to move group and wave"""
        wave_id = "wave-assign"
        mg_id = "mg-assign"
        app_id = "app-assign"
        server_id1 = "server-assign-1"
        server_id2 = "server-assign-2"

        # Create wave and move group
        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Assign Wave",
                "move_group_ids": [mg_id],
                "app_ids": [],
                "server_ids": [],
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Assign Move Group",
                "wave_id": wave_id,
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app (unassigned)
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Assign App",
                "move_group_ids": [],
                "wave_ids": [],
            }
        )

        # Create unassigned servers
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Assign Server 1",
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Assign Server 2",
                "app_ids": [app_id],
            }
        )

        # Move servers to move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id1},
                        {"entity_type": "server", "entity_id": server_id2},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify servers are assigned to move group and wave
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg_id)
        self.assertEqual(response["Item"]["wave_id"], wave_id)

        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg_id)
        self.assertEqual(response["Item"]["wave_id"], wave_id)

        # Verify app is added to move group and wave
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]
        self.assertIn(mg_id, app_item["move_group_ids"])
        self.assertIn(wave_id, app_item["wave_ids"])

        # Verify move group and wave contain app and servers
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 2)
        self.assertIn(app_id, response["Item"]["app_ids"])

        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        self.assertIn(app_id, response["Item"]["app_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave_id})

    def test_move_partial_unassigned_servers_to_move_group(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test moving some unassigned servers to move group - app should be copied to move group"""
        wave_id = "wave-assign-partial"
        mg_id1 = "mg-assign-partial-1"
        mg_id2 = "mg-assign-partial-2"
        app_id = "app-assign-partial"
        server_id1 = "server-assign-partial-1"
        server_id2 = "server-assign-partial-2"
        server_id3 = "server-assign-partial-3"

        # Create wave and move groups
        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Assign Partial Wave",
                "move_group_ids": [mg_id1, mg_id2],
                "app_ids": [],
                "server_ids": [server_id1],
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id1,
                "move_group_name": "Assign Partial Move Group 1",
                "wave_id": wave_id,
                "app_ids": [app_id],
                "server_ids": [server_id1],
                "server_count": 1,
            }
        )

        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id2,
                "move_group_name": "Assign Partial Move Group 2",
                "wave_id": wave_id,
                "app_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        # Create app (partially assigned)
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Assign Partial App",
                "move_group_ids": [mg_id1],
                "wave_ids": [wave_id],
            }
        )

        # Create servers - one assigned, two unassigned
        self.servers_table.put_item(
            Item={
                "server_id": server_id1,
                "server_name": "Assign Partial Server 1",
                "move_group_id": mg_id1,
                "wave_id": wave_id,
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id2,
                "server_name": "Assign Partial Server 2",
                "app_ids": [app_id],
            }
        )

        self.servers_table.put_item(
            Item={
                "server_id": server_id3,
                "server_name": "Assign Partial Server 3",
                "app_ids": [app_id],
            }
        )

        # Move unassigned servers to second move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id2,
                    "target_entities": [
                        {"entity_type": "server", "entity_id": server_id2},
                        {"entity_type": "server", "entity_id": server_id3},
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify moved servers are assigned to move group and wave
        response = self.servers_table.get_item(Key={"server_id": server_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg_id2)
        self.assertEqual(response["Item"]["wave_id"], wave_id)

        response = self.servers_table.get_item(Key={"server_id": server_id3})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg_id2)
        self.assertEqual(response["Item"]["wave_id"], wave_id)

        # Verify existing server remains in original move group
        response = self.servers_table.get_item(Key={"server_id": server_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["move_group_id"], mg_id1)
        self.assertEqual(response["Item"]["wave_id"], wave_id)

        # Verify app is in both move groups (copied)
        response = self.apps_table.get_item(Key={"app_id": app_id})
        self.assertIn("Item", response)
        app_item = response["Item"]
        self.assertIn(mg_id1, app_item["move_group_ids"])
        self.assertIn(mg_id2, app_item["move_group_ids"])
        self.assertIn(wave_id, app_item["wave_ids"])

        # Verify both move groups contain app
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id1})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 1)
        self.assertIn(app_id, response["Item"]["app_ids"])

        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id2})
        self.assertIn("Item", response)
        self.assertEqual(response["Item"]["server_count"], 2)
        self.assertIn(app_id, response["Item"]["app_ids"])

        # Clean up test data
        self.servers_table.delete_item(Key={"server_id": server_id1})
        self.servers_table.delete_item(Key={"server_id": server_id2})
        self.servers_table.delete_item(Key={"server_id": server_id3})
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id1})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id2})
        self.waves_table.delete_item(Key={"wave_id": wave_id})

    def test_database_app_removal_not_cleaned_from_move_group(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test failing scenario: removing app from database should remove app from move group"""
        # Setup test data
        db_id = "3"
        mg_id = "1"
        wave_id = "wave-1"
        app38_id = "app38"
        app39_id = "app39"

        # Create move group and wave
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Move Group 1",
                "wave_id": wave_id,
                "app_ids": [app38_id],
                "database_ids": [db_id],
                "server_count": 0,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Wave 1",
                "move_group_ids": [mg_id],
                "app_ids": [app38_id],
                "database_ids": [db_id],
            }
        )

        # Create apps
        self.apps_table.put_item(
            Item={
                "app_id": app38_id,
                "app_name": "App 38",
                "move_group_ids": [mg_id],
                "wave_ids": [wave_id],
                "database_ids": [db_id],
            }
        )

        self.apps_table.put_item(
            Item={
                "app_id": app39_id,
                "app_name": "App 39",
                "database_ids": [db_id],
            }
        )

        # Create database with app38
        self.databases_table.put_item(
            Item={
                "database_id": db_id,
                "database_name": "Database 3",
                "move_group_id": mg_id,
                "wave_id": wave_id,
                "app_ids": [app38_id],
            }
        )

        # Edit database: remove app38, add app39 (same move group)
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": mg_id,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": mg_id,
                    "target_entities": [
                        {
                            "entity_type": "database",
                            "entity_id": db_id,
                            "app_ids": [app39_id]  # Removed app38, added app39
                        }
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify database app_ids were updated
        response = self.databases_table.get_item(Key={"database_id": db_id})
        self.assertIn("Item", response)
        db_item = response["Item"]
        self.assertEqual(db_item["app_ids"], [app39_id])

        # FAILING TEST: app38 should be removed from move group
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id})
        self.assertIn("Item", response)
        mg_item = response["Item"]
        self.assertNotIn(app38_id, mg_item.get("app_ids", []), "app38 should be removed from move group")
        self.assertIn(app39_id, mg_item.get("app_ids", []), "app39 should be added to move group")

        # FAILING TEST: app38 should be removed from wave
        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        wave_item = response["Item"]
        self.assertNotIn(app38_id, wave_item.get("app_ids", []), "app38 should be removed from wave")
        self.assertIn(app39_id, wave_item.get("app_ids", []), "app39 should be added to wave")

        # Clean up
        self.databases_table.delete_item(Key={"database_id": db_id})
        self.apps_table.delete_item(Key={"app_id": app38_id})
        self.apps_table.delete_item(Key={"app_id": app39_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave_id})

    def test_database_move_group_change_apps_not_removed_from_source(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test failing scenario: moving database between move groups should remove apps from source"""
        # Setup test data
        db_id = "3"
        source_mg_id = "1"
        dest_mg_id = "7"
        wave1_id = "wave-1"
        wave2_id = "wave-2"
        app37_id = "app37"
        app39_id = "app39"

        # Create source move group and wave
        self.move_groups_table.put_item(
            Item={
                "move_group_id": source_mg_id,
                "move_group_name": "Move Group 1",
                "wave_id": wave1_id,
                "app_ids": [app37_id, app39_id],
                "database_ids": [db_id],
                "server_count": 0,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave1_id,
                "wave_name": "Wave 1",
                "move_group_ids": [source_mg_id],
                "app_ids": [app37_id, app39_id],
                "database_ids": [db_id],
            }
        )

        # Create destination move group and wave
        self.move_groups_table.put_item(
            Item={
                "move_group_id": dest_mg_id,
                "move_group_name": "Move Group 7",
                "wave_id": wave2_id,
                "app_ids": [],
                "database_ids": [],
                "server_count": 0,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave2_id,
                "wave_name": "Wave 2",
                "move_group_ids": [dest_mg_id],
                "app_ids": [],
                "database_ids": [],
            }
        )

        # Create apps
        self.apps_table.put_item(
            Item={
                "app_id": app37_id,
                "app_name": "App 37",
                "move_group_ids": [source_mg_id],
                "wave_ids": [wave1_id],
                "database_ids": [db_id],
            }
        )

        self.apps_table.put_item(
            Item={
                "app_id": app39_id,
                "app_name": "App 39",
                "move_group_ids": [source_mg_id],
                "wave_ids": [wave1_id],
                "database_ids": [db_id],
            }
        )

        # Create database in source move group
        self.databases_table.put_item(
            Item={
                "database_id": db_id,
                "database_name": "Database 3",
                "move_group_id": source_mg_id,
                "wave_id": wave1_id,
                "app_ids": [app37_id, app39_id],
            }
        )

        # Move database from move group 1 to move group 7
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": source_mg_id,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": dest_mg_id,
                    "target_entities": [
                        {
                            "entity_type": "database",
                            "entity_id": db_id
                        }
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify database moved to destination
        response = self.databases_table.get_item(Key={"database_id": db_id})
        self.assertIn("Item", response)
        db_item = response["Item"]
        self.assertEqual(db_item["move_group_id"], dest_mg_id)
        self.assertEqual(db_item["wave_id"], wave2_id)

        # Verify apps were added to destination move group
        response = self.move_groups_table.get_item(Key={"move_group_id": dest_mg_id})
        self.assertIn("Item", response)
        dest_mg_item = response["Item"]
        self.assertIn(app37_id, dest_mg_item.get("app_ids", []))
        self.assertIn(app39_id, dest_mg_item.get("app_ids", []))

        # FAILING TEST: apps should be removed from source move group
        response = self.move_groups_table.get_item(Key={"move_group_id": source_mg_id})
        self.assertIn("Item", response)
        source_mg_item = response["Item"]
        self.assertNotIn(app37_id, source_mg_item.get("app_ids", []), "app37 should be removed from source move group")
        self.assertNotIn(app39_id, source_mg_item.get("app_ids", []), "app39 should be removed from source move group")

        # FAILING TEST: apps should be removed from source wave
        response = self.waves_table.get_item(Key={"wave_id": wave1_id})
        self.assertIn("Item", response)
        source_wave_item = response["Item"]
        self.assertNotIn(app37_id, source_wave_item.get("app_ids", []), "app37 should be removed from source wave")
        self.assertNotIn(app39_id, source_wave_item.get("app_ids", []), "app39 should be removed from source wave")

        # Verify apps have correct move_group_ids and wave_ids
        response = self.apps_table.get_item(Key={"app_id": app37_id})
        self.assertIn("Item", response)
        app37_item = response["Item"]
        self.assertNotIn(source_mg_id, app37_item.get("move_group_ids", []), "app37 should not have source move group")
        self.assertIn(dest_mg_id, app37_item.get("move_group_ids", []), "app37 should have destination move group")
        self.assertNotIn(wave1_id, app37_item.get("wave_ids", []), "app37 should not have source wave")
        self.assertIn(wave2_id, app37_item.get("wave_ids", []), "app37 should have destination wave")

        # Clean up
        self.databases_table.delete_item(Key={"database_id": db_id})
        self.apps_table.delete_item(Key={"app_id": app37_id})
        self.apps_table.delete_item(Key={"app_id": app39_id})
        self.move_groups_table.delete_item(Key={"move_group_id": source_mg_id})
        self.move_groups_table.delete_item(Key={"move_group_id": dest_mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave1_id})
        self.waves_table.delete_item(Key={"wave_id": wave2_id})

    def test_database_move_group_change_apps_remain_with_other_assets(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test scenario: moving database between move groups where some apps should remain in source because their other assets are still there"""
        # Setup test data
        db_id = "db-move-test"
        server_id = "server-stays"
        source_mg_id = "mg-source"
        dest_mg_id = "mg-dest"
        wave1_id = "wave-source"
        wave2_id = "wave-dest"
        app_moves_id = "app-moves"  # This app only has the database, should move
        app_stays_id = "app-stays"  # This app has server in source, should remain

        # Create source move group and wave
        self.move_groups_table.put_item(
            Item={
                "move_group_id": source_mg_id,
                "move_group_name": "Source Move Group",
                "wave_id": wave1_id,
                "app_ids": [app_moves_id, app_stays_id],
                "database_ids": [db_id],
                "server_ids": [server_id],
                "server_count": 1,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave1_id,
                "wave_name": "Source Wave",
                "move_group_ids": [source_mg_id],
                "app_ids": [app_moves_id, app_stays_id],
                "database_ids": [db_id],
                "server_ids": [server_id],
            }
        )

        # Create destination move group and wave
        self.move_groups_table.put_item(
            Item={
                "move_group_id": dest_mg_id,
                "move_group_name": "Destination Move Group",
                "wave_id": wave2_id,
                "app_ids": [],
                "database_ids": [],
                "server_ids": [],
                "server_count": 0,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave2_id,
                "wave_name": "Destination Wave",
                "move_group_ids": [dest_mg_id],
                "app_ids": [],
                "database_ids": [],
                "server_ids": [],
            }
        )

        # Create app that should move (only has database)
        self.apps_table.put_item(
            Item={
                "app_id": app_moves_id,
                "app_name": "App That Moves",
                "move_group_ids": [source_mg_id],
                "wave_ids": [wave1_id],
                "database_ids": [db_id],
            }
        )

        # Create app that should stay (has server in source)
        self.apps_table.put_item(
            Item={
                "app_id": app_stays_id,
                "app_name": "App That Stays",
                "move_group_ids": [source_mg_id],
                "wave_ids": [wave1_id],
                "database_ids": [db_id],
                "server_ids": [server_id],
            }
        )

        # Create database with both apps
        self.databases_table.put_item(
            Item={
                "database_id": db_id,
                "database_name": "Shared Database",
                "move_group_id": source_mg_id,
                "wave_id": wave1_id,
                "app_ids": [app_moves_id, app_stays_id],
            }
        )

        # Create server that keeps app_stays in source
        self.servers_table.put_item(
            Item={
                "server_id": server_id,
                "server_name": "Server That Stays",
                "move_group_id": source_mg_id,
                "wave_id": wave1_id,
                "app_ids": [app_stays_id],
            }
        )

        # Move database from source to destination move group
        event = {
            "body": json.dumps(
                {
                    "operation": "move",
                    "source_entity_type": "move_group",
                    "source_entity_id": source_mg_id,
                    "destination_entity_type": "move_group",
                    "destination_entity_id": dest_mg_id,
                    "target_entities": [
                        {
                            "entity_type": "database",
                            "entity_id": db_id
                        }
                    ],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify database moved to destination
        response = self.databases_table.get_item(Key={"database_id": db_id})
        self.assertIn("Item", response)
        db_item = response["Item"]
        self.assertEqual(db_item["move_group_id"], dest_mg_id)
        self.assertEqual(db_item["wave_id"], wave2_id)

        # Verify app_moves was moved to destination (only had database)
        response = self.apps_table.get_item(Key={"app_id": app_moves_id})
        self.assertIn("Item", response)
        app_moves_item = response["Item"]
        self.assertNotIn(source_mg_id, app_moves_item.get("move_group_ids", []), "app_moves should be removed from source")
        self.assertIn(dest_mg_id, app_moves_item.get("move_group_ids", []), "app_moves should be added to destination")
        self.assertNotIn(wave1_id, app_moves_item.get("wave_ids", []), "app_moves should be removed from source wave")
        self.assertIn(wave2_id, app_moves_item.get("wave_ids", []), "app_moves should be added to destination wave")

        # Verify app_stays remains in source (has server there)
        response = self.apps_table.get_item(Key={"app_id": app_stays_id})
        self.assertIn("Item", response)
        app_stays_item = response["Item"]
        self.assertIn(source_mg_id, app_stays_item.get("move_group_ids", []), "app_stays should remain in source")
        self.assertIn(dest_mg_id, app_stays_item.get("move_group_ids", []), "app_stays should be copied to destination")
        self.assertIn(wave1_id, app_stays_item.get("wave_ids", []), "app_stays should remain in source wave")
        self.assertIn(wave2_id, app_stays_item.get("wave_ids", []), "app_stays should be copied to destination wave")

        # Verify source move group still contains app_stays but not app_moves
        response = self.move_groups_table.get_item(Key={"move_group_id": source_mg_id})
        self.assertIn("Item", response)
        source_mg_item = response["Item"]
        self.assertNotIn(app_moves_id, source_mg_item.get("app_ids", []), "app_moves should be removed from source move group")
        self.assertIn(app_stays_id, source_mg_item.get("app_ids", []), "app_stays should remain in source move group")

        # Verify destination move group contains both apps
        response = self.move_groups_table.get_item(Key={"move_group_id": dest_mg_id})
        self.assertIn("Item", response)
        dest_mg_item = response["Item"]
        self.assertIn(app_moves_id, dest_mg_item.get("app_ids", []), "app_moves should be in destination move group")
        self.assertIn(app_stays_id, dest_mg_item.get("app_ids", []), "app_stays should be copied to destination move group")

        # Verify source wave still contains app_stays but not app_moves
        response = self.waves_table.get_item(Key={"wave_id": wave1_id})
        self.assertIn("Item", response)
        source_wave_item = response["Item"]
        self.assertNotIn(app_moves_id, source_wave_item.get("app_ids", []), "app_moves should be removed from source wave")
        self.assertIn(app_stays_id, source_wave_item.get("app_ids", []), "app_stays should remain in source wave")

        # Verify destination wave contains both apps
        response = self.waves_table.get_item(Key={"wave_id": wave2_id})
        self.assertIn("Item", response)
        dest_wave_item = response["Item"]
        self.assertIn(app_moves_id, dest_wave_item.get("app_ids", []), "app_moves should be in destination wave")
        self.assertIn(app_stays_id, dest_wave_item.get("app_ids", []), "app_stays should be copied to destination wave")

        # Clean up
        self.databases_table.delete_item(Key={"database_id": db_id})
        self.servers_table.delete_item(Key={"server_id": server_id})
        self.apps_table.delete_item(Key={"app_id": app_moves_id})
        self.apps_table.delete_item(Key={"app_id": app_stays_id})
        self.move_groups_table.delete_item(Key={"move_group_id": source_mg_id})
        self.move_groups_table.delete_item(Key={"move_group_id": dest_mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave1_id})
        self.waves_table.delete_item(Key={"wave_id": wave2_id})

    def test_database_cleanup_removes_apps_from_move_group_and_wave(self, mock_creation_policy, mock_attribute_policy):
        import lambda_manage_entities

        """Test database cleanup removes associated app_ids from move group and wave"""
        # Setup test data
        db_id = "db-cleanup-test"
        mg_id = "mg-cleanup-test"
        wave_id = "wave-cleanup-test"
        app_id = "app-cleanup-test"

        # Create move group and wave with database and app
        self.move_groups_table.put_item(
            Item={
                "move_group_id": mg_id,
                "move_group_name": "Cleanup Test Move Group",
                "wave_id": wave_id,
                "app_ids": [app_id],
                "database_ids": [db_id],
                "server_count": 0,
            }
        )

        self.waves_table.put_item(
            Item={
                "wave_id": wave_id,
                "wave_name": "Cleanup Test Wave",
                "move_group_ids": [mg_id],
                "app_ids": [app_id],
                "database_ids": [db_id],
            }
        )

        # Create app associated with database
        self.apps_table.put_item(
            Item={
                "app_id": app_id,
                "app_name": "Cleanup Test App",
                "move_group_ids": [mg_id],
                "wave_ids": [wave_id],
                "database_ids": [db_id],
            }
        )

        # Create database
        self.databases_table.put_item(
            Item={
                "database_id": db_id,
                "database_name": "Cleanup Test Database",
                "move_group_id": mg_id,
                "wave_id": wave_id,
                "app_ids": [app_id],
            }
        )

        # Cleanup database
        event = {
            "body": json.dumps(
                {
                    "operation": "cleanup",
                    "entity_type": "database",
                    "entity_ids": [db_id],
                }
            )
        }

        # Call the lambda function
        response = lambda_manage_entities.lambda_handler(event, {})

        # Check the response
        self.assertEqual(response["statusCode"], 200)

        # Verify database was deleted
        response = self.databases_table.get_item(Key={"database_id": db_id})
        self.assertNotIn("Item", response)

        # FAILING TEST: app should be removed from move group
        response = self.move_groups_table.get_item(Key={"move_group_id": mg_id})
        self.assertIn("Item", response)
        mg_item = response["Item"]
        self.assertNotIn(app_id, mg_item.get("app_ids", []), "app should be removed from move group after database cleanup")

        # FAILING TEST: app should be removed from wave
        response = self.waves_table.get_item(Key={"wave_id": wave_id})
        self.assertIn("Item", response)
        wave_item = response["Item"]
        self.assertNotIn(app_id, wave_item.get("app_ids", []), "app should be removed from wave after database cleanup")

        # Clean up
        self.apps_table.delete_item(Key={"app_id": app_id})
        self.move_groups_table.delete_item(Key={"move_group_id": mg_id})
        self.waves_table.delete_item(Key={"wave_id": wave_id})

    def test_move_custom_asset_between_apps(self, mock_creation_policy, mock_attribute_policy):
        """Test moving custom assets between different app configurations"""
        import lambda_manage_entities

        # Move both storage assets in one call
        event = {
            "body": json.dumps({
                "operation": "move",
                "target_entities": [
                    {
                        "entity_type": "storage",
                        "entity_id": "storage-1",
                        "app_ids": ["app-2"] # Move storage-1 from app-1 to app-2
                    },
                    {
                        "entity_type": "storage",
                        "entity_id": "storage-2",
                        "app_ids": ["app-2"] # Move storage-2 from shared (app-1, app-2) to only app-2
                    }
                ]
            })
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        # Verify storage-1 now references app-2
        storage1 = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-1')}", "asset_id": "storage-1"}
        )["Item"]
        self.assertEqual(storage1["app_ids"], ["app-2"])

        # Verify storage-2 now only references app-2
        storage2 = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-2')}", "asset_id": "storage-2"}
        )["Item"]
        self.assertEqual(storage2["app_ids"], ["app-2"])

        # Verify app-1 no longer references either storage
        app1 = self.apps_table.get_item(Key={"app_id": "app-1"})["Item"]
        self.assertNotIn("storage-1", app1.get("storage_ids", []))
        self.assertNotIn("storage-2", app1.get("storage_ids", []))

        # Verify app-2 now references both storage assets
        app2 = self.apps_table.get_item(Key={"app_id": "app-2"})["Item"]
        self.assertIn("storage-1", app2.get("storage_ids", []))
        self.assertIn("storage-2", app2.get("storage_ids", []))


    def test_lambda_handler_duplicate_entity_ids(self, mock_creation_policy, mock_attribute_policy):
        """Test lambda_handler with duplicate entity_type+entity_id combinations in target_entities."""
        import lambda_manage_entities

        # Test with same entity_id but different entity_type (should pass validation)
        event = {
            "body": json.dumps({
                "operation": "move",
                "destination_entity_type": "move_group",
                "destination_entity_id": "mg-1",
                "target_entities": [
                    {"entity_type": "server", "entity_id": "asset-1"},
                    {"entity_type": "database", "entity_id": "asset-1"}  # Same ID, different type - valid
                ]
            })
        }
        response = lambda_manage_entities.lambda_handler(event, {})
        # Should pass validation (not 400 due to duplicate check), may fail later due to missing entities
        self.assertNotIn("Duplicate entity_id found", json.loads(response["body"]).get("message", ""))

        # Test with true duplicate entity_type+entity_id combination (should fail)
        event = {
            "body": json.dumps({
                "operation": "move",
                "target_entities": [
                    {"entity_type": "server", "entity_id": "server-1"},
                    {"entity_type": "server", "entity_id": "server-1"}  # True duplicate
                ]
            })
        }
        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Duplicate entity_id found", json.loads(response["body"])["message"])

    def test_move_custom_asset_from_app_to_unassigned(self, mock_creation_policy, mock_attribute_policy):
        """Test moving a custom asset (storage) from an app to unassigned"""
        import lambda_manage_entities

        # Move storage-1 from app-1 to unassigned (empty app_ids)
        event = {
            "body": json.dumps({
                "operation": "move",
                "target_entities": [
                    {
                        "entity_type": "storage",
                        "entity_id": "storage-1",
                        "app_ids": []  # Unassigned
                    }
                ]
            })
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        # Verify storage-1 has no app references
        storage1 = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-1')}", "asset_id": "storage-1"}
        )["Item"]
        self.assertEqual(storage1.get("app_ids", []), [])

        # Verify app-1 no longer references storage-1
        app1 = self.apps_table.get_item(Key={"app_id": "app-1"})["Item"]
        self.assertNotIn("storage-1", app1.get("storage_ids", []))

    def test_move_custom_asset_from_unassigned_to_app(self, mock_creation_policy, mock_attribute_policy):
        """Test moving a custom asset (storage) from unassigned to an app"""
        import lambda_manage_entities

        # Create an unassigned storage asset
        self.custom_assets_table.put_item(
            Item={
                "asset_type#shard": f"storage#{get_shard_number('storage-3')}",
                "asset_id": "storage-3",
                "storage_name": "Unassigned Storage",
                "storage_type": "Block",
                "app_ids": [],
            }
        )

        # Move storage-3 from unassigned to app-1
        event = {
            "body": json.dumps({
                "operation": "move",
                "target_entities": [
                    {
                        "entity_type": "storage",
                        "entity_id": "storage-3",
                        "app_ids": ["app-1"]
                    }
                ]
            })
        }

        response = lambda_manage_entities.lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

        # Verify storage-3 now references app-1
        storage3 = self.custom_assets_table.get_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-3')}", "asset_id": "storage-3"}
        )["Item"]
        self.assertEqual(storage3["app_ids"], ["app-1"])

        # Verify app-1 now references storage-3
        app1 = self.apps_table.get_item(Key={"app_id": "app-1"})["Item"]
        self.assertIn("storage-3", app1.get("storage_ids", []))

        # Clean up
        self.custom_assets_table.delete_item(
            Key={"asset_type#shard": f"storage#{get_shard_number('storage-3')}", "asset_id": "storage-3"}
        )

def scan_table(table, filter):
    """
    Scan a DynamoDB table with pagination.

    Args:
        table (DynamoDB.Table): The DynamoDB table to scan
        filter (Attr): Filter expression for the scan

    Returns:
        list: List of items matching the filter
    """
    response = table.scan(FilterExpression=filter)
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(
            FilterExpression=filter, ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items


if __name__ == "__main__":
    unittest.main()
