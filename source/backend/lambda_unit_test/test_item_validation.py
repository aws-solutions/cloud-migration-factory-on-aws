#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import logging
import os
import boto3
import sys
from moto import mock_aws
from unittest import TestCase, mock

# Create a mock for cmf_boto that will be used only during these tests
class MockCmfBoto:
    @staticmethod
    def resource(service_name):
        return boto3.resource(service_name)
    
    @staticmethod
    def client(service_name):
        return boto3.client(service_name)

# # This is to get around the relative path import issue.
# # Absolute paths are being used in this file after setting the root directory
import sys  
from pathlib import Path
file = Path(__file__).resolve()  
package_root_directory = file.parents [1]  
sys.path.append(str(package_root_directory))  
sys.path.append(str(package_root_directory)+'/lambda_layers/lambda_layer_items/python/')

# Set log level
loglevel = logging.INFO
logging.basicConfig(level=loglevel)
log = logging.getLogger(__name__)
  
# Setting the default AWS region environment variable required by the Python SDK boto3
@mock.patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1','region':'us-east-1', 'application': 'cmf', 'environment': 'unittest'})


@mock_aws
class ItemValidationTestCase(TestCase):
    def setUp(self):
        # Register the mock for cmf_boto
        sys.modules['cmf_boto'] = MockCmfBoto
        
        # Setup dynamoDB tables and put items required for test cases
        self.table_name = '{}-{}-'.format('cmf', 'unittest') + 'apps'
        boto3.setup_default_session()
        self.event = {"httpMethod": 'GET', 'pathParameters': {'schema': 'app'}}
        self.table_name = '{}-{}-'.format('cmf', 'unittest') + 'apps'
        self.client = boto3.client("dynamodb",region_name='us-east-1')
        self.client.create_table(
            TableName='{}-{}-'.format('cmf', 'unittest') + 'apps',
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
              {"AttributeName": "app_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
              {"AttributeName": "app_id", "AttributeType": "S"},
            ],
        )
        self.client.put_item(
               TableName=self.table_name,
               Item={'app_id': {'S': '3'}, 'app_name': {'S': 'test app'}})
        self.schema_table_name = '{}-{}-'.format('cmf', 'unittest') + 'schema'
        # Creating schema table and creating schema item to test out schema types
        self.schema_client = boto3.client("dynamodb",region_name='us-east-1')
        self.schema_client.create_table(
            TableName=self.schema_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
              {"AttributeName": "schema_name", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
              {"AttributeName": "schema_name", "AttributeType": "S"},
            ],
        )
        self.schema_client.put_item(
              TableName=self.schema_table_name,
              Item={'schema_name': {'S': 'app'}, 'schema_type': {'S': 'user'},'attributes':{'L':[{'M': {'name': {'S': 'app_id'}, 'type': {'S' : 'string'}}},{'M': {'name': {'S': 'app_name'}, 'type': {'S' : 'string'}}}]}})

        self.role_table_name = '{}-{}-'.format('cmf', 'unittest') + 'roles'
        self.role_client = boto3.client("dynamodb",region_name='us-east-1')
        self.role_client.create_table(
            TableName=self.role_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
              {"AttributeName": "role_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
              {"AttributeName": "role_id", "AttributeType": "S"},
            ],
        )
        self.role_client.put_item(
              TableName=self.role_table_name,
              Item={'role_id': {'S': '1'}, 'role_name': {'S': 'FactoryAdmin'},'groups': {'L':[ { "M" : { "group_name" : { "S" : "admin" } } } ]}, 'policies':{"L" : [ { "M" : { "policy_id" : { "S" : "1" } } } ]}  })



        self.policy_table_name = '{}-{}-'.format('cmf', 'unittest') + 'policies'
        self.policy_client = boto3.client("dynamodb",region_name='us-east-1')
        self.policy_client.create_table(
            TableName=self.policy_table_name,
            BillingMode='PAY_PER_REQUEST',
            KeySchema=[
              {"AttributeName": "policy_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
              {"AttributeName": "policy_id", "AttributeType": "S"},
            ],
        )
        self.policy_client.put_item(
              TableName=self.policy_table_name,
              Item={'policy_id': {'S': '1'}, 'policy_name': {'S': 'Administrator'}, \
                    'entity_access': {"L": [{"M": {"attributes": {"L": [{"M": {"attr_name": {"S": "app_id"},"attr_type": {"S": "application"}}}, \
                    {"M": {"attr_name": {"S": "app_name"},"attr_type": {"S": "application"}}}]}, \
                    "delete": {"BOOL": True },"update": {"BOOL": True },"create": {"BOOL": True },"read": {"BOOL": True },"schema_name": {"S": "application"}}}]}  })


    def tearDown(self):
        """
        Delete database resource and mock table
        """
        print("Tearing down")
        self.client.delete_table(TableName=self.table_name)
        self.policy_client.delete_table(TableName=self.policy_table_name)
        self.role_client.delete_table(TableName=self.role_table_name)
        self.schema_client.delete_table(TableName=self.schema_table_name)
        self.dynamodb = None
        
        # Clean up the cmf_boto mock to prevent affecting other tests
        if 'cmf_boto' in sys.modules:
            del sys.modules['cmf_boto']
            
        print("Teardown complete")


    def test_get_required_attributes_with_empty_schema(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: get_required_attributes with empty schema")
        schema = {}
        response = item_validation.get_required_attributes(schema, include_conditional=True )
        print("Response: ", response)
        expected_response = []
        self.assertEqual(response, expected_response)
                
    def test_get_required_attributes(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: get_required_attributes")
        schema = {
            "schema_name": "application",
            "attributes": [{
                    "required": True,
                    "name": "attr_name_1",
                    "hidden": False
                }, {
                    "hidden": True,
                    "name": "attr_name_2",
                    "conditions": {
                        "outcomes": {
                            "true": {
                                "required": True
                            }
                        }
                    }
                },
                {
                    "hidden": True,
                    "name": "attr_name_3",
                    "conditions": {
                        "outcomes": {
                            "false": {
                                "required": True
                            }
                        }
                    }
                },
                {
                    "required": False,
                    "name": "attr_name_4",
                    "conditions": {
                        "outcomes": {
                            "true": {
                                "hidden": True
                            }
                        }
                    }
                },
                {
                    "hidden": True,
                    "name": "attr_name_5",
                    "conditions": {
                        "outcomes": {
                            "false": {
                                "hidden": True
                            }
                        }
                    }
                },
            ]
        }
        response = item_validation.get_required_attributes(schema, include_conditional=True )
        print("Response: ", response)
        expected_response = [{
                'required': True,
                'name': 'attr_name_1',
                'hidden': False
            }, {
                'hidden': True,
                'name': 'attr_name_2',
                'conditions': {
                    'outcomes': {
                        'true': {
                            'required': True
                        }
                    }
                }
            }, {
                'hidden': True,
                'name': 'attr_name_3',
                'conditions': {
                    'outcomes': {
                        'false': {
                            'required': True
                        }
                    }
                }
        }]
        self.assertEqual(response, expected_response)


    def test_check_attribute_required_conditions_without_condition(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_attribute_required_conditions without condition")
        item = {}
        conditions = {}
        response = item_validation.check_attribute_required_conditions(item, conditions)
        print("Response: ", response)
        expected_response = {'required': False, 'hidden': False}
        self.assertEqual(response, expected_response)

    
    def test_check_attribute_required_conditions_with_equal_comparator_and_false_query_result(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_attribute_required_conditions"
                 " with equal comparator and generating false query result")
        item = {
            "r_type": "Retain",
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "Retain",
                        "attribute": "r_type"
                    },
                    {
                        "comparator": "=",
                        "value": "Retain2",
                        "attribute": "r_type"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        conditions = item["conditions"]
        response = item_validation.check_attribute_required_conditions(item, conditions)
        print("Response: ", response)
        expected_response = {'required': True, 'hidden': False}
        self.assertEqual(response, expected_response)


    def test_check_attribute_required_conditions_with_equal_comparator_and_true_query_result(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_attribute_required_conditions" 
                 " with equal comparator and generating true query result")
        item = {
            "r_type": "Retain",
            "conditions": {
                "queries": [
                    {
                        "comparator": "=",
                        "value": "Retain",
                        "attribute": "r_type"
                    }
                ],
                "outcomes": {
                    "true": [
                        "not_hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        conditions = item["conditions"]
        response = item_validation.check_attribute_required_conditions(item, conditions)
        print("Response: ", response)
        expected_response = {'required': False, 'hidden': False}
        self.assertEqual(response, expected_response)


    def test_check_attribute_required_conditions_with_not_equal_comparator(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_attribute_required_conditions with not equal comparator")
        item = {
            "r_type": "Retain",
            "conditions": {
                "queries": [{
                        "comparator": "!=",
                        "value": "Retain2",
                        "attribute": "r_type"
                    },
                    {
                        "comparator": "!=",
                        "value": "Retain",
                        "attribute": "r_type"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        conditions = item["conditions"]
        response = item_validation.check_attribute_required_conditions(item, conditions)
        print("Response: ", response)
        expected_response = {'required': True, 'hidden': False}
        self.assertEqual(response, expected_response)


    def test_check_attribute_required_conditions_with_empty_comparator(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_attribute_required_conditions with empty comparator")
        item = {
            "r_type": "Retain",
            "ami_id": "",
            "add_vols_size": "xxxxxx",
            "conditions": {
                "queries": [{
                        "comparator": "empty",
                        "attribute": "root_vol_size"
                    },
                    {
                        "comparator": "empty",
                        "attribute": "ami_id"
                    },
                    {
                        "comparator": "empty",
                        "attribute": "add_vols_size"
                    }
                ],
                "outcomes": {
                    "true": [
                        "required"
                    ],
                    "false": [
                        "not_required"
                    ]
                }
            }
        }
        conditions = item["conditions"]
        response = item_validation.check_attribute_required_conditions(item, conditions)
        print("Response: ", response)
        expected_response = {'required': False, 'hidden': False}
        self.assertEqual(response, expected_response)


    def test_check_attribute_required_conditions_with_not_empty_comparator(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_attribute_required_conditions with not empty comparator")
        item = {
            "r_type": "Retain",
            "ami_id": "xxxxxx",
            "add_vols_size": "",
            "conditions": {
                "queries": [{
                        "comparator": "!empty",
                        "attribute": "root_vol_size"
                    },
                    {
                        "comparator": "!empty",
                        "attribute": "ami_id"
                    },
                    {
                        "comparator": "!empty",
                        "attribute": "add_vols_size"
                    }
                ],
                "outcomes": {
                    "true": [
                        "required"
                    ],
                    "false": [
                        "not_required"
                    ]
                }
            }
        }
        conditions = item["conditions"]
        response = item_validation.check_attribute_required_conditions(item, conditions)
        print("Response: ", response)
        expected_response = {'required': False, 'hidden': False}
        self.assertEqual(response, expected_response)


    def test_check_attribute_required_conditions_with_invalid_comparator(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_attribute_required_conditions with invalid comparator")
        item = {
            "r_type": "Retain",
            "ami_id": "xxxxxx",
            "add_vols_size": "",
            "conditions": {
                "queries": [{
                        "comparator": ">",
                        "attribute": "root_vol_size"
                    }
                ],
                "outcomes": {
                    "true": [
                        "required"
                    ],
                    "false": [
                        "not_required"
                    ]
                }
            }
        }
        conditions = item["conditions"]
        exception_message = "The operation > is not supported"
        with self.assertRaises(item_validation.UnSupportedOperationTypeException) as exc:
            item_validation.check_attribute_required_conditions(item, conditions)
        self.assertEqual(str(exc.exception), exception_message)

    
    def test_check_attribute_required_conditions_without_query_attribute(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_attribute_required_conditions without query")
        item = {
            "r_type": "Retain2",
            "conditions": {
                "queries": [
                    {
                        "comparator": "=",
                        "value": "Retain",
                        "attribute": "r_type"
                    }
                ],
                "outcomes": {
                    "true": [
                        "not_hidden"
                    ],
                    "false": [
                        "not_required"
                    ]
                }
            }
        }
        conditions = item["conditions"]
        response = item_validation.check_attribute_required_conditions(item, conditions)
        print("Response: ", response)
        expected_response = {'required': False, 'hidden': False}
        self.assertEqual(response, expected_response)


    def test_check_valid_item_create_having_string_type_and_validation_error(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_valid_item_create has string type"
                 " and validation error")
        item = {
            "r_type": "Retain",
            "system_key": "_system_key",
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "Retain",
                        "attribute": "r_type"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        schema = {
            "schema_name": "application",
            "attributes": [{
                    "required": True,
                    "name": "r_type",
                    "hidden": False,
                    "listMultiSelect": True,
                    "rel_display_attribute": "aws_accountid",
                    "rel_key": "aws_accountid",
                    "description": "AWS account ID",
                    "rel_entity": "application",
                    "type": "string",
                    "system": True,
                    "validation_regex": "^(?!\\s*$).+",
                    "listvalue": "All Accounts",
                    "validation_regex_msg": "AWS account ID must be provided."
            }]
        }
        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        expected_response = ['Attribute system_key is not defined in the schema.', 'Attribute conditions is not defined in the schema.']
        self.assertEqual(response, expected_response)

    def test_check_valid_item_create_rule_schema(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_item_create with rule schema")
        item = {
            "rule_type": "PRIORITIZING",
            "rule_name": "test-rule",
            "sub_type": "SCORING",
            "status": "ENABLED",
            "scoring_criteria": [
                {"upper_bound": 200, "complexity_score": 20}
            ]
        }
        schema = {
            "schema_name": "rule",
            "attributes": [
                {"name": "rule_type", "type": "string", "required": True},
                {"name": "rule_name", "type": "string", "required": True},
                {"name": "sub_type", "type": "string", "required": False},
                {"name": "status", "type": "string", "required": True},
                {"name": "scoring_criteria", "type": "list", "required": False}
            ]
        }
        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        self.assertIsNone(response)


    def test_check_valid_item_create_having_relationship_type_but_no_key(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_valid_item_create has relationship"
                 " as type but rel_entity or rel_key doesn't present")
        item = {
            "r_type": "Retain",
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "Retain",
                        "attribute": "r_type"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        schema = {
            "schema_name": "application",
            "attributes": [{
                    "required": True,
                    "name": "r_type",
                    "hidden": False,
                    "listMultiSelect": True,
                    "description": "AWS account ID",
                    "type": "relationship",
                    "system": True,
                    "validation_regex": "^(?!\\s*$).+",
                    "listvalue": "All Accounts",
                    "validation_regex_msg": "AWS account ID must be provided."
            }]
        }
        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        expected_response = ['r_type: Invalid relationship attribute schema or key missing.', 'Attribute conditions is not defined in the schema.']
        self.assertEqual(response, expected_response)


    def test_check_valid_item_create_having_relationship_type_and_key_but_missing_attribute_in_schema(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_valid_item_create has relationship type"
                 " and relationship key, but an attribute is missing from schema")
        item = {
            "all_applications": "",
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "",
                        "attribute": "all_applications"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        schema = {
            "schema_type": "user",
            "attributes": [{
                "listMultiSelect": True,
                "rel_display_attribute": "app_name",
                "rel_key": "app_id",
                "name": "all_applications",
                "description": "All applications",
                "rel_entity": "application",
                "type": "relationship"
            }],
            "schema_name": "server",
            
        }
        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        expected_response = ['Attribute conditions is not defined in the schema.']
        self.assertEqual(response, expected_response)


    def test_check_valid_item_create_having_relationship_type_but_no_matching_key_in_db(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_valid_item_create has relationship type"
                 " and relationship key, but database record doesn't have a matching key.")
        item = {
            "all_applications": ["x", "y", "z"],
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "xyz",
                        "attribute": "all_applications"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        schema = {
            "schema_type": "user",
            "attributes": [{
                "listMultiSelect": True,
                "rel_display_attribute": "app_name",
                "rel_key": "app_id",
                "name": "all_applications",
                "description": "All applications",
                "rel_entity": "application",
                "type": "relationship",
                "conditions": {
                    "queries": [{
                            "comparator": "=",
                            "value": "",
                            "attribute": "all_applications"
                        }
                    ],
                    "outcomes": {
                        "true": [
                            "hidden"
                        ],
                        "false": [
                            "required"
                        ]
                    }
                }
            }],
            "schema_name": "server",
        }

        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        expected_response = ['all_applications: The following related record ids do not exist using key app_id - x, y, z', 
                             'Attribute conditions is not defined in the schema.']
        
        print(expected_response)
        self.assertEqual(response, expected_response)


    def test_check_valid_item_create_having_relationship_type_but_false_listmultiselect(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_valid_item_create has relationship type"
                 " and relationship key, but listMultiSelect is false.")
        item = {
            "all_applications": "xxx",
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "xxx",
                        "attribute": "all_applications"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        schema = {
            "schema_type": "user",
            "attributes": [{
                "listMultiSelect": False,
                "rel_display_attribute": "app_name",
                "rel_key": "app_id",
                "name": "all_applications",
                "description": "All applications",
                "rel_entity": "application",
                "type": "relationship",
                "conditions": {
                    "queries": [{
                            "comparator": "=",
                            "value": "",
                            "attribute": "all_applications"
                        }
                    ],
                    "outcomes": {
                        "true": [
                            "hidden"
                        ],
                        "false": [
                            "required"
                        ]
                    }
                }
            }],
            "schema_name": "server",
        }

        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        expected_response = ['all_applications:xxx related record does not exist using key app_id', 
                             'Attribute conditions is not defined in the schema.']
        self.assertEqual(response, expected_response)


    def test_check_valid_item_create_having_multivalue_string_type(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_valid_item_create"
                 " has multivalue-string as type.")
        item = {
            "subnet_IDs": "xxx",
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "xxx",
                        "attribute": "subnet_IDs"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        schema = {
            "schema_type": "user",
            "attributes": [{
                "system": True,
                "validation_regex": "^(subnet-([a-z0-9]{8}|[a-z0-9]{17})$)",
                "name": "subnet_IDs",
                "description": "Subnet Ids",
                "validation_regex_msg": "Subnets must start with subnet-, followed by 8 or 17 alphanumeric characters.",
                "type": "multivalue-string",
                "conditions": {
                    "queries": [{
                        "comparator": "!empty",
                        "attribute": "network_interface_id"
                    }],
                    "outcomes": {
                        "true": [
                            "hidden"
                        ],
                        "false": [
                            "not_required"
                        ]
                    },
                    "group": "Target - Networking"
                }
            }],
            "schema_name": "server"
        }
        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        expected_response = ['Attribute subnet_IDs, Subnets must start with subnet-, followed by 8 or 17 alphanumeric characters.', 
                             'Attribute conditions is not defined in the schema.']
        self.assertEqual(response, expected_response)


    def test_check_valid_item_create_having_list_type(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_valid_item_create"
                 " has list as type.")
        item = {
            "server_os_family": "xxx",
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "xxx",
                        "attribute": "server_os_family"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        schema ={
            "schema_type": "user",
            "attributes": [{
                "system": True,
                "validation_regex": "^(?!\\s*$).+",
                "listvalue": "windows,linux",
                "name": "server_os_family",
                "description": "Server OS Family",
                "validation_regex_msg": "Select a valid operating system.",
                "type": "list",
                "required": True
            }],
            "schema_name": "server"
        }
        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        expected_response = ["Attribute server_os_family's value does not match any of the allowed values 'windows,linux' defined in the schema", 
                             'Attribute conditions is not defined in the schema.']
        self.assertEqual(response, expected_response)


    def test_check_valid_item_create_having_list_type_and_listMultiSelect(self):
        from lambda_layers.lambda_layer_items.python import item_validation    
        log.info("Testing item_validation: check_valid_item_create"
                 " has list as type and listMultiSelect is present.")
        item = {
            "server_os_family": "xxx",
            "conditions": {
                "queries": [{
                        "comparator": "=",
                        "value": "xxx",
                        "attribute": "server_os_family"
                    }
                ],
                "outcomes": {
                    "true": [
                        "hidden"
                    ],
                    "false": [
                        "required"
                    ]
                }
            }
        }
        schema ={
            "schema_type": "user",
            "attributes": [{
                "system": True,
                "validation_regex": "^(?!\\s*$).+",
                "listvalue": "windows,linux",
                "listMultiSelect": True,
                "name": "server_os_family",
                "description": "Server OS Family",
                "validation_regex_msg": "Select a valid operating system.",
                "type": "list",
                "required": True
            }],
            "schema_name": "server"
        }
        response = item_validation.check_valid_item_create(item, schema)
        print("Response: ", response)
        expected_response = ["Attribute server_os_family's value does not match any of the allowed values 'windows,linux' defined in the schema", 
                             "Attribute server_os_family's value does not match any of the allowed values 'windows,linux' defined in the schema", 
                             "Attribute server_os_family's value does not match any of the allowed values 'windows,linux' defined in the schema", 
                             'Attribute conditions is not defined in the schema.']
        self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_scoring_rule_valid(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with valid scoring rule")
        item = {
            "rule_type": "PRIORITIZING",
            "rule_name": "test-scoring-rule",
            "sub_type": "SCORING",
            "status": "ENABLED",
            "scoring_criteria": [
                {"upper_bound": 200, "complexity_score": 20},
                {"lower_bound": 200, "upper_bound": 500, "complexity_score": 40}
            ]
        }
        response = item_validation.check_valid_rule_create(item)
        print("Response: ", response)
        self.assertEqual(response, [])

    def test_check_valid_rule_create_scoring_rule_missing_criteria(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with scoring rule missing criteria")
        item = {
            "rule_type": "PRIORITIZING",
            "rule_name": "test-scoring-rule",
            "sub_type": "SCORING",
            "status": "ENABLED"
        }
        response = item_validation.check_valid_rule_create(item)
        print("Response: ", response)
        expected_response = ['scoring_criteria is required when sub_type is SCORING']
        self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_scoring_rule_invalid_complexity_score(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with invalid complexity_score")
        item = {
            "rule_type": "PRIORITIZING",
            "rule_name": "test-scoring-rule",
            "sub_type": "SCORING",
            "status": "ENABLED",
            "scoring_criteria": [
                {"upper_bound": 200, "complexity_score": 150},  # Invalid: > 100
                {"lower_bound": 200, "complexity_score": -10}   # Invalid: < 0
            ]
        }
        response = item_validation.check_valid_rule_create(item)
        print("Response: ", response)
        expected_response = [
            'scoring_criteria[0].complexity_score must be a number between 0 and 100',
            'scoring_criteria[1].complexity_score must be a number between 0 and 100'
        ]
        self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_sorting_rule_valid(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with valid sorting rule")
        item = {
            "rule_type": "PRIORITIZING",
            "rule_name": "test-sorting-rule",
            "sub_type": "SORTING",
            "status": "ENABLED",
            "sort_order": "ASC",
            "sort_level": 1
        }
        response = item_validation.check_valid_rule_create(item)
        print("Response: ", response)
        self.assertEqual(response, [])

    def test_check_valid_rule_create_sorting_rule_missing_fields(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with sorting rule missing fields")
        item = {
            "rule_type": "PRIORITIZING",
            "rule_name": "test-sorting-rule",
            "sub_type": "SORTING",
            "status": "ENABLED"
        }
        response = item_validation.check_valid_rule_create(item)
        print("Response: ", response)
        expected_response = [
            'sort_order is required when sub_type is SORTING',
            'sort_level is required when sub_type is SORTING'
        ]
        self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_scoring_rule_string_complexity_score(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with string complexity_score")
        item = {
            "rule_type": "PRIORITIZING",
            "rule_name": "test-scoring-rule",
            "sub_type": "SCORING",
            "status": "ENABLED",
            "scoring_criteria": [
                {"upper_bound": 200, "complexity_score": "50"},  # String number
                {"lower_bound": 200, "complexity_score": "invalid"}  # Invalid string
            ]
        }
        response = item_validation.check_valid_rule_create(item)
        print("Response: ", response)
        expected_response = [
            'scoring_criteria[1].complexity_score must be a number between 0 and 100'
        ]
        self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_grouping_rule_valid(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with valid grouping rules")
        for rule_type in ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"]:
            item = {
                "rule_type": rule_type,
                "rule_name": f"test-{rule_type.lower()}-rule",
                "relationships": [
                    {
                        "asset_type": "app",
                        "asset_key": "server_ids"
                    }
                ],
                "status": "ENABLED"
            }
            response = item_validation.check_valid_rule_create(item)
            print("Response: ", response)
            self.assertEqual(response, [])

    def test_check_valid_rule_create_grouping_rule_missing_status(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with grouping rules missing status")
        
        for rule_type in ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"]:
            item = {
                "rule_type": rule_type,
                "rule_name": f"test-{rule_type.lower()}-rule",
                "relationships": [
                    {
                        "asset_type": "app",
                        "asset_key": "server_ids"
                    }
                ]
            }
            response = item_validation.check_valid_rule_create(item)
            print("Response: ", response)
            expected_response = ['status must be one of: ENABLED, DISABLED']
            self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_grouping_rule_missing_relationships(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with grouping rules missing relationships")
        
        for rule_type in ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"]:
            item = {
                "rule_type": rule_type,
                "rule_name": f"test-{rule_type.lower()}-rule",
                "status": "ENABLED"
            }
            response = item_validation.check_valid_rule_create(item)
            print("Response: ", response)
            expected_response = ['relationships is required for GROUPING rules']
            self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_grouping_rule_empty_relationships(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with grouping rules with empty relationships")
        
        for rule_type in ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"]:
            item = {
                "rule_type": rule_type,
                "rule_name": f"test-{rule_type.lower()}-rule",
                "relationships": [],
                "status": "ENABLED"
            }
            response = item_validation.check_valid_rule_create(item)
            print("Response: ", response)
            expected_response = ['relationships is required for GROUPING rules']
            self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_grouping_rule_invalid_asset_type(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with grouping rules invalid asset type")
        
        for rule_type in ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"]:
            item = {
                "rule_type": rule_type,
                "rule_name": f"test-{rule_type.lower()}-rule",
                "relationships": [
                    {
                        "asset_type": "invalid_type",
                        "asset_key": "server_ids"
                    }
                ],
                "status": "ENABLED"
            }
            response = item_validation.check_valid_rule_create(item)
            print(f"Response for {rule_type}: ", response)
            expected_response = ['relationships[0].asset_type must be one of: app, database, server']
            self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_grouping_rule_missing_asset_key(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with grouping rules invalid asset type")
        
        for rule_type in ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"]:
            item = {
                "rule_type": rule_type,
                "rule_name": f"test-{rule_type.lower()}-rule",
                "relationships": [
                    {
                        "asset_type": "app",
                    }
                ],
                "status": "ENABLED"
            }
            response = item_validation.check_valid_rule_create(item)
            print(f"Response for {rule_type}: ", response)
            expected_response = ['relationships[0].asset_key is required']
            self.assertEqual(response, expected_response)

    def test_check_valid_rule_create_grouping_rule_multiple_relationships(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: check_valid_rule_create with grouping rules multiple relationships")
        
        for rule_type in ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"]:
            item = {
                "rule_type": rule_type,
                "rule_name": f"test-{rule_type.lower()}-rule",
                "relationships": [
                    {
                        "asset_type": "app",
                        "asset_key": "app_owner"
                    },
                    {
                        "asset_type": "database",
                        "asset_key": "db_owner"
                    }
                ],
                "status": "ENABLED"
            }
            response = item_validation.check_valid_rule_create(item)
            print(f"Response for {rule_type}: ", response)
            self.assertEqual(response, [])

    def test_validate_id_string(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: validate_id_string")
        
        # Test valid cases
        self.assertIsNone(item_validation.validate_id_string("valid-id", "test_field"))
        self.assertIsNone(item_validation.validate_id_string("valid_id_123", "test_field"))

        # Test invalid cases
        self.assertIsNotNone(item_validation.validate_id_string(123, "test_field"))  # Not a string
        self.assertIsNotNone(item_validation.validate_id_string("", "test_field"))  # Empty string
        self.assertIsNotNone(item_validation.validate_id_string("a" * (item_validation.MAX_STRING_LENGTH + 1), "test_field"))  # Too long
        self.assertIsNotNone(item_validation.validate_id_string("invalid@id", "test_field"))  # Invalid characters

    def test_validate_id_list(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        log.info("Testing item_validation: validate_id_list")
        
        # Test valid cases
        self.assertIsNone(item_validation.validate_id_list(["id1", "id2"], "test_list"))

        # Test invalid cases
        self.assertIsNotNone(item_validation.validate_id_list("not-a-list", "test_list"))  # Not a list
        self.assertIsNotNone(item_validation.validate_id_list([], "test_list"))  # Empty list
        self.assertIsNotNone(item_validation.validate_id_list(["id1", "id1"], "test_list"))  # Duplicate IDs
        self.assertIsNotNone(item_validation.validate_id_list(["id1", "invalid@id"], "test_list"))  # Invalid ID

        # Test max count
        many_ids = [f"id{i}" for i in range(item_validation.MAX_LIST_COUNT + 1)]
        self.assertIsNotNone(item_validation.validate_id_list(many_ids, "test_list"))  # Too many IDs
        
    def test_validate_task_predecessors_status_no_predecessors(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        # Arrange
        item = {'task_execution_id': 'task-1'}
        task_executions = []
        
        # Act
        errors = item_validation.validate_task_predecessors_status(item, task_executions)
        
        # Assert
        self.assertEqual(errors, [])
        
    def test_validate_task_predecessors_status_valid_predecessors(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        # Arrange
        item = {'task_execution_id': 'task-1'}
        task_executions = [
            {
                'task_execution_id': 'task-1',
                'task_successors': 'predecessor-1',
                'task_execution_status': 'ABANDONED',
                'next_tasks': ['task-2']
            }
        ]
        
        # Act
        errors = item_validation.validate_task_predecessors_status(item, task_executions)
        
        # Assert
        self.assertEqual(errors, [])

    def test_validate_task_predecessors_status_invalid_predecessors(self):
        from lambda_layers.lambda_layer_items.python import item_validation
        # Arrange
        item = {'task_execution_id': 'task-1'}
        task_executions = [
            {
                'task_execution_id': 'task-1',
                'task_successors': 'task-1',
                'task_execution_status': 'IN_PROGRESS',
                'next_tasks': ['task-3'],
                'task_execution_name': 'task-1'
            }
        ]
        
        # Act
        errors = item_validation.validate_task_predecessors_status(item, task_executions)
        
        # Assert
        expected_errors = ["Can not update execution status for task as predecessor 'task-1' as it is not in a valid state (IN_PROGRESS)"]
        
        self.assertEqual(errors, expected_errors)
        
