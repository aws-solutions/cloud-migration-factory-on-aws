import json
import unittest
from unittest import mock

import boto3
from boto3.dynamodb.types import TypeSerializer
from moto import mock_aws
from test_lambda_gfcommon import mock_getUserResourceCreationPolicy
from test_common_utils import default_mock_os_environ

mock_os_environ = {
    **default_mock_os_environ,
    "RULES_TABLE_NAME": "rules",
    "SCHEMA_TABLE_NAME": "schema",
    "APPS_TABLE_NAME": "apps",
    "SERVERS_TABLE_NAME": "servers",
    "DATABASES_TABLE_NAME": "databases",
    "ASSETS_TABLE_NAME": "assets",
    "MOVE_GROUPS_TABLE_NAME": "move_groups",
    "MOVE_GROUP_REQUESTS_TABLE_NAME": "move_group_requests",
    "WPM_JOBS_TABLE_NAME": "wpm_jobs",
    "CUSTOM_ASSETS_TABLE_NAME": "custom_assets",
}

@mock.patch.dict("os.environ", mock_os_environ)
@mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
@mock_aws
class LambdaCreateMoveGroups(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        boto3.setup_default_session()
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.serializer = TypeSerializer()

        # Create all required tables
        self._create_tables()
        # Populate test data
        self._populate_test_data()

    def _create_tables(self):
        """Create all required DynamoDB tables."""
        tables_config = {
            "apps": "app_id",
            "servers": "server_id",
            "databases": "database_id",
            "rules": "rule_id",
            "schema": "schema_name",
            "move_groups": "move_group_id",
            "move_group_requests": "move_group_request_id",
            "wpm_jobs": "wpm_job_id",
        }

        for table_name, key_name in tables_config.items():
            self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": key_name, "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": key_name, "AttributeType": "S"},
                    {"AttributeName": "move_group_name", "AttributeType": "S"}
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "NameIndex",
                        "KeySchema": [{"AttributeName": "move_group_name", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "KEYS_ONLY"}
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
            )

    def _serialize_item(self, item):
        """Helper method to serialize items to DynamoDB format"""
        return {k: self.serializer.serialize(v) for k, v in item.items()}

    def _create_custom_asset_table(self):
        self.dynamodb.create_table(
            TableName="custom_assets",
            KeySchema=[
                {"AttributeName": "asset_type#shard", "KeyType": "HASH"},
                {"AttributeName": "asset_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "asset_type#shard", "AttributeType": "S"},
                {"AttributeName": "asset_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

    def _populate_test_data(self):
        """Populate test data in DynamoDB tables."""
        # Create schema items
        self.schema_table = self.dynamodb.Table("schema")
        
        # Create test WPM jobs
        jobs_table = self.dynamodb.Table("wpm_jobs")
        test_jobs = [
            {
                "wpm_job_id": "JOB001",
                "job_name": "Test Job 1",
                "status": "CREATED",
                "move_group_ids": []
            },
            {
                "wpm_job_id": "JOB002",
                "job_name": "Test Job 2",
                "status": "CREATED",
                "move_group_ids": []
            },
            {
                "wpm_job_id": "JOB003",
                "job_name": "Test Job 3",
                "status": "CREATED",
                "move_group_ids": []
            }
        ]
        
        for job in test_jobs:
            jobs_table.put_item(Item=job)

        app_schema = {
            "schema_name": "app",
            "schema_type": "user",
            "attributes": [
                {"name": "app_id", "type": "string", "required": True, "system": True},
                {
                    "name": "app_name",
                    "type": "string",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "department",
                    "type": "string",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "server_ids",
                    "type": "multivalue-relationship",
                    "rel_entity": "server",
                    "rel_key": "server_id",
                    "rel_display_attribute": "server_name",
                    "required": False,
                    "system": True,
                },
                {
                    "name": "database_ids",
                    "type": "multivalue-relationship",
                    "rel_entity": "database",
                    "rel_key": "database_id",
                    "rel_display_attribute": "database_name",
                    "required": False,
                    "system": True,
                },
            ],
        }

        server_schema = {
            "schema_name": "server",
            "schema_type": "user",
            "attributes": [
                {
                    "name": "server_id",
                    "type": "string",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "server_name",
                    "type": "string",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "server_environment",
                    "type": "string",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "app_ids",
                    "type": "multivalue-relationship",
                    "rel_entity": "app",
                    "rel_key": "app_id",
                    "rel_display_attribute": "app_name",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "r_type",
                    "type": "list",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "move_group_id",
                    "type": "string",
                    "required": False,
                    "system": True,
                },
            ],
        }

        database_schema = {
            "schema_name": "database",
            "schema_type": "user",
            "attributes": [
                {
                    "name": "database_id",
                    "type": "string",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "database_name",
                    "type": "string",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "app_ids",
                    "type": "multivalue-relationship",
                    "rel_entity": "app",
                    "rel_key": "app_id",
                    "rel_display_attribute": "app_name",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "r_type",
                    "type": "list",
                    "required": True,
                    "system": True,
                },
                {
                    "name": "move_group_id",
                    "type": "string",
                    "required": False,
                    "system": True,
                },
            ],
        }

        self.schema_table.put_item(Item=app_schema)
        self.schema_table.put_item(Item=server_schema)
        self.schema_table.put_item(Item=database_schema)

        # Create rule items
        rules_table = self.dynamodb.Table("rules")
        server_rule_item = {
            "rule_type": "GROUPING_INCLUSIVE",
            "rule_id": "1",
            "relationships": [{"asset_key": "server_ids", "asset_type": "app"}],
            "rule_name": "Apps sharing Servers",
            "status": "ENABLED",
        }
        rules_table.put_item(Item=server_rule_item)
        
        database_rule_item = {
            "rule_type": "GROUPING_INCLUSIVE",
            "rule_id": "3",
            "relationships": [{"asset_key": "database_ids", "asset_type": "app"}],
            "rule_name": "Apps sharing Databases",
            "status": "ENABLED",
        }
        rules_table.put_item(Item=database_rule_item)

        # Add test apps
        apps_table = self.dynamodb.Table("apps")
        test_apps = [
            {
                "app_id": "APP001",
                "app_name": "APP001",
            },
            {
                "app_id": "APP002",
                "app_name": "APP002",
            },
            {
                "app_id": "APP003",
                "app_name": "APP003",
                "department": "sales",
            },
            {
                "app_id": "APP004",
                "app_name": "APP004",
                "department": "finance",
            },
            {"app_id": "APP005", "app_name": "APP005", "department": "IT"},
            {"app_id": "APP006", "app_name": "APP006", "department": "sales"},
            {
                "app_id": "APP007",
                "app_name": "APP007",
                "department": "marketing",
            },
            {"app_id": "APP008", "app_name": "APP008", "department": "IT"},
            {"app_id": "APP009", "app_name": "APP009"},
            {
                "app_id": "APP010",
                "app_name": "APP010",
                "department": "marketing",
            },
        ]

        for app in test_apps:
            apps_table.put_item(Item=app)

        # Add test servers
        servers_table = self.dynamodb.Table("servers")
        test_servers = [
            {
                "server_id": "SRV001",
                "server_name": "SRV001",
                "server_fqdn": "SRV001.test.com",
                "server_os_family": "Windows",
                "server_environment": "DEV",
                "app_ids": ["APP001"],
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
            {
                "server_id": "SRV002",
                "server_name": "SRV002",
                "server_fqdn": "SRV002.test.com",
                "server_os_family": "Windows",
                "server_environment": "PROD",
                "app_ids": ["APP001", "APP002"],
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
            {
                "server_id": "SRV003",
                "server_name": "SRV003",
                "server_fqdn": "SRV003.test.com",
                "server_os_family": "Windows",
                "server_environment": "PROD",
                "app_ids": ["APP002"],
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
            {
                "server_id": "SRV004",
                "server_name": "SRV004",
                "server_fqdn": "SRV004.test.com",
                "server_os_family": "Windows",
                "server_environment": "PROD",
                "app_ids": ["APP002"],
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
            {
                "server_id": "SRV005",
                "server_name": "SRV005",
                "server_fqdn": "SRV005.test.com",
                "server_os_family": "Windows",
                "app_ids": ["APP003", "APP004"],
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
            {
                "server_id": "SRV006",
                "server_name": "SRV006",
                "server_fqdn": "SRV006.test.com",
                "server_os_family": "Windows",
                "app_ids": ["APP004", "APP007"],
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
        ]

        for server in test_servers:
            servers_table.put_item(Item=server)

        # Add test databases
        databases_table = self.dynamodb.Table("databases")
        test_databases = [
            {
                "database_id": "DB001",
                "database_name": "DB001",
                "app_ids": ["APP001"],
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
            {
                "database_id": "DB002",
                "database_name": "DB002",
                "app_ids": ["APP002"],
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
            {
                "database_id": "DB003",
                "database_name": "DB003",
                "app_ids": ["APP007"],
                "department": "marketing",
                "r_type": ["Relocate", "Rehost","Repurchase"],
            },
        ]

        for db in test_databases:
            databases_table.put_item(Item=db)
            
        # Add test move_groups
        move_groups_table = self.dynamodb.Table("move_groups")
        test_move_groups = [
            {
                "move_group_id": "1",
            },
            {
                "move_group_id": "non-numeric",
            },
        ]
        for move_group in test_move_groups:
            move_groups_table.put_item(Item=move_group)

    def test_lambda_handler_single_app1(self):
        """Test lambda_handler with a single app."""
        import lambda_create_move_groups

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ001"},
                            "app_ids": {"L": [{"S": "APP001"}]},
                            "wpm_job_id": {"S": "JOB001"},
                        }
                    },
                }
            ]
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["move_group_request_id"], "REQ001")
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertTrue(len(response_body["move_group_ids"]) == 1)

        # Verify move group creation
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]

        self.assertEqual(move_group["wpm_job_id"], "JOB001")
        self._verify_ulid(move_group["move_group_id"])
        self._verify_auto_generated_name(move_group["move_group_name"])
        self.assertEqual(set(move_group["app_ids"]), set(["APP001", "APP002"]))
        self.assertEqual(set(move_group["server_ids"]), set(["SRV001", "SRV002", "SRV003", "SRV004"]))
        self.assertEqual(set(move_group["database_ids"]), set(["DB001", "DB002"]))
        
        # Verify WPM job was updated with the move group ID
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB001"})["Item"]
        self.assertIn(response_body["move_group_ids"][0], job["move_group_ids"])
        
        # Verify apps were updated with move_group_ids and wpm_job_ids
        apps_table = self.dynamodb.Table("apps")
        app = apps_table.get_item(Key={"app_id": "APP001"})["Item"]
        self.assertIsInstance(app["move_group_ids"], list)
        self.assertIn(response_body["move_group_ids"][0], app.get("move_group_ids", []))
        self.assertIsInstance(app["wpm_job_ids"], list)
        self.assertIn("JOB001", app.get("wpm_job_ids", []))
        
        # Verify servers were updated with move_group_id and wpm_job_id
        servers_table = self.dynamodb.Table("servers")
        server1 = servers_table.get_item(Key={"server_id": "SRV001"})["Item"]
        server2 = servers_table.get_item(Key={"server_id": "SRV002"})["Item"]
        self.assertEqual(server1.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(server1.get("wpm_job_id"), "JOB001")
        self.assertEqual(server2.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(server2.get("wpm_job_id"), "JOB001")
        
        # Verify databases were updated with move_group_id and wpm_job_id
        databases_table = self.dynamodb.Table("databases")
        db1 = databases_table.get_item(Key={"database_id": "DB001"})["Item"]
        self.assertEqual(db1.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(db1.get("wpm_job_id"), "JOB001")

    def test_lambda_handler_single_app1_directly(self):
        """Test lambda_handler with a single app."""
        import lambda_create_move_groups

        event = {
            "body": json.dumps(
                {
                    "app_ids": ["APP001"],
                    "wpm_job_id": "JOB001",
                }
            )
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertTrue(len(response_body["move_group_ids"]) == 1)

        # Verify move group creation
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]

        self.assertEqual(move_group["wpm_job_id"], "JOB001")
        self._verify_ulid(move_group["move_group_id"])
        self._verify_auto_generated_name(move_group["move_group_name"])
        self.assertEqual(set(move_group["app_ids"]), set(["APP001", "APP002"]))
        self.assertEqual(set(move_group["server_ids"]), set(["SRV001", "SRV002", "SRV003", "SRV004"]))
        self.assertEqual(set(move_group["database_ids"]), set(["DB001", "DB002"]))
        
        # Verify WPM job was updated with the move group ID
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB001"})["Item"]
        self.assertIn(response_body["move_group_ids"][0], job["move_group_ids"])
        
        # Verify apps were updated with move_group_ids and wpm_job_ids
        apps_table = self.dynamodb.Table("apps")
        app = apps_table.get_item(Key={"app_id": "APP001"})["Item"]
        self.assertIsInstance(app["move_group_ids"], list)
        self.assertIn(response_body["move_group_ids"][0], app.get("move_group_ids", []))
        self.assertIsInstance(app["wpm_job_ids"], list)
        self.assertIn("JOB001", app.get("wpm_job_ids", []))
        
        # Verify servers were updated with move_group_id and wpm_job_id
        servers_table = self.dynamodb.Table("servers")
        server1 = servers_table.get_item(Key={"server_id": "SRV001"})["Item"]
        server2 = servers_table.get_item(Key={"server_id": "SRV002"})["Item"]
        self.assertEqual(server1.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(server1.get("wpm_job_id"), "JOB001")
        self.assertEqual(server2.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(server2.get("wpm_job_id"), "JOB001")
        
        # Verify databases were updated with move_group_id and wpm_job_id
        databases_table = self.dynamodb.Table("databases")
        db1 = databases_table.get_item(Key={"database_id": "DB001"})["Item"]
        self.assertEqual(db1.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(db1.get("wpm_job_id"), "JOB001")

    def test_lambda_handler_wpm_job_with_none_move_group_ids(self):
        """Test lambda_handler when move_group_ids in wpm_job is None."""
        import lambda_create_move_groups

        # Create a WPM job with move_group_ids set to None
        jobs_table = self.dynamodb.Table("wpm_jobs")
        jobs_table.put_item(Item={
            "wpm_job_id": "JOB_NONE",
            "job_name": "Test Job with None move_group_ids",
            "status": "CREATED",
            "move_group_ids": None
        })

        event = {
            "body": json.dumps({
                "app_ids": ["APP001"],
                "wpm_job_id": "JOB_NONE",
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertTrue(len(response_body["move_group_ids"]) == 1)
        
        # Verify WPM job was updated with the move group ID
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB_NONE"})["Item"]
        self.assertIn(response_body["move_group_ids"][0], job["move_group_ids"])

    def test_lambda_handler_single_app2(self):
        """Test lambda_handler with a single app."""
        import lambda_create_move_groups

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ001"},
                            "app_ids": {"L": [{"S": "APP003"}]},
                            "wpm_job_id": {"S": "JOB001"},
                        }
                    },
                }
            ]
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["move_group_request_id"], "REQ001")
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertTrue(len(response_body["move_group_ids"]) == 1)

        # Verify move group creation
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]

        self.assertEqual(move_group["wpm_job_id"], "JOB001")
        self.assertEqual(set(move_group["app_ids"]), set(["APP003", "APP004", "APP007"]))
        self.assertEqual(set(move_group["server_ids"]), set(["SRV005", "SRV006"]))
        self.assertEqual(set(move_group["database_ids"]), set(["DB003"]))
        
        # Verify WPM job was updated with the move group ID
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB001"})["Item"]
        self.assertIn(response_body["move_group_ids"][0], job["move_group_ids"])

         # Verify apps were updated with move_group_ids and wpm_job_ids
        apps_table = self.dynamodb.Table("apps")
        app3 = apps_table.get_item(Key={"app_id": "APP003"})["Item"]
        app4 = apps_table.get_item(Key={"app_id": "APP004"})["Item"]
        self.assertIn(response_body["move_group_ids"][0], app3.get("move_group_ids", []))
        self.assertIn("JOB001", app3.get("wpm_job_ids", []))
        self.assertIn(response_body["move_group_ids"][0], app4.get("move_group_ids", []))
        self.assertIn("JOB001", app4.get("wpm_job_ids", []))
        
        # Verify servers were updated with move_group_id and wpm_job_id
        servers_table = self.dynamodb.Table("servers")
        server5 = servers_table.get_item(Key={"server_id": "SRV005"})["Item"]
        server6 = servers_table.get_item(Key={"server_id": "SRV006"})["Item"]
        self.assertEqual(server5.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(server5.get("wpm_job_id"), "JOB001")
        self.assertEqual(server6.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(server6.get("wpm_job_id"), "JOB001")
        
    def test_lambda_handler_missing_history(self):
        """Test lambda_handler when the _history field is absent."""
        import lambda_create_move_groups

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ002"},
                            "app_ids": {"L": [{"S": "APP008"}]},
                            "wpm_job_id": {"S": "JOB002"},
                            # No _history field
                        }
                    },
                }
            ]
        }

        # Create a new job for this test
        jobs_table = self.dynamodb.Table("wpm_jobs")
        jobs_table.put_item(Item={"wpm_job_id": "JOB002", "move_group_ids": []})

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["move_group_request_id"], "REQ002")
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertTrue(len(response_body["move_group_ids"]) == 1)

        # Verify move group creation
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]

        self.assertEqual(move_group["wpm_job_id"], "JOB002")
        self.assertEqual(set(move_group["app_ids"]), set(["APP008"]))
        
        # Verify _history field was created with default values
        self.assertIn("_history", move_group)

    def test_lambda_handler_empty_app_ids(self):
        """Test lambda_handler rejects empty app_ids."""
        import lambda_create_move_groups

        event = {
            "body": json.dumps({
                "app_ids": [],
                "wpm_job_id": "JOB001"
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("headers", response)
        body = json.loads(response["body"])
        self.assertIn("empty", body["error"].lower())

    def test_lambda_handler_app_ids_not_list(self):
        """Test lambda_handler rejects non-list app_ids."""
        import lambda_create_move_groups

        event = {
            "body": json.dumps({
                "app_ids": "not-a-list",
                "wpm_job_id": "JOB001"
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("headers", response)
        body = json.loads(response["body"])
        self.assertIn("app_ids must be a list", body["error"])

    def test_lambda_handler_app_ids_non_string_elements(self):
        """Test lambda_handler rejects app_ids with non-string elements."""
        import lambda_create_move_groups

        event = {
            "body": json.dumps({
                "app_ids": ["APP001", 123, "APP003"],
                "wpm_job_id": "JOB001"
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("headers", response)
        body = json.loads(response["body"])
        self.assertIn("Item in app_ids must be a string", body["error"])

    def test_lambda_handler_wpm_job_id_not_string(self):
        """Test lambda_handler rejects non-string wpm_job_id."""
        import lambda_create_move_groups

        event = {
            "body": json.dumps({
                "app_ids": ["APP001"],
                "wpm_job_id": 123
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("headers", response)
        body = json.loads(response["body"])
        self.assertIn("must be a string", body["error"])

    def test_lambda_handler_missing_required_fields(self):
        """Test lambda_handler rejects missing required fields."""
        import lambda_create_move_groups

        event = {
            "body": json.dumps({
                "app_ids": ["APP001"]
                # Missing wpm_job_id
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("headers", response)
        body = json.loads(response["body"])
        self.assertIn("Missing required fields", body["error"])

    def test_lambda_handler_invalid_json(self):
        """Test lambda_handler rejects invalid JSON."""
        import lambda_create_move_groups

        event = {
            "body": "invalid-json"
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("headers", response)
        body = json.loads(response["body"])
        self.assertIn("Invalid JSON", body["error"])

    def test_lambda_handler_invalid_event_structure(self):
        """Test lambda_handler rejects invalid event structure."""
        import lambda_create_move_groups

        event = {
            "invalid": "structure"
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("headers", response)
        body = json.loads(response["body"])
        self.assertIn("Invalid event structure", body["error"])

    def test_lambda_handler_empty_apps(self):
        """Test lambda handler with empty app list."""
        import lambda_create_move_groups

        test_event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ002"},
                            "app_ids": {"L": []},
                            "wpm_job_id": {"S": "JOB002"},
                        }
                    },
                }
            ]
        }

        response = lambda_create_move_groups.lambda_handler(test_event, None)
        response_body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response_body["status"], "FAILED")
        self.assertEqual(len(response_body["move_group_ids"]), 0)
        
        # Verify WPM job was not updated since no move groups were created
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB002"})["Item"]
        self.assertEqual(job["move_group_ids"], [])

    def test_lambda_handler_multiple_apps(self):
        """Test lambda_handler with multiple apps."""
        import lambda_create_move_groups

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ003"},
                            "app_ids": {"L": [{"S": "APP001"}, {"S": "APP007"}]},
                            "wpm_job_id": {"S": "JOB003"},
                            "_history": {"M": {"createdBy": {"S": "admin-user@example.com"}}}
                        }
                    },
                }
            ]
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["move_group_request_id"], "REQ003")
        self.assertEqual(response_body["status"], "COMPLETED")

        # Verify move groups were created
        move_groups_table = self.dynamodb.Table("move_groups")

        # There should be at least two move groups
        self.assertEqual(len(response_body["move_group_ids"]), 2)

        move_group_ids = response_body["move_group_ids"]
        move_group_1 = move_groups_table.get_item(
            Key={"move_group_id": move_group_ids[0]}
        )["Item"]

        self.assertEqual(move_group_1["wpm_job_id"], "JOB003")
        self._verify_ulid(move_group_1["move_group_id"])
        self._verify_auto_generated_name(move_group_1["move_group_name"])
        self.assertEqual(set(move_group_1["app_ids"]), set(["APP001", "APP002"]))
        self.assertEqual(
            set(move_group_1["server_ids"]),
            set(["SRV001", "SRV002", "SRV003", "SRV004"]),
        )
        self.assertEqual(set(move_group_1["database_ids"]), set(["DB001", "DB002"]))
        self.assertIn("_history", move_group_1)
        self.assertEqual(move_group_1["_history"]["createdBy"], "admin-user@example.com")
        self.assertIn("createdTimestamp", move_group_1["_history"])

        move_group_2 = move_groups_table.get_item(
            Key={"move_group_id": move_group_ids[1]}
        )["Item"]

        self.assertEqual(move_group_2["wpm_job_id"], "JOB003")
        self._verify_ulid(move_group_2["move_group_id"])
        self._verify_auto_generated_name(move_group_2["move_group_name"])
        self.assertEqual(
            set(move_group_2["app_ids"]), set(["APP003", "APP004", "APP007"])
        )
        self.assertEqual(set(move_group_2["server_ids"]), set(["SRV005", "SRV006"]))
        self.assertEqual(set(move_group_2["database_ids"]), set(["DB003"]))
        self.assertIn("_history", move_group_2)
        self.assertEqual(move_group_2["_history"]["createdBy"], "admin-user@example.com")
        self.assertIn("createdTimestamp", move_group_2["_history"])

        # Verify move group request status
        move_group_requests_table = self.dynamodb.Table("move_group_requests")
        request = move_group_requests_table.get_item(
            Key={"move_group_request_id": "REQ003"}
        ).get("Item")

        if request:
            self.assertEqual(request["status"], "COMPLETED")
            
        # Verify WPM job was updated with both move group IDs
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB003"})["Item"]
        for move_group_id in move_group_ids:
            self.assertIn(move_group_id, job["move_group_ids"])
            
        # Verify apps were updated with move_group_ids and wpm_job_ids
        apps_table = self.dynamodb.Table("apps")
        app_ids = ["APP001", "APP002", "APP003", "APP004", "APP007"]
        
        for app_id in app_ids:
            app = apps_table.get_item(Key={"app_id": app_id})["Item"]
            # Each app should have at least one of the move group IDs
            self.assertTrue(any(mg_id in app.get("move_group_ids", set()) for mg_id in move_group_ids))
            self.assertIn("JOB003", app.get("wpm_job_ids", set()))
            
        # Verify servers were updated with move_group_id and wpm_job_id
        servers_table = self.dynamodb.Table("servers")
        server_ids = ["SRV001", "SRV002", "SRV003", "SRV004", "SRV005", "SRV006"]
        
        for server_id in server_ids:
            server = servers_table.get_item(Key={"server_id": server_id})["Item"]
            # Each server should have a move_group_id that is one of the created move group IDs
            self.assertIn(server.get("move_group_id"), move_group_ids)
            self.assertEqual(server.get("wpm_job_id"), "JOB003")
            
        # Verify databases were updated with move_group_id and wpm_job_id
        databases_table = self.dynamodb.Table("databases")
        db_ids = ["DB001", "DB002"]
        
        for db_id in db_ids:
            db = databases_table.get_item(Key={"database_id": db_id})["Item"]
            # Each database should have a move_group_id that is one of the created move group IDs
            self.assertIn(db.get("move_group_id"), move_group_ids)
            self.assertEqual(db.get("wpm_job_id"), "JOB003")

    def test_metadata_rule_type(self):
        """Test that metadata rule type is respected."""

        rules_table = self.dynamodb.Table("rules")
        rule_item = {
            "rule_type": "GROUPING_INCLUSIVE",
            "rule_id": "2",
            "relationships": [{"asset_key": "department", "asset_type": "app"}],
            "rule_name": "Apps with the same department",
            "status": "ENABLED",
        }
        rules_table.put_item(Item=rule_item)

        # Test the lambda function with the new entity
        import lambda_create_move_groups

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ003"},
                            "app_ids": {
                                "L": [{"S": "APP001"}, {"S": "APP005"}, {"S": "APP010"}]
                            },
                            "wpm_job_id": {"S": "JOB003"},
                        }
                    },
                }
            ]
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertEqual(len(response_body["move_group_ids"]), 3)

        # Verify that the move group was created with the multivalue relationship servers
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group1 = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]
        move_group2 = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][1]}
        )["Item"]
        move_group3 = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][2]}
        )["Item"]

        # APP001 has no department so no app is pulled
        # APP002 is pulled by APP001 because they share the same servers (SRV002)
        self.assertEqual(set(move_group1["app_ids"]), set(["APP001", "APP002"]))
        # APP008 is pulled by APP005 because they are in the same department (IT)
        self.assertEqual(set(move_group2["app_ids"]), set(["APP005", "APP008"]))
        self.assertEqual(
            set(move_group3["app_ids"]),
            # APP007 is pulled by APP010 because they are in the same department (marketing)
            # APP004 is pulled by APP007 because they share the same servers (SRV006)
            # APP003 is pulled by APP004 because they share the same servers (SRV005)
            # APP006 is pulled by APP003 because they are in the same department (sales)
            set(["APP010", "APP007", "APP004", "APP003", "APP006"]),
        )

    def test_exclusive_rule_type(self):
        """Test that exclusive rule type is respected."""

        rules_table = self.dynamodb.Table("rules")
        rule_item = {
            "rule_type": "GROUPING_EXCLUSIVE",
            "rule_id": "2",
            "relationships": [
                {"asset_key": "server_environment", "asset_type": "server"}
            ],
            "rule_name": "Split groups by server environment",
            "status": "ENABLED",
        }
        rules_table.put_item(Item=rule_item)

        # Test the lambda function with the new entity
        import lambda_create_move_groups

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ003"},
                            "app_ids": {"L": [{"S": "APP001"}, {"S": "APP002"}]},
                            "wpm_job_id": {"S": "JOB003"},
                        }
                    },
                }
            ]
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertEqual(len(response_body["move_group_ids"]), 2)

        # Verify that the move group was created with the multivalue relationship servers
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group1 = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]
        move_group2 = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][1]}
        )["Item"]

        if "APP002" in move_group1["app_ids"]:
            move_group_with_prod = move_group1
            move_group_with_dev = move_group2
        else:
            move_group_with_prod = move_group2
            move_group_with_dev = move_group1

        self.assertEqual(
            set(move_group_with_prod["app_ids"]), set(["APP001", "APP002"])
        )
        self.assertEqual(
            set(move_group_with_prod["server_ids"]), set(["SRV002", "SRV003", "SRV004"])
        )
        self.assertEqual(set(move_group_with_dev["app_ids"]), set(["APP001"]))
        self.assertEqual(set(move_group_with_dev["server_ids"]), set(["SRV001"]))
        
    def test_recursive_relationship_traversal(self):
        """Test that relationships are followed recursively."""
        import lambda_create_move_groups
        
        # Add a chain of relationships: APP011 -> SRV008 -> APP012 -> DB004
        apps_table = self.dynamodb.Table("apps")
        apps_table.put_item(Item={"app_id": "APP011", "app_name": "APP011"})
        apps_table.put_item(Item={"app_id": "APP012", "app_name": "APP012"})
        
        servers_table = self.dynamodb.Table("servers")
        servers_table.put_item(Item={
            "server_id": "SRV008",
            "server_name": "SRV008",
            "app_ids": ["APP011", "APP012"],
            "r_type": ["Rehost"]
        })
        
        databases_table = self.dynamodb.Table("databases")
        databases_table.put_item(Item={
            "database_id": "DB004",
            "database_name": "DB004",
            "app_ids": ["APP012"],
            "r_type": ["Rehost"]
        })
        
        event = {
            "Records": [{
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "move_group_request_id": {"S": "REQ004"},
                        "app_ids": {"L": [{"S": "APP011"}]},
                        "wpm_job_id": {"S": "JOB001"},
                    }
                },
            }]
        }
        
        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]
        
        # Verify all related assets are included
        self.assertIn("APP011", move_group["app_ids"])
        self.assertIn("APP012", move_group["app_ids"])
        self.assertIn("SRV008", move_group["server_ids"])
        self.assertIn("DB004", move_group["database_ids"])
        
    def test_move_group_name_uniqueness(self):
        """Test that move group names are unique."""
        import lambda_create_move_groups
        
        # Create first move group
        event1 = {
            "body": json.dumps({
                "app_ids": ["APP005"],
                "wpm_job_id": "JOB001"
            })
        }
        
        response1 = lambda_create_move_groups.lambda_handler(event1, None)
        self.assertEqual(response1["statusCode"], 200)
        
        # Create second move group with same app
        event2 = {
            "body": json.dumps({
                "app_ids": ["APP005"],
                "wpm_job_id": "JOB002"
            })
        }
        
        response2 = lambda_create_move_groups.lambda_handler(event2, None)
        self.assertEqual(response2["statusCode"], 200)
        
        # Verify names are different
        move_groups_table = self.dynamodb.Table("move_groups")
        response1_body = json.loads(response1["body"])
        response2_body = json.loads(response2["body"])
        
        move_group1 = move_groups_table.get_item(
            Key={"move_group_id": response1_body["move_group_ids"][0]}
        )["Item"]
        move_group2 = move_groups_table.get_item(
            Key={"move_group_id": response2_body["move_group_ids"][0]}
        )["Item"]
        
        self.assertNotEqual(move_group1["move_group_name"], move_group2["move_group_name"])
        
    def test_empty_relationships(self):
        """Test handling of assets with no relationships."""
        import lambda_create_move_groups
        
        # Add isolated app
        apps_table = self.dynamodb.Table("apps")
        apps_table.put_item(Item={"app_id": "APP013", "app_name": "APP013"})
        
        event = {
            "body": json.dumps({
                "app_ids": ["APP013"],
                "wpm_job_id": "JOB001"
            })
        }
        
        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]
        
        self.assertEqual(move_group["app_ids"], ["APP013"])
        self.assertEqual(move_group["server_ids"], [])
        self.assertEqual(move_group["database_ids"], [])
        
    def test_complexity_score_calculation(self):
        """Test that complexity scores are calculated correctly."""
        import lambda_create_move_groups
        
        event = {
            "body": json.dumps({
                "app_ids": ["APP001"],
                "wpm_job_id": "JOB001"
            })
        }
        
        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]
        
        # Verify complexity score is calculated (should be >= 0)
        self.assertGreaterEqual(float(move_group["complexity_score"]), 0)
        
    def test_update_wpm_job(self):
        """Test the update_wpm_job method directly."""
        import lambda_create_move_groups
        
        # Create a DynamoDBManager instance
        db_manager = lambda_create_move_groups.DynamoDBManager()
        
        # Test updating a WPM job with a new move group ID
        result = db_manager.update_wpm_job("JOB001", "MG001")
        self.assertTrue(result)
        
        # Verify the WPM job was updated
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB001"})["Item"]
        self.assertIn("MG001", job["move_group_ids"])
        
        # Test updating with the same move group ID again (should not duplicate)
        result = db_manager.update_wpm_job("JOB001", "MG001")
        self.assertTrue(result)
        
        # Verify no duplication occurred
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB001"})["Item"]
        self.assertFalse(isinstance(job["move_group_ids"], set))
        self.assertIsInstance(job["move_group_ids"], list)
        self.assertEqual(job["move_group_ids"].count("MG001"), 1)
        
        # Test updating with a different move group ID
        result = db_manager.update_wpm_job("JOB001", "MG002")
        self.assertTrue(result)
        
        # Verify both move group IDs are in the list
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB001"})["Item"]
        self.assertFalse(isinstance(job["move_group_ids"], set))
        self.assertIsInstance(job["move_group_ids"], list)
        self.assertIn("MG001", job["move_group_ids"])
        self.assertIn("MG002", job["move_group_ids"])
        
        # Test with invalid job ID
        result = db_manager.update_wpm_job("INVALID_JOB", "MG003")
        self.assertFalse(result)
        
        # Test with empty move group ID
        result = db_manager.update_wpm_job("JOB001", "")
        self.assertFalse(result)
        
        # Test with None values
        result = db_manager.update_wpm_job(None, "MG004")
        self.assertFalse(result)
        result = db_manager.update_wpm_job("JOB001", None)
        self.assertFalse(result)
        
    def test_update_assets_with_move_group(self):
        """Test updating assets with move group ID and WPM job ID."""
        import lambda_create_move_groups
        
        # Create a DynamoDBManager instance
        db_manager = lambda_create_move_groups.DynamoDBManager()
        
        # Create a test move group
        move_group = lambda_create_move_groups.MoveGroup(
            move_group_id="MG001",
            move_group_name="Test Move Group",
            wave_id=None,
            wpm_job_id="JOB001",
            server_count=2,
            total_server_storage=100.0,
            complexity_score=5.0,
            app_ids=["APP001", "APP002"],
            server_ids=["SRV001", "SRV002"],
            database_ids=["DB001"]
        )
        
        # Update assets with move group
        result = db_manager.update_assets_with_move_group(move_group)
        self.assertTrue(result)
        
        # Verify apps were updated with move_group_ids and wpm_job_ids
        apps_table = self.dynamodb.Table("apps")
        app1 = apps_table.get_item(Key={"app_id": "APP001"})["Item"]
        app2 = apps_table.get_item(Key={"app_id": "APP002"})["Item"]
        
        self.assertIn("MG001", app1.get("move_group_ids", set()))
        self.assertIn("JOB001", app1.get("wpm_job_ids", set()))
        self.assertIn("MG001", app2.get("move_group_ids", set()))
        self.assertIn("JOB001", app2.get("wpm_job_ids", set()))
        
        # Verify servers were updated with move_group_id and wpm_job_id
        servers_table = self.dynamodb.Table("servers")
        server1 = servers_table.get_item(Key={"server_id": "SRV001"})["Item"]
        server2 = servers_table.get_item(Key={"server_id": "SRV002"})["Item"]
        
        self.assertEqual(server1.get("move_group_id"), "MG001")
        self.assertEqual(server1.get("wpm_job_id"), "JOB001")
        self.assertEqual(server2.get("move_group_id"), "MG001")
        self.assertEqual(server2.get("wpm_job_id"), "JOB001")
        
        # Verify databases were updated with move_group_id and wpm_job_id
        databases_table = self.dynamodb.Table("databases")
        db1 = databases_table.get_item(Key={"database_id": "DB001"})["Item"]
        
        self.assertEqual(db1.get("move_group_id"), "MG001")
        self.assertEqual(db1.get("wpm_job_id"), "JOB001")
        
        # Test with a move group without WPM job ID
        move_group_no_job = lambda_create_move_groups.MoveGroup(
            move_group_id="MG002",
            move_group_name="Test Move Group No Job",
            wave_id=None,
            wpm_job_id=None,
            server_count=1,
            total_server_storage=50.0,
            complexity_score=2.0,
            app_ids=["APP003"],
            server_ids=["SRV003"],
            database_ids=[]
        )
        
        result = db_manager.update_assets_with_move_group(move_group_no_job)
        self.assertTrue(result)
        
        # Verify app was updated with move_group_ids but not wpm_job_ids
        app3 = apps_table.get_item(Key={"app_id": "APP003"})["Item"]
        self.assertIn("MG002", app3.get("move_group_ids", set()))
        
        # Verify server was updated with move_group_id but not wpm_job_id
        server3 = servers_table.get_item(Key={"server_id": "SRV003"})["Item"]
        self.assertEqual(server3.get("move_group_id"), "MG002")

    def test_calculate_storage_metrics(self):
        """Test that storage sizes are correctly aggregated."""
        import lambda_create_move_groups
        from lambda_create_move_groups import Asset

        # Create a set of test assets with different storage size formats
        assets = set()

        # Server with numeric storage size
        assets.add(Asset(
            asset_id="server-SRV001",
            asset_name="SRV001",
            asset_type="server",
            attributes={"server_id": "SRV001", "storage_size": 100}
        ))

        # Server with string storage size
        assets.add(Asset(
            asset_id="server-SRV002",
            asset_name="SRV002",
            asset_type="server",
            attributes={"server_id": "SRV002", "storage_size": "200"}
        ))

        # Server with no storage size
        assets.add(Asset(
            asset_id="server-SRV003",
            asset_name="SRV003",
            asset_type="server",
            attributes={"server_id": "SRV003"}
        ))

        # Server with invalid storage size
        assets.add(Asset(
            asset_id="server-SRV004",
            asset_name="SRV004",
            asset_type="server",
            attributes={"server_id": "SRV004", "storage_size": "invalid"}
        ))
        # Create a DynamoDBManager instance
        db_manager = lambda_create_move_groups.DynamoDBManager()

        # Create a move group manager instance with the db_manager
        move_group_manager = lambda_create_move_groups.MoveGroupManager(db_manager)

        # Calculate storage metrics
        total_storage = move_group_manager.calculate_storage_metrics(assets)

        # Verify the total (should be 100 + 200 = 300)
        self.assertEqual(total_storage, 300.0)

        # Test edge case: all storage sizes are invalid or missing
        invalid_assets = set()
        invalid_assets.add(Asset(
            asset_id="server-SRV005",
            asset_name="SRV005",
            asset_type="server",
            attributes={"server_id": "SRV005"}
        ))
        invalid_assets.add(Asset(
            asset_id="server-SRV006",
            asset_name="SRV006",
            asset_type="server",
            attributes={"server_id": "SRV006", "storage_size": "invalid"}
        ))
        invalid_assets.add(Asset(
            asset_id="app-APP001",
            asset_name="APP001",
            asset_type="app",
            attributes={"app_id": "APP001", "storage_size": 500}
        ))

        # Calculate storage metrics for invalid assets
        total_invalid = move_group_manager.calculate_storage_metrics(invalid_assets)

        # Verify the total is 0 when no valid storage sizes exist
        self.assertEqual(total_invalid, 0.0)

    def test_database_grouping_rule(self):
        """Test that the database grouping rule works correctly."""
        import lambda_create_move_groups
        
        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ005"},
                            "app_ids": {"L": [{"S": "APP001"}]},
                            "wpm_job_id": {"S": "JOB001"},
                        }
                    },
                }
            ]
        }
        
        response = lambda_create_move_groups.lambda_handler(event, None)
        
        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        
        # Get the move group
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]

        self.assertEqual(set(move_group["app_ids"]), set(["APP001", "APP002"]))
        self.assertEqual(set(move_group["database_ids"]), set(["DB001", "DB002"]))
        
        # Verify that the database was updated with move_group_id and wpm_job_id
        databases_table = self.dynamodb.Table("databases")
        for database_id in move_group["database_ids"]:
            db = databases_table.get_item(Key={"database_id": database_id})["Item"]
            self.assertEqual(db.get("move_group_id"), response_body["move_group_ids"][0])
            self.assertEqual(db.get("wpm_job_id"), "JOB001")
        
    def test_lambda_handler_shared_server_apps(self):
        """Test lambda_handler with multiple apps sharing a server where server's app_ids contain all shared apps."""
        import lambda_create_move_groups
        
        # Add a test server with multiple apps in app_ids
        servers_table = self.dynamodb.Table("servers")
        shared_server = {
            "server_id": "SRV007",
            "server_name": "SRV007",
            "server_fqdn": "SRV007.test.com",
            "server_os_family": "Linux",
            "server_environment": "TEST",
            "app_ids": ["APP008", "APP009", "APP010"]
        }
        servers_table.put_item(Item=shared_server)
        
        # Update the apps to reference the shared server
        apps_table = self.dynamodb.Table("apps")
        for app_id in ["APP008", "APP009", "APP010"]:
            app = apps_table.get_item(Key={"app_id": app_id})["Item"]
            server_ids = app.get("server_ids", [])
            if "SRV007" not in server_ids:
                server_ids.append("SRV007")
                app["server_ids"] = server_ids
                apps_table.put_item(Item=app)

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ004"},
                            "app_ids": {"L": [{"S": "APP008"}]},
                            "wpm_job_id": {"S": "JOB002"},
                        }
                    },
                }
            ]
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["move_group_request_id"], "REQ004")
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertEqual(len(response_body["move_group_ids"]), 1)

        # Verify move group creation
        move_groups_table = self.dynamodb.Table("move_groups")
        move_group = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]

        # Verify all apps sharing the server are in the same group
        self.assertEqual(move_group["wpm_job_id"], "JOB002")
        self.assertEqual(set(move_group["app_ids"]), set(["APP008", "APP009", "APP010"]))
        self.assertEqual(set(move_group["server_ids"]), set(["SRV007"]))
        
        # Verify WPM job was updated with the move group ID
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB002"})["Item"]
        self.assertIn(response_body["move_group_ids"][0], job["move_group_ids"])
        
        # Verify all apps were updated with move_group_ids and wpm_job_ids
        for app_id in ["APP008", "APP009", "APP010"]:
            app = apps_table.get_item(Key={"app_id": app_id})["Item"]
            self.assertIn(response_body["move_group_ids"][0], app.get("move_group_ids", set()))
            self.assertIn("JOB002", app.get("wpm_job_ids", set()))
        
        # Verify server was updated with move_group_id and wpm_job_id
        server = servers_table.get_item(Key={"server_id": "SRV007"})["Item"]
        self.assertEqual(server.get("move_group_id"), response_body["move_group_ids"][0])
        self.assertEqual(server.get("wpm_job_id"), "JOB002")
        
        # Verify WPM job was not updated since no move groups were created
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": "JOB002"})["Item"]
        self.assertEqual(job["move_group_ids"], response_body["move_group_ids"])

    def test_invalid_wpm_job_id(self):
        """Test handling of invalid WPM job ID."""
        import lambda_create_move_groups
        
        event = {
            "body": json.dumps({
                "app_ids": ["APP001"],
                "wpm_job_id": "INVALID_JOB"
            })
        }
        
        response = lambda_create_move_groups.lambda_handler(event, None)
        
        # Should still create move group but WPM job update will fail silently
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        

        
    def _verify_ulid(self, ulid_string):
        """Verify that a string is a valid ULID."""
        from ulid import ULID
        try:
            ULID.parse(ulid_string)
        except ValueError:
            self.fail(f"'{ulid_string}' is not a valid ULID")
    
    def _verify_auto_generated_name(self, move_group_name):
        """Verify that the auto-generated name follows timestamp format with milliseconds and random string."""
        # The name should follow the format "Move Group YYYYMMDD-HHMMSS###-xxxxxx"
        self.assertIsInstance(move_group_name, str)
        self.assertTrue(move_group_name.startswith("Move Group "))
        # Verify it contains a timestamp-like pattern with milliseconds and random string
        import re
        pattern = r"Move Group \d{8}-\d{6}\.\d{3}-[a-z0-9]{4}"
        self.assertTrue(re.match(pattern, move_group_name), f"Name '{move_group_name}' doesn't match expected pattern")
    
    def tearDown(self):
        """Clean up test environment."""
        tables = [
            "apps",
            "servers",
            "databases",
            "rules",
            "schema",
            "move_groups",
            "move_group_requests",
            "jobs",
            "custom_assets",
        ]
        for table_name in tables:
            try:
                table = self.dynamodb.Table(table_name)
                table.delete()
            except Exception:
                continue


    def test_custom_asset_inclusive_rule_with_custom_asset_relationship(self):
        """Test that apps are grouped together when their storage custom assets have the same name."""
        
        # Create custom assets table if it doesn't exist
        self._create_custom_asset_table()
        
        # Add custom assets of type 'storage'
        custom_assets_table = self.dynamodb.Table("custom_assets")

        # Storage asset 1 - linked to APP001 and APP003
        custom_assets_table.put_item(Item={
            "asset_type#shard": "storage#1",
            "asset_id": "STORAGE001",
            "storage_name": "SharedStorage1",  # This is the name
            "storage_type": "NAS",
            "app_ids": ["APP001", "APP003"],
            "complexity_score": 2
        })
        
        # Storage asset 2 - linked to APP005, different name
        custom_assets_table.put_item(Item={
            "asset_type#shard": "storage#1",
            "asset_id": "STORAGE003",
            "storage_name": "DifferentStorage",  # Different name
            "storage_type": "SAN",
            "app_ids": ["APP005"],
            "complexity_score": 3
        })
        
        # Create a rule to group apps by storage name
        rules_table = self.dynamodb.Table("rules")
        rule_item = {
            "rule_type": "GROUPING_INCLUSIVE",
            "rule_id": "4",
            "relationships": [{
                "asset_key": "storage_name",
                "asset_type": "storage"
            }],
            "rule_name": "Apps with the same storage name",
            "status": "ENABLED"
        }
        rules_table.put_item(Item=rule_item)
        
        # Add database relationships to APP001 and APP003
        apps_table = self.dynamodb.Table("apps")
        app1 = apps_table.get_item(Key={"app_id": "APP001"})["Item"]
        app1["database_ids"] = ["DB001"]
        apps_table.put_item(Item=app1)
        
        app3 = apps_table.get_item(Key={"app_id": "APP003"})["Item"]
        app3["database_ids"] = ["DB003"]
        apps_table.put_item(Item=app3)
        
        # Import the lambda function
        import lambda_create_move_groups
        
        # Create the test event
        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ004"},
                            "app_ids": {"L": [{"S": "APP001"}, {"S": "APP003"}, {"S": "APP005"}]},
                            "wpm_job_id": {"S": "JOB004"},
                            "_history": {"M": {"createdBy": {"S": "test-user"}}}
                        }
                    }
                }
            ]
        }
        
        # Execute the lambda function
        response = lambda_create_move_groups.lambda_handler(event, None)
        
        # Verify response
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertEqual(len(response_body["move_group_ids"]), 2)  # Should create 2 groups
        
        # Verify the move groups
        move_groups_table = self.dynamodb.Table("move_groups")

        # Find which group contains which apps
        move_group1 = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][0]}
        )["Item"]

        move_group2 = move_groups_table.get_item(
            Key={"move_group_id": response_body["move_group_ids"][1]}
        )["Item"]

        # Determine which group is which based on content
        if "APP001" in move_group1["app_ids"] and "APP003" in move_group1["app_ids"]:
            shared_storage_group = move_group1
            different_storage_group = move_group2
        else:
            shared_storage_group = move_group2
            different_storage_group = move_group1
        
        # Verify that APP001 and APP003 are grouped together due to shared storage name
        self.assertIn("APP001", shared_storage_group["app_ids"])
        self.assertIn("APP003", shared_storage_group["app_ids"])
        # Verify database IDs are included
        self.assertIn("DB001", shared_storage_group["database_ids"])
        self.assertIn("DB003", shared_storage_group["database_ids"])
        
        # Verify that APP005 is in a separate group
        self.assertIn("APP005", different_storage_group["app_ids"])

    def test_custom_asset_inclusive_rule_with_custom_asset_schema_created(self):
        """Test that apps are grouped together when their storage custom assets have 
        the same storage_name when a schema for the storage custom asset exists"""
        
        # Add storage schema to schema table
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
        
        self.test_custom_asset_inclusive_rule_with_custom_asset_relationship()
        
    def test_custom_asset_inclusive_rule_with_app_relationship(self):
        app_schema = self.schema_table.get_item(Key={"schema_name": "app"})["Item"]
        app_schema["attributes"].append({
            "description": "Related Resource Groups",
            "listMultiSelect": True,
            "name": "resource_group_ids",
            "rel_display_attribute": "resource_group_name",
            "rel_entity": "resource_group",
            "rel_key": "resource_group_id",
            "type": "multivalue-relationship"
        })
        
        self.schema_table.put_item(Item=app_schema)
        
        self.schema_table.put_item(
            Item={
                "schema_name": "resource_group",
                "attributes": [
                    {
                        "description": "Resource Group Id",
                        "name": "resource_group_id",
                        "type": "string",
                    },
                    {
                        "description": "Related Applications",
                        "listMultiSelect": True,
                        "name": "app_ids",
                        "rel_display_attribute": "app_name",
                        "rel_entity": "app",
                        "rel_key": "app_id",
                        "type": "multivalue-relationship",
                    },
                    {
                        "description": "Resource Group Name",
                        "name": "resource_group_name",
                        "type": "string",
                    },
                    {"description": "Custom Attribute 1", "name": "custom_attribute_1", "type": "string"},
                ],
                "key_type": "ulid",
                "lastModifiedTimestamp": "2025-09-25T03:55:07.061470+00:00",
                "schema_type": "custom",
            }
        )

        self._create_custom_asset_table()

        apps_table = self.dynamodb.Table("apps")
        custom_assets_table = self.dynamodb.Table("custom_assets")

        for app in [
            {
                "app_id": "app1",
                "app_name": "app1",
                "resource_group_ids": ["ulid1"],
            },
            {
                "app_id": "app2",
                "app_name": "app2",
            },
            {
                "app_id": "app3",
                "app_name": "app3",
                "resource_group_ids": ["ulid1"],
            },
        ]:
            apps_table.put_item(Item=app)

        custom_assets_table.put_item(
            Item={
                "asset_type#shard": "resource_group#2",
                "asset_id": "ulid1",
                "resource_group_name": "Resource group shared by app1 and app3",  # This is the name
                "other_attribute": "whatever",
                "app_ids": ["app1", "app3"],
            }
        )

        # Create a rule to group apps by resource_group_ids
        rules_table = self.dynamodb.Table("rules")
        rule_item = {
            "rule_id": "11",
            "rule_name": "Group apps based on shared resource groups",
            "relationships": [{"asset_type": "app", "asset_key": "resource_group_ids"}],
            "rule_type": "GROUPING_INCLUSIVE",
            "status": "ENABLED",
        }
        rules_table.put_item(Item=rule_item)

        import lambda_create_move_groups

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "move_group_request_id": {"S": "REQ004"},
                            "app_ids": {"L": [{"S": "app1"}, {"S": "app2"}, {"S": "app3"}]},
                            "wpm_job_id": {"S": "JOB004"},
                            "_history": {"M": {"createdBy": {"S": "test-user"}}},
                        }
                    },
                }
            ]
        }

        response = lambda_create_move_groups.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertEqual(response_body["status"], "COMPLETED")
        self.assertEqual(len(response_body["move_group_ids"]), 2)  # Should create 2 groups

        move_groups_table = self.dynamodb.Table("move_groups")

        move_group1 = move_groups_table.get_item(Key={"move_group_id": response_body["move_group_ids"][0]})["Item"]

        move_group2 = move_groups_table.get_item(Key={"move_group_id": response_body["move_group_ids"][1]})["Item"]

        if "app1" in move_group1["app_ids"] and "app3" in move_group1["app_ids"]:
            shared_resource_group = move_group1
            another_group = move_group2
        else:
            shared_resource_group = move_group2
            another_group = move_group1

        self.assertEqual(sorted(shared_resource_group["app_ids"]), ["app1", "app3"])
        self.assertEqual(another_group["app_ids"], ["app2"])

    def test_server_already_in_move_group_blocks_creation(self):
        """Test that creating a move group fails if a server is already assigned."""
        import lambda_create_move_groups
        
        # First, create a move group with APP001
        event1 = {"body": json.dumps({"app_ids": ["APP001"], "wpm_job_id": "JOB001"})}
        response1 = lambda_create_move_groups.lambda_handler(event1, None)
        self.assertEqual(response1["statusCode"], 200)
        
        # Try to create another move group that would include the same server
        event2 = {"body": json.dumps({"app_ids": ["APP002"], "wpm_job_id": "JOB002"})}
        response2 = lambda_create_move_groups.lambda_handler(event2, None)
        
        # Should fail with 500 error due to server conflict
        self.assertEqual(response2["statusCode"], 500)
        response_body = json.loads(response2["body"])
        self.assertIn("Server", response_body["error"])
        self.assertIn("already assigned", response_body["error"])
        
    def test_database_already_in_move_group_blocks_creation(self):
        """Test that creating a move group fails if a database is already assigned."""
        import lambda_create_move_groups
        
        # Add isolated apps with only database relationships (no servers)
        apps_table = self.dynamodb.Table("apps")
        apps_table.put_item(Item={"app_id": "APP019", "app_name": "APP019", "database_ids": ["DB019"]})
        apps_table.put_item(Item={"app_id": "APP020", "app_name": "APP020", "database_ids": ["DB019"]})
        
        databases_table = self.dynamodb.Table("databases")
        databases_table.put_item(Item={
            "database_id": "DB019", "database_name": "DB019",
            "app_ids": ["APP019", "APP020"], "r_type": ["Rehost"]
        })
        
        # First, create a move group with APP019
        event1 = {"body": json.dumps({"app_ids": ["APP019"], "wpm_job_id": "JOB001"})}
        response1 = lambda_create_move_groups.lambda_handler(event1, None)
        self.assertEqual(response1["statusCode"], 200)
        
        # Try to create another move group that would include the same database
        event2 = {"body": json.dumps({"app_ids": ["APP020"], "wpm_job_id": "JOB002"})}
        response2 = lambda_create_move_groups.lambda_handler(event2, None)
        
        # Should fail with 500 error due to database conflict
        self.assertEqual(response2["statusCode"], 500)
        response_body = json.loads(response2["body"])
        self.assertIn("Database", response_body["error"])
        self.assertIn("already assigned", response_body["error"])
        
    def test_isolated_apps_no_conflict(self):
        """Test that apps with no shared resources can be in separate move groups."""
        import lambda_create_move_groups
        
        # Add isolated apps and resources
        apps_table = self.dynamodb.Table("apps")
        apps_table.put_item(Item={"app_id": "APP015", "app_name": "APP015"})
        apps_table.put_item(Item={"app_id": "APP016", "app_name": "APP016"})
        
        servers_table = self.dynamodb.Table("servers")
        servers_table.put_item(Item={
            "server_id": "SRV015", "server_name": "SRV015",
            "app_ids": ["APP015"], "r_type": ["Rehost"]
        })
        servers_table.put_item(Item={
            "server_id": "SRV016", "server_name": "SRV016", 
            "app_ids": ["APP016"], "r_type": ["Rehost"]
        })
        
        # Create first move group
        event1 = {"body": json.dumps({"app_ids": ["APP015"], "wpm_job_id": "JOB001"})}
        response1 = lambda_create_move_groups.lambda_handler(event1, None)
        self.assertEqual(response1["statusCode"], 200)
        
        # Create second move group with different resources - should succeed
        event2 = {"body": json.dumps({"app_ids": ["APP016"], "wpm_job_id": "JOB002"})}
        response2 = lambda_create_move_groups.lambda_handler(event2, None)
        self.assertEqual(response2["statusCode"], 200)
        
        # Verify both move groups were created
        response1_body = json.loads(response1["body"])
        response2_body = json.loads(response2["body"])
        self.assertEqual(len(response1_body["move_group_ids"]), 1)
        self.assertEqual(len(response2_body["move_group_ids"]), 1)
        self.assertNotEqual(response1_body["move_group_ids"][0], response2_body["move_group_ids"][0])

    def test_lambda_handler_invalid_app_id_format(self):
        """Test lambda_handler with invalid app_id format (special characters)."""
        import lambda_create_move_groups

        event = {
            "body": json.dumps({
                "app_ids": ["APP001", "APP@002#"],  # Contains @ and # which are not allowed
                "wpm_job_id": "JOB001"
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)
        self.assertIn("alphanumeric characters, dashes, and underscores", error_response["error"])

    def test_lambda_handler_duplicate_app_ids(self):
        """Test lambda_handler with duplicate app IDs."""
        import lambda_create_move_groups

        event = {
            "body": json.dumps({
                "app_ids": ["APP001", "APP002", "APP001"],  # APP001 is duplicated
                "wpm_job_id": "JOB001"
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)
        self.assertIn("Duplicate app_ids not allowed", error_response["error"])


    def test_lambda_handler_app_ids_at_limit(self):
        """Test lambda_handler with exactly 100 app_ids (at the limit)."""
        import lambda_create_move_groups

        # Create exactly 100 app IDs
        app_ids = [f"APP{i:03d}" for i in range(1, 101)]
        
        event = {
            "body": json.dumps({
                "app_ids": app_ids,
                "wpm_job_id": "JOB001"
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        # Should be accepted (200 status)
        self.assertEqual(response["statusCode"], 200)
        response_body = json.loads(response["body"])
        self.assertIn("status", response_body)

    def test_lambda_handler_app_ids_exceeds_limit(self):
        """Test lambda_handler with 101 app_ids (exceeding the limit)."""
        import lambda_create_move_groups

        # Create 101 app IDs (exceeds limit of 100)
        app_ids = [f"APP{i:03d}" for i in range(1, 102)]
        
        event = {
            "body": json.dumps({
                "app_ids": app_ids,
                "wpm_job_id": "JOB001"
            })
        }

        response = lambda_create_move_groups.lambda_handler(event, None)
        
        # Should be rejected (400 status)
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)
        self.assertIn("Too many app_ids. Maximum allowed is 100", error_response["error"])
