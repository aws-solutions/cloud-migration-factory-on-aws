#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

schema = [

    {
        "schema_name": {
            "S": "EC2"
        },
      "schema_type": {
        "S": "automation"
      },
      "friendly_name": {
        "S": "EC2"
      },
      "attributes": {
        "L": [
          {
            "M": {
              "rel_display_attribute": {
                "S": "aws_accountid"
              },
              "system": {
                "BOOL": True
              },
              "validation_regex": {
                "S": "^(?!\\s*$).+"
              },
              "rel_key": {
                "S": "aws_accountid"
              },
              "name": {
                "S": "accountid"
              },
              "description": {
                "S": "AWS account ID"
              },
              "rel_entity": {
                "S": "application"
              },
              "validation_regex_msg": {
                "S": "AWS account ID must be provided."
              },
              "type": {
                "S": "relationship"
              }
            }
          },
          {
            "M": {
              "rel_display_attribute": {
                "S": "wave_name"
              },
              "system": {
                "BOOL": True
              },
              "validation_regex": {
                "S": "^(?!\\s*$).+"
              },
              "rel_key": {
                "S": "wave_id"
              },
              "name": {
                "S": "waveid"
              },
              "description": {
                "S": "Wave"
              },
              "rel_entity": {
                "S": "wave"
              },
              "validation_regex_msg": {
                "S": "Wave must be provided."
              },
              "type": {
                "S": "relationship"
              }
            }
          }
        ]
      },
      "group": {
        "S": "RePlatform"
      },
      "description": {
        "S": "New EC2 Build"
      },
      "actions": {
        "L": [
          {
            "M": {
              "name": {
                "S": "EC2 Input Validation"
              },
              "apiMethod": {
                "S": "post"
              },
              "id": {
                "S": "EC2 Input Validation"
              },
              "awsuistyle": {
                "S": "primary"
              },
              "apiPath": {
                "S": "/gfvalidate"
              }
            }
          },
          {
            "M": {
              "name": {
                "S": "EC2 Generate CF Template"
              },
              "apiMethod": {
                "S": "post"
              },
              "id": {
                "S": "EC2 Generate CF Template"
              },
              "awsuistyle": {
                "S": "primary"
              },
              "apiPath": {
                "S": "/gfbuild"
              }
            }
          },
          {
            "M": {
              "name": {
                "S": "EC2 Deployment"
              },
              "apiMethod": {
                "S": "post"
              },
              "id": {
                "S": "EC2 Deployment"
              },
              "awsuistyle": {
                "S": "primary"
              },
              "apiPath": {
                "S": "/gfdeploy"
              }
            }
          }
        ]
      }
    }
]
