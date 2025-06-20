import re
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from defusedxml.ElementTree import fromstring
import uuid
from typing import List, Dict, Optional, Any
from models import ClientException
from cmf_logger import logger
from diagram_parser import DiagramParser

class DrawIOParser(DiagramParser):
    
    def _parse_xml(self, file_content: str) -> ET.Element:
        return fromstring(file_content)

    def _sanitize_text(self, text: str) -> str:
        
        """
        Sanitizes text by removing HTML tags and normalizing whitespace.
        
        This method handles text that may contain HTML markup by:
        1. Parsing HTML content using a custom HTMLParser
        2. Extracting only the text content from HTML elements
        3. Removing extra whitespace and normalizing spacing
        4. If no HTML is detected, returns the original text with stripped whitespace
        
        Args:
            text (str): The input text that may contain HTML markup
                Example: "<p>Hello  <br/>  World</p>"
        
        Returns:
            str: Cleaned text with HTML removed and normalized spacing
                Example: "Hello World"
        """
        class SanitizerHTMLParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.texts: List[str] = []

            def handle_data(self, data: str) -> None:
                self.texts.append(data.strip())

            def get_data(self) -> str:
                return " ".join(self.texts).strip()

        def extract_text_from_html(html_content: str) -> str:
            parser = SanitizerHTMLParser()
            parser.feed(html_content)
            return parser.get_data()

        contains_html = bool(re.search(r"<[^>]+>", text))
        return extract_text_from_html(text) if contains_html else text

    def _find_start_node(self, root: ET.Element) -> Optional[ET.Element]:
        """
        Finds the start node in a DrawIO diagram XML tree.
        
        Searches through all elements in the XML tree to find the first node
        that represents the start of the pipeline. A start node is identified
        by having either a "UserObject" or "object" tag and containing a "Start"
        attribute.
        
        Args:
            root (ET.Element): The root element of the DrawIO XML tree to search
        
        Returns:
            Optional[ET.Element]: The start node element if found, None otherwise
        
        Example:
            >>> root = ET.fromstring('<diagram><object Start="Rehost"/></diagram>')
        """
        for elem in root.iter():
            if elem.tag in ["UserObject", "object"] and "Start" in elem.attrib:
                return elem
        return None

    def _get_case_insensitive_attr(self, elem: ET.Element, attr_name: str, default: str = "") -> str:
        """
        Retrieves an attribute value from an XML element using case-insensitive matching.
        
        Searches for an attribute in the element's attributes where the attribute name
        matches the requested name regardless of case. This is useful for DrawIO XML
        where attribute names might have inconsistent casing.
        
        Args:
            elem (ET.Element): The XML element to search for the attribute
            attr_name (str): The name of the attribute to find (case-insensitive)
            default (str, optional): The default value to return if attribute is not found.
                Defaults to empty string.
        
        Returns:
            str: The value of the matched attribute or the default value if not found
        
        Example:
            >>> elem = ET.fromstring('<node TaskType="Manual" tasktype="Auto"/>')
        """
        actual_key = next(
            (key for key in elem.attrib.keys() if key.lower() == attr_name.lower()),
            None
        )
        return elem.attrib.get(actual_key, default) if actual_key else default

    def _build_tasks(self, root: ET.Element, pipeline_template_id: str) -> List[Dict[str, Any]]:
        """
        Builds a list of pipeline tasks from the DrawIO XML diagram.
        
        This method processes the XML tree to:
        1. Extract tasks from diagram nodes
        2. Process connections between nodes
        3. Update task dependencies based on connections
        
        Args:
            root (ET.Element): The root element of the DrawIO XML tree
            pipeline_template_id (str): Unique identifier for the pipeline template
        
        Returns:
            List[Dict[str, Any]]: List of task dictionaries, each containing:
                - pipeline_template_task_name: Name of the task
                - task_successors: List of successor task IDs
                - task_version: Version of the task
                - pipeline_template_task_id: Unique task identifier
                - pipeline_template_id: Parent template identifier
                - task_name: Automation ID for the task
        """
        nodes: Dict[str, Dict[str, Any]] = {}
        connections: Dict[str, Dict[str, List[str]]] = {}
        pipeline_tasks: List[Dict[str, Any]] = []

        # Process nodes
        for elem in root.iter():
            if elem.tag in ["UserObject", "object"]:
                task = self._process_node(elem, pipeline_template_id)
                if task:
                    node_id = elem.attrib.get("id", "")
                    nodes[node_id] = task
                    pipeline_tasks.append(task)
            # Process connections
            elif elem.tag == "mxCell" and "edge" in elem.attrib:
                self._process_connection(elem, connections)

        # Update task successors
        self._update_task_successors(nodes, connections)

        return pipeline_tasks

    def _process_node(self, elem: ET.Element, pipeline_template_id: str) -> Optional[Dict[str, Any]]:
        """
        Processes a single diagram node into a task definition.
        
        Extracts task information from a DrawIO node element, including:
        - Task name from the node label
        - Task type (manual or automated)
        - Automation ID for automated tasks
        
        Args:
            elem (ET.Element): The XML element representing a diagram node
            pipeline_template_id (str): ID of the parent pipeline template
        
        Returns:
            Optional[Dict[str, Any]]: Task dictionary if node represents a valid task,
                None otherwise. Task dictionary includes:
                - pipeline_template_task_name: Name from node label
                - task_successors: Empty list (populated later)
                - task_version: Always "1"
                - pipeline_template_task_id: Node ID
                - pipeline_template_id: Parent template ID
                - task_name: Automation ID or "Manual"
        """
        id_attr = elem.attrib.get("id")
        if not id_attr:
            return None

        task_name = self._sanitize_text(
            elem.attrib.get("label", "").replace("<br>", " ").strip()
        )
        
        task_type = self._sanitize_text(
            self._get_case_insensitive_attr(elem, "TaskType").replace("<br>", " ").strip().lower()
        )
        
        automation_id = self._get_case_insensitive_attr(elem, "AutomationID", "Manual")

        if task_type in ["manual", "automated"]:
            return self.create_task(
                task_name=task_name,
                task_id=id_attr,
                pipeline_template_id=pipeline_template_id,
                automation_id=automation_id
            )
        return None

    def _process_connection(self, elem: ET.Element, connections: Dict[str, Dict[str, List[str]]]) -> None:
        """
        Processes connection elements to build task dependencies.
        Extracts source and target information from connection elements and
        builds a mapping of task dependencies.
        """
        if "source" in elem.attrib and "target" in elem.attrib:
            source_id = elem.attrib["source"]
            target_id = elem.attrib["target"]
            
            for node_id in [source_id, target_id]:
                if node_id not in connections:
                    connections[node_id] = {"successors": []}
            
            connections[source_id]["successors"].append(target_id)

    def _update_task_successors(
        self,
        nodes: Dict[str, Dict[str, Any]], 
        connections: Dict[str, Dict[str, List[str]]]
    ) -> None:
        """Update task successors based on connections."""
        for node_id, node_details in nodes.items():
            if node_id in connections:
                node_details["task_successors"] = connections[node_id]["successors"]

    def parse(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Parse pipeline templates from DrawIO XML content.
        
        Args:
            xml_content: Raw XML content from the DrawIO file
                
        Returns:
            List[Dict[str, Any]]: List of parsed cmf-json templates
            
        Raises:
            Exception: If template processing fails
        """
        try:
            root = self._parse_xml(xml_content)
            templates = []
            
            for diagram in root.findall('.//diagram'):
                
                start_node = self._find_start_node(diagram)
                if not start_node:
                    diagram_name = diagram.attrib.get('name', 'Unnamed')
                    raise ClientException(
                        error="ValidationError",
                        message=f"Missing start node in diagram '{diagram_name}'. Each diagram must have exactly one start node.",
                        status_code=400
                    )

                template_id = str(uuid.uuid4())
                tasks = self._build_tasks(diagram, template_id)
                
                if tasks:
                    template = self.create_template(
                        template_id=template_id,
                        description=self._get_case_insensitive_attr(start_node, "Start", ""),
                        name=diagram.attrib.get("name", ""),
                        tasks=tasks
                    )
                    templates.append(template)
            return templates
        except ET.ParseError as e:
            logger.error(f"Error: {e}")
            raise ClientException(
                error="XMLParsingError",
                message=f"Invalid XML format: {str(e)}",
                status_code=400
            )
        except ClientException as e:
            logger.error(f"Validation Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error: {e}")
            raise ClientException(
                error="InternalError",
                message=f"Unexpected error while parsing templates",
                status_code=500
            )

