import unittest
from drawio_parser import DrawIOParser
class TestDrawIOParser(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.parser = DrawIOParser()
    
    def valid_dtr_diagram(self):
        return '''
        <mxfile host="drawio.corp.com" modified="2025-01-15T21:24:45.274Z" agent="Mozilla/5.0" version="21.7.4" type="device">
            <diagram name="DTR-1" id="XXXXXXXXXXXXXXXXXXXX">
                <mxGraphModel>
                    <root>
                        <mxCell id="0"/>
                        <mxCell id="1" parent="0"/>
                        <object label="Start" Start="Rehost file test" id="start1">
                            <mxCell style="ellipse;whiteSpace=wrap;html=1;aspect=fixed;" vertex="1">
                                <mxGeometry x="360" y="140" width="80" height="80"/>
                            </mxCell>
                        </object>
                        <object label="0-Check MGN Prerequisites" AutomationID="0-Check MGN Prerequisites" TaskType="Automated" id="task1">
                            <mxCell style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;" vertex="1">
                                <mxGeometry x="340" y="290" width="120" height="60"/>
                            </mxCell>
                        </object>
                        <object label="Manual Approval" TaskType="Manual" id="task2">
                            <mxCell style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1">
                                <mxGeometry x="340" y="440" width="120" height="50"/>
                            </mxCell>
                        </object>
                        <mxCell id="edge1" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="start1" target="task1"/>
                        <mxCell id="edge2" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="task1" target="task2"/>
                    </root>
                </mxGraphModel>
            </diagram>
        </mxfile>
        '''

    def test_valid_pipeline(self):
        """Test parsing pipeline with correct shapes"""
        templates = self.parser.parse(self.valid_dtr_diagram())
        
        self.assertEqual(len(templates), 1)
        template = templates[0]
        
        # Verify template metadata
        self.assertEqual(template["pipeline_template_name"], "DTR-1")
        self.assertEqual(template["pipeline_template_description"], "Rehost file test")
        
        # Verify tasks
        tasks = template["pipeline_template_tasks"]
        self.assertEqual(len(tasks), 2)
        
        # Verify automated task
        automated_task = next(t for t in tasks if t["pipeline_template_task_name"] == "0-Check MGN Prerequisites")
        self.assertEqual(automated_task["task_name"], "0-Check MGN Prerequisites")
        self.assertEqual(len(automated_task["task_successors"]), 1)
        
        # Verify manual task
        manual_task = next(t for t in tasks if t["pipeline_template_task_name"] == "Manual Approval")
        self.assertEqual(manual_task["task_name"], "Manual")
        self.assertEqual(len(manual_task["task_successors"]), 0)

    def test_empty_diagram(self):
        """Test handling of empty diagram"""
        empty_diagram = '''
        <mxfile host="drawio.corp.com">
        </mxfile>
        '''
        templates = self.parser.parse(empty_diagram)
        self.assertEqual(len(templates), 0)

    def test_missing_start_node_raises_exception(self):
        # GIVEN: XML content with a diagram that has no start node
        from models import ClientException
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
            <mxfile host="app.diagrams.net">
                <diagram name="Pipeline Without Start">
                    <mxGraphModel>
                        <root>
                            <mxCell id="0"/>
                            <mxCell id="1" parent="0"/>
                            <UserObject id="2" label="Task 1">
                                <mxCell vertex="1" parent="1"/>
                            </UserObject>
                        </root>
                    </mxGraphModel>
                </diagram>
            </mxfile>'''

        # WHEN/THEN: Parsing should raise ClientException
        with self.assertRaises(ClientException) as context:
            self.parser.parse(xml_content)
            # Validate the exception details
            self.assertEqual(context.exception.error, "ValidationError")
            self.assertEqual(context.exception.status_code, 400)
            self.assertIn("Missing start node in diagram 'Pipeline Without Start'", context.exception.message)
            self.assertIn("Each diagram must have exactly one start node", context.exception.message)


    def test_multiple_diagrams(self):
        """Test parsing multiple diagrams from a single file"""
        multiple_diagrams = '''
        <mxfile host="drawio.corp.com" modified="2025-01-15T21:24:45.274Z" agent="Mozilla/5.0" version="21.7.4" type="device">
            <diagram name="DTR-1" id="diagram1">
                <mxGraphModel>
                    <root>
                        <mxCell id="0"/>
                        <mxCell id="1" parent="0"/>
                        <object label="Start" Start="First Pipeline" id="start1">
                            <mxCell style="ellipse;whiteSpace=wrap;html=1;aspect=fixed;" vertex="1">
                                <mxGeometry x="360" y="140" width="80" height="80"/>
                            </mxCell>
                        </object>
                        <object label="Check Prerequisites" AutomationID="Check Prerequisites" TaskType="Automated" id="task1">
                            <mxCell style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;" vertex="1">
                                <mxGeometry x="340" y="290" width="120" height="60"/>
                            </mxCell>
                        </object>
                        <mxCell id="edge1" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="start1" target="task1"/>
                    </root>
                </mxGraphModel>
            </diagram>
            <diagram name="DTR-2" id="diagram2">
                <mxGraphModel>
                    <root>
                        <mxCell id="0"/>
                        <mxCell id="1" parent="0"/>
                        <object label="Start" Start="Second Pipeline" id="start2">
                            <mxCell style="ellipse;whiteSpace=wrap;html=1;aspect=fixed;" vertex="1">
                                <mxGeometry x="360" y="140" width="80" height="80"/>
                            </mxCell>
                        </object>
                        <object label="Manual Task" TaskType="Manual" id="task2">
                            <mxCell style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1">
                                <mxGeometry x="340" y="290" width="120" height="60"/>
                            </mxCell>
                        </object>
                        <object label="Automated Task" AutomationID="AUTO_1" TaskType="Automated" id="task3">
                            <mxCell style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;" vertex="1">
                                <mxGeometry x="340" y="420" width="120" height="60"/>
                            </mxCell>
                        </object>
                        <mxCell id="edge2" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="start2" target="task2"/>
                        <mxCell id="edge3" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="task2" target="task3"/>
                    </root>
                </mxGraphModel>
            </diagram>
        </mxfile>
        '''
        
        templates = self.parser.parse(multiple_diagrams)
        
        # Verify we got both templates
        self.assertEqual(len(templates), 2)
        
        # Verify first template (DTR-1)
        template1 = next(t for t in templates if t["pipeline_template_name"] == "DTR-1")
        self.assertEqual(template1["pipeline_template_description"], "First Pipeline")
        tasks1 = template1["pipeline_template_tasks"]
        self.assertEqual(len(tasks1), 1)
        self.assertEqual(tasks1[0]["pipeline_template_task_name"], "Check Prerequisites")
        self.assertEqual(tasks1[0]["task_name"], "Check Prerequisites")
        
        # Verify second template (DTR-2)
        template2 = next(t for t in templates if t["pipeline_template_name"] == "DTR-2")
        self.assertEqual(template2["pipeline_template_description"], "Second Pipeline")
        tasks2 = template2["pipeline_template_tasks"]
        self.assertEqual(len(tasks2), 2)
        
        # Verify manual task
        manual_task = next(t for t in tasks2 if t["pipeline_template_task_name"] == "Manual Task")
        self.assertEqual(manual_task["task_name"], "Manual")
        self.assertEqual(len(manual_task["task_successors"]), 1)
        
        # Verify automated task
        auto_task = next(t for t in tasks2 if t["pipeline_template_task_name"] == "Automated Task")
        self.assertEqual(auto_task["task_name"], "AUTO_1")
        self.assertEqual(len(auto_task["task_successors"]), 0)


if __name__ == '__main__':
    unittest.main()
