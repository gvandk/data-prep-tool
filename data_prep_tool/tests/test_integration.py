import unittest
import pandas as pd
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.core.script_generator import ScriptGenerator

class TestIntegration(unittest.TestCase):
    def setUp(self):
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        self.wrapper = DataFrameWrapper(df)
        self.manager = TransformationManager(self.wrapper)

    def test_undo_erases_history(self):
        """Verify undoing a Cell Edit removes it from the exported script."""
        uuid_a = self.wrapper.get_uuid_by_name('A')
        
        # 1. Edit
        self.manager.add_cell_edit(0, uuid_a, 999)
        
        # 2. Undo
        self.manager.undo_transformation()
        
        # 3. Export
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        # 4. Verify
        self.assertNotIn("999", script)
        self.assertNotIn("manual_edits", str(graph.nodes[uuid_a].params))

    def test_shell_game_renames(self):
        """Test A->Temp, B->A, Temp->B swap logic."""
        # (This is the robust test we fixed earlier)
        self.manager.add_rename(0, 'Temp') # A -> Temp
        self.manager.add_rename(1, 'A')    # B -> A
        self.manager.add_rename(0, 'B')    # Temp -> B
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        # Verify script contains the mapping
        self.assertIn("'A': 'B'", script)
        self.assertIn("'B': 'A'", script)

    def test_binary_label_update_after_onehot_reorder_and_rename(self):
        """Regression: relabeling booleans must not crash after one-hot, reorder, and renames."""
        df = pd.DataFrame({
            'Color': ['Red', 'Blue', 'Red'],
            'Value': [1, 2, 3]
        })
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        manager.add_onehot(0)

        # Reorder columns to a non-default order
        current_order = manager.df_wrapper.get_all_uuids()
        manager.add_column_reorder([current_order[-1]] + current_order[:-1])

        # Rename one-hot columns after reorder
        for old_name, new_name in [('Color_Red', 'is_red'), ('Color_Blue', 'is_blue')]:
            col_idx = manager.df_wrapper.df.columns.get_loc(old_name)
            manager.add_rename(col_idx, new_name)

        expected_order = list(manager.get_current_dataframe().columns)

        # This used to crash while undoing one-hot in history replay
        manager.update_binary_labels('YES', 'NO')

        out_df = manager.get_current_dataframe()
        self.assertIn('is_red', out_df.columns)
        self.assertIn('is_blue', out_df.columns)
        self.assertEqual(list(out_df.columns), expected_order)
        self.assertEqual(set(out_df['is_red'].unique()), {'YES', 'NO'})
        self.assertEqual(set(out_df['is_blue'].unique()), {'YES', 'NO'})

    def test_binary_label_update_tolerates_missing_onehot_children(self):
        """Regression: update_binary_labels should not crash if some one-hot child columns are missing."""
        df = pd.DataFrame({'Year of Birth': [1990, 1991, 1990], 'City': ['A', 'B', 'C']})
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        manager.add_onehot(0)

        # Simulate inconsistent runtime state where some generated child columns are gone.
        onehot = manager.history[-1]
        missing_children = manager.df_wrapper.uuid_manager.get_children_names(onehot.col_uuid)[:1]
        if missing_children:
            manager.df_wrapper.df.drop(columns=missing_children, inplace=True)

        # Must not raise KeyError during undo/replay.
        manager.update_binary_labels('YES', 'NO')

        out_df = manager.get_current_dataframe()
        self.assertTrue(len(out_df.columns) > 0)