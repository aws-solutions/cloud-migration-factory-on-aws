#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
JSON Schema definitions for Lambda input validation using aws-lambda-powertools.
"""

AUDIT_HISTORY = {
    "type": "object",
    "required": [
        "createdBy",
        "createdTimestamp"
    ],
    "properties": {
        "createdBy": {
            "type": "object",
            "required": [
                "userRef"
            ],
            "properties": {
                "email": {
                    "type": "string",
                },
                "userRef": {
                    "type": "string",
                }
            }
        },
        "createdTimestamp": {
            "type": "string",
            "format": "date-time"
        },
        "lastModifiedBy": {
            "type": "object",
            "required": [
                "userRef"
            ],
            "properties": {
                "email": {
                    "type": "string",
                },
                "userRef": {
                    "type": "string",
                }
            }
        },
        "lastModifiedTimestamp": {
            "type": "string",
            "format": "date-time"
        }
    }
}

# Input validation schema for POST /upload/data/entities
POST_ENTITIES_INPUT = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "required": ["updated_schemas", "file_size", "total_entities", "filename", "data_source_id"],
    "properties": {
        "updated_schemas": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 50,
                "pattern": "^[a-zA-Z][a-zA-Z0-9_-]*$"
            },
            "minItems": 1,
            "maxItems": 20,
            "uniqueItems": True
        },
        # 50mb max
        "file_size": {
            "type": "number",
            "minimum": 1,
            "maximum": 50000000 
        },
        # 100k max
        "total_entities": {
            "type": "number",
            "minimum": 1,
            "maximum": 100000
        },
        "filename": {
            "type": "string",
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9][-a-zA-Z0-9()_ .,]+$"
        },
        "data_source_id": {
            "type": "string",
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
    },
    "additionalProperties": False
}

# Output validation schema for POST /upload/data/entities
POST_ENTITIES_OUTPUT = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "required": ["id", "status", "uploaded_by", "filename", "file_size", "total_entities", "data_source_id", "presigned_url", "expires_at", "s3_object_metadata", "_history"],
    "properties": {
        "id": {
            "type": "string",
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "status": {
            "type": "string",
            "enum": ["pending", "complete", "in-progress", "failed", "complete-with-warnings", "superseded"]
        },
        "uploaded_by": {
            "type": "string",
            "maxLength": 50,
        },
        "filename": {
            "type": "string",
            "maxLength": 100,
        },
        "file_size": {
            "type": "number",
            "minimum": 1,
            "maximum": 50000000
        },
        "total_entities": {
            "type": "number",
            "minimum": 1,
            "maximum": 100000
        },
        "data_source_id": {
            "type": "string",
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "presigned_url": {
            "type": "string",
            "maxLength": 5000,
        },
        "expires_at": {
            "type": "string",
            "maxLength": 30,
        },
        "s3_object_metadata": {
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z0-9_-]+$": {
                    "type": "string",
                    "maxLength": 2048
                }
            },
            "additionalProperties": False,
            "maxProperties": 10
        },
        "_history": AUDIT_HISTORY,
    },
    "additionalProperties": False
}

# Input validation schema for GET /upload/data/entities/{id}
GET_ENTITY_INPUT = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "required": ["pathParameters"],
    "properties": {
        "pathParameters": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {
                    "type": "string",
                    "maxLength": 100,
                    "pattern": "^[a-zA-Z0-9_-]+$"
                },
            },
            "additionalProperties": False
        },
    },
    "additionalProperties": True
}

# Output validation schema for GET /upload/data/entities/{id}
GET_ENTITY_OUTPUT = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "required": ["id", "status", "uploaded_by", "filename", "file_size", "total_entities", "data_source_id", "_history"],
    "properties": {
        "id": {
            "type": "string",
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "status": {
            "type": "string",
            "enum": ["pending", "complete", "in-progress", "failed", "complete-with-warnings", "superseded"]
        },
        "uploaded_by": {
            "type": "string",
            "maxLength": 50,
        },
        "filename": {
            "type": "string",
            "maxLength": 100,
        },
        "file_size": {
            "type": "number",
            "minimum": 1,
            "maximum": 50000000
        },
        "total_entities": {
            "type": "number",
            "minimum": 1,
            "maximum": 100000
        },
        "data_source_id": {
            "type": "string",
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "results_url": {
            "type": "string",
            "maxLength": 20000,
        },
        "_history": AUDIT_HISTORY,
    },
    "additionalProperties": False
}

# Input validation schema for GET /upload/data/entities
LIST_ENTITIES_INPUT = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "required": ["queryStringParameters"],
    "properties": {
        "queryStringParameters": {
            "type": "object",
            "required": ["limit"],
            "properties": {
                "limit": {
                    "type": "string",
                    "maxLength": 3,
                    "pattern": "^[0-9]+$"
                },
                "next_token": {
                    "type": "string",
                    "maxLength": 400,
                },
            },
            "additionalProperties": False
        },
    },
    "additionalProperties": True
}

# Output validation schema for GET /upload/data/entities
LIST_ENTITIES_OUTPUT = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "status", "uploaded_by", "filename", "file_size", "total_entities", "data_source_id", "_history"],
                "properties": {
                    "id": {
                        "type": "string",
                        "maxLength": 100,
                        "pattern": "^[a-zA-Z0-9_-]+$"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "complete", "in-progress", "failed", "complete-with-warnings", "superseded"]
                    },
                    "uploaded_by": {
                        "type": "string",
                        "maxLength": 50,
                    },
                    "filename": {
                        "type": "string",
                        "maxLength": 100,
                    },
                    "file_size": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 50000000
                    },
                    "total_entities": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 100000
                    },
                    "data_source_id": {
                        "type": "string",
                        "maxLength": 100,
                        "pattern": "^[a-zA-Z0-9_-]+$"
                    },
                    "results_url": {
                        "type": "string",
                        "maxLength": 20000,
                    },
                    "_history": AUDIT_HISTORY,
                },
                "additionalProperties": False
            },
            "maxItems": 100
        },
        "next_token": {
            "type": "string",
            "maxLength": 400,
        },
        "count": {
            "type": "number",
            "maximum": 100
        },
    },
    "additionalProperties": False
}
