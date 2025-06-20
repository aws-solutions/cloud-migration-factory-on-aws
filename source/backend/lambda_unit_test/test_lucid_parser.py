import unittest
from lucid_parser import LucidCSVParser
from models import ClientException
class TestLucidIOParser(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.parser = LucidCSVParser()
    
    def valid_dtr_diagram(self):
        return '''Id,Name,Shape Library,Page ID,Contained By,Group,Line Source,Line Destination,Source Arrow,Destination Arrow,Status,Text Area 1,Comments,automationid,start,tasktype
1,Document,,,,,,,,,Draft,Lusid-DTR,,,,
2,Page,,,,,,,,,,LTR1,,,,
3,Connector,Flowchart Shapes/Containers,2,,,,,,,,Rehost Servers,,,Rehost Servers,
4,Process,Flowchart Shapes/Containers,2,,,,,,,,Manual Task1,,,,Manual
5,Process,Flowchart Shapes/Containers,2,,,,,,,,Automated 1,,0-Check MGN Prerequisites,,Automated
6,Process,Flowchart Shapes/Containers,2,,,,,,,,Automated 2,,1-Copy Post Launch Scripts,,Automated
7,Line,,2,,,3,4,None,Arrow,,,,,,
8,Line,,2,,,4,5,None,Arrow,,,,,,
9,Line,,2,,,4,6,None,Arrow,,,,,,
'''

    def test_valid_pipeline(self):
        """Test parsing pipeline with correct shapes"""
        templates = self.parser.parse(self.valid_dtr_diagram())
        
        self.assertEqual(len(templates), 1)
        template = templates[0]
        
        # Verify template metadata
        self.assertEqual(template["pipeline_template_name"], "LTR1")
        self.assertEqual(template["pipeline_template_description"], "Rehost Servers")
        
        # Verify tasks
        tasks = template["pipeline_template_tasks"]
        self.assertEqual(len(tasks), 3)
        
        # Verify automated task
        automated_task = next(t for t in tasks if t["pipeline_template_task_name"] == "Automated 1")
        self.assertEqual(automated_task["task_name"], "0-Check MGN Prerequisites")
        self.assertEqual(len(automated_task["task_successors"]), 0)
        
        # Verify manual task
        manual_task = next(t for t in tasks if t["pipeline_template_task_name"] == "Manual Task1")
        self.assertEqual(manual_task["task_name"], "Manual")
        self.assertEqual(len(manual_task["task_successors"]), 2)

    def test_diagram_without_links(self):
        """Test handling of diagram without any links"""
        diagram_without_links = '''Id,Name,Shape Library,Page ID,Contained By,Group,Status,Text Area 1,Comments
    1,Document,,,,,Draft,Blank diagram,
    2,Page,,,,,,Page 1,'''
        
        with self.assertRaises(ClientException) as context:
            self.parser.parse(diagram_without_links)
        
        # Validate the exception details
        self.assertEqual(context.exception.error, "ValidationError")
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Required columns 'Line Source' or 'Line Destination' are missing in CSV file", context.exception.message)

    def test_diagram_without_start_node(self):
        """Test handling of diagram without any links"""
        diagram_without_links = '''Id,Name,Shape Library,Page ID,Contained By,Group,Line Source,Line Destination,Source Arrow,Destination Arrow,Status,Text Area 1,Comments,automationid,tasktype
1,Document,,,,,,,,,Draft,Lusid-DTR,,,
7,Line,,2,,,3,4,None,Arrow,,,,,
'''
        
        with self.assertRaises(ClientException) as context:
            self.parser.parse(diagram_without_links)
        
        # Validate the exception details
        self.assertEqual(context.exception.error, "ValidationError")
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Required columns 'Id' or 'start' are missing in CSV file", context.exception.message)

    def test_diagram_without_valid_node(self):
        """Test handling of diagram without any links"""
        diagram_without_links = '''Name,Shape Library,Page ID,Contained By,Group,Line Source,Line Destination,Source Arrow,Destination Arrow,Status,Text Area 1,Comments,automationid,tasktype
Document,,,,,,,,,Draft,Lusid-DTR,,,
Line,,2,,,3,4,None,Arrow,,,,,
'''
        
        with self.assertRaises(ClientException) as context:
            self.parser.parse(diagram_without_links)
        
        # Validate the exception details
        self.assertEqual(context.exception.error, "ValidationError")
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Required columns 'Id' or 'Text Area 1' are missing in CSV file", context.exception.message)


if __name__ == '__main__':
    unittest.main()
