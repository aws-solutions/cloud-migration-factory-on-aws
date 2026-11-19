#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import json
from boto3 import client as boto3_client
from typing import Any
from enum import Enum
import re

import cmf_boto
from cmf_logger import logger, log_event_received
from cmf_utils import default_http_headers

bedrock_runtime = boto3_client("bedrock-runtime")
model = os.environ["model"]
schema_table_name = os.environ["SCHEMA_TABLE_NAME"]


# RuleType enums
class RuleType(Enum):
    PRIORITIZING = "PRIORITIZING"
    GROUPING = "GROUPING"


# Constants
RELATIONSHIP_ATTRIBUTE_TYPES = frozenset(["relationship", "multivalue-relationship"])


def lambda_handler(event: Any, _):
    log_event_received(event)

    if model == "Not Supported":
        return {
            "headers": {**default_http_headers}, 
            "statusCode": 500, 
            "body": "No preferred model was available. Confirm Bedrock is available in your deployed AWS Region"
        }

    try:
        body = json.loads(event["body"])
    except Exception as e:
        logger.error(f"malformed json input {e}")
        return {
            "headers": {**default_http_headers},
            "statusCode": 400,
            "body": "malformed json input",
        }

    try:
        rule_type = body.get("rule_type")
        # Validate rule_type
        if rule_type is None:
            raise ValueError(
                f"rule_type is required. Supported values: {', '.join(rt.value for rt in RULE_PROMPTS.keys())}"
            )
        try:
            rule_type_enum = RuleType(rule_type)  # This will raise ValueError if invalid
        except ValueError:
            raise ValueError(
                f"rule_type is invalid. Supported values: {', '.join(rt.value for rt in RULE_PROMPTS.keys())}"
            )

        if rule_type_enum not in RULE_PROMPTS:
            raise ValueError(
                f"rule_type is invalid. Supported values: {', '.join(rt.value for rt in RULE_PROMPTS.keys())}"
            )

        user_input = body.get("user_input", "")
        if not user_input.strip():
            raise ValueError("user_input is required")
        if len(user_input) < 5:
            raise ValueError("user_input too short (minimum 5 characters)")
        if len(user_input) > 500:
            raise ValueError("user_input too long (maximum 500 characters)")

        # Allowlist: letters, numbers, spaces, basic punctuation, common rule keywords
        allowed_pattern = r'^[a-zA-Z0-9\s\-_.,;:()\[\]{}\/\\\'"]+$'
        if not re.match(allowed_pattern, user_input):
            raise ValueError("user_input contains invalid characters")

    except ValueError as e:
        logger.error(f"Unable to parse user input {e}")
        return {
            "headers": {**default_http_headers},
            "statusCode": 400,
            "body": f"incorrect request type. {e}",
        }

    try:
        schema = get_schema(rule_type_enum)
        response = generate_rule(rule_type_enum, user_input, schema)
    except ValueError as e:
        logger.error(f"Unable to generate rule {e}")
        return {"headers": {**default_http_headers}, "statusCode": 400, "body": str(e)}
    except Exception as e:
        logger.error(f"Unable to generate rule {e}")
        return {
            "headers": {**default_http_headers},
            "statusCode": 500,
            "body": f"internal server exception",
        }

    return {
        "headers": {**default_http_headers},
        "statusCode": 200,
        "body": json.dumps(response),
    }


