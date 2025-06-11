#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os

import cmf_boto
import requests
from cmf_logger import logger

import factory

SCHEMA_TABLE = os.getenv('SchemaDynamoDBTable')

CONST_REPLATFORM_ATTRIBUTE_NAMES = ["root_vol_size", "ami_id", "availabilityzone", "root_vol_type", "add_vols_size", "add_vols_type", "ebs_optimized", "ebs_kms_key_id", "detailed_monitoring", "root_vol_name", "add_vols_name"]
CONST_TARGET_STORAGE = 'Target - Storage'
CONST_TARGET_INSTANCE = 'Target - Instance'


class ServerSchema:
    def __init__(self):
        self._rootvolsizeexist = 0
        self._amiidexist = 0
        self._azexist = 0
        self._roottypeexist = 0
        self._addvolsizeexists = 0
        self._addvoltypeeexists = 0
        self._ebsoptexists = 0
        self._ebskmsexists = 0
        self._detailexists = 0
        self._rootvolnamexists = 0
        self._addvolvolnamexists = 0

    @property
    def rootvolsizeexist(self):
        return self._rootvolsizeexist

    @rootvolsizeexist.setter
    def rootvolsizeexist(self, value):
        self._rootvolsizeexist = value

    @property
    def amiidexist(self):
        return self._amiidexist

    @amiidexist.setter
    def amiidexist(self, value):
        self._amiidexist = value

    @property
    def azexist(self):
        return self._azexist

    @azexist.setter
    def azexist(self, value):
        self._azexist = value

    @property
    def roottypeexist(self):
        return self._roottypeexist

    @roottypeexist.setter
    def roottypeexist(self, value):
        self._roottypeexist = value

    @property
    def addvolsizeexists(self):
        return self._addvolsizeexists

    @addvolsizeexists.setter
    def addvolsizeexists(self, value):
        self._addvolsizeexists = value

    @property
    def addvoltypeeexists(self):
        return self._addvoltypeeexists

    @addvoltypeeexists.setter
    def addvoltypeeexists(self, value):
        self._addvoltypeeexists = value

    @property
    def ebsoptexists(self):
        return self._ebsoptexists

    @ebsoptexists.setter
    def ebsoptexists(self, value):
        self._ebsoptexists = value

    @property
    def ebskmsexists(self):
        return self._ebskmsexists

    @ebskmsexists.setter
    def ebskmsexists(self, value):
        self._ebskmsexists = value

    @property
    def detailexists(self):
        return self._detailexists

    @detailexists.setter
    def detailexists(self, value):
        self._detailexists = value

    @property
    def rootvolnamexists(self):
        return self._rootvolnamexists

    @rootvolnamexists.setter
    def rootvolnamexists(self, value):
        self._rootvolnamexists = value

    @property
    def addvolvolnamexists(self):
        return self._addvolvolnamexists

    @addvolvolnamexists.setter
    def addvolvolnamexists(self, value):
        self._addvolvolnamexists = value


def read_attributes(attr: dict, server_schema: ServerSchema):
    if attr['name'] == 'root_vol_size':
        server_schema.rootvolsizeexist = 1

    if attr['name'] == 'ami_id':
        server_schema.amiidexist = 1

    if attr['name'] == 'availabilityzone':
        server_schema.azexist = 1

    if attr['name'] == 'root_vol_type':
        server_schema.roottypeexist = 1

    if attr['name'] == 'add_vols_size':
        server_schema.addvolsizeexists = 1

    if attr['name'] == 'add_vols_type':
        server_schema.addvoltypeeexists = 1

    if attr['name'] == 'ebs_optimized':
        server_schema.ebsoptexists = 1

    if attr['name'] == 'ebs_kms_key_id':
        server_schema.ebskmsexists = 1

    if attr['name'] == 'detailed_monitoring':
        server_schema.detailexists = 1

    if attr['name'] == 'root_vol_name':
        server_schema.rootvolnamexists = 1

    if attr['name'] == 'add_vols_name':
        server_schema.addvolvolnamexists = 1


def compute_server_schema_attrs(attributes):
    server_schema_computed = ServerSchema()
    for attr in attributes:
        read_attributes(attr, server_schema_computed)

    return server_schema_computed


