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

    def test_rename_on_deleted_column_is_ignored(self):
        self.graph.register_load("u1", "Age")
        self.graph.register_rename("u1", "Years")
        self.graph.mark_deleted("u1")

        script = self.generator.generate_script()

        self.assertNotIn("df.rename(columns={'Age': 'Years'}, inplace=True)", script)

    def test_cell_edit_script(self):
        self.graph.register_load("u1", "Age")
        self.graph.register_cell_edit("u1", 10, 500)

        script = self.generator.generate_script()

        self.assertIn("df.at[10, 'Age'] = 500", script)

    def test_cell_edit_with_missing_target_node_is_ignored(self):
        self.graph.register_cell_edit("missing_uuid", 1, 42)

        script = self.generator.generate_script()

        self.assertNotIn("df.at[1", script)

    def test_cell_edit_on_deleted_column_is_ignored(self):
        self.graph.register_load("u1", "Age")
        self.graph.register_cell_edit("u1", 10, 500)
        self.graph.mark_deleted("u1")

        script = self.generator.generate_script()

        self.assertNotIn("df.at[10, 'Age'] = 500", script)

    def test_cell_edit_before_one_hot_is_kept(self):
        self.graph.register_load("u1", "Age")
        self.graph.register_cell_edit("u1", 10, 500)
        self.graph.register_one_hot("u1", ["c1"], ["Age_500"], prefix="Age")
        self.graph.mark_deleted("u1")

        script = self.generator.generate_script()

        self.assertIn("df.at[10, 'Age'] = 500", script)

    def test_non_consecutive_cell_edits_collapse_after_pruning_deleted_branch(self):
        self.graph.register_load("u1", "Age")
        self.graph.register_load("u2", "Drop")
        self.graph.register_cell_edit("u1", 0, 10)
        self.graph.register_cell_edit("u2", 0, 999)
        self.graph.mark_deleted("u2")
        self.graph.register_cell_edit("u1", 0, 20)

        script = self.generator.generate_script()

        self.assertNotIn("df.at[0, 'Age'] = 10", script)
        self.assertNotIn("df.at[0, 'Drop'] = 999", script)
        self.assertIn("df.at[0, 'Age'] = 20", script)
        self.assertEqual(script.count("df.at[0, 'Age']"), 1)

    def test_cell_edit_block_keeps_only_last_per_cell(self):
        self.graph.register_load("u1", "Year of Birth")
        self.graph.register_cell_edit("u1", 1, "a")
        self.graph.register_cell_edit("u1", 5, "b")
        self.graph.register_cell_edit("u1", 1, 1)
        self.graph.register_cell_edit("u1", 5, 2)

        script = self.generator.generate_script()

        self.assertNotIn("df.at[1, 'Year of Birth'] = 'a'", script)
        self.assertNotIn("df.at[5, 'Year of Birth'] = 'b'", script)
        self.assertIn("df.at[1, 'Year of Birth'] = 1", script)
        self.assertIn("df.at[5, 'Year of Birth'] = 2", script)
        self.assertEqual(script.count("df.at[1, 'Year of Birth']"), 1)
        self.assertEqual(script.count("df.at[5, 'Year of Birth']"), 1)

    def test_cell_edit_block_prunes_deleted_column_and_coalesces_remaining(self):
        self.graph.register_load("u1", "Year of Birth")
        self.graph.register_load("u2", "Drop")
        self.graph.register_cell_edit("u1", 1, "a")
        self.graph.register_cell_edit("u2", 0, "x")
        self.graph.register_cell_edit("u1", 1, "b")
        self.graph.mark_deleted("u2")

        script = self.generator.generate_script()

        self.assertNotIn("df.at[1, 'Year of Birth'] = 'a'", script)
        self.assertIn("df.at[1, 'Year of Birth'] = 'b'", script)
        self.assertNotIn("df.at[0, 'Drop'] = 'x'", script)
        self.assertEqual(script.count("df.at[1, 'Year of Birth']"), 1)

    def test_parent_edits_ignored_when_all_onehot_children_deleted(self):
        self.graph.register_load("u1", "Color")
        self.graph.register_cell_edit("u1", 0, "Red")
        self.graph.register_one_hot("u1", ["c1", "c2"], ["Color_Red", "Color_Blue"], prefix="Color")
        self.graph.mark_deleted("u1")
        self.graph.mark_deleted("c1")
        self.graph.mark_deleted("c2")

        script = self.generator.generate_script()

        self.assertNotIn("df.at[0, 'Color'] = 'Red'", script)
        self.assertNotIn("pd.get_dummies", script)

    def test_final_columns_skip_empty_names(self):
        self.graph.register_load("u1", "A")
        self.graph.nodes["u1"].current_name = ""

        script = self.generator.generate_script()

        self.assertIn("df = df[[]]", script)

    def test_row_deletes_keep_action_time_indices_descending_case(self):
        self.graph.register_load("u1", "A")
        self.graph.register_row_delete(10)
        self.graph.register_row_delete(3)

        script = self.generator.generate_script()

        drop_lines = [line.strip() for line in script.split("\n") if "df.drop(index=" in line]
        self.assertEqual(
            drop_lines,
            [
                "df = df.drop(index=10).reset_index(drop=True)",
                "df = df.drop(index=3).reset_index(drop=True)",
            ],
        )

    def test_row_deletes_keep_action_time_indices_repeated_zero(self):
        self.graph.register_load("u1", "A")
        self.graph.register_row_delete(0)
        self.graph.register_row_delete(0)

        script = self.generator.generate_script()

        drop_lines = [line.strip() for line in script.split("\n") if "df.drop(index=" in line]
        self.assertEqual(
            drop_lines,
            [
                "df = df.drop(index=0).reset_index(drop=True)",
                "df = df.drop(index=0).reset_index(drop=True)",
            ],
        )