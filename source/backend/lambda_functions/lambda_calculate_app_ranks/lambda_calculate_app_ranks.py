#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import re
import sys
import simplejson as json
import os
import boto3
from typing import Any, Dict, List
from botocore.config import Config
from botocore.exceptions import ClientError

from policy import MFAuth
from cmf_logger import logger, log_event_received
from cmf_utils import default_http_headers


# Validate environment variables at module load
def validate_environment():
    required_vars = ["APPS_TABLE_NAME", "SERVERS_TABLE_NAME", "RULES_TABLE_NAME"]
    missing = [var for var in required_vars if var not in os.environ]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


# Call at module load
validate_environment()

# DynamoDB table names from environment variables
apps_table_name = os.environ["APPS_TABLE_NAME"]
servers_table_name = os.environ["SERVERS_TABLE_NAME"]
rules_table_name = os.environ["RULES_TABLE_NAME"]

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
apps_table = dynamodb.Table(apps_table_name)
servers_table = dynamodb.Table(servers_table_name)
rules_table = dynamodb.Table(rules_table_name)
client = boto3.client("dynamodb", config=Config(
             retries={
                 'mode': 'standard',
                 'total_max_attempts': 3
             }
         ))


class RuleEngine:
    def __init__(self, rules: List[Dict[str, Any]]):
        self.scoring_rules = [r for r in rules if r['sub_type'] == 'SCORING' and r['status'] == 'ENABLED']
        self.sorting_rules = [r for r in rules if r['sub_type'] == 'SORTING' and r['status'] == 'ENABLED']
        self.sorting_rules.sort(key=lambda x: x['sort_level'])
        self.pattern_cache = {}

    def apply_scoring_rule(self, rule: Dict[str, Any], asset: Dict[str, Any]) -> int:
        """Apply a scoring rule to an asset and return the complexity score."""
        attr_key = rule['attr_key']
        if attr_key not in asset:
            return 0
        
        attr_value = asset[attr_key]
        
        if 'scoring_criteria' in rule:
            for criteria in rule['scoring_criteria']:
                if is_exact_value_match_rule(criteria):
                    if attr_value == criteria['value']:
                        return criteria['complexity_score']
                elif is_pattern_based_match_rule(criteria):
                    pattern_to_check = criteria['pattern']
                    try:
                        if pattern_to_check not in self.pattern_cache:
                            self.pattern_cache[pattern_to_check] = re.compile(pattern_to_check, re.IGNORECASE)
                        if self.pattern_cache[pattern_to_check].search(str(attr_value)):
                            return criteria['complexity_score']
                    except re.error:
                        logger.warning(f"Invalid regex pattern: {pattern_to_check}")
                        continue
                elif is_range_based_match_rule(criteria):
                    try:
                        converted_value = float(attr_value)
                        lower_bound = criteria['lower_bound'] if 'lower_bound' in criteria else 0
                        upper_bound = criteria['upper_bound'] if 'upper_bound' in criteria else sys.maxsize
                        if lower_bound <= converted_value < upper_bound:
                            return criteria['complexity_score']
                    except (ValueError, TypeError):
                        logger.warning(f"Cannot convert {attr_value} to float for range comparison")
                        continue
        return 0


def calculate_asset_complexity(asset: Dict[str, Any], rule_engine: RuleEngine) -> int:
    """Calculate complexity score for a single asset."""
    total_score = 0
    
    for rule in rule_engine.scoring_rules:
        if rule['asset_type'] == asset.get('asset_type', ''):
            score = rule_engine.apply_scoring_rule(rule, asset)
            total_score += score
            
    return total_score


def calculate_app_complexity(application: Dict[str, Any], servers: List[Dict[str, Any]], rule_engine: RuleEngine) -> int:
    """Calculate complexity score for an application based on its servers."""
    total_score = 0
    
    # Calculate scores for all associated servers
    for server in servers:
        server['asset_type'] = 'server'  # Ensure asset_type is set for rule matching
        server_score = calculate_asset_complexity(server, rule_engine)
        total_score += server_score
    
    return total_score


def get_sort_key(application: Dict[str, Any], rule: Dict[str, Any]) -> Any:
    """Get the sort key for an application based on a sorting rule."""
    attr_key = rule['attr_key']
    if attr_key not in application:
        # Return a default value based on the expected type
        return 0 if attr_key == 'complexity_score' or attr_key == 'server_count' else ""
    
    attr_value = application[attr_key]
    
    if 'sort_by_value' in rule:
        # Handle custom sort order
        try:
            return rule['sort_by_value'].index(attr_value)
        except ValueError:
            return len(rule['sort_by_value'])
    
    return attr_value


