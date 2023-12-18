/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import ItemAmend from "./ItemAmend";
import React from "react";
import {mockNotificationContext} from "../__tests__/TestUtils";
import {NotificationContext} from '../contexts/NotificationContext';

let props: any = {};
props.schema = {};
props.schema['server'] = {
  "schema_type": "user",
  "attributes": [
    {
      "system": true,
      "help_content": {
        "header": "Server ID",
        "content_links": [
          {
            "value": "https://ww.amazon.com",
            "existing": false,
            "key": "test"
          }
        ],
        "content_html": "This is an internal reference to the server record."
      },
      "hidden": true,
      "name": "server_id",
      "description": "Server Id",
      "type": "string",
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
      "required": false
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
      "description": "Subnet Ids - Test",
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
      "group": "Target - Networking"
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
      "description": "IAM role",
      "system": true,
      "type": "string",
      "group": "Target"
    },
    {
      "system": true,
      "validation_regex": "^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\\.|$)){4}",
      "name": "private_ip",
      "validation_regex_msg": "A valid IPv4 IP address must be provided.",
      "description": "Private IP",
      "type": "string",
      "group": "Target - Networking"
    },
    {
      "sample_data_intake": "tagname2=tagevalue2;tagname2=tagvalue2",
      "system": true,
      "help_content": {
        "header": "Application Name",
        "content_md": "",
        "content_html": "<h2> Database names should be provided for all databases.</h2>",
        "content_text": ""
      },
      "name": "tags",
      "description": "Tags",
      "type": "tag",
      "group": "Target"
    },
    {
      "system": true,
      "help_content": {
        "header": "Applicatioddn Name",
        "content_md": "",
        "content_html": "<h2> Database names should be provided for all databases.</h2>",
        "content_text": ""
      },
      "listvalue": "Shared,Dedicated,Dedicated host",
      "name": "tenancy",
      "description": "Tenancy",
      "group_order": "100",
      "type": "list",
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
      "name": "r_type",
      "description": "Migration Strategy",
      "system": true,
      "help_content": {
        "header": "Migration Strategy",
        "content_html": "The following Migration Strategies are commonly used in Cloud Migration projects.  The AWS Cloud Migration factory solution supports the automation activities to assist with these strategies, for Rehost and Replatform prepackaged automations are provided, and for other strategies customized automations can be created and imported into the AWS CMF solution:\n<ul>\n<li><b>Retire</b> - Server retired and not migrated, data will need to be removed and any software services decommissioned.</li>\n<li><b>Retain</b> - Server will remain on-premise , assessment should be preformed to verify any changes for migrating dependent services.</li>\n<li><b>Relocate</b> - VMware virtual machine on-premise, is due to be relocated to VMware Cloud on AWS, using VMware HCX. Currently AWS CMF does not natively support this capability, although custom automation script packages coudl be used to interface with this service.</li>\n<li><b>Rehost</b> - AWS Cloud Migration Factory supports native integration with AWS MGN, selecting this strategy will enable the options in the server UI to support specifying the required parameters to migrate a server instance to EC2 using block level replication. The AWS CMF Solution comes packaged will all the required automation scripts to support the standard tasks required to migrate a server, all of which can be initiated from the CMF web interface.</li>\n<li><b>Repurchase</b> - Service that the server is currently supporting will be replaced with another service.</li>\n<li><b>Replatform</b> - AWS Cloud Migration Factory supports native integration to create Cloud Formation templates for each application in a wave, these Cloud Formation template are automatically generated through the UI based on the properties of the servers defined here, and can then be deployed to any account that has had the target AWS CMF Solution CFT deployed.</li>\n<li><b>Reachitect</b> - Service will be rebuilt from other services in the AWS Cloud.</li>\n</ul>\n"
      },
      "type": "list",
      "listvalue": "Retire,Retain,Relocate,Rehost,Repurchase,Replatform,Reachitect,TBC"
    },
    {
      "system": true,
      "validation_regex": "^(h-([a-z0-9]{8}|[a-z0-9]{17})$)",
      "name": "dedicated_host_id",
      "description": "Dedicated Host ID",
      "validation_regex_msg": "Dedicated Host IDs must start with h-, followed by 8 or 17 alphanumeric characters.",
      "group_order": "101",
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
      "type": "string",
      "required": false,
      "group": "Target"
    },
    {
      "system": true,
      "help_content": {
        "header": "Network Interface ID",
        "content_html": "If Network Interface ID is provided you cannot set Subnet IDs, as the instance will be launched with this Network Interface ID.\n\nThis Network Interface ID will be assigned to the migrating server."
      },
      "validation_regex": "^(eni-(([a-z0-9]{17})+)$)",
      "name": "network_interface_id",
      "description": "Network Interface ID",
      "validation_regex_msg": "Network Interface ID must start with eni- and followed by upto 17 alphanumeric characters.",
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
        "header": "Network Interface ID",
        "content_html": "If Network Interface ID is provided you cannot set Subnet IDs, as the instance will be launched with this Network Interface ID.\n\nThis Network Interface ID will be assigned to the migrating server."
      },
      "validation_regex": "^(eni-(([a-z0-9]{17})+)$)",
      "name": "network_interface_id_test",
      "description": "Network Interface ID - Test",
      "validation_regex_msg": "Network Interface ID must start with eni- and followed by upto 17 alphanumeric characters.",
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
      "hidden": true,
      "name": "root_vol_size",
      "description": "Root Volume Size (GiB)",
      "validation_regex_msg": "Volume Size needs to between 1 GiB and 16384 GiB",
      "type": "Integer",
      "conditions": {
        "queries": [
          {
            "comparator": "=",
            "value": "Replatform",
            "attribute": "r_type"
          }
        ],
        "outcomes": {
          "true": [
            "required",
            "not_hidden"
          ],
          "false": []
        }
      },
      "group": "Target - Storage"
    },
    {
      "system": true,
      "validation_regex": "^(ami-(([a-z0-9]{8,17})+)$)",
      "hidden": true,
      "name": "ami_id",
      "description": "AMI Id",
      "validation_regex_msg": "AMI ID must start with ami- and followed by  upto 12 alphanumeric characters.",
      "group_order": "1",
      "type": "string",
      "conditions": {
        "queries": [
          {
            "comparator": "=",
            "value": "Replatform",
            "attribute": "r_type"
          }
        ],
        "outcomes": {
          "true": [
            "required",
            "not_hidden"
          ],
          "false": []
        }
      },
      "group": "Target"
    },
    {
      "system": true,
      "name": "availabilityzone",
      "description": "Availability zone",
      "group_order": "2",
      "type": "string",
      "conditions": {
        "queries": [
          {
            "comparator": "!=",
            "value": "Replatform",
            "attribute": "r_type"
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
      "description": "Additional Volume Types",
      "validation_regex_msg": "Allowed List of Volume Types \"standard\", \"io1\", \"io2\", \"gp2\", or \"gp3\"",
      "type": "multivalue-string",
      "conditions": {
        "queries": [
          {
            "comparator": "!=",
            "value": "Replatform",
            "attribute": "r_type"
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
        "queries": [
          {
            "comparator": "!=",
            "value": "Replatform",
            "attribute": "r_type"
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
      "validation_regex": "^(arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/){0,1}[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
      "name": "ebs_kmskey_id",
      "description": "EBS KMS Key Id for Volume Encryption",
      "validation_regex_msg": "Provide a valid KMS Key or ARN.",
      "type": "string",
      "conditions": {
        "queries": [
          {
            "comparator": "!=",
            "value": "Replatform",
            "attribute": "r_type"
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
      "name": "detailed_monitoring",
      "description": "Enable Detailed Monitoring",
      "group_order": "5",
      "type": "checkbox",
      "conditions": {
        "queries": [
          {
            "comparator": "!=",
            "value": "Replatform",
            "attribute": "r_type"
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
      "listMultiSelect": true,
      "rel_display_attribute": "app_name",
      "rel_key": "app_id",
      "name": "all_app_names",
      "description": "All Applications",
      "rel_entity": "application",
      "type": "relationship",
      "long_desc": "If server supports multiple applications they will be listed here."
    }
  ],
  "schema_name": "server"
}

props.userEntityAccess = {}

let schemaName = 'server';

afterEach(cleanup);

let testItem: any = {}
let cancelled = false;

async function stub() {

}

async function stubSave(localItem: any, _: string) {
  testItem = {testItem, ...localItem};
}

async function stubCancel() {
  cancelled = true;
}

const setup = (inputAriaText: string) => {
  const comp = render(
    <NotificationContext.Provider value={mockNotificationContext}>
      <ItemAmend
        action={'Add'}
        schemaName={schemaName}
        schemas={props.schema}
        userAccess={props.userEntityAccess}
        item={testItem}
        handleSave={stubSave}
        handleCancel={stubCancel}/>
    </NotificationContext.Provider>)

  const input = screen.getByLabelText(inputAriaText) as HTMLInputElement
  return {
    ...comp,
    input
  }
}

const setupTag = () => {
  const comp = render(
    <NotificationContext.Provider value={mockNotificationContext}>
      <ItemAmend
        action={'Add'}
        schemaName={schemaName}
        schemas={props.schema}
        userAccess={props.userEntityAccess}
        item={testItem}
        handleSave={stubSave}
        handleCancel={stubCancel}/>
    </NotificationContext.Provider>)
  const input = screen.getByText('Add new tag')
  return {
    ...comp,
    input
  }
}


test('ItemAmend displays the generic items amend component and populates with some dummy server data', () => {
  setup('server_name')

  expect(screen.getByText('Server Name')).toBeTruthy();

});

test('Update server_name enter string to trigger update', () => {
  const {input} = setup('server_name')
  fireEvent.change(input, {target: {value: 'newvalue'}})
  expect(input.value).toBe('newvalue')
});

test('Click save', () => {
  const {input} = setup('server_name')
  fireEvent.change(input, {target: {value: 'newvalue'}})
  const saveButton = screen.getByLabelText('save')
  console.debug(saveButton);
  fireEvent.click(saveButton)
  expect(testItem['server_name'] === 'newvalue').toBeTruthy();
});

test('Update tag to verify array update code', () => {
  const {input} = setupTag()
  fireEvent.click(input)
  const tagKeyInput = screen.getByPlaceholderText('Enter key') as HTMLInputElement;

  fireEvent.change(tagKeyInput, {target: {value: 'newvalue'}})
  expect(tagKeyInput.value).toBe('newvalue')
});

test('Click cancel', () => {
  setup('server_name')
  const cancelButton = screen.getByLabelText('cancel')
  fireEvent.click(cancelButton)
  expect(cancelled).toBeTruthy();
});


