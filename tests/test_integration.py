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


        self.manager.add_cell_edit(0, uuid_a, 999)


        self.manager.undo_transformation()


        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()


        self.assertNotIn("999", script)
        self.assertNotIn("manual_edits", str(graph.nodes[uuid_a].params))

    def test_shell_game_renames(self):
        """Test A->Temp, B->A, Temp->B swap logic."""
        uuid_a = self.wrapper.get_uuid_by_name('A')
        uuid_b = self.wrapper.get_uuid_by_name('B')

        self.manager.add_rename(uuid_a, 'Temp')
        self.manager.add_rename(uuid_b, 'A')
        self.manager.add_rename(uuid_a, 'B')

        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()


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


        current_order = manager.df_wrapper.get_all_uuids()
        manager.add_column_reorder([current_order[-1]] + current_order[:-1])


        for old_name, new_name in [('Color_Red', 'is_red'), ('Color_Blue', 'is_blue')]:
            uuid = manager.df_wrapper.get_uuid_by_name(old_name)
            manager.add_rename(uuid, new_name)

        expected_order = list(manager.get_current_dataframe().columns)


        manager.update_binary_labels('YES', 'NO')

        out_df = manager.get_current_dataframe()
        self.assertIn('is_red', out_df.columns)
        self.assertIn('is_blue', out_df.columns)
        self.assertEqual(list(out_df.columns), expected_order)
        self.assertEqual(set(out_df['is_red'].unique()), {'YES', 'NO'})
        self.assertEqual(set(out_df['is_blue'].unique()), {'YES', 'NO'})

    def test_repeated_binary_label_updates_after_complex_history(self):
        """Repeated relabeling should stay responsive and consistent after complex edits."""
        df = pd.DataFrame({
            'Color': ['Red', 'Blue', 'Red', 'Green'],
            'Size': ['S', 'M', 'L', 'S'],
            'Value': [10, 20, 30, 40]
        })
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        value_uuid = wrapper.get_uuid_by_name('Value')

        manager.add_onehot(0)
        value_idx = manager.df_wrapper.get_all_uuids().index(value_uuid)
        manager.add_binning(value_idx, 'Equal Width', 2)

        current = manager.df_wrapper.get_all_uuids()
        manager.add_column_reorder(list(reversed(current)))

        manager.add_row_add(0)
        manager.add_row_delete(0)

        manager.undo_transformation()
        manager.redo_transformation()

        manager.update_binary_labels('YES', 'NO')
        manager.update_binary_labels('T', 'F')
        manager.update_binary_labels('1', '0')

        out_df = manager.get_current_dataframe()
        flat_vals = set(str(v) for v in out_df.values.ravel())
        self.assertIn('1', flat_vals)
        self.assertIn('0', flat_vals)

    def test_binary_label_update_with_deleted_encoded_child_columns(self):
        """Relabeling remains stable when some encoded child columns were deleted."""
        df = pd.DataFrame({'Color': ['Red', 'Blue', 'Red']})
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        manager.add_onehot(0)
        parent_uuid = manager.history[-1].col_uuid
        child_uuids = list(manager.df_wrapper.get_children_uuids(parent_uuid) or [])
        manager.add_col_delete(child_uuids[0])

        manager.update_binary_labels('YES', 'NO')
        manager.update_binary_labels('ON', 'OFF')

        out_df = manager.get_current_dataframe()
        flat_vals = set(str(v) for v in out_df.values.ravel())
        self.assertIn('ON', flat_vals)
        self.assertIn('OFF', flat_vals)

    def test_binary_label_update_tolerates_missing_onehot_children(self):
        """Regression: update_binary_labels should not crash if some one-hot child columns are missing."""
        df = pd.DataFrame({'Year of Birth': [1990, 1991, 1990], 'City': ['A', 'B', 'C']})
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        manager.add_onehot(0)


        onehot = manager.history[-1]
        missing_children = manager.df_wrapper.uuid_manager.get_children_names(onehot.col_uuid)[:1]
        if missing_children:
            manager.df_wrapper.df.drop(columns=missing_children, inplace=True)


        manager.update_binary_labels('YES', 'NO')

        out_df = manager.get_current_dataframe()
        self.assertTrue(len(out_df.columns) > 0)