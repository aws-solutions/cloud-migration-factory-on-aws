// @ts-nocheck


/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render} from '@testing-library/react';
import React from "react";
import EmbeddedEntityAttribute from "./EmbeddedEntityAttribute";

afterEach(cleanup);

let props = {};
props.item = {}
let attribute = {name: 'embedded_entity', type: 'embedded_entity', description: 'embedded_entity', rel_entity: "script"}
const schema = {
  status: 'loaded'
  ,
  value: [
    {
      "name": "testembeddedattribute",
      "description": "testembeddedattribute",
      "type": "date",
      "required": true,
      "long_desc": "test attribute.",
      "group": "Script Arguments"
    }
  ]
}
const schemas =  {
  "mgn": {
    "schema_type": "automation",
      "friendly_name": "MGN",
      "attributes": [
      {
        "listMultiSelect": true,
        "rel_display_attribute": "aws_accountid",
        "hidden": true,
        "rel_key": "aws_accountid",
        "description": "AWS account ID",
        "rel_entity": "application",
        "type": "relationship",
        "required": true,
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "listvalue": "All Accounts",
        "name": "accountid",
        "validation_regex_msg": "AWS account ID must be provided."
      },
      {
        "listMultiSelect": true,
        "rel_display_attribute": "app_name",
        "rel_key": "app_id",
        "source_filter_attribute_name": "waveid",
        "description": "Applications",
        "rel_entity": "application",
        "type": "relationship",
        "required": true,
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "rel_additional_attributes": [
          "aws_accountid",
          "aws_region"
        ],
        "name": "appidlist",
        "validation_regex_msg": "At least one application must be provided.",
        "rel_filter_attribute_name": "wave_id",
        "group_order": "3"
      },
      {
        "rel_display_attribute": "wave_name",
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "rel_key": "wave_id",
        "name": "waveid",
        "description": "Wave",
        "rel_entity": "wave",
        "validation_regex_msg": "Wave must be provided.",
        "group_order": "2",
        "type": "relationship",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "listvalue": "Validate Launch Template,Launch Test Instances,Mark as Ready for Cutover,Launch Cutover Instances,Finalize Cutover,- Revert to ready for testing,- Revert to ready for cutover,- Terminate Launched instances,- Disconnect from AWS,- Mark as archived",
        "name": "action",
        "description": "Action",
        "validation_regex_msg": "You must select an action to perform.",
        "group_order": "1",
        "type": "list",
        "required": true
      }
    ],
      "schema_name": "mgn",
      "group": "Rehost",
      "description": "MGN server migration",
      "actions": [
      {
        "name": "Submit",
        "apiMethod": "post",
        "id": "submit",
        "awsuistyle": "primary",
        "apiPath": "/mgn"
      }
    ]
  },
  "policy": {
    "schema_type": "system",
      "attributes": [
      {
        "system": true,
        "name": "policy_name",
        "description": "Policy Name",
        "group_order": 1,
        "type": "string",
        "required": true,
        "long_desc": "Policy name"
      },
      {
        "system": true,
        "hidden": true,
        "name": "policy_id",
        "description": "Policy Id",
        "type": "string",
        "required": true,
        "long_desc": "Policy ID"
      },
      {
        "listMultiSelect": true,
        "system": true,
        "name": "entity_access",
        "description": "Access",
        "type": "policy",
        "required": false,
        "long_desc": "Access"
      }
    ],
      "schema_name": "policy"
  },
  "group": {
    "schema_type": "system",
      "attributes": [
      {
        "name": "group_name",
        "description": "Group Name",
        "system": true,
        "type": "string",
        "required": true,
        "long_desc": "Group name"
      }
    ],
      "schema_name": "group"
  },
  "ce": {
    "schema_type": "automation",
      "friendly_name": "CloudEndure",
      "attributes": [
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "userapitoken",
        "description": "CloudEndure API Token",
        "validation_regex_msg": "CE token must be provided.",
        "type": "password",
        "required": true,
        "long_desc": "CloudEndure API token."
      },
      {
        "rel_display_attribute": "cloudendure_projectname",
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "rel_key": "cloudendure_projectname",
        "source_filter_attribute_name": "waveid",
        "name": "projectname",
        "description": "CloudEndure project name",
        "rel_entity": "application",
        "validation_regex_msg": "CE project name must be provided.",
        "rel_filter_attribute_name": "wave_id",
        "type": "relationship",
        "required": true
      },
      {
        "rel_display_attribute": "wave_name",
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "rel_key": "wave_id",
        "name": "waveid",
        "description": "Wave",
        "rel_entity": "wave",
        "validation_regex_msg": "Wave must be provided.",
        "type": "relationship",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "listvalue": "yes, no",
        "name": "dryrun",
        "description": "Dryrun",
        "validation_regex_msg": "You must choose if this is a dry run or not.",
        "type": "list",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "listvalue": "test, cutover",
        "name": "launchtype",
        "description": "Launch type",
        "validation_regex_msg": "You must select a Launch type.",
        "type": "list",
        "required": true
      },
      {
        "name": "relaunch",
        "description": "Enforce a server relaunch",
        "system": true,
        "type": "checkbox"
      }
    ],
      "schema_name": "ce",
      "group": "Rehost",
      "description": "CloudEndure server migration",
      "actions": [
      {
        "name": "Status check",
        "apiMethod": "post",
        "id": "statuscheck",
        "awsuistyle": "normal",
        "additionalData": {
          "statuscheck": "yes"
        },
        "apiPath": "/cloudendure"
      },
      {
        "name": "Remove servers from CE",
        "apiMethod": "post",
        "id": "cleanup",
        "awsuistyle": "normal",
        "additionalData": {
          "cleanup": "yes"
        },
        "apiPath": "/cloudendure"
      },
      {
        "name": "Launch",
        "apiMethod": "post",
        "id": "launch",
        "awsuistyle": "primary",
        "apiPath": "/cloudendure"
      }
    ]
  },
  "database": {
    "schema_type": "user",
      "attributes": [
      {
        "name": "database_id",
        "description": "Database Id",
        "system": true,
        "hidden": true,
        "type": "string",
        "required": true
      },
      {
        "rel_display_attribute": "app_name",
        "system": true,
        "rel_key": "app_id",
        "name": "app_id",
        "description": "Application",
        "rel_entity": "application",
        "group_order": "-998",
        "type": "relationship",
        "required": true
      },
      {
        "name": "database_name",
        "description": "Database Name",
        "group_order": "-1000",
        "system": true,
        "type": "string",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "listvalue": "oracle,mssql,db2,mysql,postgresql",
        "name": "database_type",
        "description": "Database Type",
        "validation_regex_msg": "Select a valid database type.",
        "type": "list",
        "required": true
      }
    ],
      "schema_name": "database"
  },
  "wave": {
    "schema_type": "user",
      "lastModifiedTimestamp": "2023-05-16T14:15:12.571866",
      "attributes": [
      {
        "name": "wave_id",
        "description": "Wave Id",
        "system": true,
        "hidden": true,
        "type": "string",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "wave_name",
        "description": "Wave Name",
        "validation_regex_msg": "Wave name must be specified.",
        "group_order": "-1000",
        "type": "string",
        "required": true
      },
      {
        "name": "wave_status",
        "description": "Wave Status",
        "group_order": "-999",
        "type": "list",
        "listvalue": "Not started,Planning,In progress,Completed,Blocked"
      },
      {
        "name": "wave_start_time",
        "type": "date",
        "description": "Wave Start Time"
      },
      {
        "name": "wave_end_time",
        "type": "date",
        "description": "Wave End Time"
      },
      {
        "schema": "wave",
        "name": "cutover_runbook",
        "description": "Cutover runbook URL",
        "type": "string",
        "long_desc": "URL to the Cutover runbook.",
        "group": "Migration tracking"
      }
    ],
      "schema_name": "wave"
  },
  "EC2": {
    "schema_type": "automation",
      "friendly_name": "EC2",
      "attributes": [
      {
        "rel_display_attribute": "aws_accountid",
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "rel_key": "aws_accountid",
        "name": "accountid",
        "description": "AWS account ID",
        "rel_entity": "application",
        "validation_regex_msg": "AWS account ID must be provided.",
        "type": "relationship"
      },
      {
        "rel_display_attribute": "wave_name",
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "rel_key": "wave_id",
        "name": "waveid",
        "description": "Wave",
        "rel_entity": "wave",
        "validation_regex_msg": "Wave must be provided.",
        "type": "relationship"
      }
    ],
      "schema_name": "EC2",
      "group": "RePlatform",
      "description": "New EC2 Build",
      "actions": [
      {
        "name": "EC2 Input Validation",
        "apiMethod": "post",
        "id": "EC2 Input Validation",
        "awsuistyle": "primary",
        "apiPath": "/gfvalidate"
      },
      {
        "name": "EC2 Generate CF Template",
        "apiMethod": "post",
        "id": "EC2 Generate CF Template",
        "awsuistyle": "primary",
        "apiPath": "/gfbuild"
      },
      {
        "name": "EC2 Deployment",
        "apiMethod": "post",
        "id": "EC2 Deployment",
        "awsuistyle": "primary",
        "apiPath": "/gfdeploy"
      }
    ]
  },
  "job": {
    "schema_type": "automation",
      "friendly_name": "Job",
      "attributes": [
      {
        "system": true,
        "hidden": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "SSMId",
        "description": "SSMID",
        "validation_regex_msg": "CE token must be provided.",
        "type": "string",
        "long_desc": "SSM Task ID [system generated]."
      },
      {
        "default": "i-0de99e421ecf0fc2c",
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "mi_id",
        "description": "SSM Instance ID",
        "validation_regex_msg": "MI must be supplied.",
        "type": "string",
        "long_desc": "SSM Instance IDs. Only showing those with a tag defined of role=mf_automation"
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "jobname",
        "description": "Job Name",
        "validation_regex_msg": "Job name must be supplied.",
        "type": "string",
        "required": true,
        "long_desc": "Job name."
      },
      {
        "name": "outputLastMessage",
        "description": "Last Message",
        "system": true,
        "type": "string",
        "required": true,
        "long_desc": "Last Message."
      },
      {
        "lookup": "script.package_uuid",
        "system": true,
        "rel_attribute": "script_arguments",
        "rel_key": "package_uuid",
        "name": "script.script_arguments",
        "description": "Script Arguments",
        "rel_entity": "script",
        "type": "embedded_entity",
        "required": true,
        "long_desc": "Automation Script."
      },
      {
        "name": "script.script_name",
        "description": "Script Name",
        "system": true,
        "type": "string",
        "long_desc": "Automation Script."
      },
      {
        "name": "script.package_uuid",
        "description": "Script Package UUID",
        "system": true,
        "type": "string",
        "long_desc": "Automation Script UUID."
      },
      {
        "name": "script.default",
        "description": "Script Version",
        "system": true,
        "type": "string",
        "long_desc": "Automation Script Version Run."
      },
      {
        "name": "script.script_description",
        "description": "Script Description",
        "system": true,
        "type": "string",
        "long_desc": "Automation Script Description."
      },
      {
        "name": "script.script_masterfile",
        "description": "Script FileName",
        "system": true,
        "type": "string",
        "long_desc": "Automation script file name."
      },
      {
        "name": "status",
        "description": "Status",
        "system": true,
        "type": "status",
        "required": true,
        "long_desc": "Job Status."
      },
      {
        "name": "SSMAutomationExecutionId",
        "description": "SSM Execution ID",
        "system": true,
        "type": "string",
        "required": true,
        "long_desc": "SSM Execution ID."
      },
      {
        "name": "uuid",
        "description": "Job ID",
        "system": true,
        "type": "string",
        "long_desc": "Migration Factory Job ID."
      }
    ],
      "schema_name": "job",
      "description": "Automation",
      "actions": []
  },
  "application": {
    "schema_type": "user",
      "lastModifiedTimestamp": "2023-05-16T14:15:12.433004",
      "attributes": [
      {
        "name": "app_id",
        "description": "Application Id",
        "system": true,
        "hidden": true,
        "type": "string",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "app_name",
        "description": "Application Name",
        "validation_regex_msg": "Application name must be specified.",
        "group_order": "-1000",
        "type": "string",
        "required": true
      },
      {
        "system": true,
        "rel_display_attribute": "wave_name",
        "rel_key": "wave_id",
        "name": "wave_id",
        "description": "Wave Id",
        "rel_entity": "wave",
        "group_order": "-999",
        "type": "relationship",
        "required": false
      },
      {
        "name": "cloudendure_projectname",
        "description": "CloudEndure Project Name",
        "system": true,
        "type": "list",
        "listvalue": "project1,project2",
        "group": "Target"
      },
      {
        "schema": "application",
        "system": true,
        "validation_regex": "^\\d{12}$",
        "listvalue": "123456789012",
        "name": "aws_accountid",
        "description": "AWS Account Id",
        "validation_regex_msg": "Invalid AWS account Id.",
        "type": "list",
        "required": true,
        "group": "Target"
      },
      {
        "system": true,
        "listvalue": "us-east-2,us-east-1,us-west-1,us-west-2,af-south-1,ap-east-1,ap-southeast-3,ap-south-1,ap-northeast-3,ap-northeast-2,ap-southeast-1,ap-southeast-2,ap-northeast-1,ca-central-1,cn-north-1,cn-northwest-1,eu-central-1,eu-west-1,eu-west-2,eu-south-1,eu-west-3,eu-north-1,me-south-1,sa-east-1",
        "name": "aws_region",
        "description": "AWS Region",
        "type": "list",
        "required": true,
        "group": "Target"
      },
      {
        "schema": "application",
        "name": "cutover_runbook",
        "description": "Cutover runbook URL",
        "type": "string",
        "long_desc": "URL to the Cutover runbook for the tracking of this application.",
        "group": "Migration tracking"
      }
    ],
      "schema_name": "app"
  },
  "template": {
    "schema_type": "user",
      "attributes": [
      {
        "name": "template_id",
        "description": "Template Id",
        "system": true,
        "hidden": true,
        "type": "string",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "yemplate_name",
        "description": "Template name",
        "validation_regex_msg": "Template name must be specified.",
        "group_order": "-1000",
        "type": "string",
        "required": true
      }
    ],
      "schema_name": "template"
  },
  "script": {
    "schema_type": "system",
      "attributes": [
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "script_name",
        "description": "Script Name",
        "validation_regex_msg": "Provide a name for this script.",
        "type": "string",
        "required": true,
        "long_desc": "Script name."
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "script_description",
        "description": "Script Description",
        "validation_regex_msg": "Provide a description of the outcome for this script.",
        "type": "string",
        "required": true,
        "long_desc": "Script description."
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "fileName",
        "description": "Script Filename",
        "validation_regex_msg": "Select a filename.",
        "type": "string",
        "long_desc": "Script filename."
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "path",
        "description": "Script path",
        "validation_regex_msg": "Select a file path.",
        "type": "string",
        "long_desc": "Script path."
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "script_masterfile",
        "description": "Script master filename",
        "validation_regex_msg": "Select a master filename path.",
        "type": "string",
        "long_desc": "Script master filename."
      },
      {
        "name": "package_uuid",
        "description": "Script UUID",
        "system": true,
        "type": "string",
        "long_desc": "Automation script UUID."
      },
      {
        "system": true,
        "readonly": true,
        "name": "default",
        "description": "Default Version",
        "type": "string",
        "required": true,
        "long_desc": "Default Version."
      },
      {
        "system": true,
        "readonly": true,
        "name": "latest",
        "description": "Latest Version",
        "type": "string",
        "required": true,
        "long_desc": "Latest Version."
      }
    ],
      "schema_name": "script"
  },
  "pipeline": {
    "schema_type": "user",
      "attributes": [
      {
        "name": "pipeline_id",
        "description": "Pipeline Id",
        "system": true,
        "hidden": true,
        "type": "string",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "pipeline_name",
        "description": "Pipeline name",
        "validation_regex_msg": "Pipeline name must be specified.",
        "group_order": "-1000",
        "type": "string",
        "required": true
      }
    ],
      "schema_name": "pipeline"
  },
  "user": {
    "schema_type": "system",
      "attributes": [
      {
        "system": true,
        "hidden": true,
        "name": "userRef",
        "description": "User reference",
        "type": "string",
        "required": true,
        "long_desc": "User reference"
      },
      {
        "name": "email",
        "description": "User Email address",
        "system": true,
        "type": "string",
        "required": true,
        "long_desc": "User Email address"
      },
      {
        "name": "enabled",
        "description": "User enabled",
        "system": true,
        "type": "checkbox",
        "required": true,
        "long_desc": "User enabled"
      },
      {
        "name": "status",
        "description": "User status",
        "system": true,
        "type": "string",
        "required": true,
        "long_desc": "User status"
      },
      {
        "name": "groups",
        "description": "User groups",
        "system": true,
        "type": "groups",
        "required": true,
        "long_desc": "User groups"
      },
      {
        "name": "mfaEnabled",
        "description": "User MFA enabled",
        "system": true,
        "type": "checkbox",
        "required": true,
        "long_desc": "User MFA enabled"
      }
    ],
      "schema_name": "user"
  },
  "server": {
    "schema_type": "user",
      "lastModifiedTimestamp": "2023-05-16T10:03:45.651720",
      "attributes": [
      {
        "name": "server_id",
        "description": "Server Id",
        "system": true,
        "hidden": true,
        "type": "string",
        "required": true
      },
      {
        "rel_display_attribute": "app_name",
        "system": true,
        "rel_key": "app_id",
        "name": "app_id",
        "description": "Application",
        "rel_entity": "application",
        "group_order": "-998",
        "type": "relationship",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9])\\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\\-]*[A-Za-z0-9])$",
        "name": "server_name",
        "description": "Server Name",
        "validation_regex_msg": "Server names must contain only aplhanumeric, hyphen or period characters.",
        "group_order": "-1000",
        "type": "string",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "listvalue": "windows,linux",
        "name": "server_os_family",
        "description": "Server OS Family",
        "validation_regex_msg": "Select a valid operating system.",
        "type": "list",
        "required": true
      },
      {
        "name": "server_os_version",
        "description": "Server OS Version",
        "system": true,
        "type": "string",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9])\\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\\-]*[A-Za-z0-9])$",
        "name": "server_fqdn",
        "description": "Server FQDN",
        "validation_regex_msg": "Server FQDN must contain only aplhanumeric, hyphen or period charaters.",
        "group_order": "-999",
        "type": "string",
        "required": true
      },
      {
        "name": "server_tier",
        "description": "Server Tier",
        "system": true,
        "type": "string"
      },
      {
        "name": "server_environment",
        "description": "Server Environment",
        "group_order": "-997",
        "system": true,
        "type": "string"
      },
      {
        "system": true,
        "validation_regex": "^(subnet-([a-z0-9]{8}|[a-z0-9]{17})$)",
        "name": "subnet_IDs",
        "description": "Subnet Ids",
        "validation_regex_msg": "Subnets must start with subnet-, followed by 8 or 17 alphanumeric characters.",
        "type": "multivalue-string",
        "conditions": {
          "queries": [
            {
              "comparator": "!empty",
              "attribute": "network_interface_id"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ],
            "false": [
              "not_required"
            ]
          }
        },
        "group": "Target - Networking"
      },
      {
        "system": true,
        "validation_regex": "^(sg-([a-z0-9]{8}|[a-z0-9]{17})$)",
        "name": "securitygroup_IDs",
        "description": "Security Group Ids",
        "validation_regex_msg": "Security groups must start with sg-, followed by 8 or 17 alphanumeric characters.",
        "type": "multivalue-string",
        "group": "Target - Networking"
      },
      {
        "system": true,
        "validation_regex": "^(subnet-([a-z0-9]{8}|[a-z0-9]{17})$)",
        "name": "subnet_IDs_test",
        "description": "Subnet Ids - Test1",
        "validation_regex_msg": "Subnets must start with subnet-, followed by 8 or 17 alphanumeric characters.",
        "type": "multivalue-string",
        "conditions": {
          "queries": [
            {
              "comparator": "!empty",
              "attribute": "network_interface_id_test"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ],
            "false": [
              "not_required"
            ]
          }
        },
        "group": "Target"
      },
      {
        "system": true,
        "validation_regex": "^(sg-([a-z0-9]{8}|[a-z0-9]{17})$)",
        "name": "securitygroup_IDs_test",
        "description": "Security Group Ids - Test",
        "validation_regex_msg": "Security groups must start with sg-, followed by 8 or 17 alphanumeric characters.",
        "type": "multivalue-string",
        "group": "Target - Networking"
      },
      {
        "name": "instanceType",
        "description": "Instance Type",
        "system": true,
        "type": "string",
        "group": "Target"
      },
      {
        "name": "iamRole",
        "description": "EC2 Instance Profile Name",
        "system": true,
        "type": "string",
        "group": "Target",
        "long_desc": "Verify that the value entered here is the Instance Profile name not the IAM Role name, they maybe different. If you use the AWS CLI, API, or an AWS SDK to create a role, you create the role and instance profile as separate actions, with potentially different names."
      },
      {
        "system": true,
        "validation_regex": "^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\\.|$)){4}",
        "name": "private_ip",
        "description": "Private IP",
        "validation_regex_msg": "A valid IPv4 IP address must be provided.",
        "type": "string",
        "group": "Target - Networking"
      },
      {
        "name": "tags",
        "description": "Tags",
        "system": true,
        "type": "tag",
        "group": "Target - Instance"
      },
      {
        "name": "tenancy",
        "description": "Tenancy",
        "system": true,
        "type": "list",
        "listvalue": "Shared,Dedicated,Dedicated host",
        "group": "Target"
      },
      {
        "name": "migration_status",
        "description": "Migration Status",
        "system": true,
        "type": "string",
        "group": "Status"
      },
      {
        "name": "replication_status",
        "description": "Replication Status",
        "system": true,
        "type": "string",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Rehost",
              "attribute": "r_type"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ],
            "false": [
              "not_required"
            ]
          }
        },
        "group": "Status"
      },
      {
        "schema": "server",
        "system": true,
        "help_content": {
          "header": "Migration Strategy",
          "content_html": "The following Migration Strategies are commonly used in Cloud Migration projects.  The AWS Cloud Migration factory solution supports the automation activities to assist with these strategies, for Rehost and Replatform prepackaged automations are provided, and for other strategies customized automations can be created and imported into the AWS CMF solution:\n<ul>\n<li><b>Retire</b> - Server retired and not migrated, data will need to be removed and any software services decommissioned.</li>\n<li><b>Retain</b> - Server will remain on-premise , assessment should be preformed to verify any changes for migrating dependent services.</li>\n<li><b>Relocate</b> - VMware virtual machine on-premise, is due to be relocated to VMware Cloud on AWS, using VMware HCX. Currently AWS CMF does not natively support this capability, although custom automation script packages coudl be used to interface with this service.</li>\n<li><b>Rehost</b> - AWS Cloud Migration Factory supports native integration with AWS MGN, selecting this strategy will enable the options in the server UI to support specifying the required parameters to migrate a server instance to EC2 using block level replication. The AWS CMF Solution comes packaged will all the required automation scripts to support the standard tasks required to migrate a server, all of which can be initiated from the CMF web interface.</li>\n<li><b>Repurchase</b> - Service that the server is currently supporting will be replaced with another service.</li>\n<li><b>Replatform</b> - AWS Cloud Migration Factory supports native integration to create Cloud Formation templates for each application in a wave, these Cloud Formation template are automatically generated through the UI based on the properties of the servers defined here, and can then be deployed to any account that has had the target AWS CMF Solution CFT deployed.</li>\n<li><b>Reachitect</b> - Service will be rebuilt from other services in the AWS Cloud.</li>\n</ul>\n"
        },
        "listvalue": "Retire,Retain,Relocate,Rehost,Repurchase,Replatform,Reachitect,TBC,Replatform - A2C",
        "name": "r_type",
        "description": "Migration Strategy",
        "type": "list",
        "required": true
      },
      {
        "system": true,
        "validation_regex": "^(h-([a-z0-9]{8}|[a-z0-9]{17})$)",
        "name": "dedicated_host_id",
        "description": "Dedicated Host ID",
        "validation_regex_msg": "Dedicated Host IDs must start with h-, followed by 8 or 17 alphanumeric characters.",
        "type": "string",
        "conditions": {
          "outcomes": {
            "true": [
              "required"
            ],
            "false": [
              "not_required",
              "hidden"
            ]
          },
          "queries": [
            {
              "comparator": "=",
              "value": "Dedicated host",
              "attribute": "tenancy"
            }
          ]
        },
        "group": "Target"
      },
      {
        "system": true,
        "help_content": {
          "header": "Network Interface ID",
          "content_html": "If Network Interface ID is provided you cannot set Subnet IDs, as the instance will be launched with this Network Interface ID.\n\nThis Network Interface ID will be assigned to the migrating server."
        },
        "validation_regex": "^(eni-([a-z0-9]{8}|[a-z0-9]{17})$)",
        "name": "network_interface_id",
        "description": "Network Interface ID",
        "validation_regex_msg": "Network Interface ID must start with eni- followed by 8 or 17 alphanumeric characters.",
        "type": "string",
        "conditions": {
          "queries": [
            {
              "comparator": "!empty",
              "attribute": "subnet_IDs"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ],
            "false": [
              "not_required"
            ]
          }
        },
        "group": "Target - Networking"
      },
      {
        "system": true,
        "help_content": {
          "header": "Network Interface ID - Test",
          "content_html": "If 'Network Interface ID -Test' is provided you cannot set 'Subnet IDs - Test', as the instance will be launched with this Network Interface ID.\n\nThis Network Interface ID will be assigned to the migrating server."
        },
        "validation_regex": "^(eni-([a-z0-9]{8}|[a-z0-9]{17})$)",
        "name": "network_interface_id_test",
        "description": "Network Interface ID - Test",
        "validation_regex_msg": "Network Interface ID must start with eni- followed by 8 or 17 alphanumeric characters.",
        "type": "string",
        "conditions": {
          "queries": [
            {
              "comparator": "!empty",
              "attribute": "subnet_IDs_test"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ],
            "false": [
              "not_required"
            ]
          }
        },
        "group": "Target - Networking"
      },
      {
        "system": true,
        "validation_regex": "^([1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[1][0-6][0-3][0-8][0-4])$",
        "name": "root_vol_size",
        "description": "Root Volume Size (GiB)",
        "validation_regex_msg": "Volume Size needs to between 1 GiB and 16384 GiB",
        "type": "Integer",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "root_vol_size"
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
        },
        "group": "Target - Storage"
      },
      {
        "system": true,
        "validation_regex": "^(ami-(([a-z0-9]{8,17})+)$)",
        "name": "ami_id",
        "description": "AMI Id",
        "validation_regex_msg": "AMI ID must start with ami- and followed by upto 12 alphanumeric characters.",
        "type": "string",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "ami_id"
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
        },
        "group": "Target"
      },
      {
        "name": "availabilityzone",
        "description": "Availability zone",
        "system": true,
        "type": "string",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "availabilityzone"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target"
      },
      {
        "system": true,
        "listvalue": "standard,io1,io2,gp2,gp3,",
        "name": "root_vol_type",
        "description": "Root Volume Type",
        "type": "list",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "root_vol_type"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target - Storage"
      },
      {
        "system": true,
        "validation_regex": "^([1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[1][0-6][0-3][0-8][0-4])$",
        "name": "add_vols_size",
        "description": "Additional Volume Sizes (GiB)",
        "validation_regex_msg": "Volume Sizes need to be between 1 GiB and 16384 GiB",
        "type": "multivalue-string",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "add_vols_size"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target - Storage"
      },
      {
        "system": true,
        "validation_regex": "^(standard|io1|io2|gp2|gp3)$",
        "name": "add_vols_type",
        "description": "Additional Volume Types (standard, io1, io2, gp2, or gp3)",
        "validation_regex_msg": "Allowed Volume Types \"standard\", \"io1\", \"io2\", \"gp2\", or \"gp3\"",
        "type": "multivalue-string",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "add_vols_type"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target - Storage"
      },
      {
        "name": "ebs_optimized",
        "description": "Enable EBS Optimized",
        "system": true,
        "type": "checkbox",
        "conditions": {
          "queries": [],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target - Storage"
      },
      {
        "system": true,
        "validation_regex": "^(arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/){0,1}[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
        "name": "ebs_kmskey_id",
        "description": "EBS KMS Key Id or ARN for Volume Encryption",
        "validation_regex_msg": "Provide a valid KMS Key or ARN.",
        "type": "string",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "ebs_kmskey_id"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target - Storage"
      },
      {
        "name": "detailed_monitoring",
        "description": "Enable Detailed Monitoring",
        "system": true,
        "type": "checkbox",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "detailed_monitoring"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target"
      },
      {
        "system": true,
        "listvalue": "/dev/sda1,/dev/xvda,",
        "name": "root_vol_name",
        "description": "Root Volume Name",
        "type": "list",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "root_vol_name"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target - Storage"
      },
      {
        "name": "add_vols_name",
        "description": "Additional Volume Names",
        "system": true,
        "type": "multivalue-string",
        "conditions": {
          "queries": [
            {
              "comparator": "!=",
              "value": "Replatform",
              "attribute": "r_type"
            },
            {
              "comparator": "empty",
              "attribute": "add_vols_name"
            }
          ],
          "outcomes": {
            "true": [
              "hidden"
            ]
          }
        },
        "group": "Target - Storage"
      },
      {
        "name": "server_test_json",
        "type": "json",
        "description": "Json"
      },
      {
        "name": "instance_metadata_options_tags",
        "type": "checkbox",
        "description": "Enable instance metadata tags"
      },
      {
        "hidden": true,
        "name": "show_advanced_instance_parameters",
        "description": "Show advanced instance parameters",
        "group_order": "1",
        "type": "checkbox",
        "conditions": {
          "queries": [
            {
              "comparator": "=",
              "value": "Rehost",
              "attribute": "r_type"
            }
          ],
          "outcomes": {
            "true": [
              "not_hidden"
            ],
            "false": [
              "hidden"
            ]
          }
        },
        "group": "Target - Instance"
      },
      {
        "name": "volumetype",
        "type": "string",
        "description": "Volume Type"
      },
      {
        "hidden": true,
        "listvalue": "standard,io1,io2,gp2,gp3,",
        "name": "ebs_volume_type",
        "description": "EBS volume type",
        "group_order": "100",
        "type": "list",
        "conditions": {
          "queries": [
            {
              "comparator": "=",
              "value": "Rehost",
              "attribute": "r_type"
            },
            {
              "comparator": "!empty",
              "attribute": "show_advanced_instance_parameters"
            }
          ],
          "outcomes": {
            "true": [
              "not_hidden"
            ],
            "false": [
              "hidden"
            ]
          }
        },
        "group": "Target - Instance"
      },
      {
        "name": "private_ip_test",
        "type": "string",
        "description": "Private IP Address - Test"
      },
      {
        "name": "termination_protection_test",
        "type": "checkbox",
        "description": "Enable termination protection - test"
      },
      {
        "name": "termination_protection",
        "type": "checkbox",
        "description": "Enable termination protection"
      },
      {
        "listMultiSelect": true,
        "rel_display_attribute": "app_name",
        "rel_key": "app_id",
        "name": "all_applications",
        "description": "All applications",
        "rel_entity": "application",
        "type": "relationship"
      }
    ],
      "schema_name": "server"
  },
  "role": {
    "schema_type": "system",
      "attributes": [
      {
        "system": true,
        "name": "role_name",
        "description": "Role Name",
        "group_order": 1,
        "type": "string",
        "required": true,
        "long_desc": "Role name"
      },
      {
        "system": true,
        "hidden": true,
        "name": "role_id",
        "description": "Role Id",
        "type": "string",
        "required": true,
        "long_desc": "Role ID"
      },
      {
        "listMultiSelect": true,
        "system": true,
        "name": "groups",
        "description": "Groups",
        "type": "groups",
        "listValueAPI": "/admin/groups",
        "required": true,
        "long_desc": "Groups"
      },
      {
        "listMultiSelect": true,
        "system": true,
        "rel_display_attribute": "policy_name",
        "rel_key": "policy_id",
        "name": "policies",
        "description": "Attached Policies",
        "rel_entity": "policy",
        "type": "policies",
        "required": true,
        "long_desc": "Policies"
      }
    ],
      "schema_name": "role"
  },
  "secret": {
    "schema_type": "system",
      "attributes": [
      {
        "name": "name",
        "description": "Secret Name",
        "system": true,
        "type": "string",
        "long_desc": "Secret name."
      },
      {
        "name": "description",
        "description": "Secret Description",
        "system": true,
        "type": "string",
        "long_desc": "Secret description."
      },
      {
        "name": "data.SECRET_TYPE",
        "description": "Secret Type",
        "system": true,
        "type": "string",
        "long_desc": "Secret Type."
      }
    ],
      "schema_name": "secret"
  },
  "ssm_job": {
    "schema_type": "automation",
      "friendly_name": "Run Automation",
      "attributes": [
      {
        "system": true,
        "name": "mi_id",
        "description": "Automation Server",
        "group_order": "3",
        "type": "list",
        "listValueAPI": "/ssm",
        "valueKey": "mi_id",
        "labelKey": "mi_name",
        "required": true,
        "long_desc": "SSM Instance IDs. Only showing those with a tag defined of role=mf_automation"
      },
      {
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "name": "jobname",
        "description": "Job Name",
        "validation_regex_msg": "Job name must be supplied.",
        "group_order": "1",
        "type": "string",
        "required": true,
        "long_desc": "Job name."
      },
      {
        "rel_display_attribute": "script_name",
        "system": true,
        "validation_regex": "^(?!\\s*$).+",
        "rel_key": "package_uuid",
        "name": "script.package_uuid",
        "description": "Script Name",
        "rel_entity": "script",
        "validation_regex_msg": "Script name must be provided.",
        "group_order": "3",
        "type": "relationship",
        "required": true
      },
      {
        "lookup": "script.package_uuid",
        "system": true,
        "rel_attribute": "script_arguments",
        "rel_key": "package_uuid",
        "name": "script.script_arguments",
        "description": "Script Arguments",
        "rel_entity": "script",
        "group_order": "4",
        "type": "embedded_entity",
        "required": true,
        "long_desc": "Automation Script."
      }
    ],
      "schema_name": "ssm_job",
      "description": "Run Automation",
      "actions": [
      {
        "name": "Submit Automation Job",
        "apiMethod": "post",
        "id": "submit",
        "awsuistyle": "primary",
        "apiPath": "/ssm"
      }
    ]
  }
}
const userAccess = {
  "application": {
    "create": true,
      "read": true,
      "update": true,
      "delete": true,
      "attributes": [
      {
        "attr_type": "application",
        "attr_name": "app_id"
      },
      {
        "attr_type": "application",
        "attr_name": "app_name"
      },
      {
        "attr_type": "application",
        "attr_name": "wave_id"
      },
      {
        "attr_type": "application",
        "attr_name": "cloudendure_projectname"
      },
      {
        "attr_type": "application",
        "attr_name": "aws_accountid"
      },
      {
        "attr_type": "application",
        "attr_name": "aws_region"
      }
    ]
  },
  "wave": {
    "create": true,
      "read": true,
      "update": true,
      "delete": true,
      "attributes": [
      {
        "attr_type": "wave",
        "attr_name": "wave_id"
      },
      {
        "attr_type": "wave",
        "attr_name": "wave_name"
      },
      {
        "attr_type": "wave",
        "attr_name": "wave_status"
      },
      {
        "attr_type": "wave",
        "attr_name": "wave_start_time"
      },
      {
        "attr_type": "wave",
        "attr_name": "wave_end_time"
      }
    ]
  },
  "server": {
    "create": true,
      "read": true,
      "update": true,
      "delete": true,
      "attributes": [
      {
        "attr_type": "server",
        "attr_name": "server_id"
      },
      {
        "attr_type": "server",
        "attr_name": "app_id"
      },
      {
        "attr_type": "server",
        "attr_name": "server_name"
      },
      {
        "attr_type": "server",
        "attr_name": "server_os_family"
      },
      {
        "attr_type": "server",
        "attr_name": "server_os_version"
      },
      {
        "attr_type": "server",
        "attr_name": "server_fqdn"
      },
      {
        "attr_type": "server",
        "attr_name": "server_tier"
      },
      {
        "attr_type": "server",
        "attr_name": "server_environment"
      },
      {
        "attr_type": "server",
        "attr_name": "subnet_IDs"
      },
      {
        "attr_type": "server",
        "attr_name": "securitygroup_IDs"
      },
      {
        "attr_type": "server",
        "attr_name": "subnet_IDs_test"
      },
      {
        "attr_type": "server",
        "attr_name": "securitygroup_IDs_test"
      },
      {
        "attr_type": "server",
        "attr_name": "instanceType"
      },
      {
        "attr_type": "server",
        "attr_name": "iamRole"
      },
      {
        "attr_type": "server",
        "attr_name": "private_ip"
      },
      {
        "attr_type": "server",
        "attr_name": "tags"
      },
      {
        "attr_type": "server",
        "attr_name": "tenancy"
      },
      {
        "attr_type": "server",
        "attr_name": "migration_status"
      },
      {
        "attr_type": "server",
        "attr_name": "replication_status"
      },
      {
        "attr_type": "server",
        "attr_name": "r_type"
      },
      {
        "attr_type": "server",
        "attr_name": "dedicated_host_id"
      },
      {
        "attr_type": "server",
        "attr_name": "network_interface_id"
      },
      {
        "attr_type": "server",
        "attr_name": "network_interface_id_test"
      },
      {
        "attr_type": "server",
        "attr_name": "root_vol_size"
      },
      {
        "attr_type": "server",
        "attr_name": "ami_id"
      },
      {
        "attr_type": "server",
        "attr_name": "availabilityzone"
      },
      {
        "attr_type": "server",
        "attr_name": "root_vol_type"
      },
      {
        "attr_type": "server",
        "attr_name": "add_vols_size"
      },
      {
        "attr_type": "server",
        "attr_name": "add_vols_type"
      },
      {
        "attr_type": "server",
        "attr_name": "ebs_optimized"
      },
      {
        "attr_type": "server",
        "attr_name": "ebs_kmskey_id"
      },
      {
        "attr_type": "server",
        "attr_name": "detailed_monitoring"
      },
      {
        "attr_type": "server",
        "attr_name": "root_vol_name"
      },
      {
        "attr_type": "server",
        "attr_name": "add_vols_name"
      },
      {
        "attr_type": "server",
        "attr_name": "server_test_json"
      },
      {
        "attr_type": "server",
        "attr_name": "instance_metadata_options_tags"
      },
      {
        "attr_type": "server",
        "attr_name": "show_advanced_instance_parameters"
      },
      {
        "attr_type": "server",
        "attr_name": "volumetype"
      },
      {
        "attr_type": "server",
        "attr_name": "ebs_volume_type"
      },
      {
        "attr_type": "server",
        "attr_name": "private_ip_test"
      },
      {
        "attr_type": "server",
        "attr_name": "termination_protection_test"
      },
      {
        "attr_type": "server",
        "attr_name": "termination_protection"
      }
    ]
  },
  "database": {
    "create": true,
      "read": true,
      "update": true,
      "delete": true,
      "attributes": [
      {
        "attr_type": "database",
        "attr_name": "database_id"
      },
      {
        "attr_type": "database",
        "attr_name": "app_id"
      },
      {
        "attr_type": "database",
        "attr_name": "database_name"
      },
      {
        "attr_type": "database",
        "attr_name": "database_type"
      }
    ]
  },
  "mgn": {
    "create": true,
      "attributes": []
  },
  "ce": {
    "create": true,
      "attributes": []
  },
  "ssm_job": {
    "create": true,
      "attributes": []
  },
  "script": {
    "create": true,
      "read": false,
      "update": true,
      "delete": false,
      "attributes": [
      {
        "attr_type": "script",
        "attr_name": "script_name"
      },
      {
        "attr_type": "script",
        "attr_name": "script_description"
      },
      {
        "attr_type": "script",
        "attr_name": "fileName"
      },
      {
        "attr_type": "script",
        "attr_name": "path"
      },
      {
        "attr_type": "script",
        "attr_name": "script_masterfile"
      },
      {
        "attr_type": "script",
        "attr_name": "default"
      },
      {
        "attr_type": "script",
        "attr_name": "latest"
      }
    ]
  },
  "EC2": {
    "create": true,
      "attributes": []
  }
}
var item = {
  "script": {
    "package_uuid": "d5ec74d4-9410-4525-83ce-c162ba36ed69"
  }
}


// Function stubs
const handleUserInput = () => {

}

const displayInfoLink = () => {

}

const handleStub = () => {

}

const setup = () => {
  const comp =  render(
    <EmbeddedEntityAttribute
      schemas={schemas}
      parentSchemaType={'automation'}
      parentSchemaName={'ssm_job'}
      parentUserAccess={userAccess}
      embeddedEntitySchema={schema}
      attribute={attribute}
      embeddedItem={item}
      handleUserInput={handleUserInput}
      displayHelpInfoLink={displayInfoLink}
      handleUpdateValidationErrors={handleStub}
    />)

  return {
    ...comp,
  }
}

test('EmbeddedEntityAttribute displays an attribute and text provided', () => {
  setup()
  expect(screen.getByText('testembeddedattribute')).toBeTruthy();
});