def get_schema(rule_type: RuleType):
    """Fetch schema from DynamoDB and filter for id, description, type, and listvalue fields"""
    try:
        dynamodb = cmf_boto.resource("dynamodb")
        schema_table = dynamodb.Table(schema_table_name)

        response = schema_table.scan(ConsistentRead=True)
        schemas = {}

        for item in response["Items"]:
            schema_name = item.get("schema_name")
            schema_type = item.get("schema_type")
            # Default schemas and all custom asset schemas
            if schema_name and schema_name in DEFAULT_SCHEMAS or schema_type == "custom":
                filtered_attrs = []
                for attr in item.get("attributes", []):
                    attr_name = attr.get("name", "")
                    attr_type = attr.get("type", "string")
                    # If GROUPING rule then all attributes otherwise i.e. PRIORITIZING only non-relationship attributes
                    if rule_type == RuleType.GROUPING or attr_type not in RELATIONSHIP_ATTRIBUTE_TYPES:
                        attr_dict = {
                            "name": attr_name,
                            "description": attr.get("description", ""),
                            "type": attr_type,
                        }
                        listvalue = attr.get("listvalue", "")
                        if listvalue and listvalue.strip():
                            attr_dict["listvalue"] = listvalue
                        filtered_attrs.append(attr_dict)
                schemas[schema_name] = filtered_attrs

        return schemas
    except Exception as e:
        logger.error(f"Error fetching schema: {str(e)}")
        return {}


def generate_rule(rule_type: RuleType, user_input: str, schema: dict):
    # Step 1: Apply guardrail if configured. There is a known compatibility issue between guardrailConfig and toolConfig
    guardrail_id = os.environ.get("BEDROCK_GUARDRAIL_ID")
    guardrail_version = os.environ.get("BEDROCK_GUARDRAIL_VERSION")
    
    if guardrail_id and guardrail_version:
        guardrail_response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            source="INPUT",
            content=[{"text": {"text": user_input}}]
        )
        
        if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
            logger.error(f"Guardrail validation error: {guardrail_response}")
            raise ValueError("Content blocked by guardrail policy")
        
    # Get rule type configuration and tool spec
    rule_prompt = RULE_PROMPTS[rule_type]
    examples = RULE_EXAMPLES.get(rule_type, {})

    format_args = {
        # Convert to string and escape special characters
        "sanitized_schema": json.dumps(schema),
        "user_input": user_input,
    }

    # Add any examples defined for this rule type
    for example_key, example_value in examples.items():
        format_args[f"{example_key}"] = example_value

    # Format the prompt with dynamic arguments
    prompt = rule_prompt["prompt_template"].format(**format_args)

    # Format the tool spec template
    tool_spec_template = TOOL_SPECS[rule_type]
    schema_names = json.dumps(list(schema.keys()))
    tool_spec = json.loads(tool_spec_template.format(schema_names=schema_names))



    # Step 2: Call LLM
    request_payload = {
        "modelId": model,
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "toolConfig": {
            "tools": [{"toolSpec": tool_spec}],
            "toolChoice": {"tool": {"name": tool_spec["name"]}},
        },
    }

    try:
        response = bedrock_runtime.converse(**request_payload)
        return response["output"]["message"]["content"][0]["toolUse"]["input"]

    except Exception as e:
        error_msg = str(e)
        if "AccessDeniedException" in error_msg:
            raise ValueError("Access denied to AI model. Please check your permissions.")
        elif "ValidationException" in error_msg:
            raise ValueError("Invalid request to AI model. Please try again.")
        elif "ThrottlingException" in error_msg:
            raise ValueError("AI service is busy. Please try again later.")
        else:
            raise ValueError(f"AI service error: {error_msg}")


# Define supported entity schemas
DEFAULT_SCHEMAS = ["app", "server", "database"]

# Common prompt context that applies to all rules
COMMON_RULE_PROMPT_CONTEXT = """
XYZ is an IT asset management system that maintains records of various types of assets. 
The system comes with three built-in asset types: `app`, `server`, and `database`. 
Users also have the flexibility to define their own custom asset types.

Each asset type is defined by a schema that specifies its attributes. The primary identifier 
for any asset follows the naming pattern `<asset_type>_id` (for example, `app_id`, `server_id`, `database_id`).

Apps can have many-to-many relationships with assets of other types. Such relationships enable the grouping, sorting
or scoring the apps based on the related assets of other types.
"""

