import unittest
import pandas as pd
import numpy as np
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.core.script_generator import ScriptGenerator
from data_prep_tool.ui.main_controller import MainController

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

    def test_binary_label_update_relabels_native_boolean_columns(self):
        """Binary relabeling must also affect non-transformed boolean columns loaded from CSV."""
        df = pd.DataFrame({
            'Flag': [True, False, True, None],
            'Value': [10, 20, 30, 40],
        })
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        manager.update_binary_labels('YES', 'NO')

        out_df = manager.get_current_dataframe()
        self.assertEqual(list(out_df['Flag'].dropna()), ['YES', 'NO', 'YES'])

    def test_calculate_stats_reports_binary_counts(self):
        """Binary stats should include true/false bucket counts for boolean-like columns."""
        class DummyManager:
            binary_true = 'YES'
            binary_false = 'NO'

        class DummyController:
            pass

        dummy = DummyController()
        dummy.manager = DummyManager()
        dummy._get_binary_counts = lambda series: MainController._get_binary_counts(dummy, series)

        stats = MainController._calculate_stats(dummy, pd.Series([True, False, True, None]))

        self.assertIn('Type: Binary', stats)
        self.assertIn('YES: 2', stats)
        self.assertIn('NO: 1', stats)

    def test_calculate_stats_reports_categorical_top_counts(self):
        """Categorical stats should include top values with their counts."""
        class DummyManager:
            binary_true = 'YES'
            binary_false = 'NO'

        class DummyController:
            pass

        dummy = DummyController()
        dummy.manager = DummyManager()
        dummy._get_binary_counts = lambda series: MainController._get_binary_counts(dummy, series)
        dummy._build_categorical_top_counts = lambda series: MainController._build_categorical_top_counts(dummy, series)
        dummy._format_category_label = lambda value, max_len=32: MainController._format_category_label(dummy, value, max_len)

        stats = MainController._calculate_stats(dummy, pd.Series(['A', 'A', 'B', 'C', None]))

        self.assertIn('Type: Categorical', stats)
        self.assertIn('Top Values (count):', stats)
        self.assertIn('- A: 2', stats)
        self.assertIn('- B: 1', stats)
        self.assertIn('- C: 1', stats)

    def test_calculate_stats_categorical_top_counts_all_missing(self):
        """Categorical top-counts should handle all-null columns without crashing."""
        class DummyManager:
            binary_true = 'YES'
            binary_false = 'NO'

        class DummyController:
            pass

        dummy = DummyController()
        dummy.manager = DummyManager()
        dummy._get_binary_counts = lambda series: MainController._get_binary_counts(dummy, series)
        dummy._build_categorical_top_counts = lambda series: MainController._build_categorical_top_counts(dummy, series)
        dummy._format_category_label = lambda value, max_len=32: MainController._format_category_label(dummy, value, max_len)

        stats = MainController._calculate_stats(dummy, pd.Series([None, None], dtype='object'))

        self.assertIn('Type: Categorical', stats)
        self.assertIn('Top Values (count):', stats)
        self.assertIn('No non-missing values.', stats)

    def test_binary_label_update_relabels_numpy_boolean_scalars(self):
        """Regression: relabeling should work for NumPy bool scalars immediately after load."""
        df = pd.DataFrame({
            'Flag': pd.Series([np.bool_(True), np.bool_(False), np.bool_(True)], dtype=object),
            'Value': [1, 2, 3],
        })
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        manager.update_binary_labels('YES', 'NO')

        out_df = manager.get_current_dataframe()
        self.assertEqual(list(out_df['Flag']), ['YES', 'NO', 'YES'])

    def test_build_child_column_stats_contains_parent_and_child_binary_details(self):
        """Expanded child stats should keep parent stats and include child binary true/false counts."""
        class DummyManager:
            binary_true = 'YES'
            binary_false = 'NO'

        class DummyController:
            pass

        dummy = DummyController()
        dummy.manager = DummyManager()
        dummy._get_binary_counts = lambda series: MainController._get_binary_counts(dummy, series)
        dummy._calculate_stats = lambda series: MainController._calculate_stats(dummy, series)

        parent_series = pd.Series([10, 20, 30, 40])
        child_series = pd.Series(['YES', 'NO', 'YES', 'NO'])
        stats = MainController._build_child_column_stats(
            dummy,
            parent_name='OriginalFlag',
            parent_series=parent_series,
            child_name='OriginalFlag_True',
            child_series=child_series,
        )

        self.assertIn('Parent Column (OriginalFlag)', stats)
        self.assertIn('Expanded Column (OriginalFlag_True)', stats)
        self.assertIn('Type: Numeric', stats)
        self.assertIn('Type: Binary', stats)
        self.assertIn('YES: 2', stats)
        self.assertIn('NO: 2', stats)

    def test_row_filter_by_value_is_undoable_and_redoable(self):
        df = pd.DataFrame({
            'Status': ['keep', 'remove', 'keep', 'remove'],
            'Value': [1, 2, 3, 4],
        })
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        status_uuid = wrapper.get_uuid_by_name('Status')
        manager.add_row_filter_by_value(status_uuid, 'remove')

        self.assertEqual(list(manager.get_current_dataframe()['Status']), ['keep', 'keep'])

        manager.undo_transformation()
        self.assertEqual(list(manager.get_current_dataframe()['Status']), ['keep', 'remove', 'keep', 'remove'])

        manager.redo_transformation()
        self.assertEqual(list(manager.get_current_dataframe()['Status']), ['keep', 'keep'])

    def test_row_filter_raises_when_value_missing(self):
        df = pd.DataFrame({'A': [1, 2, 3]})
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        col_uuid = wrapper.get_uuid_by_name('A')
        with self.assertRaises(ValueError):
            manager.add_row_filter_by_value(col_uuid, 999)

    def test_binary_label_update_remaps_active_row_filter(self):
        df = pd.DataFrame({'Flag': [True, False, True, False]})
        wrapper = DataFrameWrapper(df)
        manager = TransformationManager(wrapper)

        flag_uuid = wrapper.get_uuid_by_name('Flag')
        manager.add_row_filter_by_value(flag_uuid, True)

        manager.update_binary_labels('YES', 'NO')

        out_df = manager.get_current_dataframe()
        self.assertEqual(list(out_df['Flag']), ['NO', 'NO'])

        graph = manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        self.assertIn("_to_binary_flag(value, 'YES', 'NO')", script)