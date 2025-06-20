from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DiagramParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse diagram content and return list of templates.
        
        Args:
            content: The raw content of the diagram file
            
        Returns:
            List of parsed pipeline templates
            
        Raises:
            ClientException: If parsing fails
        """
        pass

    def create_template(self, template_id: str, description: str, name: str, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates a standardized template structure used by all parsers.
        
        Args:
            template_id: Unique identifier for the template
            description: Template description
            name: Template name
            tasks: List of template tasks
            
        Returns:
            Dictionary containing the standardized template structure
        """
        return {
            "pipeline_template_id": template_id,
            "pipeline_template_description": description,
            "pipeline_template_name": name,
            "pipeline_template_tasks": tasks
        }
    
    def create_task(self, 
                    task_name: str, 
                    task_id: str, 
                    pipeline_template_id: str,
                    automation_id: str,
                    successors: List[str] = [],
                    task_version: str = "1") -> Dict[str, Any]:
        """
        Creates a standardized task structure used by all parsers.
        
        Args:
            task_name: Name of the task
            task_id: Unique identifier for the task
            pipeline_template_id: ID of the parent template
            automation_id: ID of the automation
            
        Returns:
            Dictionary containing the standardized task structure
        """
        return {
            "pipeline_template_task_name": task_name,
            "task_successors": successors,
            "task_version": task_version,
            "pipeline_template_task_id": task_id,
            "pipeline_template_id": pipeline_template_id,
            "task_name": automation_id
        }