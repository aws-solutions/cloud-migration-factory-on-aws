#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
from typing import Any, List, Dict

from cmf_logger import logger


def process_map_headers_request(request: Dict[str, Any], bedrock_runtime: Any, model: str) -> Dict[str, Any]:
    """
    Process a request to map headers by querying Bedrock and posting the response.

    Args:
        request: The request containing headers and schemas
        bedrock_runtime: Bedrock runtime client
        model: The Bedrock model ID to use

    Returns:
        The response to be sent to the client
    """
    try:
        response = query_bedrock(request, bedrock_runtime, model)
    except Exception as e:
        logger.warning(f"Unable to query bedrock: {e}")
        raise RuntimeError(f"Failed to query bedrock: {str(e)}") from e

    return response


def query_bedrock(request: Dict[str, Any], bedrock_runtime: Any, model: str) -> Dict[str, Any]:
    """
    Query the Bedrock API to map headers.

    Args:
        request: The request containing headers and schemas
        bedrock_runtime: Bedrock runtime client
        model: The Bedrock model ID to use

    Returns:
        Dict[str, Any]: The processed mappings

    Raises:
        RuntimeError: If the Bedrock API call fails
        ValueError: If the response format is invalid
    """

    tool_name = "header_map"
    schemas = request.get("schemas", {})
    headers = request.get("headers", [])
    # Step 1: Apply guardrail if configured. There is a known compatibility issue between guardrailConfig and toolConfig
    guardrail_id = os.environ.get("BEDROCK_GUARDRAIL_ID")
    guardrail_version = os.environ.get("BEDROCK_GUARDRAIL_VERSION")

    if guardrail_id and guardrail_version:
        guardrail_response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=guardrail_id,
            guardrailVersion=guardrail_version,
            source="INPUT",
            content=[{"text": {"text": json.dumps(headers)}}],
        )

        if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
            logger.error(f"Guardrail validation error: {guardrail_response}")
            raise RuntimeError("Content blocked by guardrail policy")

    prompt = generate_prompt(headers, schemas, tool_name)

    tool_spec = create_tool_spec(schemas, tool_name)

    # Step 2: Call LLM
    try:
        converse_params = {
            "modelId": model,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "toolConfig": {"tools": tool_spec, "toolChoice": {"tool": {"name": tool_name}}},
        }

        response = bedrock_runtime.converse(**converse_params)

    except Exception as e:
        logger.warning(f"Bedrock API error: {str(e)}")
        raise RuntimeError(f"Failed to query Bedrock API: {str(e)}")

    try:
        result = response["output"]["message"]["content"][0]["toolUse"]["input"]
    except (KeyError, IndexError, TypeError) as e:
        logger.warning(f"Invalid response format from Bedrock: {str(e)}. Response structure {str(response)}")
        raise ValueError("Invalid response format from Bedrock: missing expected toolUse structure")

    # Process each entity's mappings to sort by confidence
    for entity in schemas.keys():
        if entity in result and "mappings" in result[entity]:
            sort_mappings_by_confidence(result[entity]["mappings"])

    return result


