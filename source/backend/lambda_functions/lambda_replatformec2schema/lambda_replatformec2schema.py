#########################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                    #
# SPDX-License-Identifier: MIT-0                                                        #
#                                                                                       #
# Permission is hereby granted, free of charge, to any person obtaining a copy of this  #
# software and associated documentation files (the "Software"), to deal in the Software #
# without restriction, including without limitation the rights to use, copy, modify,    #
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to    #
# permit persons to whom the Software is furnished to do so.                            #
#                                                                                       #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,   #
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A         #
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT    #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION     #
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE        #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                #
#########################################################################################
import factory
import json, boto3, logging, os
import requests

log = logging.getLogger()
log.setLevel(logging.INFO)

SCHEMA_TABLE = os.getenv('SchemaDynamoDBTable')


def load_schema():
    client = boto3.client('dynamodb')

    for item in factory.schema:
        response = client.put_item(
            TableName=SCHEMA_TABLE,
            Item=item
        )
    schema_table = boto3.resource('dynamodb').Table(SCHEMA_TABLE)
    resp = schema_table.get_item(Key={'schema_name': 'server'})
    if 'Item' in resp:
        attributes = []
        attributes = resp['Item']['attributes']
        rootvolsizeexist = 0
        amiidexist = 0
        azexist = 0
        roottypeexist = 0
        addvolsizeexists = 0
        addvoltypeeexists = 0
        ebsoptexists = 0
        ebskmsexists = 0
        detailexists = 0
        rootvolnamexists = 0
        addvolvolnamexists = 0
        for attr in attributes:
            if attr['name'] == 'root_vol_size':
                rootvolsizeexist = 1

            if attr['name'] == 'ami_id':
                amiidexist = 1

            if attr['name'] == 'availabilityzone':
                azexist = 1

            if attr['name'] == 'root_vol_type':
                roottypeexist = 1

            if attr['name'] == 'add_vols_size':
                addvolsizeexists = 1

            if attr['name'] == 'add_vols_type':
                addvoltypeeexists = 1

            if attr['name'] == 'ebs_optimized':
                ebsoptexists = 1

            if attr['name'] == 'ebs_kmskey_id':
                ebskmsexists = 1

            if attr['name'] == 'detailed_monitoring':
                detailexists = 1

            if attr['name'] == 'root_vol_name':
                rootvolnamexists = 1

            if attr['name'] == 'add_vols_name':
                addvolvolnamexists = 1

        if rootvolsizeexist == 0:
            attributes.append({
                "description": "Root Volume Size (GiB)",
                "name": "root_vol_size",
                "system": True,
                "validation_regex_msg": "Volume Size needs to between 1 GiB and 16384 GiB",
                "validation_regex": "^([1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[1][0-6][0-3][0-8][0-4])$",
                "type": "Integer",
                "group": "Target - Storage",
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
        if amiidexist == 0:
            attributes.append(

                {
                    "description": "AMI Id",
                    "name": "ami_id",
                    "system": True,
                    "type": "string",
                    "group": "Target - Instance",
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
        if azexist == 0:
            attributes.append(

                {
                    "description": "Availability zone",
                    "name": "availabilityzone",
                    "system": True,
                    "type": "string",
                    "group": "Target - Instance",
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

        if roottypeexist == 0:
            attributes.append(

                {
                    "description": "Root Volume Type",
                    "name": "root_vol_type",
                    "system": True,
                    "type": "list",
                    "listvalue": "standard,io1,io2,gp2,gp3,",
                    "group": "Target - Storage",
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

        if addvolsizeexists == 0:
            attributes.append(

                {
                    "description": "Additional Volume Sizes (GiB)",
                    "name": "add_vols_size",
                    "system": True,
                    "validation_regex_msg": "Volume Sizes need to be between 1 GiB and 16384 GiB",
                    "validation_regex": "^([1-9]|[1-9][0-9]|[1-9][0-9][0-9]|[1-9][0-9][0-9][0-9]|[1][0-6][0-3][0-8][0-4])$",
                    "type": "multivalue-string",
                    "group": "Target - Storage",
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

        if addvoltypeeexists == 0:
            attributes.append(
                {
                    "description": "Additional Volume Types (standard, io1, io2, gp2, or gp3)",
                    "name": "add_vols_type",
                    "system": True,
                    "type": "multivalue-string",
                    "validation_regex": "^(standard|io1|io2|gp2|gp3)$",
                    "validation_regex_msg": "Allowed Volume Types \"standard\", \"io1\", \"io2\", \"gp2\", or \"gp3\"",
                    "group": "Target - Storage",
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

        if ebsoptexists == 0:
            attributes.append(
                {
                    "description": "Enable EBS Optimized",
                    "name": "ebs_optimized",
                    "system": True,
                    "type": "checkbox",
                    "group": "Target - Storage",
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

        if ebskmsexists == 0:
            attributes.append(

                {
                    "description": "EBS KMS Key Id or ARN for Volume Encryption",
                    "name": "ebs_kmskey_id",
                    "system": True,
                    "type": "string",
                    "group": "Target - Storage",
                    "validation_regex": "^(arn:aws:kms:[a-z0-9-]+:[0-9]{12}:key/){0,1}[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
                    "validation_regex_msg": "Provide a valid KMS Key or ARN.",
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
                    }
                })

        if detailexists == 0:
            attributes.append(

                {
                    "description": "Enable Detailed Monitoring",
                    "name": "detailed_monitoring",
                    "system": True,
                    "type": "checkbox",
                    "group": "Target - Instance",
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

        if rootvolnamexists == 0:
            attributes.append(

                {
                    "description": "Root Volume Name",
                    "name": "root_vol_name",
                    "system": True,
                    "type": "list",
                    "listvalue": "/dev/sda1,/dev/xvda,",
                    "group": "Target - Storage",
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

        if addvolvolnamexists == 0:
            attributes.append(

                {
                    "description": "Additional Volume Names",
                    "name": "add_vols_name",
                    "system": True,
                    "type": "multivalue-string",
                    "group": "Target - Storage",
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

    resp = schema_table.put_item(

        Item={
            'schema_name': 'server',
            'schema_type': 'user',
            'attributes': attributes
        }

    )


def delete_schema():
    schema_table = boto3.resource('dynamodb').Table(SCHEMA_TABLE)
    delresp = schema_table.delete_item(Key={'schema_name': 'EC2'})
    resp = schema_table.get_item(Key={'schema_name': 'server'})
    if 'Item' in resp:
        attributes = []
        attributes = resp['Item']['attributes']
        rootvolsizeexist = 0
        amiidexist = 0
        azexist = 0
        roottypeexist = 0
        addvolsizeexists = 0
        addvoltypeeexists = 0
        ebsoptexists = 0
        ebskmsexists = 0
        detailexists = 0
        rootvolnamexists = 0
        addvolvolnamexists = 0
        for attr in attributes:
            if attr['name'] == 'root_vol_size':
                rootvolsizeexist = 1
                print('rootvolsizeexist')

            if attr['name'] == 'ami_id':
                amiidexist = 1
                print('amiidexist')

            if attr['name'] == 'availabilityzone':
                azexist = 1
                print('azexist')

            if attr['name'] == 'root_vol_type':
                roottypeexist = 1
                print('roottypeexist')

            if attr['name'] == 'add_vols_size':
                addvolsizeexists = 1
                print('addvolsizeexists')

            if attr['name'] == 'add_vols_type':
                addvoltypeeexists = 1
                print('addvoltypeeexists')

            if attr['name'] == 'ebs_optimized':
                ebsoptexists = 1
                print('ebsoptexists')

            if attr['name'] == 'ebs_kmskey_id':
                ebskmsexists = 1
                print('ebskmsexists')

            if attr['name'] == 'detailed_monitoring':
                detailexists = 1
                print('detailexists')

            if attr['name'] == 'root_vol_name':
                rootvolnamexists = 1
                print('rootvolnamexists')

            if attr['name'] == 'add_vols_name':
                addvolvolnamexists = 1
                print('addvolvolnamexists')

        if rootvolsizeexist == 1:
            attributes.remove({
                "description": "Root Volume Size",
                "name": "root_vol_size",
                "system": True,
                "type": "Integer",
                "group": "Target - Storage"
            })
        if amiidexist == 1:
            attributes.remove(

                {
                    "description": "AMI Id",
                    "name": "ami_id",
                    "system": True,
                    "type": "string",
                    "group": "Target - Instance"
                })
        if azexist == 1:
            attributes.remove(

                {
                    "description": "Availability zone",
                    "name": "availabilityzone",
                    "system": True,
                    "type": "string",
                    "group": "Target - Instance"
                })

        if roottypeexist == 1:
            attributes.remove(

                {
                    "description": "Root Volume Type",
                    "name": "root_vol_type",
                    "system": True,
                    "type": "string",
                    "group": "Target - Storage"
                })

        if addvolsizeexists == 1:
            attributes.remove(

                {
                    "description": "Additional Volume Sizes",
                    "name": "add_vols_size",
                    "system": True,
                    "type": "string",
                    "group": "Target - Storage"
                })

        if addvoltypeeexists == 1:
            attributes.remove(

                {
                    "description": "Additional Volume Types",
                    "name": "add_vols_type",
                    "system": True,
                    "type": "string",
                    "group": "Target - Storage"
                })

        if ebsoptexists == 1:
            attributes.remove(

                {
                    "description": "Enable EBS Optimized",
                    "name": "ebs_optimized",
                    "system": True,
                    "type": "checkbox",
                    "group": "Target - Storage"
                })

        if ebskmsexists == 1:
            attributes.remove(

                {
                    "description": "EBS KMS Key Id for Volume Encryption",
                    "name": "ebs_kmskey_id",
                    "system": True,
                    "type": "string",
                    "group": "Target - Storage"
                })

        if detailexists == 1:
            attributes.remove(

                {
                    "description": "Enable Detailed Monitoring",
                    "name": "detailed_monitoring",
                    "system": True,
                    "type": "checkbox",
                    "group": "Target - Instance"
                })

        if rootvolnamexists == 1:
            attributes.remove(

                {
                    "description": "Root Volume Name",
                    "name": "root_vol_name",
                    "system": True,
                    "type": "string",
                    "group": "Target - Storage"
                })

        if addvolvolnamexists == 1:
            attributes.remove(

                {
                    "description": "Additional Volume Names seperated by semicolon(;)",
                    "name": "add_vols_name",
                    "system": True,
                    "type": "string",
                    "group": "Target - Storage"
                })

    resp = schema_table.put_item(

        Item={
            'schema_name': 'server',
            'schema_type': 'user',
            'attributes': attributes
        }

    )


def lambda_handler(event, context):
    try:
        log.info('Event:\n {}'.format(event))
        log.info('Contex:\n {}'.format(context))

        if event['RequestType'] == 'Create':
            log.info('Create action')
            load_schema()
            status = 'SUCCESS'
            message = 'Default schema loaded successfully for Replatform Stack'

        elif event['RequestType'] == 'Update':
            log.info('Update action')
            status = 'SUCCESS'
            message = 'No update required'

        elif event['RequestType'] == 'Delete':
            log.info('Delete action')
            delete_schema()
            status = 'SUCCESS'
            message = 'EC2 Replatform Schema has been deleted'

        else:
            log.info('SUCCESS!')
            status = 'SUCCESS'
            message = 'Unexpected event received from CloudFormation'

    except Exception as e:
        log.info('FAILED!')
        log.info(e)
        status = 'FAILED'
        message = 'Exception during processing'

    response_data = {'Message': message}
    response = respond(event, context, status, response_data, None)

    return {
        'Response': response
    }


def respond(event, context, responseStatus, responseData, physicalResourceId):
    # Build response payload required by CloudFormation
    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'Details in: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['Data'] = responseData

    # Convert json object to string and log it
    json_responseBody = json.dumps(responseBody)
    log.info('Response body: {}'.format(str(json_responseBody)))

    # Set response URL
    responseUrl = event['ResponseURL']

    # Set headers for preparation for a PUT
    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    # Return the response to the signed S3 URL
    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        log.info('Status code: {}'.format(str(response.reason)))
        return 'SUCCESS'

    except Exception as e:
        log.error('Failed to put message: {}'.format(str(e)))
        return 'FAILED'
