"""
Wave relationship utility functions for the Migration Factory solution.

This module contains helper functions for managing wave relationships when moving apps
between move groups, eliminating code duplication and providing centralized error handling.

Author: AWS Professional Services
"""

import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger()


def update_app_wave_relationships(
    app_id: str,
    app: Dict[str, Any],
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    destination_type: Optional[str] = None,
    destination_id: Optional[str] = None,
    updates: Optional[Dict[str, Any]] = None,
    get_entity_func=None,
    update_relationship_func=None
) -> Dict[str, Any]:
    """Update wave relationships when moving apps between move groups

    Args:
        app_id: ID of the app being updated
        app: App entity data
        source_type: Type of source entity (if removing/moving)
        source_id: ID of source entity (if removing/moving)
        destination_type: Type of destination entity (if moving/copying)
        destination_id: ID of destination entity (if moving/copying)
        updates: Dictionary of updates to apply to the app
        get_entity_func: Function to retrieve entity data
        update_relationship_func: Function to update relationships

    Returns:
        Updated updates dictionary with wave_ids if modified
    """
    updates = updates or {}
    current_wave_ids = list(app.get("wave_ids", []))

    try:
        # Handle source/removal if applicable
        if source_type == "move_group" and source_id and get_entity_func:
            source_entity = get_entity_func(source_type, source_id)
            if source_entity and "wave_id" in source_entity and source_entity["wave_id"] in current_wave_ids:
                current_wave_ids.remove(source_entity["wave_id"])
                if update_relationship_func:
                    update_relationship_func("wave", source_entity["wave_id"], "app", app_id, "remove")

        # Handle destination if applicable
        if destination_type == "move_group" and destination_id and get_entity_func:
            dest_entity = get_entity_func(destination_type, destination_id)
            if dest_entity and "wave_id" in dest_entity and dest_entity["wave_id"] not in current_wave_ids:
                current_wave_ids.append(dest_entity["wave_id"])
                if update_relationship_func:
                    update_relationship_func("wave", dest_entity["wave_id"], "app", app_id, "add")

        # Only update if wave_ids changed
        if current_wave_ids != app.get("wave_ids", []):
            updates["wave_ids"] = current_wave_ids

        return updates
    except Exception as e:
        logger.error(f"Error updating wave relationships for app {app_id}: {str(e)}")
        return updates