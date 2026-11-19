from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from request import ImportRequestData, ValidationIssues

@dataclass
class FailureDetails:
    """Details for a failed entity operation"""
    data: Dict[str, Any]
    error_message: str

@dataclass
class ProcessingResults:
    upload_id: str
    original_file: str
    uploaded_by: Optional[str]
    create_failures: Dict[str, Dict[str, FailureDetails]] = field(default_factory=dict)  # {entity_type: {entity_name: FailureDetails}}
    update_failures: Dict[str, Dict[str, FailureDetails]] = field(default_factory=dict)  # {entity_type: {entity_name: FailureDetails}}
    created_items: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # For tracking successful creates
    updated_items: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # For tracking successful updates
    validation_issues: Optional[ValidationIssues] = None  # Validation issues from frontend
    
    def get_successful_creates_count(self) -> int:
        """Calculate total successful creates"""
        return sum(len(items) for items in self.created_items.values())
    
    def get_successful_updates_count(self) -> int:
        """Calculate total successful updates"""
        return sum(len(items) for items in self.updated_items.values())
    
    def get_failed_creates_count(self) -> int:
        """Calculate total failed creates from failure dictionaries"""
        return sum(len(failures) for failures in self.create_failures.values())
    
    def get_failed_updates_count(self) -> int:
        """Calculate total failed updates from failure dictionaries"""
        return sum(len(failures) for failures in self.update_failures.values())
    
    def has_failures(self) -> bool:
        """Check if there are any failures"""
        return len(self.create_failures) > 0 or len(self.update_failures) > 0

def create_processing_results(upload_id: str, original_file: str, uploaded_by: Optional[str], 
                            import_data: ImportRequestData) -> ProcessingResults:
    """Create ProcessingResults from import data"""
    
    return ProcessingResults(
        upload_id=upload_id,
        original_file=original_file,
        uploaded_by=uploaded_by,
        validation_issues=import_data.issues
    )