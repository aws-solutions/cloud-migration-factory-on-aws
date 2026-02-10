from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class EntitySchema:
    """Entity schema definition"""
    schema_name: str
    attributes: List[Dict[str, Any]]

@dataclass
class Entity:
    """An Entity to import"""
    entityName: str
    schema: EntitySchema
    data: Dict[str, Dict[str, Any]]

@dataclass
class ValidationIssues:
    """Validation issues from frontend"""
    deduplicationErrors: Optional[List[Dict[str, Any]]] = None
    deduplicationWarnings: Optional[List[Dict[str, Any]]] = None
    requiredAttributeErrors: Optional[List[Dict[str, Any]]] = None
    validationErrors: Optional[List[Dict[str, Any]]] = None
    validationWarnings: Optional[List[Dict[str, Any]]] = None
    crossReferenceErrors: Optional[List[Dict[str, Any]]] = None

@dataclass
class ImportRequestData:
    """Import request data containing entities to create and update"""
    entities_to_create: List[Entity]
    entities_to_update: List[Entity]
    issues: Optional[ValidationIssues] = None

def parse_import_request(json_data: Dict[str, Any]) -> ImportRequestData:
    """Parse JSON data into ImportRequestData object"""
    entities_to_create = _parse_entities(json_data.get('entities_to_create', []))
    entities_to_update = _parse_entities(json_data.get('entities_to_update', []))
    issues = _parse_validation_issues(json_data.get('issues'))
    
    return ImportRequestData(
        entities_to_create=entities_to_create,
        entities_to_update=entities_to_update,
        issues=issues
    )

def _parse_entities(entities_data: List[Dict[str, Any]]) -> List[Entity]:
    """Parse list of entity data into Entity objects."""
    entities = []
    for entity_data in entities_data:
        schema = EntitySchema(
            schema_name=entity_data['schema']['schema_name'],
            attributes=entity_data['schema']['attributes']
        )
        
        entity = Entity(
            entityName=entity_data['entityName'],
            schema=schema,
            data=entity_data['data']
        )
        entities.append(entity)
    
    return entities

def _parse_validation_issues(issues_data: Optional[Dict[str, Any]]) -> Optional[ValidationIssues]:
    """Parse validation issues data into ValidationIssues object."""
    if not issues_data:
        return None
    
    return ValidationIssues(
        deduplicationErrors=issues_data.get('deduplicationErrors', []),
        deduplicationWarnings=issues_data.get('deduplicationWarnings', []),
        requiredAttributeErrors=issues_data.get('requiredAttributeErrors', []),
        validationErrors=issues_data.get('validationErrors', []),
        validationWarnings=issues_data.get('validationWarnings', []),
        crossReferenceErrors=issues_data.get('crossReferenceErrors', [])
    )