def sort_applications(applications: List[Dict[str, Any]], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort applications based on sorting rules."""
    rule_engine = RuleEngine(rules)
    
    if not rule_engine.sorting_rules:
        return applications[:]
    
    def compound_sort_key(app):
        """Create a compound sort key for all sorting rules."""
        keys = []
        for rule in rule_engine.sorting_rules:
            key_value = get_sort_key(app, rule)
            # For DSC order, negate numeric values
            if rule['sort_order'] == 'DSC':
                if isinstance(key_value, (int, float)):
                    key_value = -key_value
                else:
                    # For non-numeric values in DESC order, we need to reverse the comparison
                    # We'll wrap it in a custom class that reverses comparison
                    key_value = ReverseOrder(key_value)
            keys.append(key_value)
        return keys
    
    # Sort with compound key
    sorted_apps = sorted(applications, key=compound_sort_key)
    
    return sorted_apps


class ReverseOrder:
    """Wrapper class to reverse the natural ordering of a value."""
    def __init__(self, value):
        self.value = value
    
    def _get_other_value(self, other):
        """Extract the value from other, whether it's a ReverseOrder object or raw value."""
        return other.value if isinstance(other, ReverseOrder) else other
    
    def __lt__(self, other):
        other_value = self._get_other_value(other)
        return self.value > other_value
    
    def __gt__(self, other):
        other_value = self._get_other_value(other)
        return self.value < other_value
    
    def __eq__(self, other):
        other_value = self._get_other_value(other)
        return self.value == other_value
    
    def __le__(self, other):
        other_value = self._get_other_value(other)
        return self.value >= other_value
    
    def __ge__(self, other):
        other_value = self._get_other_value(other)
        return self.value <= other_value
    
    def __ne__(self, other):
        other_value = self._get_other_value(other)
        return self.value != other_value


def process_applications(applications: List[Dict[str, Any]], servers_by_app: Dict[str, List[Dict[str, Any]]], rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process applications to calculate complexity scores and assign ranks."""
    # Step 1: Calculate complexity scores
    rule_engine = RuleEngine(rules)

    for app in applications:
        app_servers = servers_by_app.get(app['app_id'], [])
        app['server_count'] = len(app_servers)
        app['complexity_score'] = calculate_app_complexity(app, app_servers, rule_engine)
    
    # Step 2: Sort applications
    sorted_apps = sort_applications(applications, rules)
    
    # Step 3: Assign priority ranks
    result = []
    for rank, app in enumerate(sorted_apps, 1):
        result.append({
            'app_id': app['app_id'],
            'complexity_score': app['complexity_score'],
            'rank': rank
        })
    
    return result

def get_all_items_from_table(table: Any) -> List[Dict[str, Any]]:
    """Retrieve all items from a database using parallel scan."""
    import concurrent.futures
    
    def scan_segment(segment, total_segments):
        items = []
        scan_kwargs = {
            "Segment": segment,
            "TotalSegments": total_segments,
            "Limit": 1000,
        }
        try:
            done = False
            start_key = None
            while not done:
                if start_key:
                    scan_kwargs["ExclusiveStartKey"] = start_key
                response = table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))
                start_key = response.get("LastEvaluatedKey", None)
                done = start_key is None
        except dynamodb.ClientError as err:
            logger.error(f"Error scanning segment {segment}: {str(err)}")
            raise
        return items
    
    total_segments = 10
    all_items = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=total_segments) as executor:
        futures = [executor.submit(scan_segment, i, total_segments) for i in range(total_segments)]
        for future in concurrent.futures.as_completed(futures):
            all_items.extend(future.result())
    
    return all_items

def get_all_applications() -> List[Dict[str, Any]]:
    """Retrieve all applications from the database."""
    return get_all_items_from_table(apps_table)


def get_all_servers() -> List[Dict[str, Any]]:
    """Retrieve all servers from the database."""
    return get_all_items_from_table(servers_table)


def get_all_rules() -> List[Dict[str, Any]]:
    """Retrieve all prioritization rules from the database."""
    response = get_all_items_from_table(rules_table)
    rules = []
    
    for item in response:
        if item.get('rule_type') == 'PRIORITIZING':
            rules.append(item)
    
    return rules


def is_exact_value_match_rule(criteria: Dict[str, Any]) -> bool:
    """Return true if the provided rule is a value-based rule"""
    return 'value' in criteria

def is_pattern_based_match_rule(criteria: Dict[str, Any]) -> bool:
    """Return true if the provided rule is a pattern-based rule"""
    return 'pattern' in criteria

def is_range_based_match_rule(criteria: Dict[str, Any]) -> bool:
    """Return true if the provided rule is a range-based rule"""
    return 'lower_bound' in criteria or 'upper_bound' in criteria


def group_servers_by_app(servers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group servers by their associated application ID."""
    servers_by_app = {}
    
    for server in servers:
        # Also handle servers with multiple app_ids
        app_ids = server.get('app_ids', [])
        for aid in app_ids:
            if aid and aid not in servers_by_app:
                servers_by_app[aid] = []
            servers_by_app[aid].append(server)
    
    return servers_by_app


def update_app_ranks(app_ranks: List[Dict[str, Any]]) -> None:
    """Update application ranks in the database using transactions."""
    transact_items = []
    
    for app_rank in app_ranks:
        transact_items.append({
            'Update': {
                'TableName': apps_table_name,
                'Key': {'app_id': {'S': app_rank['app_id']}},
                'UpdateExpression': 'SET #c = :c, #r = :r',
                'ExpressionAttributeNames': {
                    '#c': 'complexity_score',
                    '#r': 'rank'
                },
                'ExpressionAttributeValues': {
                    ':c': {'N': str(app_rank['complexity_score'])},
                    ':r': {'N': str(app_rank['rank'])}
                }
            }
        })
    
    # Execute transaction
    results = commit_transactions(transact_items)

    # Check for any errors in the results
    errors = [r for r in results if r["status"] == "error"]
    if errors:
        error_message = f"Failed to update {len(errors)} transaction batches"
        logger.error(error_message)
        raise Exception(error_message)

def commit_transactions(transaction_items):
    """
    Commit transaction items to DynamoDB in batches of 100 items.
    Uses the AWS SDK's built-in retry configuration for handling transient errors.

    Args:
        transaction_items: List of transaction items to commit

    Returns:
        List of transaction results
    """
    results = []
    MAX_TRANSACTION_ITEMS = 100

    # Split transaction items into batches of 100
    for i in range(0, len(transaction_items), MAX_TRANSACTION_ITEMS):
        batch = transaction_items[i : i + MAX_TRANSACTION_ITEMS]
        batch_num = i // MAX_TRANSACTION_ITEMS + 1

        try:
            # Execute the transaction with built-in retry handling
            client.transact_write_items(TransactItems=batch)
            results.append(
                {
                    "status": "success",
                    "batch": batch_num,
                    "items_count": len(batch),
                }
            )
            logger.info(
                f"Successfully committed transaction batch {batch_num} with {len(batch)} items"
            )
        except ClientError as e:
            # Extract error code safely
            logger.error(
                f"Error committing transaction batch {batch_num}: {str(e)}"
            )
            results.append(
                {
                    "status": "error",
                    "batch": batch_num,
                    "error": str(e),
                    "items_count": len(batch),
                }
            )

    return results


def lambda_handler(event: Dict[str, Any], _) -> Dict[str, Any]:
    """Lambda handler for calculating application ranks."""
    import time
    start_time = time.time()
    
    log_event_received(event)
    logger.info("Starting application rank calculation")
    
    # Check authorization
    auth = MFAuth()
    auth_response = auth.get_user_resource_creation_policy(event, 'app')
    
    if auth_response['action'] != 'allow':
        logger.error(f"Authorization failed: {json.dumps(auth_response)}")
        return {
            'headers': {**default_http_headers},
            'statusCode': 401,
            'body': json.dumps({'errors': [auth_response]})
        }
    
    try:
        # Get all applications, servers, and rules
        data_fetch_start = time.time()
        applications = get_all_applications()
        servers = get_all_servers()
        rules = get_all_rules()
        data_fetch_time = time.time() - data_fetch_start
        logger.debug(f"Data fetch completed in {data_fetch_time:.2f} seconds")
        
        # Group servers by application
        grouping_start = time.time()
        servers_by_app = group_servers_by_app(servers)
        grouping_time = time.time() - grouping_start
        logger.debug(f"Server grouping completed in {grouping_time:.2f} seconds")
        
        # Process applications to calculate scores and ranks
        processing_start = time.time()
        app_ranks = process_applications(applications, servers_by_app, rules)
        processing_time = time.time() - processing_start
        logger.debug(f"Application processing completed in {processing_time:.2f} seconds")
        
        # Update application ranks in the database
        update_start = time.time()
        update_app_ranks(app_ranks)
        update_time = time.time() - update_start
        logger.debug(f"Database update completed in {update_time:.2f} seconds")
        
        total_time = time.time() - start_time
        logger.debug(f"Application rank calculation completed successfully in {total_time:.2f} seconds")
        
        return {
            'headers': {**default_http_headers},
            'statusCode': 200,
            'body': json.dumps(app_ranks)
        }
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Error calculating application ranks after {total_time:.2f} seconds: {str(e)}")
        return {
            'headers': {**default_http_headers},
            'statusCode': 500,
            'body': json.dumps({'errors': [f"Error calculating application ranks: {str(e)}"]})
        }