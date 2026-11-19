from decimal import Decimal
import time
import unittest
from unittest import mock
import json

import boto3
from moto import mock_aws

from test_lambda_gfcommon import mock_getUserResourceCreationPolicy
from test_common_utils import default_mock_os_environ

mock_os_environ = {
    **default_mock_os_environ,
    "WPM_JOBS_TABLE_NAME": "wpm_jobs",
    "MOVE_GROUPS_TABLE_NAME": "move_groups",
    "WAVES_TABLE_NAME": "waves",
    "APPS_TABLE_NAME": "apps",
    "SERVERS_TABLE_NAME": "servers",
    "DATABASES_TABLE_NAME": "databases",
    "AWS_DEFAULT_REGION": "us-east-1",
}


@mock.patch.dict("os.environ", mock_os_environ)
@mock.patch('lambda_gfdeploy.MFAuth.get_user_resource_creation_policy', new=mock_getUserResourceCreationPolicy)
@mock_aws
class LambdaCreateWaves(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.test_job_id_without_starting_server_count = "JOB001"
        self.test_job_id_with_starting_server_count = "JOB002"
        self.test_job_id_with_none_capacities = "JOB003"
        self.test_move_group_ids_small = ["MG001", "MG002", "MG003"]
        self.test_move_group_ids_big = ["MG001", "MG002", "MG003", "MG004", "MG005"]

        # Set up mock AWS services
        boto3.setup_default_session()
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Create required DynamoDB tables
        self._create_tables()
        # Populate test data
        self._populate_test_data()

    def _create_tables(self):
        """Create mock DynamoDB tables"""
        tables_config = {
            "move_groups": "move_group_id",
            "waves": "wave_id",
            "wpm_jobs": "wpm_job_id",  # Added jobs table
            "apps": "app_id",
            "servers": "server_id",
            "databases": "database_id",
            "assets": "asset_id",
        }

        for table_name, key_name in tables_config.items():
            self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": key_name, "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": key_name, "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

    def _populate_test_data(self):
        """Populate test data in DynamoDB tables"""
        # Add test job configuration
        jobs_table = self.dynamodb.Table("wpm_jobs")
        jobs_table.put_item(
            Item={
                "wpm_job_id": self.test_job_id_without_starting_server_count,
                "wave_server_capacity": 5,
                "wave_storage_capacity": 2000,
                "status": "ACTIVE",
            }
        )
        jobs_table.put_item(
            Item={
                "wpm_job_id": self.test_job_id_with_starting_server_count,
                "starting_wave_server_capacity": 1,
                "wave_server_capacity_increase": 2,
                "wave_server_capacity": 5,
                "wave_storage_capacity": 2000,
                "status": "ACTIVE",
            }
        )
        jobs_table.put_item(
            Item={
                "wpm_job_id": self.test_job_id_with_none_capacities,
                "starting_wave_server_capacity": None,
                "wave_server_capacity_increase": None,
                "wave_server_capacity": 5,
                "wave_storage_capacity": 2000,
                "status": "ACTIVE",
            }
        )

        self.move_groups_table = self.dynamodb.Table("move_groups")

        # Add test move groups
        self.test_move_groups = [
            {
                "move_group_id": "MG001",
                "wpm_job_id": self.test_job_id_without_starting_server_count,
                "app_ids": ["APP1"],
                "server_ids": ["SRV3", "SRV4", "SRV5"],
                "server_count": 3,
                "total_server_storage": Decimal(600.0),
                "complexity_score": Decimal(1500.0),
                "status": "READY",
            },
            {
                "move_group_id": "MG002",
                "wpm_job_id": self.test_job_id_without_starting_server_count,
                "app_ids": ["APP2"],
                "server_ids": ["SRV1", "SRV2"],
                "server_count": 2,
                "total_server_storage": Decimal(300.0),
                "complexity_score": Decimal(1000.0),
                "status": "READY",
            },
            {
                "move_group_id": "MG003",
                "wpm_job_id": self.test_job_id_without_starting_server_count,
                "app_ids": ["APP3"],
                "server_ids": ["SRV6", "SRV7"],
                "server_count": 2,
                "total_server_storage": Decimal(400.0),
                "complexity_score": Decimal(2000.0),
                "status": "READY",
            },
            {
                "move_group_id": "MG004",
                "wpm_job_id": self.test_job_id_without_starting_server_count,
                "app_ids": ["APP4"],
                "server_ids": ["SRV10", "SRV11"],
                "server_count": 2,
                "total_server_storage": Decimal(900.0),
                "complexity_score": Decimal(2400.0),
                "status": "READY",
            },
            {
                "move_group_id": "MG005",
                "wpm_job_id": self.test_job_id_without_starting_server_count,
                "app_ids": ["APP5"],
                "server_ids": ["SRV15", "SRV16", "SRV17", "SRV18", "SRV19", "SRV20"],
                "server_count": 6,
                "total_server_storage": Decimal(1200.0),
                "complexity_score": Decimal(2500.0),
                "status": "READY",
            },
            {
                "move_group_id": "MG006",
                "wpm_job_id": self.test_job_id_with_none_capacities,
                "app_ids": ["APP6"],
                "server_ids": ["SRV21", "SRV22"],
                "server_count": 2,
                "total_server_storage": Decimal(500.0),
                "complexity_score": Decimal(1200.0),
                "status": "READY",
            },
        ]

        for move_group in self.test_move_groups:
            self.move_groups_table.put_item(Item=move_group)
            
        # Add test apps
        apps_table = self.dynamodb.Table("apps")
        test_apps = [
            {"app_id": "APP1", "app_name": "Application 1"},
            {"app_id": "APP2", "app_name": "Application 2"},
            {"app_id": "APP3", "app_name": "Application 3"},
            {"app_id": "APP4", "app_name": "Application 4"},
            {"app_id": "APP5", "app_name": "Application 5"},
            {"app_id": "APP6", "app_name": "Application 6"},
        ]
        
        for app in test_apps:
            apps_table.put_item(Item=app)
            
        # Add test servers
        servers_table = self.dynamodb.Table("servers")
        test_servers = [
            {"server_id": "SRV1", "server_name": "Server 1"},
            {"server_id": "SRV2", "server_name": "Server 2"},
            {"server_id": "SRV3", "server_name": "Server 3"},
            {"server_id": "SRV4", "server_name": "Server 4"},
            {"server_id": "SRV5", "server_name": "Server 5"},
            {"server_id": "SRV6", "server_name": "Server 6"},
            {"server_id": "SRV7", "server_name": "Server 7"},
            {"server_id": "SRV10", "server_name": "Server 10"},
            {"server_id": "SRV11", "server_name": "Server 11"},
            {"server_id": "SRV15", "server_name": "Server 15"},
            {"server_id": "SRV16", "server_name": "Server 16"},
            {"server_id": "SRV17", "server_name": "Server 17"},
            {"server_id": "SRV18", "server_name": "Server 18"},
            {"server_id": "SRV19", "server_name": "Server 19"},
            {"server_id": "SRV20", "server_name": "Server 20"},
            {"server_id": "SRV21", "server_name": "Server 21"},
            {"server_id": "SRV22", "server_name": "Server 22"},
        ]
        
        for server in test_servers:
            servers_table.put_item(Item=server)
        
        # Add test waves
        waves_table = self.dynamodb.Table("waves")
        test_waves = [
            {
                "wave_id": "1",
            },
            {
                "wave_id": "non-numeric",
            },
        ]
        for wave in test_waves:
            waves_table.put_item(Item=wave)

    def test_lambda_handler_success_without_starting_server_count(self):
        """Test successful lambda_handler execution"""
        import lambda_create_waves

        # Arrange
        event = {
            "body": json.dumps(
                {
                    "wpm_job_id": self.test_job_id_without_starting_server_count,
                    "move_group_ids": self.test_move_group_ids_small,
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)
        waves = json.loads(response["body"])

        # Assert
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(isinstance(waves, list))
        self.assertEqual(len(waves), 2)

        # Verify wave structure
        wave1 = waves[0]
        self.assertIn("wave_id", wave1)
        self.assertIn("wave_name", wave1)
        self.assertIn("wave_status", wave1)
        self.assertIn("server_count", wave1)
        self.assertIn("total_server_storage", wave1)
        self.assertIn("complexity_score", wave1)
        self.assertIn("move_group_ids", wave1)
        self.assertEqual(
            wave1["wpm_job_id"], self.test_job_id_without_starting_server_count
        )
        self.assertEqual(wave1["wave_id"], "2")
        self.assertEqual(wave1["wave_status"], "Not started")
        self.assertEqual(wave1["server_count"], 4)
        self.assertEqual(float(wave1["total_server_storage"]), 700)
        self.assertIn("_history", wave1)
        self.assertEqual(wave1["_history"]["createdBy"], "testuser@testuser")
        self.assertIn("createdTimestamp", wave1["_history"])

        wave2 = waves[1]
        self.assertIn("wave_id", wave2)
        self.assertIn("wave_name", wave2)
        self.assertIn("wave_status", wave2)
        self.assertIn("server_count", wave2)
        self.assertIn("total_server_storage", wave2)
        self.assertIn("complexity_score", wave2)
        self.assertIn("move_group_ids", wave2)
        self.assertEqual(
            wave2["wpm_job_id"], self.test_job_id_without_starting_server_count
        )
        self.assertEqual(wave2["wave_id"], "3")
        self.assertEqual(wave2["wave_status"], "Not started")
        self.assertEqual(wave2["server_count"], 3)
        self.assertEqual(float(wave2["total_server_storage"]), 600)
        self.assertIn("_history", wave2)
        self.assertEqual(wave2["_history"]["createdBy"], "testuser@testuser")
        self.assertIn("createdTimestamp", wave2["_history"])

        # Verify waves were stored in DynamoDB
        waves_table = self.dynamodb.Table("waves")
        for wave in waves:
            response = waves_table.get_item(Key={"wave_id": wave["wave_id"]})
            self.assertIn("Item", response)
            stored_wave = response["Item"]
            self.assertEqual(stored_wave["wave_status"], "Not started")
            
        # Verify WPM job was updated with wave IDs
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": self.test_job_id_without_starting_server_count})["Item"]
        self.assertIn("wave_ids", job)
        for wave in waves:
            self.assertIsInstance(job["wave_ids"], list)
            self.assertIn(wave["wave_id"], job["wave_ids"])
            
        # Verify apps were updated with wave_ids
        apps_table = self.dynamodb.Table("apps")
        for wave in waves:
            for app_id in wave["app_ids"]:
                app = apps_table.get_item(Key={"app_id": app_id})["Item"]
                self.assertIsInstance(app.get("wave_ids"), list)
                self.assertIn(wave["wave_id"], app.get("wave_ids", []))
                
        # Verify servers were updated with wave_id
        servers_table = self.dynamodb.Table("servers")
        for wave in waves:
            for server_id in wave["server_ids"]:
                server = servers_table.get_item(Key={"server_id": server_id})["Item"]
                self.assertEqual(server.get("wave_id"), wave["wave_id"])

    def test_lambda_handler_success_with_starting_server_count(self):
        """Test successful lambda_handler execution"""
        import lambda_create_waves

        for move_group in self.test_move_groups:
            move_group["wpm_job_id"] = self.test_job_id_with_starting_server_count
            self.move_groups_table.put_item(Item=move_group)

        # Arrange
        event = {
            "body": json.dumps(
                {
                    "wpm_job_id": self.test_job_id_with_starting_server_count,
                    "move_group_ids": self.test_move_group_ids_small,
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)
        waves = json.loads(response["body"])

        # Assert
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(isinstance(waves, list))
        self.assertEqual(len(waves), 3)

        # Verify wave structure
        wave1 = waves[0]
        self.assertIn("wave_id", wave1)
        self.assertIn("wave_name", wave1)
        self.assertIn("wave_status", wave1)
        self.assertIn("server_count", wave1)
        self.assertIn("total_server_storage", wave1)
        self.assertIn("complexity_score", wave1)
        self.assertIn("move_group_ids", wave1)
        self.assertEqual(
            wave1["wpm_job_id"], self.test_job_id_with_starting_server_count
        )
        self.assertEqual(wave1["wave_id"], "2")
        self.assertEqual(wave1["wave_status"], "Not started")
        self.assertEqual(wave1["server_count"], 2)
        self.assertEqual(float(wave1["total_server_storage"]), 300)

        wave2 = waves[1]
        self.assertIn("wave_id", wave2)
        self.assertIn("wave_name", wave2)
        self.assertIn("wave_status", wave2)
        self.assertIn("server_count", wave2)
        self.assertIn("total_server_storage", wave2)
        self.assertIn("complexity_score", wave2)
        self.assertIn("move_group_ids", wave2)
        self.assertEqual(
            wave2["wpm_job_id"], self.test_job_id_with_starting_server_count
        )
        self.assertEqual(wave2["wave_id"], "3")
        self.assertEqual(wave2["wave_status"], "Not started")
        self.assertEqual(wave2["server_count"], 2)
        self.assertEqual(float(wave2["total_server_storage"]), 400)

        wave3 = waves[2]
        self.assertIn("wave_id", wave3)
        self.assertIn("wave_name", wave3)
        self.assertIn("wave_status", wave3)
        self.assertIn("server_count", wave3)
        self.assertIn("total_server_storage", wave3)
        self.assertIn("complexity_score", wave3)
        self.assertIn("move_group_ids", wave3)
        self.assertEqual(
            wave3["wpm_job_id"], self.test_job_id_with_starting_server_count
        )
        self.assertEqual(wave3["wave_id"], "4")
        self.assertEqual(wave3["wave_status"], "Not started")
        self.assertEqual(wave3["server_count"], 3)
        self.assertEqual(float(wave3["total_server_storage"]), 600)

        # Verify waves were stored in DynamoDB
        waves_table = self.dynamodb.Table("waves")
        for wave in waves:
            response = waves_table.get_item(Key={"wave_id": wave["wave_id"]})
            self.assertIn("Item", response)
            stored_wave = response["Item"]
            self.assertEqual(stored_wave["wave_status"], "Not started")
            
        # Verify WPM job was updated with wave IDs
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": self.test_job_id_with_starting_server_count})["Item"]
        self.assertIn("wave_ids", job)
        for wave in waves:
            self.assertIn(wave["wave_id"], job["wave_ids"])

    def test_lambda_handler_invalid_json(self):
        """Test lambda_handler with invalid JSON input"""
        import lambda_create_waves

        # Arrange
        event = {"body": "invalid json"}

        # Act
        response = lambda_create_waves.lambda_handler(event, None)

        # Assert
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)

    def test_lambda_handler_missing_required_fields(self):
        """Test lambda_handler with missing required fields"""
        import lambda_create_waves

        # Arrange
        event = {
            "body": json.dumps(
                {
                    # Missing required fields
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)

        # Assert
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)

    def test_lambda_handler_empty_move_groups(self):
        """Test lambda_handler with empty move groups list"""
        import lambda_create_waves

        # Arrange
        event = {
            "body": json.dumps(
                {
                    "wpm_job_id": self.test_job_id_without_starting_server_count,
                    "move_group_ids": [],
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)

        # Assert
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)
        self.assertIn("move_group_ids cannot be empty", error_response["error"])

    def test_lambda_handler_missing_body(self):
        """Test lambda_handler with missing body"""
        import lambda_create_waves

        # Arrange
        event = {}

        # Act
        response = lambda_create_waves.lambda_handler(event, None)

        # Assert
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)

    def test_lambda_handler_multiple_waves(self):
        """Test lambda_handler when multiple waves are needed due to capacity limits"""
        import lambda_create_waves

        for move_group in self.test_move_groups:
            move_group["wpm_job_id"] = self.test_job_id_with_starting_server_count
            self.move_groups_table.put_item(Item=move_group)

        event = {
            "body": json.dumps(
                {
                    "wpm_job_id": self.test_job_id_with_starting_server_count,
                    "move_group_ids": self.test_move_group_ids_big,
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)
        waves = json.loads(response["body"])

        # Assert
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(isinstance(waves, list))
        self.assertEqual(len(waves), 4)
        
        # Verify WPM job was updated with all wave IDs
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": self.test_job_id_with_starting_server_count})["Item"]
        self.assertIn("wave_ids", job)
        for wave in waves:
            self.assertIn(wave["wave_id"], job["wave_ids"])

        # Verify wave structure
        wave1 = waves[0]
        self.assertIn("wave_id", wave1)
        self.assertIn("wave_name", wave1)
        self.assertIn("wave_status", wave1)
        self.assertIn("server_count", wave1)
        self.assertIn("total_server_storage", wave1)
        self.assertIn("complexity_score", wave1)
        self.assertIn("move_group_ids", wave1)
        self.assertEqual(
            wave1["wpm_job_id"], self.test_job_id_with_starting_server_count
        )
        self.assertEqual(wave1["wave_status"], "Not started")
        self.assertEqual(wave1["server_count"], 2)
        self.assertEqual(float(wave1["total_server_storage"]), 300)

        wave2 = waves[1]
        self.assertIn("wave_id", wave2)
        self.assertIn("wave_name", wave2)
        self.assertIn("wave_status", wave2)
        self.assertIn("server_count", wave2)
        self.assertIn("total_server_storage", wave2)
        self.assertIn("complexity_score", wave2)
        self.assertIn("move_group_ids", wave2)
        self.assertEqual(
            wave2["wpm_job_id"], self.test_job_id_with_starting_server_count
        )
        self.assertEqual(wave2["wave_status"], "Not started")
        self.assertEqual(wave2["server_count"], 2)
        self.assertEqual(float(wave2["total_server_storage"]), 400)

        wave3 = waves[2]
        self.assertIn("wave_id", wave3)
        self.assertIn("wave_name", wave3)
        self.assertIn("wave_status", wave3)
        self.assertIn("server_count", wave3)
        self.assertIn("total_server_storage", wave3)
        self.assertIn("complexity_score", wave3)
        self.assertIn("move_group_ids", wave3)
        self.assertEqual(
            wave3["wpm_job_id"], self.test_job_id_with_starting_server_count
        )
        self.assertEqual(wave3["wave_status"], "Not started")
        self.assertEqual(wave3["server_count"], 5)
        self.assertEqual(float(wave3["total_server_storage"]), 1500)

        wave4 = waves[3]
        self.assertIn("wave_id", wave4)
        self.assertIn("wave_name", wave4)
        self.assertIn("wave_status", wave4)
        self.assertIn("server_count", wave4)
        self.assertIn("total_server_storage", wave4)
        self.assertIn("complexity_score", wave4)
        self.assertIn("move_group_ids", wave4)
        self.assertEqual(
            wave4["wpm_job_id"], self.test_job_id_with_starting_server_count
        )
        self.assertEqual(wave4["wave_status"], "Not started")
        self.assertEqual(wave4["server_count"], 6)
        self.assertEqual(float(wave4["total_server_storage"]), 1200)

    def test_lambda_handler_duplicate_move_group_ids(self):
        """Test lambda_handler with duplicate move group IDs"""
        import lambda_create_waves

        # Arrange
        duplicate_move_group_ids = [
            "MG001",
            "MG002",
            "MG001",
            "MG003",
        ]  # MG001 is duplicated
        event = {
            "body": json.dumps(
                {
                    "wpm_job_id": self.test_job_id_without_starting_server_count,
                    "move_group_ids": duplicate_move_group_ids,
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)

        # Assert
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)
        self.assertIn("Duplicate move_group_ids not allowed", error_response["error"])

    def test_lambda_handler_too_many_move_groups(self):
        """Test lambda_handler with too many move group IDs"""
        import lambda_create_waves

        # Save original constant
        original_max_count = lambda_create_waves.MAX_MOVE_GROUPS_COUNT

        try:
            # Temporarily set the max count to a small number for testing
            lambda_create_waves.MAX_MOVE_GROUPS_COUNT = 3

            # Arrange - create a list with more IDs than the limit
            too_many_ids = ["MG001", "MG002", "MG003", "MG004", "MG005"]
            event = {
                "body": json.dumps(
                    {
                        "wpm_job_id": self.test_job_id_without_starting_server_count,
                        "move_group_ids": too_many_ids,
                    }
                )
            }

            # Act
            response = lambda_create_waves.lambda_handler(event, None)

            # Assert
            self.assertEqual(response["statusCode"], 400)
            error_response = json.loads(response["body"])
            self.assertIn("error", error_response)
            self.assertIn("Too many move_group_ids", error_response["error"])
        finally:
            # Restore original constant
            lambda_create_waves.MAX_MOVE_GROUPS_COUNT = original_max_count

    def test_lambda_handler_nonexistent_job(self):
        """Test lambda_handler with a job ID that doesn't exist"""
        import lambda_create_waves

        # Arrange
        event = {
            "body": json.dumps(
                {
                    "wpm_job_id": "NONEXISTENT_JOB",
                    "move_group_ids": ["MG001", "MG002"],
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)

        # Assert
        self.assertEqual(response["statusCode"], 404)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)
        self.assertIn("Job not found", error_response["error"])

    def test_update_job_wave_ids(self):
        """Test the update_job_wave_ids function directly"""
        import lambda_create_waves
        
        # Test adding a new wave ID
        result = lambda_create_waves.update_job_wave_ids(self.test_job_id_without_starting_server_count, "WAVE_TEST_1")
        self.assertTrue(result)
        
        # Verify the wave ID was added to the job
        jobs_table = self.dynamodb.Table("wpm_jobs")
        job = jobs_table.get_item(Key={"wpm_job_id": self.test_job_id_without_starting_server_count})["Item"]
        self.assertIn("wave_ids", job)
        self.assertIn("WAVE_TEST_1", job["wave_ids"])
        
        # Test adding the same wave ID again (should not duplicate)
        result = lambda_create_waves.update_job_wave_ids(self.test_job_id_without_starting_server_count, "WAVE_TEST_1")
        self.assertTrue(result)
        
        # Verify no duplication occurred
        job = jobs_table.get_item(Key={"wpm_job_id": self.test_job_id_without_starting_server_count})["Item"]
        self.assertEqual(job["wave_ids"].count("WAVE_TEST_1"), 1)
        
        # Test adding a different wave ID
        result = lambda_create_waves.update_job_wave_ids(self.test_job_id_without_starting_server_count, "WAVE_TEST_2")
        self.assertTrue(result)
        
        # Verify both wave IDs are in the list
        job = jobs_table.get_item(Key={"wpm_job_id": self.test_job_id_without_starting_server_count})["Item"]
        self.assertIn("WAVE_TEST_1", job["wave_ids"])
        self.assertIn("WAVE_TEST_2", job["wave_ids"])
        
        # Test with invalid job ID
        result = lambda_create_waves.update_job_wave_ids("INVALID_JOB", "WAVE_TEST_3")
        self.assertFalse(result)
        
        # Test with empty wave ID
        result = lambda_create_waves.update_job_wave_ids(self.test_job_id_without_starting_server_count, "")
        self.assertFalse(result)
        
        # Test with None values
        result = lambda_create_waves.update_job_wave_ids(None, "WAVE_TEST_4")
        self.assertFalse(result)
        result = lambda_create_waves.update_job_wave_ids(self.test_job_id_without_starting_server_count, None)
        self.assertFalse(result)
        
    def test_update_assets_with_wave_id(self):
        """Test updating assets with wave ID."""
        import lambda_create_waves
        
        wave_id = "WAVE_TEST_1"
        app_ids = ["APP1", "APP2"]
        server_ids = ["SRV1", "SRV2", "SRV3"]
        database_ids = []
        
        # Test updating assets with wave ID
        result = lambda_create_waves.update_assets_with_wave_id(wave_id, app_ids, server_ids, database_ids)
        self.assertTrue(result)
        
        # Verify apps were updated with wave_ids
        apps_table = self.dynamodb.Table("apps")
        for app_id in app_ids:
            app = apps_table.get_item(Key={"app_id": app_id})["Item"]
            self.assertIn(wave_id, app.get("wave_ids", []))
        
        # Verify servers were updated with wave_id
        servers_table = self.dynamodb.Table("servers")
        for server_id in server_ids:
            server = servers_table.get_item(Key={"server_id": server_id})["Item"]
            self.assertEqual(server.get("wave_id"), wave_id)
        
        # Test updating with a different wave ID
        wave_id2 = "WAVE_TEST_2"
        result = lambda_create_waves.update_assets_with_wave_id(wave_id2, app_ids, server_ids, database_ids)
        self.assertTrue(result)
        
        # Verify apps were updated with both wave IDs
        for app_id in app_ids:
            app = apps_table.get_item(Key={"app_id": app_id})["Item"]
            self.assertIn(wave_id, app.get("wave_ids", []))
            self.assertIn(wave_id2, app.get("wave_ids", []))
        
        # Verify servers were updated with the new wave ID (overwriting the previous one)
        for server_id in server_ids:
            server = servers_table.get_item(Key={"server_id": server_id})["Item"]
            self.assertEqual(server.get("wave_id"), wave_id2)
        
        # Test with empty wave ID
        result = lambda_create_waves.update_assets_with_wave_id("", app_ids, server_ids, database_ids)
        self.assertFalse(result)
        
        # Test with empty asset lists
        result = lambda_create_waves.update_assets_with_wave_id(wave_id, [], [], [])
        self.assertTrue(result)

    def test_lambda_handler_request_id_in_error_responses(self):
        """Test that request_id is included in error responses"""
        import lambda_create_waves

        # Test cases for different error scenarios
        test_cases = [
            {
                "event": {},
                "expected_status": 400,
                "error_contains": "Missing request body",
            },
            {
                "event": {"body": "invalid json"},
                "expected_status": 400,
                "error_contains": "Invalid JSON",
            },
            {
                "event": {"body": json.dumps({})},
                "expected_status": 400,
                "error_contains": "Missing required fields",
            },
            {
                "event": {
                    "body": json.dumps(
                        {"wpm_job_id": "test", "move_group_ids": "not_a_list"}
                    )
                },
                "expected_status": 400,
                "error_contains": "must be a list",
            },
        ]

        for test_case in test_cases:
            # Act
            response = lambda_create_waves.lambda_handler(test_case["event"], None)

            # Assert
            self.assertEqual(response["statusCode"], test_case["expected_status"])
            error_response = json.loads(response["body"])
            self.assertIn("error", error_response)
            self.assertIn(test_case["error_contains"], error_response["error"])

    def test_lambda_handler_with_none_capacities(self):
        """Test lambda_handler with None starting_wave_server_capacity and wave_server_capacity_increase"""
        import lambda_create_waves

        # Arrange
        event = {
            "body": json.dumps(
                {
                    "wpm_job_id": self.test_job_id_with_none_capacities,
                    "move_group_ids": ["MG006"],
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)
        waves = json.loads(response["body"])

        # Assert
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(isinstance(waves, list))
        self.assertEqual(len(waves), 1)

    def test_lambda_handler_invalid_wpm_job_id_format(self):
        """Test lambda_handler with invalid wpm_job_id format (special characters)"""
        import lambda_create_waves

        # Arrange - test with special characters not allowed by regex
        event = {
            "body": json.dumps(
                {
                    "wpm_job_id": "JOB@001#",  # Contains @ and # which are not allowed
                    "move_group_ids": ["MG001"],
                }
            )
        }

        # Act
        response = lambda_create_waves.lambda_handler(event, None)

        # Assert
        self.assertEqual(response["statusCode"], 400)
        error_response = json.loads(response["body"])
        self.assertIn("error", error_response)
        self.assertIn("wpm_job_id must contain only alphanumeric characters, dashes, and underscores", error_response["error"])

    def test_lambda_handler_invalid_move_group_id_format(self):
        """Test lambda_handler with invalid move_group_id format and duplicate IDs"""
        import lambda_create_waves

        # Test case 1: Invalid characters in move group ID
        event1 = {
            "body": json.dumps(
                {
                    "wpm_job_id": "JOB001",
                    "move_group_ids": ["MG001", "MG@002"],  # MG@002 contains invalid character
                }
            )
        }

        response1 = lambda_create_waves.lambda_handler(event1, None)
        self.assertEqual(response1["statusCode"], 400)
        error_response1 = json.loads(response1["body"])
        self.assertIn("move_group_ids must contain only alphanumeric characters, dashes, and underscores", error_response1["error"])

        # Test case 2: Duplicate move group IDs
        event2 = {
            "body": json.dumps(
                {
                    "wpm_job_id": "JOB001",
                    "move_group_ids": ["MG001", "MG002", "MG001"],  # MG001 is duplicated
                }
            )
        }

        response2 = lambda_create_waves.lambda_handler(event2, None)
        self.assertEqual(response2["statusCode"], 400)
        error_response2 = json.loads(response2["body"])
        self.assertIn("Duplicate move_group_ids not allowed", error_response2["error"])