def generate_prompt(headers: List[str], schemas: Dict[str, Any], tool_name: str) -> str:
    """
    Generate a prompt for the Bedrock model to map headers.

    Args:
        headers: List of CSV headers
        schemas: Dictionary of schema definitions where keys are entity types

    Returns:
        str: The generated prompt
    """
    sanitized_headers = json.dumps(headers)
    sanitized_schemas = json.dumps(schemas)

    entity_types = ", ".join(schemas.keys())

    prompt = f"""
    <instructions>
    You are an expert data mapping specialist. 
    Your task is to create precise mappings between CSV headers and schema attributes for multiple entity types ({entity_types}) using both syntactic and semantic analysis.
    You should perform this task efficiently with a best-guess approach; there will be an opportunity for someone to correct any mistakes.
    </instructions>

    <strategy>
    Apply these matching techniques in priority order:
    1. Exact match (case-insensitive)
    2. Normalized matches (remove spaces, underscores, special characters)
    3. Abbreviation expansion (e.g. ver -> Version, env -> Environment, db -> Database)
    4. Semantic equivalents (e.g. Host <-> Server, App <-> Application)
    5. Pattern recognition using sample values to infer field purpose
    6. For relationship attributes: Match against both the attribute name AND the rel_display_attribute
    7. Schema description similarity - use attribute descriptions to understand semantic meaning and purpose
    </strategy>

    <rules>
    - Each CSV header can map to attributes across multiple entity types
    - For each entity type, a CSV header should map to at most one attribute
    - Focus on higher confidence matches (>0.7 for strong matches, >0.4 for potential matches)
    - Ensure data type compatibility between headers and target attributes
    - When mapping to relationship or multivalue-relationship attributes, always use the 'name' field as the target_header, not the display_name
    </rules>

    <relationship_matching>
    - Relationship and multivalue-relationship attributes have both a 'name' (internal identifier) and 'rel_display_attribute' (human-readable name)
    - CSV headers may match either the internal name (e.g., 'app_ids') or the display name (e.g., 'app_name')
    - If a multivalue-relationship, the display name can be a plural
    - Always map to the 'name' field in your response, but consider both names when determining matches
    </relationship_matching>

    <unmatched>
    - For CSV headers that appear to belong to an entity type but have no matching attribute, recommend a new attribute name.
    - Only make a recommendation if the confidence score exceeds 0.8 or if there are clear semantic matches based on field naming conventions.
    - For each entity type, list any schema attributes that have no corresponding CSV header
    </unmatched>

    <input>
    <schemas>{sanitized_schemas}</schemas>
    <headers>{sanitized_headers}</headers>
    </input>

    <output>
    - Use the {tool_name} tool to return mappings for each entity type in the required JSON format.
    - For each mapping, source header must exist in the input headers.
    - For relationship attributes, use the 'name' field as target_header, not the display name.
    </output>
    """

    return prompt


def create_tool_spec(schemas: Dict[str, Any], tool_name: str) -> List[Dict[str, Any]]:
    """
    Create the tool spec for header mapping based on provided schemas.

    Args:
        schemas: Dictionary of schema definitions where keys are entity types

    Returns:
        List[Dict[str, Any]]: Tool configuration including schema definitions
    """

    inputSchema = {
        "type": "object",
        "properties": {
            "mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_header": {
                            "type": "string",
                            "description": "The name of the source header from the CSV file.",
                        },
                        "target_header": {
                            "type": "string",
                            "description": "The attribute name in the schema that the source_header maps to. For relationship and multivalue-relationship attributes, use the 'name' field not the rel_display_attribute.",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "The confidence level of the match, from 0 to 1.",
                        },
                    },
                },
            },
            "unmapped_attributes": {
                "type": "array",
                "description": "Attributes in the schema that are not mapped to any source header",
                "items": {"type": "string"},
            },
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_header": {
                            "type": "string",
                            "description": "The name of the source header from the CSV file.",
                        },
                        "recommended_header": {
                            "type": "string",
                            "description": "A recommended new attribute to add to the schema",
                        },
                        "recommended_title": {
                            "type": "string",
                            "description": "A human-readable name of the new attribute being added to the schema",
                        },
                    },
                },
            },
        },
    }

    # Repeat for each schema - this seems working better than the JSON schema $ref
    properties = {key: inputSchema for key in schemas.keys()}

    return [
        {
            "toolSpec": {
                "name": tool_name,
                "description": "Maps CSV headers to fields in multiple schemas, identifying matches and suggesting new attributes for unmatched headers.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": properties,
                        "required": list(schemas.keys()),
                    }
                },
            }
        }
    ]


def sort_mappings_by_confidence(header_mappings: List[Dict[str, Any]]) -> None:
    """
    Despite of the instruction in the prompt LLM can still map multiple headers to the same entity attribute.
    This function sorts the mappings by confidence in-place and expects client to use only the one with highest confidence.

    Args:
        header_mappings: List of header mapping dictionaries
    """
    if not header_mappings:
        return

    headers_by_target: Dict[str, List[Dict[str, Any]]] = {}

    # Group mappings by target header
    for mapping in header_mappings:
        target = mapping.get("target_header")
        if not target:
            continue

        if target in headers_by_target:
            headers_by_target[target].append(mapping)
        else:
            headers_by_target[target] = [mapping]

    # Create a new sorted list
    sorted_mappings = []

    # Process each group of mappings
    for target, mappings in headers_by_target.items():
        # Sort mappings by confidence (highest first)
        mappings.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        sorted_mappings.extend(mappings)

    # Clear and update the original list with sorted mappings
    header_mappings.clear()
    header_mappings.extend(sorted_mappings)