def set_default_attributes(server_schema, attributes):
    if server_schema.rootvolsizeexist == 0:
        attributes.append({
            "description": "Root Volume Size (GiB)",
            "name": "root_vol_size",
            "system": True,
            "validation_regex_msg": "Volume Size needs to between 1 GiB and 16384 GiB",
            "validation_regex": "^([1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[1][0-6][0-3][0-8][0-4])$",
            "type": "Integer",
            "group": CONST_TARGET_STORAGE,
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
            }
        })
    if server_schema.amiidexist == 0:
        attributes.append(

            {
                "description": "AMI Id",
                "name": "ami_id",
                "system": True,
                "type": "string",
                "group": CONST_TARGET_INSTANCE,
                "validation_regex": "^(ami-(([a-z0-9]{8,17})+)$)",
                "validation_regex_msg": "AMI ID must start with ami- and followed by upto 12 alphanumeric characters.",
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
                }
            })
    if server_schema.azexist == 0:
        attributes.append(

            {
                "description": "Availability zone",
                "name": "availabilityzone",
                "system": True,
                "type": "string",
                "group": CONST_TARGET_INSTANCE,
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
                }
            })

    if server_schema.roottypeexist == 0:
        attributes.append(

            {
                "description": "Root Volume Type",
                "name": "root_vol_type",
                "system": True,
                "type": "list",
                "listvalue": "standard,io1,io2,gp2,gp3,",
                "group": CONST_TARGET_STORAGE,
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
                }
            })

    if server_schema.addvolsizeexists == 0:
        attributes.append(

            {
                "description": "Additional Volume Sizes (GiB)",
                "name": "add_vols_size",
                "system": True,
                "validation_regex_msg": "Volume Sizes need to be between 1 GiB and 16384 GiB",
                "validation_regex": "^([1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[1][0-6][0-3][0-8][0-4])$",
                "type": "multivalue-string",
                "group": CONST_TARGET_STORAGE,
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
                }
            })

    if server_schema.addvoltypeeexists == 0:
        attributes.append(
            {
                "description": "Additional Volume Types (standard, io1, io2, gp2, or gp3)",
                "name": "add_vols_type",
                "system": True,
                "type": "multivalue-string",
                "validation_regex": "^(standard|io1|io2|gp2|gp3)$",
                "validation_regex_msg": "Allowed Volume Types \"standard\", \"io1\", \"io2\", \"gp2\", or \"gp3\"",
                "group": CONST_TARGET_STORAGE,
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
                }
            })

    if server_schema.ebsoptexists == 0:
        attributes.append(
            {
                "description": "Enable EBS Optimized",
                "name": "ebs_optimized",
                "system": True,
                "type": "checkbox",
                "group": CONST_TARGET_STORAGE,
                "conditions": {
                    "queries": [
                        {
                            "comparator": "!=",
                            "value": "Replatform",
                            "attribute": "r_type"
                        },
                        {
                            "comparator": "empty",
                            "attribute": "ebs_optimized"
                        }
                    ],
                    "outcomes": {
                        "true": [
                            "hidden"
                        ]
                    }
                }
            })

    if server_schema.ebskmsexists == 0:
        attributes.append(

            {
                "description": "EBS KMS Key Id or ARN for Volume Encryption",
                "name": "ebs_kms_key_id",
                "system": True,
                "type": "string",
                "group": CONST_TARGET_STORAGE,
                "validation_regex": "^(arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/){0,1}([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}|mrk-[a-f0-9]{32})$",
                "validation_regex_msg": "Provide a valid KMS Key or ARN."
            })

    if server_schema.detailexists == 0:
        attributes.append(

            {
                "description": "Enable Detailed Monitoring",
                "name": "detailed_monitoring",
                "system": True,
                "type": "checkbox",
                "group": CONST_TARGET_INSTANCE,
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
                }
            })

    if server_schema.rootvolnamexists == 0:
        attributes.append(

            {
                "description": "Root Volume Name",
                "name": "root_vol_name",
                "system": True,
                "type": "list",
                "listvalue": "/dev/sda1,/dev/xvda,",
                "group": CONST_TARGET_STORAGE,
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
                }
            })

    if server_schema.addvolvolnamexists == 0:
        attributes.append(

            {
                "description": "Additional Volume Names",
                "name": "add_vols_name",
                "system": True,
                "type": "multivalue-string",
                "group": CONST_TARGET_STORAGE,
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
                }
            })


def load_schema():
    client = cmf_boto.client('dynamodb')

    for item in factory.schema:
        client.put_item(
            TableName=SCHEMA_TABLE,
            Item=item
        )
    schema_table = cmf_boto.resource('dynamodb').Table(SCHEMA_TABLE)
    resp = schema_table.get_item(Key={'schema_name': 'server'})
    if 'Item' in resp:
        attributes = resp['Item']['attributes']
        server_schema = compute_server_schema_attrs(attributes)
        set_default_attributes(server_schema, attributes)

        schema_table.put_item(
            Item={
                'schema_name': 'server',
                'schema_type': 'user',
                'attributes': attributes
            }

        )


def delete_schema():
    schema_table = cmf_boto.resource('dynamodb').Table(SCHEMA_TABLE)
    schema_table.delete_item(Key={'schema_name': 'EC2'})
    resp = schema_table.get_item(Key={'schema_name': 'server'})
    if 'Item' in resp:
        attributes = resp['Item']['attributes']
        # Remove all Replatform attributes present from the server schema.
        attributes = [attribute for attribute in attributes if attribute['name'] not in CONST_REPLATFORM_ATTRIBUTE_NAMES]

        schema_table.put_item(
            Item={
                'schema_name': 'server',
                'schema_type': 'user',
                'attributes': attributes
            }
        )


def lambda_handler(event, context):
    try:
        logger.info('Event:\n {}'.format(event))
        logger.info('Contex:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            logger.info('Create action')
            load_schema()
            status = 'SUCCESS'
            message = 'Default schema loaded successfully for Replatform Stack'

        elif event['RequestType'] == 'Update':
            logger.info('Update action')
            status = 'SUCCESS'
            message = 'No update required'

        elif event['RequestType'] == 'Delete':
            logger.info('Delete action')
            delete_schema()
            status = 'SUCCESS'
            message = 'EC2 Replatform Schema has been deleted'

        else:
            logger.info('SUCCESS!')
            status = 'SUCCESS'
            message = 'Unexpected event received from CloudFormation'

    except Exception as e:
        logger.info('FAILED!')
        logger.info(e)
        status = 'FAILED'
        message = 'Exception during processing'

    response_data = {'Message': message}
    response = respond(event, context, status, response_data)

    return {
        'Response': response
    }


def respond(event, context, response_status, response_data):
    # Build response payload required by CloudFormation
    response_body = {
        'Status': response_status,
        'Reason': 'Details in: ' + context.log_stream_name,
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }

    # Convert json object to string and log it
    json_response_body = json.dumps(response_body)
    logger.info('Response body: {}'.format(str(json_response_body)))

    # Set response URL
    response_url = event['ResponseURL']

    # Set headers for preparation for a PUT
    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }

    # Return the response to the signed S3 URL
    try:
        response = requests.put(response_url,
                                data=json_response_body,
                                headers=headers,
                                timeout=30)
        logger.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        logger.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'
