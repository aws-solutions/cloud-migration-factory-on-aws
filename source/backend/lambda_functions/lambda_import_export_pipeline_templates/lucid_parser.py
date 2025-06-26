import io
import csv
import json
import os
import uuid
from models import ClientException
from cmf_logger import logger
from diagram_parser import DiagramParser

class LucidCSVParser(DiagramParser):
    
    # Constants for CSV column names
    TEXT_AREA_1_COLUMN = "Text Area 1"
    
    def _get_nodes(self, csv_data):
        """
        Extract valid nodes from CSV data.
        
        A valid node must have both an 'Id' and 'Text Area 1' value. Creates a dictionary
        where the key is the node Id and the value is the entire row data.
        
        Args:
            csv_data (List[Dict[str, str]]): List of dictionaries containing CSV row data
            
        Returns:
            Dict[str, Dict[str, str]]: Dictionary of valid nodes with their IDs as keys
            
        Raises:
            ClientException: If no valid nodes are found or required columns are missing
                - error: "ValidationError"
                - status_code: 400
                - message: Descriptive error message about missing data
        """
        try:
            nodes = {row["Id"]: row for row in csv_data if row["Id"] and row[self.TEXT_AREA_1_COLUMN]}
            if not nodes:
                raise ClientException(error="ValidationError",
                message=f"No valid nodes found. Each node must have an 'Id' and '{self.TEXT_AREA_1_COLUMN}'",
                status_code=400)
            return nodes
        except KeyError:
            raise ClientException( error="ValidationError",
                message=f"Required columns 'Id' or '{self.TEXT_AREA_1_COLUMN}' are missing in CSV file",
                status_code=400)
        
    def _get_links(self, csv_data):
        
        """
        Extract valid links from CSV data.
        
        A valid link must have both 'Line Source' and 'Line Destination' values. Returns
        a list of rows that represent connections between nodes.
        
        Args:
            csv_data (List[Dict[str, str]]): List of dictionaries containing CSV row data
            
        Returns:
            List[Dict[str, str]]: List of valid link rows
            
        Raises:
            ClientException: If no valid links are found or required columns are missing
                - error: "ValidationError"
                - status_code: 400
                - message: Descriptive error message about missing data
        """
        try:
            links = [
                row for row in csv_data if row["Line Source"] and row["Line Destination"]
            ]
            if not links:
                raise ClientException(error="ValidationError",
                message="No valid links found. Each link must have 'Line Source' and 'Line Destination'",
                status_code=400)
            return links
        except KeyError:
            raise ClientException(error="ValidationError",
                message="Required columns 'Line Source' or 'Line Destination' are missing in CSV file",
                status_code=400)
    
    def _get_start_nodes(self, csv_data):
        
        """
        Extract valid start nodes from CSV data.
        
        A valid start node must have both an 'Id' and a non-empty 'start' value. Creates
        a dictionary where the key is the node Id and the value is the entire row data.
        
        Args:
            csv_data (List[Dict[str, str]]): List of dictionaries containing CSV row data
            
        Returns:
            Dict[str, Dict[str, str]]: Dictionary of valid start nodes with their IDs as keys
            
        Raises:
            ClientException: If no valid start nodes are found or required columns are missing
                - error: "ValidationError"
                - status_code: 400
                - message: Descriptive error message about missing data
        """
        try:
            start_nodes = {row["Id"]: row for row in csv_data if row["Id"] and row["start"].strip()}
            if not start_nodes:
                raise ClientException(error="ValidationError",
                message="No start nodes found. At least one node must have a non-empty 'start' value",
                status_code=400)
            return start_nodes
        except KeyError:
            raise ClientException(error="ValidationError",
                message="Required columns 'Id' or 'start' are missing in CSV file",
                status_code=400)
        
    def _parse_csv(self, file_content):
        csv_file = io.StringIO(file_content)
        dict_reader = csv.DictReader(csv_file)
        return [row for row in dict_reader]
    
    def _traverse_and_build(self,node_id, nodes, links, tasks, template_id):
        """
        Recursively traverse the nodes and links to build a list of tasks.

        Args:
            node_id (int): The ID of the current node.
            nodes (dict): A dictionary of nodes, where the keys are node IDs and the values are node data.
            links (list): A list of links between nodes.
            tasks (list): The list of tasks to be populated.
        """
        visited = set()
        node_key = str(node_id)
        if node_key in nodes:
            node = nodes[node_key]
            
            task_name = node.get(self.TEXT_AREA_1_COLUMN) or None
            automation_id = node.get("automationid") or "Manual"
            
            successors = self._find_relations(node_key, links)

            task =  self.create_task(
                task_name=task_name,
                task_id=node_key,
                pipeline_template_id=template_id,
                automation_id=automation_id,
                successors=successors
            )
            
            visited.add(node_key)
            # Recursively process successors
            for successor_id in successors:
                if successor_id not in visited:
                    self._traverse_and_build(
                        successor_id, nodes, links, tasks, template_id
                    )
            tasks.append(task)

    def _find_relations(self, node_key, links):
        """
        Find the successor nodes for a given node.

        Args:
            node_key (str): The key of the node for which to find relations.
            links (list): A list of links between nodes.

        Returns:
            list of successors
        """
        successors = [
            link["Line Destination"]
            for link in links
            if link["Line Source"] == node_key
        ]
        return successors
    
    def parse(self, file_content):
        """
        Parse Lucid CSV file content and create pipeline templates.
        
        Args:
            file_content: CSV file content
            
        Returns:
            list: List of pipeline templates
            
        Raises:
            ClientError: If required data is missing or invalid
        """
        try:
            csv_data = self._parse_csv(file_content)
            nodes = self._get_nodes(csv_data)
            links = self._get_links(csv_data)
            start_nodes = self._get_start_nodes(csv_data)
            
            templates = []
            for node_id, node_data in start_nodes.items():
                page_id = node_data.get("Page ID")
                page_node = nodes[page_id]
                template_name = page_node.get(self.TEXT_AREA_1_COLUMN)
                description = node_data.get(self.TEXT_AREA_1_COLUMN)
                tasks = []
                template_id = str(uuid.uuid4())
                
                starting_nodes = self._find_relations(node_id, links)
                
                for node_key in starting_nodes:
                    self._traverse_and_build(
                        node_key, nodes, links, tasks, template_id
                    )
                template = self.create_template(template_id=template_id, name=template_name, description=description, tasks=tasks)
                templates.append(template)
            return templates
            
        except ClientException as e:
            logger.error(f"Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error: {e}")
            raise ClientException(error="InternalError",
                message=f"Error parsing CSV file: {str(e)}",
                status_code=500)
        
    
    
