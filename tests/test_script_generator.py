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
        self.assertIn("pd.read_csv(input_path)", script)

    def test_rename_script(self):

        self.graph.register_load("u1", "Age")
        self.graph.register_rename("u1", "Years")

        script = self.generator.generate_script()

        self.assertIn("df.rename(columns={'Age': 'Years'}, inplace=True)", script)

    def test_cell_edit_script(self):
        self.graph.register_load("u1", "Age")
        self.graph.register_cell_edit("u1", 10, 500)

        script = self.generator.generate_script()

        self.assertIn("df.at[10, 'Age'] = 500", script)

    def test_cell_edit_with_missing_target_node_is_ignored(self):
        self.graph.register_cell_edit("missing_uuid", 1, 42)

        script = self.generator.generate_script()

        self.assertNotIn("df.at[1", script)

    def test_final_columns_skip_empty_names(self):
        self.graph.register_load("u1", "A")
        self.graph.nodes["u1"].current_name = ""

        script = self.generator.generate_script()

        self.assertIn("df = df[[]]", script)