# Common instructions that apply to all rules
COMMON_RULE_PROMPT_INSTRUCTIONS = """
## IMPORTANT: Single Rule Generation
- **You MUST generate exactly ONE rule, never multiple rules**
- **If the user input contains multiple rule requests, choose the FIRST rule mentioned**
- **Ignore any additional rule requests beyond the first one**
- **Do not attempt to combine multiple rules into one**
"""

# Define prompt templates for different rule types
RULE_PROMPTS = {
    RuleType.PRIORITIZING: {
        "prompt_template": f"""
# Context

{COMMON_RULE_PROMPT_CONTEXT}

# Task: You are a rule generation assistant. Convert user input into a single structured JSON rule.

{COMMON_RULE_PROMPT_INSTRUCTIONS}

## Rule Type Decision Process:
First, analyze the user input to determine if they want:
- **SCORING**: When users mention prioritizing, scoring, giving higher/lower priority, complexity, or importance
- **SORTING**: When users mention ordering, sorting, arranging by sequence, or organizing by specific order

## Supported rule types:
1. **SCORING with numeric ranges**: Use lower_bound/upper_bound to define value ranges; omit a bound to indicate it is open-ended
2. **SCORING with categorical values**: Use value field for exact matches. Consider listvalue in schema for expected values
3. **SCORING with patterns**: Use name/pattern fields for regex matching
4. **SORTING**: Use sort_order (ASC/DSC), sort_level, and optionally sort_by_value array for custom ordering

**For SCORING rules**: Include scoring_criteria array with complexity_score (0-100, lower = higher priority)
**For SORTING rules**: Include sort_order, sort_level, and optionally sort_by_value array

## High-Level Principles:
- **CRITICAL: Set asset_type based on which schema contains the attribute, NOT the user's wording**
- **Example: "score applications by server storage size" should use asset_type="server" because server_storage_size is in the server schema**
- **You do NOT need to assign scores to every possible value**
- **If user mentions specific values, score only those and leave others out**
- Lower complexity_score means higher priority (0-100 range)
- Keep rules minimal for high-cardinality columns unless user specifies multiple values
- For sorting, use sort_level to indicate priority order when multiple sort rules exist

## Examples:

### SCORING Rule:
User: "Give higher complexity_score to larger storage sizes"
json
{{scoring_example}}

### SORTING Rule:
User: "Sort applications by department priority: IT, marketing, sales, finance"
json
{{sorting_example}}

## Input:
<schema>{{sanitized_schema}}</schema>
<user_input>{{user_input}}</user_input>

## Output:
Use the rule_generator tool to return the rule in the required JSON format.
Do not wrap the rule in an array or container object. Return only the single rule object.
        """
    },
    RuleType.GROUPING: {
        "prompt_template": f"""
# Context

{COMMON_RULE_PROMPT_CONTEXT}

A 'Move Group' function will be provided with:
- Inventories of assets such as apps, databases and servers. The data match the respective schema.
- Grouping rules that defines how assets should be grouped together in JSON format.

There are two types of grouping rules:

1. Inclusive Rule: A type of grouping rule that identifies and combines related assets into the same group 
based on shared dependencies or attributes (e.g., apps sharing same server or database must move together).
2. Exclusive Rule: A type of grouping rule that segments a group into smaller groups based on specific
asset attributes (e.g., splitting servers by environment).

At runtime, the function groups the assets based on the grouping rules in two phases where:
1. Inclusive rules are evaluated first to identify related assets, 
2. Followed by exclusive rules to segment the groups based on specific criteria.

# Task

You are a rule generation assistant. Convert user input into a grouping rule as described above.

{COMMON_RULE_PROMPT_INSTRUCTIONS}

## Rule Type Decision Process
- First, analyze the user input to determine if they want:
  - GROUPING_INCLUSIVE: When users mention grouping, dependency, relationship, or shared/sharing resources
  - GROUPING_EXCLUSIVE: When users mention segment, breaking down, or splitting
- Then deduce the 'asset_type' (e.g. app, database, server, etc) and 'asset_key' by matching user input with the attributes defined in the provided schemas.
  - The 'asset_key' must exists in the attribute list of the related schema.
  - **DO NOT** include 'app' (as 'asset_type') and related relationship attributes (e.g. 'server_ids'
  for 'server' asset type, or 'storage_ids' for 'storage' custom asset type) in the array of 'relationships' attribute.

## Examples

### Inclusive rule with single asset_type
- User: 'Group apps sharing servers'
- json:
{{inclusive_rule_with_single_asset_type}}
- Notes:
{{inclusive_rule_with_single_asset_type_notes}}

### Inclusive rule with multiple asset_type
- User: 'Group apps and databases belong to the same owner'
- json:
{{inclusive_rule_with_multiple_asset_type}}
- Notes:
{{inclusive_rule_with_multiple_asset_type_notes}}

### Exclusive rule
- User: 'Break servers by their environment'
- json:
{{exclusive_rule}}
- Notes:
{{exclusive_rule_notes}}

## Input:
<schema>{{sanitized_schema}}</schema>
<user_input>{{user_input}}</user_input>

## Output:
Use the rule_generator tool to return the rule in the required JSON format.
Do not wrap the rule in an array or container object. Return only the single rule object.
        """
    },
}

