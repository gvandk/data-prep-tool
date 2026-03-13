import unittest
from data_prep_tool.core.dependency_graph import DependencyGraph
from data_prep_tool.core.script_generator import ScriptGenerator

class TestScriptGenerator(unittest.TestCase):
    def setUp(self):
        self.graph = DependencyGraph()
        self.generator = ScriptGenerator(self.graph)

    def test_simple_load(self):
        self.graph.register_load("u1", "Age", "data.csv")
        script = self.generator.generate_script()
        self.assertIn("pd.read_csv('data.csv')", script)

    def test_rename_script(self):
        # Setup: Loaded as 'Age', Renamed to 'Years'
        self.graph.register_load("u1", "Age")
        self.graph.register_rename("u1", "Years")
        
        script = self.generator.generate_script()
        # Verify specific pandas syntax
        self.assertIn("df.rename(columns={'Age': 'Years'}, inplace=True)", script)

    def test_cell_edit_script(self):
        self.graph.register_load("u1", "Age")
        self.graph.register_cell_edit("u1", 10, 500)
        
        script = self.generator.generate_script()
        # Check for .at[] syntax
        self.assertIn("df.at[10, 'Age'] = 500", script)