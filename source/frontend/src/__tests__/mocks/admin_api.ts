/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { rest } from "msw";
import { testGroups, testPolicies } from "../TestUtils";

export const mock_admin_api = [
  rest.get("/admin/role", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/admin/policy", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/admin/users", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/admin/schema/mgn", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        mgn: {
          schema_type: "automation",
          friendly_name: "MGN",
          attributes: [
            {
              listMultiSelect: true,
              rel_display_attribute: "aws_accountid",
              hidden: true,
              rel_key: "aws_accountid",
              description: "AWS account ID",
              rel_entity: "application",
              type: "relationship",
              required: true,
              system: true,
              validation_regex: "^(?!\\s*$).+",
              listvalue: "All Accounts",
              name: "accountid",
              validation_regex_msg: "AWS account ID must be provided.",
            },
            {
              listMultiSelect: true,
              rel_display_attribute: "app_name",
              rel_key: "app_id",
              source_filter_attribute_name: "waveid",
              description: "Applications",
              rel_entity: "application",
              type: "relationship",
              required: true,
              system: true,
              validation_regex: "^(?!\\s*$).+",
              rel_additional_attributes: ["aws_accountid", "aws_region"],
              name: "appidlist",
              validation_regex_msg: "At least one application must be provided.",
              rel_filter_attribute_name: "wave_id",
              group_order: "3",
            },
            {
              rel_display_attribute: "wave_name",
              system: true,
              validation_regex: "^(?!\\s*$).+",
              rel_key: "wave_id",
              name: "waveid",
              description: "Wave",
              rel_entity: "wave",
              validation_regex_msg: "Wave must be provided.",
              group_order: "2",
              type: "relationship",
              required: true,
            },
            {
              system: true,
              validation_regex: "^(?!\\s*$).+",
              listvalue:
                "Validate Launch Template,Launch Test Instances,Mark as Ready for Cutover,Launch Cutover Instances,Finalize Cutover,- Revert to ready for testing,- Revert to ready for cutover,- Terminate Launched instances,- Disconnect from AWS,- Mark as archived",
              name: "action",
              description: "Action",
              validation_regex_msg: "You must select an action to perform.",
              group_order: "1",
              type: "list",
              required: true,
            },
          ],
          schema_name: "mgn",
          group: "Rehost",
          description: "MGN server migration",
          actions: [
            {
              name: "Submit",
              apiMethod: "post",
              id: "submit",
              awsuistyle: "primary",
              apiPath: "/mgn",
            },
          ],
        },
      })
    );
  }),
  rest.get("/admin/schema/policy", (request, response, context) => {
    return response(context.status(200), context.json(testPolicies));
  }),
  rest.get("/admin/schema/group", (request, response, context) => {
    return response(context.status(200), context.json(testGroups));
  }),
  rest.get("/admin/schema/wave", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "user",
        attributes: [
          {
            name: "wave_id",
            description: "Wave Id",
            system: true,
            hidden: true,
            type: "string",
            required: true,
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "wave_name",
            description: "Wave Name",
            validation_regex_msg: "Wave name must be specified.",
            group_order: "-1000",
            type: "string",
            required: true,
          },
          {
            name: "wave_status",
            description: "Wave Status",
            group_order: "-999",
            type: "list",
            listvalue: "Not started,Planning,In progress,Completed,Blocked",
          },
          {
            name: "wave_start_time",
            type: "date",
            description: "Wave Start Time",
          },
          {
            name: "wave_end_time",
            type: "date",
            description: "Wave End Time",
          },
        ],
        schema_name: "wave",
      })
    );
  }),
  rest.get("/admin/schema/EC2", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "automation",
        friendly_name: "EC2",
        attributes: [
          {
            rel_display_attribute: "aws_accountid",
            system: true,
            validation_regex: "^(?!\\s*$).+",
            rel_key: "aws_accountid",
            name: "accountid",
            description: "AWS account ID",
            rel_entity: "application",
            validation_regex_msg: "AWS account ID must be provided.",
            type: "relationship",
          },
          {
            rel_display_attribute: "wave_name",
            system: true,
            validation_regex: "^(?!\\s*$).+",
            rel_key: "wave_id",
            name: "waveid",
            description: "Wave",
            rel_entity: "wave",
            validation_regex_msg: "Wave must be provided.",
            type: "relationship",
          },
        ],
        schema_name: "EC2",
        group: "RePlatform",
        description: "New EC2 Build",
        actions: [
          {
            name: "EC2 Input Validation",
            apiMethod: "post",
            id: "EC2 Input Validation",
            awsuistyle: "primary",
            apiPath: "/gfvalidate",
          },
          {
            name: "EC2 Generate CF Template",
            apiMethod: "post",
            id: "EC2 Generate CF Template",
            awsuistyle: "primary",
            apiPath: "/gfbuild",
          },
          {
            name: "EC2 Deployment",
            apiMethod: "post",
            id: "EC2 Deployment",
            awsuistyle: "primary",
            apiPath: "/gfdeploy",
          },
        ],
      })
    );
  }),
  rest.get("/admin/schema/job", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "automation",
        friendly_name: "Job",
        attributes: [
          {
            system: true,
            hidden: true,
            validation_regex: "^(?!\\s*$).+",
            name: "SSMId",
            description: "SSMID",
            validation_regex_msg: "CE token must be provided.",
            type: "string",
            long_desc: "SSM Task ID [system generated].",
          },
          {
            default: "i-0de99e421ecf0fc2c",
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "mi_id",
            description: "SSM Instance ID",
            validation_regex_msg: "MI must be supplied.",
            type: "string",
            long_desc: "SSM Instance IDs. Only showing those with a tag defined of role=mf_automation",
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "jobname",
            description: "Job Name",
            validation_regex_msg: "Job name must be supplied.",
            type: "string",
            required: true,
            long_desc: "Job name.",
          },
          {
            name: "outputLastMessage",
            description: "Last Message",
            system: true,
            type: "string",
            required: true,
            long_desc: "Last Message.",
          },
          {
            lookup: "script.package_uuid",
            system: true,
            rel_attribute: "script_arguments",
            rel_key: "package_uuid",
            name: "script.script_arguments",
            description: "Script Arguments",
            rel_entity: "script",
            type: "embedded_entity",
            required: true,
            long_desc: "Automation Script.",
          },
          {
            name: "script.script_name",
            description: "Script Name",
            system: true,
            type: "string",
            long_desc: "Automation Script.",
          },
          {
            name: "script.package_uuid",
            description: "Script Package UUID",
            system: true,
            type: "string",
            long_desc: "Automation Script UUID.",
          },
          {
            name: "script.default",
            description: "Script Version",
            system: true,
            type: "string",
            long_desc: "Automation Script Version Run.",
          },
          {
            name: "script.script_description",
            description: "Script Description",
            system: true,
            type: "string",
            long_desc: "Automation Script Description.",
          },
          {
            name: "script.script_masterfile",
            description: "Script FileName",
            system: true,
            type: "string",
            long_desc: "Automation script file name.",
          },
          {
            name: "status",
            description: "Status",
            system: true,
            type: "status",
            required: true,
            long_desc: "Job Status.",
          },
          {
            name: "SSMAutomationExecutionId",
            description: "SSM Execution ID",
            system: true,
            type: "string",
            required: true,
            long_desc: "SSM Execution ID.",
          },
          {
            name: "uuid",
            description: "Job ID",
            system: true,
            type: "string",
            long_desc: "Migration Factory Job ID.",
          },
        ],
        schema_name: "job",
        description: "Automation",
        actions: [],
      })
    );
  }),
  rest.get("/admin/schema/app", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "user",
        attributes: [
          {
            name: "app_id",
            description: "Application Id",
            system: true,
            hidden: true,
            type: "string",
            required: true,
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "app_name",
            description: "Application Name",
            validation_regex_msg: "Application name must be specified.",
            group_order: "-1000",
            type: "string",
            required: true,
          },
          {
            system: true,
            rel_display_attribute: "wave_name",
            rel_key: "wave_id",
            name: "wave_id",
            description: "Wave Id",
            rel_entity: "wave",
            group_order: "-999",
            type: "relationship",
            required: false,
          },
          {
            system: true,
            validation_regex: "^\\d{12}$",
            listvalue: "111122223333,222233334444",
            name: "aws_accountid",
            description: "AWS Account Id",
            validation_regex_msg: "Invalid AWS account Id.",
            type: "list",
            required: true,
            group: "Target",
          },
          {
            system: true,
            listvalue:
              "us-east-2,us-east-1,us-west-1,us-west-2,af-south-1,ap-east-1,ap-southeast-3,ap-south-1,ap-northeast-3,ap-northeast-2,ap-southeast-1,ap-southeast-2,ap-northeast-1,ca-central-1,cn-north-1,cn-northwest-1,eu-central-1,eu-west-1,eu-west-2,eu-south-1,eu-west-3,eu-north-1,me-south-1,sa-east-1",
            name: "aws_region",
            description: "AWS Region",
            type: "list",
            required: true,
            group: "Target",
          },
        ],
        schema_name: "app",
      })
    );
  }),
  rest.get("/admin/schema/script", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "system",
        attributes: [
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "script_name",
            description: "Name",
            validation_regex_msg: "Provide a name for this script.",
            type: "string",
            required: true,
            long_desc: "Script name.",
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "script_description",
            description: "Description",
            validation_regex_msg: "Provide a description of the outcome for this script.",
            type: "string",
            required: true,
            long_desc: "Script description.",
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "fileName",
            description: "Filename",
            validation_regex_msg: "Select a filename.",
            type: "string",
            long_desc: "Script filename.",
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "path",
            description: "Path",
            validation_regex_msg: "Select a file path.",
            type: "string",
            long_desc: "Script path.",
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "script_masterfile",
            description: "Master filename",
            validation_regex_msg: "Select a master filename path.",
            type: "string",
            long_desc: "Script master filename.",
          },
          {
            name: "package_uuid",
            description: "UUID",
            system: true,
            type: "string",
            long_desc: "Automation script UUID.",
          },
          {
            system: true,
            readonly: true,
            name: "default",
            description: "Default version",
            type: "string",
            required: true,
            long_desc: "Default version.",
          },
          {
            system: true,
            readonly: true,
            name: "latest",
            description: "Latest version",
            type: "string",
            required: true,
            long_desc: "Latest version.",
          },
          {
            system: true,
            readonly: true,
            name: "script_group",
            description: "Group",
            type: "string",
            required: false,
            long_desc: "Group or category the script is linked to.",
          },
        ],
        schema_name: "script",
      })
    );
  }),
  rest.get("/admin/schema/user", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "system",
        attributes: [
          {
            system: true,
            hidden: true,
            name: "userRef",
            description: "User reference",
            type: "string",
            required: true,
            long_desc: "User reference",
          },
          {
            name: "email",
            description: "User Email address",
            system: true,
            type: "string",
            required: true,
            long_desc: "User Email address",
          },
          {
            name: "enabled",
            description: "User enabled",
            system: true,
            type: "checkbox",
            required: true,
            long_desc: "User enabled",
          },
          {
            name: "status",
            description: "User status",
            system: true,
            type: "string",
            required: true,
            long_desc: "User status",
          },
          {
            name: "groups",
            description: "User groups",
            system: true,
            type: "groups",
            required: true,
            long_desc: "User groups",
          },
          {
            name: "mfaEnabled",
            description: "User MFA enabled",
            system: true,
            type: "checkbox",
            required: true,
            long_desc: "User MFA enabled",
          },
        ],
        schema_name: "user",
      })
    );
  }),
  rest.get("/admin/schema/role", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "system",
        attributes: [
          {
            system: true,
            name: "role_name",
            description: "Role Name",
            group_order: 1,
            type: "string",
            required: true,
            long_desc: "Role name",
          },
          {
            system: true,
            hidden: true,
            name: "role_id",
            description: "Role Id",
            type: "string",
            required: true,
            long_desc: "Role ID",
          },
          {
            listMultiSelect: true,
            system: true,
            name: "groups",
            description: "Groups",
            type: "groups",
            listValueAPI: "/admin/groups",
            required: true,
            long_desc: "Groups",
          },
          {
            listMultiSelect: true,
            system: true,
            rel_display_attribute: "policy_name",
            rel_key: "policy_id",
            name: "policies",
            description: "Attached Policies",
            rel_entity: "policy",
            type: "policies",
            required: true,
            long_desc: "Policies",
          },
        ],
        schema_name: "role",
      })
    );
  }),
  rest.get("/admin/schema/secret", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "system",
        attributes: [
          {
            name: "name",
            description: "Secret Name",
            system: true,
            type: "string",
            long_desc: "Secret name.",
          },
          {
            name: "description",
            description: "Secret Description",
            system: true,
            type: "string",
            long_desc: "Secret description.",
          },
          {
            name: "data.SECRET_TYPE",
            description: "Secret Type",
            system: true,
            type: "string",
            long_desc: "Secret Type.",
          },
        ],
        schema_name: "secret",
      })
    );
  }),
  rest.get("/admin/schema/ssm_job", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "automation",
        friendly_name: "Run Automation",
        attributes: [
          {
            system: true,
            name: "mi_id",
            description: "Automation Server",
            group_order: "3",
            type: "list",
            listValueAPI: "/ssm",
            valueKey: "mi_id",
            labelKey: "mi_name",
            required: true,
            long_desc: "SSM Instance IDs. Only showing those with a tag defined of role=mf_automation",
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            name: "jobname",
            description: "Job Name",
            validation_regex_msg: "Job name must be supplied.",
            group_order: "1",
            type: "string",
            required: true,
            long_desc: "Job name.",
          },
          {
            rel_display_attribute: "script_name",
            system: true,
            validation_regex: "^(?!\\s*$).+",
            rel_key: "package_uuid",
            name: "script.package_uuid",
            description: "Script Name",
            rel_entity: "script",
            validation_regex_msg: "Script name must be provided.",
            group_order: "3",
            type: "relationship",
            required: true,
          },
          {
            lookup: "script.package_uuid",
            system: true,
            rel_attribute: "script_arguments",
            rel_key: "package_uuid",
            name: "script.script_arguments",
            description: "Script Arguments",
            rel_entity: "script",
            group_order: "4",
            type: "embedded_entity",
            required: true,
            long_desc: "Automation Script.",
          },
        ],
        schema_name: "ssm_job",
        description: "Run Automation",
        actions: [
          {
            name: "Submit Automation Job",
            apiMethod: "post",
            id: "submit",
            awsuistyle: "primary",
            apiPath: "/ssm",
          },
        ],
      })
    );
  }),
  rest.get("/admin/schema/server", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "user",
        attributes: [
          {
            name: "server_id",
            description: "Server Id",
            system: true,
            hidden: true,
            type: "string",
            required: true,
          },
          {
            rel_display_attribute: "app_name",
            system: true,
            rel_key: "app_id",
            name: "app_id",
            description: "Application",
            rel_entity: "application",
            group_order: "-998",
            type: "relationship",
            required: true,
          },
          {
            system: true,
            validation_regex:
              "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9])\\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\\-]*[A-Za-z0-9])$",
            name: "server_name",
            description: "Server Name",
            validation_regex_msg: "Server names must contain only alphanumeric, hyphen or period characters.",
            group_order: "-1000",
            type: "string",
            required: true,
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            listvalue: "windows,linux",
            name: "server_os_family",
            description: "Server OS Family",
            validation_regex_msg: "Select a valid operating system.",
            type: "list",
            required: true,
          },
          {
            name: "server_os_version",
            description: "Server OS Version",
            system: true,
            type: "string",
            required: true,
          },
          {
            system: true,
            validation_regex:
              "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9])\\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\\-]*[A-Za-z0-9])$",
            name: "server_fqdn",
            description: "Server FQDN",
            validation_regex_msg: "Server FQDN must contain only alphanumeric, hyphen or period charaters.",
            group_order: "-999",
            type: "string",
            required: true,
          },
          {
            name: "server_tier",
            description: "Server Tier",
            system: true,
            type: "string",
          },
          {
            name: "server_environment",
            description: "Server Environment",
            group_order: "-997",
            system: true,
            type: "string",
          },
          {
            system: true,
            validation_regex: "^(subnet-([a-z0-9]{8}|[a-z0-9]{17})$)",
            name: "subnet_IDs",
            description: "Subnet Ids",
            validation_regex_msg: "Subnets must start with subnet-, followed by 8 or 17 alphanumeric characters.",
            type: "multivalue-string",
            conditions: {
              queries: [
                {
                  comparator: "!empty",
                  attribute: "network_interface_id",
                },
              ],
              outcomes: {
                true: ["hidden"],
                false: ["not_required"],
              },
            },
            group: "Target - Networking",
          },
          {
            system: true,
            validation_regex: "^(sg-([a-z0-9]{8}|[a-z0-9]{17})$)",
            name: "securitygroup_IDs",
            description: "Security Group Ids",
            validation_regex_msg: "Security groups must start with sg-, followed by 8 or 17 alphanumeric characters.",
            type: "multivalue-string",
            group: "Target - Networking",
          },
          {
            system: true,
            validation_regex: "^(subnet-([a-z0-9]{8}|[a-z0-9]{17})$)",
            name: "subnet_IDs_test",
            description: "Subnet Ids - Test",
            validation_regex_msg: "Subnets must start with subnet-, followed by 8 or 17 alphanumeric characters.",
            type: "multivalue-string",
            conditions: {
              queries: [
                {
                  comparator: "!empty",
                  attribute: "network_interface_id_test",
                },
              ],
              outcomes: {
                true: ["hidden"],
                false: ["not_required"],
              },
            },
            group: "Target - Networking",
          },
          {
            system: true,
            validation_regex: "^(sg-([a-z0-9]{8}|[a-z0-9]{17})$)",
            name: "securitygroup_IDs_test",
            description: "Security Group Ids - Test",
            validation_regex_msg: "Security groups must start with sg-, followed by 8 or 17 alphanumeric characters.",
            type: "multivalue-string",
            group: "Target - Networking",
          },
          {
            name: "instanceType",
            description: "Instance Type",
            system: true,
            type: "string",
            group: "Target - Instance",
          },
          {
            name: "iamRole",
            description: "EC2 Instance Profile Name",
            system: true,
            type: "string",
            group: "Target - Instance",
            long_desc:
              "Verify that the value entered here is the Instance Profile name not the IAM Role name, they maybe different. If you use the AWS CLI, API, or an AWS SDK to create a role, you create the role and instance profile as separate actions, with potentially different names.",
          },
          {
            system: true,
            validation_regex: "^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\\.|$)){4}",
            name: "private_ip",
            description: "Private IP",
            validation_regex_msg: "A valid IPv4 IP address must be provided.",
            type: "string",
            group: "Target - Networking",
          },
          {
            name: "tags",
            description: "Tags",
            system: true,
            type: "tag",
            group: "Target - Instance",
          },
          {
            name: "tenancy",
            description: "Tenancy",
            system: true,
            type: "list",
            listvalue: "Shared,Dedicated,Dedicated host",
            group: "Target - Instance",
          },
          {
            name: "migration_status",
            description: "Migration Status",
            system: true,
            type: "string",
            group: "Status",
          },
          {
            name: "replication_status",
            description: "Replication Status",
            system: true,
            type: "string",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Rehost",
                  attribute: "r_type",
                },
              ],
              outcomes: {
                true: ["hidden"],
                false: ["not_required"],
              },
            },
            group: "Status",
          },
          {
            system: true,
            help_content: {
              header: "Migration Strategy",
              content_html:
                "The following Migration Strategies are commonly used in Cloud Migration projects.  The AWS Cloud Migration factory solution supports the automation activities to assist with these strategies, for Rehost and Replatform prepackaged automations are provided, and for other strategies customized automations can be created and imported into the AWS CMF solution:\n<ul>\n<li><b>Retire</b> - Server retired and not migrated, data will need to be removed and any software services decommissioned.</li>\n<li><b>Retain</b> - Server will remain on-premise , assessment should be preformed to verify any changes for migrating dependent services.</li>\n<li><b>Relocate</b> - VMware virtual machine on-premise, is due to be relocated to VMware Cloud on AWS, using VMware HCX. Currently AWS CMF does not natively support this capability, although custom automation script packages coudl be used to interface with this service.</li>\n<li><b>Rehost</b> - AWS Cloud Migration Factory supports native integration with AWS MGN, selecting this strategy will enable the options in the server UI to support specifying the required parameters to migrate a server instance to EC2 using block level replication. The AWS CMF Solution comes packaged will all the required automation scripts to support the standard tasks required to migrate a server, all of which can be initiated from the CMF web interface.</li>\n<li><b>Repurchase</b> - Service that the server is currently supporting will be replaced with another service.</li>\n<li><b>Replatform</b> - AWS Cloud Migration Factory supports native integration to create Cloud Formation templates for each application in a wave, these Cloud Formation template are automatically generated through the UI based on the properties of the servers defined here, and can then be deployed to any account that has had the target AWS CMF Solution CFT deployed.</li>\n<li><b>Reachitect</b> - Service will be rebuilt from other services in the AWS Cloud.</li>\n</ul>\n",
            },
            listvalue: "Retire,Retain,Relocate,Rehost,Repurchase,Replatform,Rearchitect,TBC",
            name: "r_type",
            description: "Migration Strategy",
            type: "list",
            required: true,
          },
          {
            system: true,
            validation_regex: "^(h-([a-z0-9]{8}|[a-z0-9]{17})$)",
            name: "dedicated_host_id",
            description: "Dedicated Host ID",
            validation_regex_msg: "Dedicated Host IDs must start with h-, followed by 8 or 17 alphanumeric characters.",
            type: "string",
            conditions: {
              outcomes: {
                true: ["required"],
                false: ["not_required", "hidden"],
              },
              queries: [
                {
                  comparator: "=",
                  value: "Dedicated host",
                  attribute: "tenancy",
                },
              ],
            },
            group: "Target - Instance",
          },
          {
            system: true,
            help_content: {
              header: "Network Interface ID",
              content_html:
                "If Network Interface ID is provided you cannot set Subnet IDs, as the instance will be launched with this Network Interface ID.\n\nThis Network Interface ID will be assigned to the migrating server.",
            },
            validation_regex: "^(eni-([a-z0-9]{8}|[a-z0-9]{17})$)",
            name: "network_interface_id",
            description: "Network Interface ID",
            validation_regex_msg:
              "Network Interface ID must start with eni- followed by 8 or 17 alphanumeric characters.",
            type: "string",
            conditions: {
              queries: [
                {
                  comparator: "!empty",
                  attribute: "subnet_IDs",
                },
              ],
              outcomes: {
                true: ["hidden"],
                false: ["not_required"],
              },
            },
            group: "Target - Networking",
          },
          {
            system: true,
            help_content: {
              header: "Network Interface ID - Test",
              content_html:
                "If 'Network Interface ID -Test' is provided you cannot set 'Subnet IDs - Test', as the instance will be launched with this Network Interface ID.\n\nThis Network Interface ID will be assigned to the migrating server.",
            },
            validation_regex: "^(eni-([a-z0-9]{8}|[a-z0-9]{17})$)",
            name: "network_interface_id_test",
            description: "Network Interface ID - Test",
            validation_regex_msg:
              "Network Interface ID must start with eni- followed by 8 or 17 alphanumeric characters.",
            type: "string",
            conditions: {
              queries: [
                {
                  comparator: "!empty",
                  attribute: "subnet_IDs_test",
                },
              ],
              outcomes: {
                true: ["hidden"],
                false: ["not_required"],
              },
            },
            group: "Target - Networking",
          },
          {
            system: true,
            validation_regex: "^([1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[1][0-6][0-3][0-8][0-4])$",
            name: "root_vol_size",
            description: "Root Volume Size (GiB)",
            validation_regex_msg: "Volume Size needs to between 1 GiB and 16384 GiB",
            type: "Integer",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "root_vol_size",
                },
              ],
              outcomes: {
                true: ["hidden"],
                false: ["required"],
              },
            },
            group: "Target - Storage",
          },
          {
            system: true,
            validation_regex: "^(ami-(([a-z0-9]{8,17})+)$)",
            name: "ami_id",
            description: "AMI Id",
            validation_regex_msg: "AMI ID must start with ami- and followed by upto 12 alphanumeric characters.",
            type: "string",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "ami_id",
                },
              ],
              outcomes: {
                true: ["hidden"],
                false: ["required"],
              },
            },
            group: "Target - Instance",
          },
          {
            name: "availabilityzone",
            description: "Availability zone",
            system: true,
            type: "string",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "availabilityzone",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Instance",
          },
          {
            system: true,
            listvalue: "standard,io1,io2,gp2,gp3,",
            name: "root_vol_type",
            description: "Root Volume Type",
            type: "list",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "root_vol_type",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Storage",
          },
          {
            system: true,
            validation_regex: "^([1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[1][0-6][0-3][0-8][0-4])$",
            name: "add_vols_size",
            description: "Additional Volume Sizes (GiB)",
            validation_regex_msg: "Volume Sizes need to be between 1 GiB and 16384 GiB",
            type: "multivalue-string",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "add_vols_size",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Storage",
          },
          {
            system: true,
            validation_regex: "^(standard|io1|io2|gp2|gp3)$",
            name: "add_vols_type",
            description: "Additional Volume Types (standard, io1, io2, gp2, or gp3)",
            validation_regex_msg: 'Allowed Volume Types "standard", "io1", "io2", "gp2", or "gp3"',
            type: "multivalue-string",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "add_vols_type",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Storage",
          },
          {
            name: "ebs_optimized",
            description: "Enable EBS Optimized",
            system: true,
            type: "checkbox",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "ebs_optimized",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Storage",
          },
          {
            system: true,
            validation_regex:
              "^(arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/){0,1}[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
            name: "ebs_kms_key_id",
            description: "EBS KMS Key Id or ARN for Volume Encryption",
            validation_regex_msg: "Provide a valid KMS Key or ARN.",
            type: "string",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "ebs_kms_key_id",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Storage",
          },
          {
            name: "detailed_monitoring",
            description: "Enable Detailed Monitoring",
            system: true,
            type: "checkbox",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "detailed_monitoring",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Instance",
          },
          {
            system: true,
            listvalue: "/dev/sda1,/dev/xvda,",
            name: "root_vol_name",
            description: "Root Volume Name",
            type: "list",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "root_vol_name",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Storage",
          },
          {
            name: "add_vols_name",
            description: "Additional Volume Names",
            system: true,
            type: "multivalue-string",
            conditions: {
              queries: [
                {
                  comparator: "!=",
                  value: "Replatform",
                  attribute: "r_type",
                },
                {
                  comparator: "empty",
                  attribute: "add_vols_name",
                },
              ],
              outcomes: {
                true: ["hidden"],
              },
            },
            group: "Target - Storage",
          },
        ],
        schema_name: "server",
      })
    );
  }),
  rest.get("/admin/schema/database", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        schema_type: "user",
        attributes: [
          {
            name: "database_id",
            description: "Database Id",
            system: true,
            hidden: true,
            type: "string",
            required: true,
          },
          {
            rel_display_attribute: "app_name",
            system: true,
            rel_key: "app_id",
            name: "app_id",
            description: "Application",
            rel_entity: "application",
            group_order: "-998",
            type: "relationship",
            required: true,
          },
          {
            name: "database_name",
            description: "Database Name",
            group_order: "-1000",
            system: true,
            type: "string",
            required: true,
          },
          {
            system: true,
            validation_regex: "^(?!\\s*$).+",
            listvalue: "oracle,mssql,db2,mysql,postgresql",
            name: "database_type",
            description: "Database Type",
            validation_regex_msg: "Select a valid database type.",
            type: "list",
            required: true,
          },
        ],
        schema_name: "database",
      })
    );
  }),
  rest.get("/admin/schema/pipeline_template", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        "schema_name": "pipeline_template",
        "attributes": [
          {
            "description": "Pipeline Template Id",
            "hidden": true,
            "name": "pipeline_template_id",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Pipeline Template Name",
            "name": "pipeline_template_name",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Pipeline Template Description",
            "name": "pipeline_template_description",
            "required": true,
            "type": "string"
          }
        ],
        "schema_type": "user"
      })
    );
  }),
  rest.get("/admin/schema/pipeline_template_task", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        "schema_name": "pipeline_template_task",
        "attributes": [
          {
            "description": "Pipeline Template ID",
            "hidden": true,
            "name": "pipeline_template_id",
            "rel_display_attribute": "pipeline_template_name",
            "rel_entity": "pipeline_template",
            "rel_key": "pipeline_template_id",
            "required": true,
            "system": true,
            "type": "relationship"
          },
          {
            "description": "Task Name",
            "group_order": "2",
            "name": "task_id",
            "rel_display_attribute": "script_name",
            "rel_entity": "script",
            "rel_key": "package_uuid",
            "required": true,
            "system": true,
            "type": "relationship"
          },
          {
            "description": "Task Version",
            "group_order": "3",
            "name": "task_version",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
           "description": "Successors",
           "group_order": "4",
           "listMultiSelect": true,
           "long_desc": "Next task",
           "name": "task_successors",
           "rel_display_attribute": "pipeline_template_task_name",
           "rel_entity": "pipeline_template_task",
           "rel_filter_attribute_name": "pipeline_template_id",
           "rel_key": "pipeline_template_task_id",
           "required": false,
           "source_filter_attribute_name": "pipeline_template_id",
           "system": true,
           "type": "relationship"
          },
          {
            "description": "Internal name identifier",
            "hidden": true,
            "name": "pipeline_template_task_name",
            "required": true,
            "system": true,
            "type": "string"
          }
        ],
        "schema_type": "system"
      })
    );
  }),
  rest.get("/admin/schema/pipeline", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        "schema_name": "pipeline",
        "attributes": [
          {
            "description": "Pipeline Id",
            "hidden": true,
            "name": "pipeline_id",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Pipeline Name",
            "group_order": "1",
            "name": "pipeline_name",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Pipeline Description",
            "group_order": "2",
            "name": "pipeline_description",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Pipeline Status",
            "group_order": "3",
            "hiddenCreate": true,
            "name": "pipeline_status",
            "required": true,
            "system": true,
            "type": "status"
          },
          {
            "description": "Pipeline Template ID",
            "group_order": "4",
            "name": "pipeline_template_id",
            "rel_display_attribute": "pipeline_template_name",
            "rel_entity": "pipeline_template",
            "rel_key": "pipeline_template_id",
            "required": true,
            "system": true,
            "type": "relationship"
          },
          {
            "description": "Task Arguments",
            "group_order": "5",
            "long_desc": "Template Task Arguments",
            "lookup": "task.package_uuid",
            "name": "task_arguments",
            "rel_attribute": "script_arguments",
            "rel_entity": "script",
            "rel_key": "package_uuid",
            "required": true,
            "system": true,
            "type": "embedded_entity"
          },
          {
            "description": "Current Task ID",
            "group_order": "6",
            "hiddenCreate": true,
            "name": "current_task_id",
            "required": false,
            "system": true,
            "type": "string"
          }
        ],
        "schema_type": "user"
      })
    );
  }),
  rest.get("/admin/schema/task_execution", (request, response, context) => {
    return response(
      context.status(200),
      context.json({
        "schema_name": "task_execution",
        "attributes": [
          {
            "description": "Task Execution ID",
            "hidden": true,
            "name": "task_execution_id",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Task Execution Name",
            "hidden": true,
            "name": "task_execution_name",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Pipeline Name",
            "hidden": true,
            "name": "pipeline_id",
            "rel_display_attribute": "pipeline_name",
            "rel_entity": "pipeline",
            "rel_key": "pipeline_id",
            "system": true,
            "type": "relationship"
          },
          {
           "description": "Successors",
           "group_order": "4",
           "listMultiSelect": true,
           "long_desc": "Next task",
           "name": "task_successors",
           "rel_display_attribute": "task_execution_name",
           "rel_entity": "task_execution",
           "rel_filter_attribute_name": "pipeline_template_id",
           "rel_key": "task_execution_id",
           "required": false,
           "source_filter_attribute_name": "pipeline_template_id",
           "system": true,
           "type": "relationship"
          },
          {
            "description": "Task Name",
            "group_order": "2",
            "long_desc": "Pipeline Task Name",
            "name": "task_id",
            "rel_display_attribute": "pipeline_template_task_name",
            "rel_entity": "pipeline_template_task",
            "rel_key": "task_id",
            "required": true,
            "system": true,
            "type": "relationship"
          },
          {
            "description": "Task Version",
            "group_order": "2",
            "long_desc": "Pipeline Task version",
            "name": "task_version",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Task Execution Status",
            "group_order": "5",
            "name": "task_execution_status",
            "required": true,
            "system": true,
            "type": "status"
          },
          {
            "description": "Last Message",
            "group_order": "6",
            "long_desc": "Last Message.",
            "name": "outputLastMessage",
            "required": true,
            "system": true,
            "type": "string"
          },
          {
            "description": "Log Output",
            "hidden": true,
            "name": "output",
            "system": true,
            "type": "json"
          },
          {
            "description": "Task Execution Inputs",
            "hidden": true,
            "name": "task_execution_inputs",
            "type": "json"
          }
        ],
        "schema_type": "system"
      })
    );
  }),
];

export function generateTestPolicies(count: number): Array<any> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    policy_id: `${number}`,
    entity_access: [
      {
        create: false,
        update: false,
        schema_name: "application",
        read: true,
        delete: false,
      },
      {
        create: false,
        update: false,
        schema_name: "wave",
        read: true,
        delete: false,
      },
      {
        create: false,
        update: false,
        schema_name: "server",
        read: true,
        delete: false,
      },
    ],
    policy_name: `ReadOnly-${number}`,
  }));
}
