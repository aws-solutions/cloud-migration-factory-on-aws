#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import unittest
from unittest import mock
import json
import boto3
from moto import mock_aws

from test_common_utils import default_mock_os_environ

mock_os_environ = {
    **default_mock_os_environ,
    "application": "cmf",
    "environment": "unittest",
    "AWS_DEFAULT_REGION": "us-east-1",
    "JOBS_TABLE_NAME": "wpm_jobs",
    "MOVE_GROUPS_TABLE_NAME": "move_groups",
    "WAVES_TABLE_NAME": "waves",
    "APPS_TABLE_NAME": "apps",
    "SERVERS_TABLE_NAME": "servers",
    "DATABASES_TABLE_NAME": "databases",
    "RULES_TABLE_NAME": "rules",
}


@mock.patch.dict("os.environ", mock_os_environ)
@mock_aws
class LambdaCalculateAppsRanks(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
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
            "wpm_jobs": "wpm_job_id",
            "apps": "app_id",
            "servers": "server_id",
            "databases": "database_id",
            "assets": "asset_id",
            "rules": "rule_id",
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
        # Add test applications
        apps_table = self.dynamodb.Table("apps")
        test_apps = [
            {"app_id": "APP1", "app_name": "Application 1", "criticality": "High"},
            {"app_id": "APP2", "app_name": "Application 2", "criticality": "Medium"},
            {"app_id": "APP3", "app_name": "Application 3", "criticality": "Low"},
            {"app_id": "APP4", "app_name": "Application 4", "criticality": "High"},
            {"app_id": "APP5", "app_name": "Application 5", "criticality": "Medium"},
        ]
        
        for app in test_apps:
            apps_table.put_item(Item=app)
            
        # Add test servers
        servers_table = self.dynamodb.Table("servers")
        test_servers = [
            {
                "server_id": "SRV1", 
                "server_name": "Server 1", 
                "app_ids": ["APP1"],
                "server_type": "Web",
                "os_version": "RHEL 9.x",
                "memory": 16,
                "cpu_cores": 4
            },
            {
                "server_id": "SRV2", 
                "server_name": "Server 2", 
                "app_ids": ["APP1"],
                "server_type": "Database",
                "os_version": "Ubuntu 22.05",
                "memory": 32,
                "cpu_cores": 8
            },
            {
                "server_id": "SRV3", 
                "server_name": "Server 3", 
                "app_ids": ["APP2"],
                "server_type": "Web",
                "os_version": "Windows 12",
                "memory": 8,
                "cpu_cores": 2
            },
            {
                "server_id": "SRV4", 
                "server_name": "Server 4", 
                "app_ids": ["APP3"],
                "server_type": "Application",
                "os_version": "RHEL 9.x",
                "memory": 16,
                "cpu_cores": 4
            },
            {
                "server_id": "SRV5", 
                "server_name": "Server 5", 
                "app_ids": ["APP3"],
                "server_type": "Database",
                "os_version": "Windows 12",
                "memory": 64,
                "cpu_cores": 16
            },
            {
                "server_id": "SRV6", 
                "server_name": "Server 6", 
                "app_ids": ["APP4"],
                "server_type": "Web",
                "os_version": "RHEL 9.x",
                "memory": 8,
                "cpu_cores": 2
            },
            {
                "server_id": "SRV7", 
                "server_name": "Server 7", 
                "app_ids": ["APP4", "APP5"],
                "server_type": "Application",
                "os_version": "RHEL 9.x",
                "memory": 16,
                "cpu_cores": 4
            },
        ]
        
        for server in test_servers:
            servers_table.put_item(Item=server)
            
        # Add test rules
        rules_table = self.dynamodb.Table("rules")
        test_rules = [
            {
                "rule_id": "RULE1",
                "rule_name": "Server Type Complexity",
                "rule_type": "PRIORITIZING",
                "sub_type": "SCORING",
                "asset_type": "server",
                "attr_key": "server_type",
                "status": "ENABLED",
                "scoring_criteria": [
                    {"value": "Web", "complexity_score": 1},
                    {"value": "Application", "complexity_score": 2},
                    {"value": "Database", "complexity_score": 3}
                ]
            },
            {
                "rule_id": "RULE2",
                "rule_name": "OS Version Complexity",
                "rule_type": "PRIORITIZING",
                "sub_type": "SCORING",
                "asset_type": "server",
                "attr_key": "os_version",
                "status": "ENABLED",
                "scoring_criteria": [
                    {"value": "RHEL 9.x", "complexity_score": 1},
                    {"value": "Windows 12", "complexity_score": 2},
                    {"name": "Ubuntu 22.04+", "pattern": "^Ubuntu (?:22\\.(?:0[4-9]|[1-9]\\d)|2[3-9]|[3-9]\\d)(?:\\.\\d+)?$", "complexity_score": 1},
                ]
            },
            {
                "rule_id": "RULE3",
                "rule_name": "Memory Size Complexity",
                "rule_type": "PRIORITIZING",
                "sub_type": "SCORING",
                "asset_type": "server",
                "attr_key": "memory",
                "status": "ENABLED",
                "scoring_criteria": [
                    {"upper_bound": 16, "complexity_score": 1},
                    {"lower_bound": 16, "upper_bound": 32, "complexity_score": 2},
                    {"lower_bound": 32, "complexity_score": 3},
                ]
            },
            {
                "rule_id": "RULE4",
                "rule_name": "Sort by Complexity Score",
                "rule_type": "PRIORITIZING",
                "sub_type": "SORTING",
                "attr_key": "complexity_score",
                "sort_order": "DSC",
                "sort_level": 1,
                "status": "ENABLED"
            },
            {
                "rule_id": "RULE5",
                "rule_name": "Sort by Criticality",
                "rule_type": "PRIORITIZING",
                "sub_type": "SORTING",
                "attr_key": "criticality",
                "sort_order": "ASC",
                "sort_level": 2,
                "sort_by_value": ["High", "Medium", "Low"],
                "status": "ENABLED"
            },
            {
                "rule_id": "RULE6",
                "rule_name": "Disabled Rule",
                "rule_type": "PRIORITIZING",
                "sub_type": "SCORING",
                "asset_type": "server",
                "attr_key": "cpu_cores",
                "status": "DISABLED",
                "scoring_criteria": [
                    {"lower_bound": 0, "upper_bound": 4, "complexity_score": 1},
                    {"lower_bound": 4, "upper_bound": 8, "complexity_score": 2},
                    {"lower_bound": 8, "upper_bound": 100, "complexity_score": 3}
                ]
            }
        ]
        
        for rule in test_rules:
            rules_table.put_item(Item=rule)

    @mock.patch("lambda_calculate_app_ranks.MFAuth")
    def test_lambda_handler_success(self, mock_auth):
        """Test successful lambda_handler execution"""
        # Set up mock auth
        mock_auth_instance = mock_auth.return_value
        mock_auth_instance.get_user_resource_creation_policy.return_value = {
            "action": "allow",
            "user": "testuser@example.com"
        }
        
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Arrange
        event = {}

        # Act
        response = lambda_calculate_app_ranks.lambda_handler(event, None)
        app_ranks = json.loads(response["body"])

        # Assert
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(isinstance(app_ranks, list))
        self.assertEqual(len(app_ranks), 5)  # 5 applications should be ranked

        # Verify the first app has the highest complexity score
        self.assertEqual(app_ranks[0]["rank"], 1)
        
        # Verify apps were updated in DynamoDB
        apps_table = self.dynamodb.Table("apps")
        for app_rank in app_ranks:
            response = apps_table.get_item(Key={"app_id": app_rank["app_id"]})
            self.assertIn("Item", response)
            stored_app = response["Item"]
            self.assertIn("complexity_score", stored_app)
            self.assertIn("rank", stored_app)
            self.assertEqual(stored_app["rank"], app_rank["rank"])

    def test_rule_engine_scoring(self):
        """Test the RuleEngine scoring functionality"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Create a test asset and rules
        test_asset = {
            "asset_type": "server",
            "server_type": "Database",
            "os_version": "Windows 12",
            "memory": 32
        }
        
        # Get rules from DynamoDB
        rules_table = self.dynamodb.Table("rules")
        response = rules_table.scan()
        rules = response.get("Items", [])
        rule_engine = lambda_calculate_app_ranks.RuleEngine(rules)
        
        # Calculate complexity score
        score = lambda_calculate_app_ranks.calculate_asset_complexity(test_asset, rule_engine)
        
        # Expected score: 3 (Database) + 2 (Windows) + 3 (32GB memory) = 8
        self.assertEqual(score, 8)

    def test_app_complexity_calculation(self):
        """Test application complexity calculation"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Get an application and its servers
        app_id = "APP1"
        
        # Get rules from DynamoDB
        rules_table = self.dynamodb.Table("rules")
        response = rules_table.scan()
        rules = response.get("Items", [])
        
        # Get application
        apps_table = self.dynamodb.Table("apps")
        response = apps_table.get_item(Key={"app_id": app_id})
        application = response["Item"]
        
        # Get servers for this application
        servers_table = self.dynamodb.Table("servers")
        response = servers_table.scan()
        all_servers = response.get("Items", [])
        app_servers = [s for s in all_servers if app_id in s.get("app_ids")]
        rule_engine = lambda_calculate_app_ranks.RuleEngine(rules)
        
        # Calculate complexity score
        score = lambda_calculate_app_ranks.calculate_app_complexity(application, app_servers, rule_engine)
        
        # Expected score: 
        # Server 1: 1 (Web) + 1 (RHEL 9.x) + 2 (16GB memory) = 4
        # Server 2: 3 (Database) + 1 (RHEL 9.x) + 3 (32GB memory) = 7
        # Total: 4 + 7 = 11
        self.assertEqual(score, 11)

    def test_sort_applications(self):
        """Test application sorting functionality"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Create test applications with complexity scores
        test_apps = [
            {"app_id": "APP1", "complexity_score": 10, "criticality": "High"},
            {"app_id": "APP2", "complexity_score": 5, "criticality": "Medium"},
            {"app_id": "APP3", "complexity_score": 10, "criticality": "Medium"},
            {"app_id": "APP4", "complexity_score": 5, "criticality": "High"},
        ]
        
        # Get rules from DynamoDB
        rules_table = self.dynamodb.Table("rules")
        response = rules_table.scan()
        rules = response.get("Items", [])
        
        # Sort applications
        sorted_apps = lambda_calculate_app_ranks.sort_applications(test_apps, rules)
        
        # Expected order:
        # 1. APP1 (score 10, criticality High)
        # 2. APP3 (score 10, criticality Medium)
        # 3. APP4 (score 5, criticality High)
        # 4. APP2 (score 5, criticality Medium)
        self.assertEqual(sorted_apps[0]["app_id"], "APP1")
        self.assertEqual(sorted_apps[1]["app_id"], "APP3")
        self.assertEqual(sorted_apps[2]["app_id"], "APP4")
        self.assertEqual(sorted_apps[3]["app_id"], "APP2")

    def test_applications_sort_by_value_desc(self):
        """Test application sorting by value functionality in descending order"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Create test applications with complexity scores
        test_apps = [
            {"app_id": "APP1", "complexity_score": 10, "criticality": "High"},
            {"app_id": "APP2", "complexity_score": 5, "criticality": "Medium"},
            {"app_id": "APP3", "complexity_score": 10, "criticality": "Medium"},
            {"app_id": "APP4", "complexity_score": 5, "criticality": "High"},
        ]
        
        # Get rules from DynamoDB
        rules_table = self.dynamodb.Table("rules")
        response = rules_table.scan()
        rules = response.get("Items", [])

        # Override the sort by value rule so its ordering in descending order
        rules = [rule for rule in rules if rule["rule_id"] != "RULE5"]
        rules.append({
            "rule_id": "RULE5",
            "rule_name": "Sort by Criticality",
            "rule_type": "PRIORITIZING",
            "sub_type": "SORTING",
            "attr_key": "criticality",
            "sort_order": "DSC",
            "sort_level": 2,
            "sort_by_value": ["High", "Medium", "Low"],
            "status": "ENABLED"
        })
        
        # Sort applications
        sorted_apps = lambda_calculate_app_ranks.sort_applications(test_apps, rules)
        
        # Expected order:
        # 1. APP3 (score 10, criticality Medium)
        # 2. APP1 (score 10, criticality High)
        # 3. APP2 (score 5, criticality Medium)
        # 4. APP4 (score 5, criticality High)
        self.assertEqual(sorted_apps[0]["app_id"], "APP3")
        self.assertEqual(sorted_apps[1]["app_id"], "APP1")
        self.assertEqual(sorted_apps[2]["app_id"], "APP2")
        self.assertEqual(sorted_apps[3]["app_id"], "APP4")

    @mock.patch("lambda_calculate_app_ranks.MFAuth")
    def test_sort_applications_strings_asc(self, mock_auth):
        """Test application sorting functionality with string values ascending"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Create test applications with different app names
        test_apps = [
            {
                "app_id": "APP1",
                "app_name": "app906",
                "server_count": 1,
                "complexity_score": 0,
            },
            {
                "app_id": "APP2", 
                "app_name": "app901",
                "server_count": 2,
                "complexity_score": 0,
            },
            {
                "app_id": "APP3",
                "app_name": "app905", 
                "server_count": 2,
                "complexity_score": 100,
            },
        ]

        rules = [
            {
                "rule_description": "Sort applications by app name",
                "sort_level": 1,
                "rule_id": "1",
                "rule_type": "PRIORITIZING",
                "status": "ENABLED",
                "rule_name": "sort-by-name",
                "sub_type": "SORTING",
                "sort_order": "ASC",
                "asset_type": "app",
                "attr_key": "app_name",
            },
        ]

        # Sort applications
        sorted_apps = lambda_calculate_app_ranks.sort_applications(test_apps, rules)

        # Verify sorting by app_name in ascending order
        # Expected order: app901, app905, app906
        self.assertEqual(len(sorted_apps), 3)
        self.assertEqual(sorted_apps[0]["app_name"], "app901")
        self.assertEqual(sorted_apps[1]["app_name"], "app905") 
        self.assertEqual(sorted_apps[2]["app_name"], "app906")

    @mock.patch("lambda_calculate_app_ranks.MFAuth")
    def test_sort_applications_strings_desc(self, mock_auth):
        """Test application sorting functionality with string values descending"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Create test applications with different app names
        test_apps = [
            {
                "app_id": "APP1",
                "app_name": "app906",
                "server_count": 1,
                "complexity_score": 0,
            },
            {
                "app_id": "APP2", 
                "app_name": "app901",
                "server_count": 2,
                "complexity_score": 0,
            },
            {
                "app_id": "APP3",
                "app_name": "app905", 
                "server_count": 2,
                "complexity_score": 100,
            },
        ]

        rules = [
            {
                "rule_description": "Sort applications by app name",
                "sort_level": 1,
                "rule_id": "1",
                "rule_type": "PRIORITIZING",
                "status": "ENABLED",
                "rule_name": "sort-by-name",
                "sub_type": "SORTING",
                "sort_order": "DSC",
                "asset_type": "app",
                "attr_key": "app_name",
            },
        ]

        # Sort applications
        sorted_apps = lambda_calculate_app_ranks.sort_applications(test_apps, rules)

        # Verify sorting by app_name in descending order
        # Expected order: app906, app905, app901
        self.assertEqual(len(sorted_apps), 3)
        self.assertEqual(sorted_apps[0]["app_name"], "app906")
        self.assertEqual(sorted_apps[1]["app_name"], "app905") 
        self.assertEqual(sorted_apps[2]["app_name"], "app901")

    @mock.patch("lambda_calculate_app_ranks.MFAuth")
    def test_sort_applications_floats_asc(self, mock_auth):
        """Test application sorting functionality with float values ascending"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Create test applications with different app names
        test_apps = [
            {
                "app_id": "APP1",
                "app_name": "app906",
                "server_count": 1,
                "complexity_score": 0,
            },
            {
                "app_id": "APP2", 
                "app_name": "app901",
                "server_count": 2,
                "complexity_score": 0,
            },
            {
                "app_id": "APP3",
                "app_name": "app905", 
                "server_count": 2,
                "complexity_score": 100,
            },
        ]

        rules = [
            {
                "rule_description": "Sort applications by complexity score",
                "sort_level": 1,
                "rule_id": "1",
                "rule_type": "PRIORITIZING",
                "status": "ENABLED",
                "rule_name": "sort-by-complexity",
                "sub_type": "SORTING",
                "sort_order": "ASC",
                "asset_type": "app",
                "attr_key": "complexity_score",
            },
        ]

        # Sort applications
        sorted_apps = lambda_calculate_app_ranks.sort_applications(test_apps, rules)

        # Verify sorting by complexity_score in ascending order
        # Expected order: APP1/APP2 (both score 0), then APP3 (score 100)
        # Since APP1 and APP2 have the same score, their order is not guaranteed
        self.assertEqual(len(sorted_apps), 3)
        # First two should have complexity_score = 0
        self.assertEqual(sorted_apps[0]["complexity_score"], 0)
        self.assertEqual(sorted_apps[1]["complexity_score"], 0)
        # Last one should have complexity_score = 100
        self.assertEqual(sorted_apps[2]["complexity_score"], 100)
        self.assertEqual(sorted_apps[2]["app_name"], "app905")

    @mock.patch("lambda_calculate_app_ranks.MFAuth")
    def test_sort_applications_floats_desc(self, mock_auth):
        """Test application sorting functionality with float values descending"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Create test applications with different app names
        test_apps = [
            {
                "app_id": "APP1",
                "app_name": "app906",
                "server_count": 1,
                "complexity_score": 0,
            },
            {
                "app_id": "APP2", 
                "app_name": "app901",
                "server_count": 2,
                "complexity_score": 0,
            },
            {
                "app_id": "APP3",
                "app_name": "app905", 
                "server_count": 2,
                "complexity_score": 100,
            },
        ]

        rules = [
            {
                "rule_description": "Sort applications by complexity score",
                "sort_level": 1,
                "rule_id": "1",
                "rule_type": "PRIORITIZING",
                "status": "ENABLED",
                "rule_name": "sort-by-complexity",
                "sub_type": "SORTING",
                "sort_order": "DSC",
                "asset_type": "app",
                "attr_key": "complexity_score",
            },
        ]

        # Sort applications
        sorted_apps = lambda_calculate_app_ranks.sort_applications(test_apps, rules)

        # Verify sorting by complexity_score in ascending order
        # Expected order: APP3 (score 100), then APP1/APP2 (both score 0)
        # Since APP1 and APP2 have the same score, their order is not guaranteed
        self.assertEqual(len(sorted_apps), 3)
        self.assertEqual(sorted_apps[0]["app_name"], "app905")
        # Last two should have complexity_score = 0
        self.assertEqual(sorted_apps[1]["complexity_score"], 0)
        self.assertEqual(sorted_apps[2]["complexity_score"], 0)

    def test_servers_with_multiple_apps(self):
        """Test handling of servers with multiple applications"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Get all servers
        servers = lambda_calculate_app_ranks.get_all_servers()
        
        # Group servers by application
        servers_by_app = lambda_calculate_app_ranks.group_servers_by_app(servers)
        
        # Verify that server SRV7 is included for both APP4 and APP5
        self.assertIn("SRV7", [s["server_id"] for s in servers_by_app.get("APP4", [])])
        self.assertIn("SRV7", [s["server_id"] for s in servers_by_app.get("APP5", [])])
    
    def test_validation_apply_scoring_rule(self):
        """Test data validation in apply_scoring_rule function"""
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Create malformed test asset
        test_asset = {
            "asset_type": "server",
            "server_type": "Database",
            "os_version": "Windows 12",
            "memory": 'bad-data'
        }
        
        # Get rules from DynamoDB
        rules_table = self.dynamodb.Table("rules")
        response = rules_table.scan()
        rules = response.get("Items", [])
        rule_engine = lambda_calculate_app_ranks.RuleEngine(rules)
        
        # Calculate complexity score
        score = lambda_calculate_app_ranks.calculate_asset_complexity(test_asset, rule_engine)
        
        # Expected score: 3 (Database) + 2 (Windows) + 0 (bad data in memory) = 5
        self.assertEqual(score, 5)

    @mock.patch("lambda_calculate_app_ranks.MFAuth")
    def test_lambda_handler_unauthorized(self, mock_auth):
        """Test lambda_handler with unauthorized access"""
        # Set up mock auth to deny access
        mock_auth_instance = mock_auth.return_value
        mock_auth_instance.get_user_resource_creation_policy.return_value = {
            "action": "deny",
            "cause": "Unauthorized"
        }
        
        # Import the lambda function
        import lambda_calculate_app_ranks

        # Arrange
        event = {}

        # Act
        response = lambda_calculate_app_ranks.lambda_handler(event, None)

        # Assert
        self.assertEqual(response["statusCode"], 401)
        error_response = json.loads(response["body"])
        self.assertIn("errors", error_response)

    @mock.patch("lambda_calculate_app_ranks.MFAuth")
    def test_lambda_handler_exception(self, mock_auth):
        """Test lambda_handler with an exception"""
        # Set up mock auth
        mock_auth_instance = mock_auth.return_value
        mock_auth_instance.get_user_resource_creation_policy.return_value = {
            "action": "allow",
            "user": "testuser@example.com"
        }
        
        # Import the lambda function
        import lambda_calculate_app_ranks
        
        # Mock get_all_applications to raise an exception
        with mock.patch.object(lambda_calculate_app_ranks, "get_all_applications", 
                              side_effect=Exception("Test exception")):
            # Arrange
            event = {}

            # Act
            response = lambda_calculate_app_ranks.lambda_handler(event, None)

            # Assert
            self.assertEqual(response["statusCode"], 500)
            error_response = json.loads(response["body"])
            self.assertIn("errors", error_response)
            self.assertTrue(any("Test exception" in str(error) for error in error_response["errors"]))