# Define tool specifications for different rule types
TOOL_SPECS = {
    RuleType.PRIORITIZING: """{{
        "name": "rule_generator",
        "description": "Generates a single prioritization rule from user input in structured JSON format.",
        "inputSchema": {{
            "json": {{
                "type": "object",
                "properties": {{
                    "rule_type": {{
                        "type": "string",
                        "enum": ["PRIORITIZING"],
                        "description": "The type of rule being generated"
                    }},
                    "rule_name": {{
                        "type": "string",
                        "description": "Name for the rule, start with Sort By or Score By"
                    }},
                    "rule_description": {{
                        "type": "string",
                        "description": "Clear description of what the rule does"
                    }},
                    "sub_type": {{
                        "type": "string",
                        "enum": ["SCORING", "SORTING"],
                        "description": "The sub-type of prioritization rule"
                    }},
                    "status": {{
                        "type": "string",
                        "enum": ["ENABLED", "DISABLED"],
                        "description": "Whether the rule is active"
                    }},
                    "asset_type": {{
                        "type": "string",
                        "enum": {schema_names},
                        "description": "The type of asset this rule applies to"
                    }},
                    "attr_key": {{
                        "type": "string",
                        "description": "The attribute key being evaluated"
                    }},
                    "scoring_criteria": {{
                        "type": "array",
                        "description": "Scoring criteria for SCORING rules",
                        "items": {{
                            "type": "object",
                            "properties": {{
                                "value": {{"type": "string"}},
                                "lower_bound": {{"type": "number"}},
                                "upper_bound": {{"type": "number"}},
                                "name": {{"type": "string"}},
                                "pattern": {{"type": "string"}},
                                "complexity_score": {{"type": "number", "minimum": 0, "maximum": 100}}
                            }},
                            "required": ["complexity_score"]
                        }}
                    }},
                    "sort_order": {{
                        "type": "string",
                        "enum": ["ASC", "DSC"],
                        "description": "Sort order for SORTING rules"
                    }},
                    "sort_level": {{
                        "type": "number",
                        "description": "Priority level for SORTING rules"
                    }},
                    "sort_by_value": {{
                        "type": "array",
                        "items": {{"type": "string"}},
                        "description": "OPTIONAL: Custom ordering array for SORTING rules"
                    }}
                }},
                "required": [
                    "rule_type",
                    "rule_name",
                    "rule_description",
                    "sub_type",
                    "status",
                    "asset_type",
                    "attr_key"
                ]
            }}
        }}
    }}""",
    RuleType.GROUPING: """{{
        "name": "rule_generator",
        "description": "Generates a single grouping rule from user input in structured JSON format.",
        "inputSchema": {{
            "json": {{
                "type": "object",
                "properties": {{
                    "rule_type": {{
                        "type": "string",
                        "enum": ["GROUPING_INCLUSIVE", "GROUPING_EXCLUSIVE"],
                        "description": "Type of the rule"
                    }},
                    "rule_name": {{"type": "string", "description": "Name of the rule"}},
                    "rule_description": {{"type": "string", "description": "Detailed description of what the rule does"}},
                    "relationships": {{
                        "type": "array",
                        "items": {{
                            "type": "object",
                            "properties": {{
                                "asset_type": {{
                                    "type": "string",
                                    "enum": {schema_names},
                                    "description": "Type of asset"
                                }},
                                "asset_key": {{"type": "string", "description": "Key used for grouping assets"}}
                            }},
                            "required": ["asset_type", "asset_key"]
                        }},
                        "minItems": 1,
                        "description": "List of relationships defining the grouping criteria"
                    }},
                    "status": {{"type": "string", "enum": ["ENABLED", "DISABLED"], "description": "Status of the rule"}}
                }},
                "required": ["rule_type", "rule_name", "relationships", "status"]
            }}
        }}
    }}""",
}

# Define examples for different rule types
RULE_EXAMPLES = {
    RuleType.PRIORITIZING: {
        "scoring_example": {
            "rule_type": "PRIORITIZING",
            "rule_name": "Score By Storage Size",
            "rule_description": "Score servers based on storage size",
            "sub_type": "SCORING",
            "status": "ENABLED",
            "asset_type": "server",
            "attr_key": "server_storage_size",
            "scoring_criteria": [
                {"upper_bound": 200, "complexity_score": 20},
                {"lower_bound": 200, "upper_bound": 500, "complexity_score": 40},
                {"lower_bound": 500, "upper_bound": 1000, "complexity_score": 60},
                {"lower_bound": 1000, "complexity_score": 80},
            ],
        },
        "sorting_example": {
            "rule_type": "PRIORITIZING",
            "rule_name": "Sort By Department Priority",
            "rule_description": "Sort applications by department priority order",
            "sub_type": "SORTING",
            "status": "ENABLED",
            "asset_type": "app",
            "attr_key": "app_department",
            "sort_by_value": ["IT", "marketing", "sales", "finance"],
            "sort_order": "ASC",
            "sort_level": 1,
        },
    },
    RuleType.GROUPING: {
        "inclusive_rule_with_single_asset_type": {
            "rule_type": "GROUPING_INCLUSIVE",
            "rule_name": "Group apps sharing servers",
            "relationships": [{"asset_type": "app", "asset_key": "server_ids"}],
            "status": "ENABLED",
        },
        "inclusive_rule_with_single_asset_type_notes": """
You only need to generate one item in the `relationships` array as `server_ids` is defined as a 
relationship attribute in app schema, and `app_ids` are defined as a relationship attribute in 
server schema. At runtime the function will automatically interpret the rule into the following 
two unidirectional rules:
```
  "relationships": [
    {"asset_type": "app", "asset_key": "server_ids"}
    {"asset_type": "server", "asset_key": "app_ids"}
  ]
```
""",
        "inclusive_rule_with_multiple_asset_type": {
            "rule_type": "GROUPING_INCLUSIVE",
            "rule_name": "Group app and db by owner",
            "relationships": [
                {"asset_type": "app", "asset_key": "app_owner"},
                {"asset_type": "database", "asset_key": "db_owner"},
            ],
            "status": "ENABLED",
        },
        "inclusive_rule_with_multiple_asset_type_notes": """
You need to generate two items in the `relationships` array as `app_owner` and `db_owner` are
defined as string attributes in app and database schemas respectively.
""",
        "exclusive_rule": {
            "rule_type": "GROUPING_EXCLUSIVE",
            "rule_name": "Segment servers by environment",
            "relationships": [{"asset_type": "server", "asset_key": "environment"}],
        },
        "exclusive_rule_notes": "",
    },
}
