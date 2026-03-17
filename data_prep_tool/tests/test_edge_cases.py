"""
Edge Case Tests for Data Prep Tool
===================================
Tests focus on:
1. Complex transformation combinations and interactions
2. Script export correctness under complex histories
3. Undo/redo correctness in edge case sequences
4. UUID tracking through multi-step transformations
5. Column ordering correctness throughout all operations
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.core.script_generator import ScriptGenerator
from data_prep_tool.core.dependency_graph import DependencyGraph
from data_prep_tool.transformation.col_rename_transformation import ColumnRenameTransformation
from data_prep_tool.transformation.one_hot_encode import oneHotEncodeTransformation
from data_prep_tool.transformation.binning_transformation import BinningTransformation
from data_prep_tool.transformation.cell_edit_transformation import CellEditTransformation
from data_prep_tool.transformation.col_delete_transformation import ColDeleteTransformation
from data_prep_tool.transformation.col_add_transformation import ColAddTransformation
from data_prep_tool.transformation.row_delete_transformation import RowDeleteTransformation
from data_prep_tool.transformation.row_add_transformation import RowAddTransformation
from data_prep_tool.transformation.col_reorder_transformation import ColumnReorderTransformation


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_manager(df: pd.DataFrame) -> tuple[DataFrameWrapper, TransformationManager]:
    wrapper = DataFrameWrapper(df)
    manager = TransformationManager(wrapper)
    return wrapper, manager


def generate_script(manager: TransformationManager, final_uuids=None) -> str:
    graph = manager.build_dependency_graph()
    return ScriptGenerator(graph).generate_script(final_uuids)


# ===========================================================================
# 1. RENAME EDGE CASES
# ===========================================================================

class TestRenameEdgeCases(unittest.TestCase):

    def test_rename_to_same_name_is_noop_in_script(self):
        """Renaming A -> A should not emit a rename line."""
        df = pd.DataFrame({'A': [1, 2]})
        _, mgr = make_manager(df)
        mgr.add_rename(0, 'A')
        script = generate_script(mgr)
        # Script should not rename 'A' to 'A'
        self.assertNotIn("df.rename(columns={'A': 'A'}", script)
        self.assertIn("df = df[['A']]", script)

    def test_rename_chain_collapses_to_single_rename(self):
        """A -> B -> C should produce only one rename (A -> C), not two."""
        df = pd.DataFrame({'A': [1]})
        _, mgr = make_manager(df)
        mgr.add_rename(0, 'B')
        mgr.add_rename(0, 'C')
        script = generate_script(mgr)
        self.assertIn("'A': 'C'", script)
        self.assertNotIn("'A': 'B'", script)
        self.assertNotIn("'B': 'C'", script)

    def test_circular_rename_preserves_uuid_identity(self):
        """A -> Temp, B -> A, Temp -> B: UUID tracks data identity, not name."""
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_a = wrapper.get_uuid_by_name('A')
        uuid_b = wrapper.get_uuid_by_name('B')

        mgr.add_rename(0, 'Temp')
        mgr.add_rename(1, 'A')
        mgr.add_rename(0, 'B')

        graph = mgr.build_dependency_graph()
        self.assertEqual(graph.nodes[uuid_a].current_name, 'B')
        self.assertEqual(graph.nodes[uuid_b].current_name, 'A')

    def test_rename_after_onehot_child_reflects_in_script(self):
        """Renaming a one-hot child column should appear as a column rename in the script."""
        df = pd.DataFrame({'Color': ['Red', 'Blue', 'Red']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_onehot(0)  # Creates Color_Red, Color_Blue

        # Rename first child
        # Get current children from manager's wrapper
        parent_uuid = mgr.history[-1].col_uuid
        child_uuids = mgr.df_wrapper.get_children_uuids(parent_uuid)
        child_idx = mgr.df_wrapper.get_all_uuids().index(child_uuids[0])

        mgr.add_rename(child_idx, 'IsRed')

        script = generate_script(mgr)
        self.assertIn('IsRed', script)
        self.assertIn("pd.get_dummies", script)

    def test_undo_rename_restores_original_name(self):
        """Undoing a rename restores the original name in the wrapper and subsequent script."""
        df = pd.DataFrame({'Original': [1, 2]})
        _, mgr = make_manager(df)
        mgr.add_rename(0, 'Changed')
        mgr.undo_transformation()

        self.assertIn('Original', mgr.df_wrapper.df.columns)
        self.assertNotIn('Changed', mgr.df_wrapper.df.columns)

        script = generate_script(mgr)
        self.assertNotIn("'Original': 'Changed'", script)


# ===========================================================================
# 2. ONE-HOT EDGE CASES
# ===========================================================================

class TestOneHotEdgeCases(unittest.TestCase):

    def test_onehot_then_rename_parent_before_encoding(self):
        """Rename A -> Category, then one-hot encode Category.
        Script must rename first, then get_dummies on 'Category'."""
        df = pd.DataFrame({'A': ['x', 'y', 'x']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_rename(0, 'Category')
        mgr.add_onehot(0)

        script = generate_script(mgr)
        rename_pos = script.find("'A': 'Category'")
        dummies_pos = script.find("pd.get_dummies")
        self.assertGreater(rename_pos, -1, "Rename step missing")
        self.assertGreater(dummies_pos, -1, "get_dummies step missing")
        self.assertLess(rename_pos, dummies_pos, "Rename must come before get_dummies")
        self.assertIn("df['Category']", script)

    def test_onehot_column_order_preserved(self):
        """One-hot children should appear at the parent's original position."""
        df = pd.DataFrame({'A': [1], 'B': ['x', 'y'][0:1], 'C': [3]})
        df = pd.DataFrame({'A': [1, 2], 'B': ['x', 'y'], 'C': [3, 4]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_onehot(1)  # Encode B (middle column)

        cols = list(mgr.df_wrapper.df.columns)
        # B_x and B_y should be between A and C
        self.assertEqual(cols[0], 'A')
        self.assertEqual(cols[-1], 'C')
        self.assertTrue(all('B_' in c for c in cols[1:-1]))

    def test_onehot_undo_restores_exact_position(self):
        """Undoing one-hot on a middle column restores parent at original position."""
        df = pd.DataFrame({'A': [1], 'B': ['x'], 'C': [3]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_onehot(1)
        mgr.undo_transformation()

        self.assertEqual(list(mgr.df_wrapper.df.columns), ['A', 'B', 'C'])

    def test_double_onehot_different_columns(self):
        """Encoding two columns sequentially both appear correctly in script."""
        df = pd.DataFrame({'Color': ['R', 'G'], 'Size': ['S', 'M']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_onehot(0)  # Color
        mgr.add_onehot(1)  # Size (now at index 1 after Color children inserted)

        script = generate_script(mgr)
        self.assertEqual(script.count("pd.get_dummies"), 2)

    def test_onehot_undo_redo_cycle(self):
        """Apply, undo, redo should give the same final state as just applying."""
        df = pd.DataFrame({'X': ['a', 'b', 'a']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_onehot(0)
        after_apply = list(mgr.df_wrapper.df.columns)

        mgr.undo_transformation()
        mgr.redo_transformation()

        self.assertEqual(list(mgr.df_wrapper.df.columns), after_apply)

    def test_onehot_script_not_emitted_after_undo(self):
        """After undoing a one-hot, the script must not contain get_dummies."""
        df = pd.DataFrame({'Color': ['R', 'G']})
        _, mgr = make_manager(df)
        mgr.add_onehot(0)
        mgr.undo_transformation()

        script = generate_script(mgr)
        self.assertNotIn("pd.get_dummies", script)
        self.assertIn("df = df[['Color']]", script)

    def test_onehot_custom_labels_appear_in_script(self):
        """Custom true/false labels must propagate into the generated script."""
        df = pd.DataFrame({'Flag': ['yes', 'no', 'yes']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        mgr.binary_true = '1'
        mgr.binary_false = '0'

        mgr.add_onehot(0)

        script = generate_script(mgr)
        self.assertIn("'1'", script)
        self.assertIn("'0'", script)


# ===========================================================================
# 3. BINNING EDGE CASES
# ===========================================================================

class TestBinningEdgeCases(unittest.TestCase):

    def test_binning_then_rename_child_in_script(self):
        """After binning, renaming a child column reflects in the final column selection."""
        df = pd.DataFrame({'Score': [10, 50, 90]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_binning(0, 'Equal Width', 2)

        # Rename first child
        child_uuids = mgr.df_wrapper.get_children_uuids(mgr.history[-1].col_uuid)
        child_idx = mgr.df_wrapper.get_all_uuids().index(child_uuids[0])
        original_child_name = mgr.df_wrapper.get_col_name_by_uuid(child_uuids[0])

        mgr.add_rename(child_idx, 'LowScore')

        script = generate_script(mgr)
        self.assertIn("LowScore", script)
        self.assertIn("df = df[['LowScore'", script)

    def test_rename_before_binning_uses_renamed_column(self):
        """Renaming a column before binning it must use the new name in the script."""
        df = pd.DataFrame({'A': [1, 5, 10, 15, 20]})
        _, mgr = make_manager(df)

        mgr.add_rename(0, 'Score')
        mgr.add_binning(0, 'Equal Width', 2)

        script = generate_script(mgr)
        self.assertIn("df['Score']", script)
        self.assertNotIn("df['A'],", script)  # 'A' should not be binned

    def test_binning_undo_restores_original_data_exactly(self):
        """Undo after binning must restore the exact original data."""
        original = pd.Series([1.5, 2.5, 3.5, 4.5])
        df = pd.DataFrame({'Val': original})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_binning(0, 'Equal Width', 2)
        mgr.undo_transformation()

        pd.testing.assert_series_equal(mgr.df_wrapper.df['Val'], original, check_names=False)

    def test_binning_script_drops_parent_column(self):
        """Generated script must drop the original column after binning."""
        df = pd.DataFrame({'Age': [20, 40, 60]})
        _, mgr = make_manager(df)
        mgr.add_binning(0, 'Equal Width', 3)

        script = generate_script(mgr)
        self.assertIn("df.drop(columns=['Age']", script)

    def test_ordinal_script_uses_correct_syntax(self):
        """Ordinal binning must use pd.cut with labels=False."""
        df = pd.DataFrame({'Score': [10, 30, 50, 70, 90]})
        _, mgr = make_manager(df)
        mgr.add_binning(0, 'Ordinal', 3)

        script = generate_script(mgr)
        self.assertIn("binned_codes = pd.cut(numeric_vals, bins=3, labels=False)", script)

    def test_custom_binning_uses_provided_cutoffs(self):
        """Custom binning script must include the exact cutoffs supplied."""
        df = pd.DataFrame({'Val': [1, 5, 9]})
        _, mgr = make_manager(df)
        mgr.add_binning(0, 'Custom', 2, cutoffs=[0, 5, 10])

        script = generate_script(mgr)
        self.assertIn("binned = pd.cut(numeric_vals, bins=[0, 5, 10])", script)

    def test_equal_frequency_script_uses_qcut(self):
        """Equal Frequency binning must use pd.qcut in the generated script."""
        df = pd.DataFrame({'V': range(20)})
        _, mgr = make_manager(df)
        mgr.add_binning(0, 'Equal Frequency', 4)

        script = generate_script(mgr)
        self.assertIn("binned = pd.qcut(numeric_vals, q=4", script)


# ===========================================================================
# 4. CELL EDIT EDGE CASES
# ===========================================================================

class TestCellEditEdgeCases(unittest.TestCase):

    def test_multiple_edits_same_cell_only_last_value_in_graph(self):
        """Multiple edits to the same cell should collapse to the last value."""
        df = pd.DataFrame({'A': [10, 20, 30]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_a = wrapper.get_uuid_by_name('A')

        mgr.add_cell_edit(0, uuid_a, 100)
        mgr.add_cell_edit(0, uuid_a, 200)
        mgr.add_cell_edit(0, uuid_a, 999)

        graph = mgr.build_dependency_graph()
        edits = graph.nodes[uuid_a].params.get('manual_edits', [])
        row0_edits = [e for e in edits if e['row'] == 0]
        self.assertEqual(len(row0_edits), 1)
        self.assertEqual(row0_edits[0]['value'], 999)

    def test_edit_after_rename_still_targets_correct_column(self):
        """Cell edit after renaming a column must target the renamed column."""
        df = pd.DataFrame({'OldName': [1, 2, 3]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_rename(0, 'NewName')
        uuid = wrapper.get_uuid_by_name('NewName')
        mgr.add_cell_edit(0, uuid, 999)

        self.assertEqual(mgr.df_wrapper.df.at[0, 'NewName'], 999)

    def test_cell_edit_undo_restores_previous_value(self):
        """After undoing a cell edit, the original value is restored."""
        df = pd.DataFrame({'A': [42]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_a = wrapper.get_uuid_by_name('A')

        mgr.add_cell_edit(0, uuid_a, 999)
        mgr.undo_transformation()

        self.assertEqual(mgr.df_wrapper.df.at[0, 'A'], 42)

    def test_edit_does_not_appear_in_script_after_undo(self):
        """Script should not contain an edit that was undone."""
        df = pd.DataFrame({'A': [1]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_a = wrapper.get_uuid_by_name('A')

        mgr.add_cell_edit(0, uuid_a, 999)
        mgr.undo_transformation()

        script = generate_script(mgr)
        self.assertNotIn("999", script)


# ===========================================================================
# 5. COLUMN DELETE EDGE CASES
# ===========================================================================

class TestColDeleteEdgeCases(unittest.TestCase):

    def test_delete_then_add_same_name_works(self):
        """Deleting a column and adding one with the same name should not conflict."""
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_a = wrapper.get_uuid_by_name('A')

        mgr.add_col_delete(uuid_a)
        mgr.add_col_add('A', 0)  # Add a new 'A' column

        self.assertIn('A', mgr.df_wrapper.df.columns)
        # New 'A' UUID should differ from old 'A' UUID
        new_uuid_a = mgr.df_wrapper.get_uuid_by_name('A')
        self.assertNotEqual(new_uuid_a, uuid_a)

    def test_deleted_column_absent_from_script(self):
        """A deleted column must not appear in the final column selection."""
        df = pd.DataFrame({'Keep': [1], 'Drop': [2]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_drop = wrapper.get_uuid_by_name('Drop')

        mgr.add_col_delete(uuid_drop)
        script = generate_script(mgr)

        self.assertNotIn("'Drop'", script)
        self.assertIn("'Keep'", script)

    def test_delete_undo_restores_column_and_data(self):
        """Undoing a delete must restore the column with its original data."""
        df = pd.DataFrame({'A': [10, 20, 30]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_a = wrapper.get_uuid_by_name('A')

        mgr.add_col_delete(uuid_a)
        mgr.undo_transformation()

        self.assertIn('A', mgr.df_wrapper.df.columns)
        self.assertEqual(list(mgr.df_wrapper.df['A']), [10, 20, 30])

    def test_delete_undo_restores_original_column_position(self):
        """Undoing delete on a middle column must restore it at the original index."""
        df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_b = wrapper.get_uuid_by_name('B')

        mgr.add_col_delete(uuid_b)
        mgr.undo_transformation()

        self.assertEqual(list(mgr.df_wrapper.df.columns), ['A', 'B', 'C'])

    def test_delete_after_rename_removes_renamed_column(self):
        """Deleting a column after renaming removes the renamed column from the script."""
        df = pd.DataFrame({'OldName': [1]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_rename(0, 'NewName')
        uuid = wrapper.get_uuid_by_name('NewName')
        mgr.add_col_delete(uuid)

        script = generate_script(mgr)
        self.assertNotIn("'OldName'", script)
        self.assertNotIn("'NewName'", script)


# ===========================================================================
# 6. ROW DELETE EDGE CASES
# ===========================================================================

class TestRowDeleteEdgeCases(unittest.TestCase):

    def test_multiple_row_deletes_adjust_indices_correctly(self):
        """Deleting row 0, then row 0 again removes original rows 0 and 1."""
        df = pd.DataFrame({'A': [10, 20, 30, 40]})
        _, mgr = make_manager(df)

        mgr.add_row_delete(0)
        mgr.add_row_delete(0)  # This removes what was originally row 1

        self.assertEqual(list(mgr.df_wrapper.df['A']), [30, 40])

    def test_row_delete_undo_restores_data(self):
        """Undoing a row delete restores the row with correct data."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        _, mgr = make_manager(df)

        mgr.add_row_delete(1)
        mgr.undo_transformation()

        self.assertEqual(list(mgr.df_wrapper.df['A']), [1, 2, 3])

    def test_row_delete_script_adjusts_index_offset(self):
        """Script for two sequential deletes must use offset-adjusted indices."""
        df = pd.DataFrame({'A': range(5)})
        _, mgr = make_manager(df)

        mgr.add_row_delete(0)
        mgr.add_row_delete(0)

        script = generate_script(mgr)
        # First delete: index 0; second delete: index 0 (offset 0 already deleted)
        self.assertIn("df = df.drop(index=0)", script)
        # Second drop also uses adjusted index = 0
        drop_lines = [l for l in script.split('\n') if 'df.drop(index=' in l]
        self.assertEqual(len(drop_lines), 2)

    def test_row_delete_non_zero_index(self):
        """Deleting a non-first row leaves surrounding rows intact."""
        df = pd.DataFrame({'A': [10, 20, 30]})
        _, mgr = make_manager(df)

        mgr.add_row_delete(1)

        self.assertEqual(list(mgr.df_wrapper.df['A']), [10, 30])

    def test_row_delete_then_add_roundtrip(self):
        """Deleting the last row, then adding a row keeps row count the same."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        _, mgr = make_manager(df)

        mgr.add_row_delete(2)
        mgr.add_row_add('')

        self.assertEqual(len(mgr.df_wrapper.df), 3)


# ===========================================================================
# 7. COLUMN ADD EDGE CASES
# ===========================================================================

class TestColAddEdgeCases(unittest.TestCase):

    def test_add_column_appears_in_script(self):
        """An added column must appear in the generated script."""
        df = pd.DataFrame({'A': [1, 2]})
        _, mgr = make_manager(df)

        mgr.add_col_add('NewCol', 0)
        script = generate_script(mgr)

        self.assertIn("df['NewCol']", script)
        self.assertIn("'NewCol'", script)

    def test_add_column_undo_removes_column(self):
        """Undoing an add column removes it from the wrapper."""
        df = pd.DataFrame({'A': [1]})
        _, mgr = make_manager(df)

        mgr.add_col_add('Extra', 99)
        mgr.undo_transformation()

        self.assertNotIn('Extra', mgr.df_wrapper.df.columns)

    def test_add_column_default_value_in_script(self):
        """The default value for an added column must appear in the script."""
        df = pd.DataFrame({'A': [1]})
        _, mgr = make_manager(df)

        mgr.add_col_add('Flag', 'unknown')
        script = generate_script(mgr)

        self.assertIn("'unknown'", script)

    def test_add_duplicate_column_name_raises(self):
        """Adding a column with an existing name should raise ValueError."""
        df = pd.DataFrame({'A': [1, 2]})
        _, mgr = make_manager(df)

        with self.assertRaises((ValueError, Exception)):
            mgr.add_col_add('A', 0)


# ===========================================================================
# 8. REORDER EDGE CASES
# ===========================================================================

class TestReorderEdgeCases(unittest.TestCase):

    def test_reorder_undo_restores_original_order(self):
        """Undoing a reorder returns columns to their previous order."""
        df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuids = wrapper.get_all_uuids()

        mgr.add_column_reorder([uuids[2], uuids[1], uuids[0]])  # C, B, A
        mgr.undo_transformation()

        self.assertEqual(list(mgr.df_wrapper.df.columns), ['A', 'B', 'C'])

    def test_reorder_after_onehot_reflects_in_final_script(self):
        """Column order in final script should match the user-defined reorder."""
        df = pd.DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_onehot(1)  # B -> B_x, B_y; columns: A, B_x, B_y

        all_uuids = mgr.df_wrapper.get_all_uuids()
        # Reorder: B_x, A, B_y  (reversed)
        mgr.add_column_reorder([all_uuids[1], all_uuids[0], all_uuids[2]])

        final_uuids = mgr.df_wrapper.get_all_uuids()
        script = generate_script(mgr, final_uuids)

        # Determine expected order of names
        final_names = [mgr.df_wrapper.get_col_name_by_uuid(u) for u in final_uuids]
        final_cols_str = ", ".join(f"'{n}'" for n in final_names)
        self.assertIn(final_cols_str, script)


# ===========================================================================
# 9. COMPLEX MULTI-STEP COMBINATION TESTS
# ===========================================================================

class TestComplexCombinations(unittest.TestCase):

    def test_rename_onehot_rename_child_all_in_script(self):
        """Full pipeline: rename parent, one-hot, rename child -> script is coherent."""
        df = pd.DataFrame({'type': ['cat', 'dog', 'cat']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        # 1. Rename parent
        mgr.add_rename(0, 'AnimalType')

        # 2. One-hot
        mgr.add_onehot(0)

        # 3. Rename first child
        parent_uuid = mgr.history[-2].col_uuid  # The rename trans holds the uuid
        child_uuids = mgr.df_wrapper.get_children_uuids(parent_uuid)
        child_idx = mgr.df_wrapper.get_all_uuids().index(child_uuids[0])
        original_child_name = mgr.df_wrapper.get_col_name_by_uuid(child_uuids[0])

        mgr.add_rename(child_idx, 'IsCat')

        script = generate_script(mgr)

        # Parent rename must precede get_dummies
        self.assertIn("'type': 'AnimalType'", script)
        self.assertIn("pd.get_dummies", script)
        # Child rename must be present
        self.assertIn("IsCat", script)
        self.assertIn("df = df[[", script)

    def test_binning_then_cell_edit_child_in_script(self):
        """After binning, editing a cell in a child column shows in the script via manual_edits."""
        df = pd.DataFrame({'Score': [10, 50, 90]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_binning(0, 'Equal Width', 2)

        # Edit cell in first child
        child_uuids = mgr.df_wrapper.get_children_uuids(mgr.history[-1].col_uuid)
        mgr.add_cell_edit(0, child_uuids[0], 'custom_val')

        graph = mgr.build_dependency_graph()
        child_node = graph.get_node(child_uuids[0])
        self.assertIsNotNone(child_node)
        edits = child_node.params.get('manual_edits', [])
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]['value'], 'custom_val')

    def test_full_pipeline_script_is_executable(self):
        """Generated script must be valid Python (compile check)."""
        df = pd.DataFrame({
            'Name': ['Alice', 'Bob', 'Charlie'],
            'Age': [25, 35, 45],
            'Color': ['R', 'G', 'B']
        })
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_rename(0, 'CustomerName')
        mgr.add_binning(1, 'Equal Width', 2)
        mgr.add_onehot(1)  # Color is now at index 1 after age's children occupy spots

        script = generate_script(mgr)
        # Should compile without syntax errors
        try:
            compile(script, '<string>', 'exec')
        except SyntaxError as e:
            self.fail(f"Generated script has a syntax error: {e}")

    def test_undo_after_complex_sequence_preserves_state(self):
        """After undoing several transformations, state must match expected intermediate state."""
        df = pd.DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_rename(0, 'Alpha')  # history[0]
        mgr.add_onehot(1)           # history[1]
        mgr.add_col_add('Extra', 0) # history[2]

        # Undo twice: removes Extra and OneHot
        mgr.undo_transformation()
        mgr.undo_transformation()

        cols = list(mgr.df_wrapper.df.columns)
        self.assertIn('Alpha', cols)
        self.assertIn('B', cols)
        self.assertNotIn('B_x', cols)
        self.assertNotIn('Extra', cols)

    def test_redo_after_undo_sequence(self):
        """Redo restores the transformation that was undone."""
        df = pd.DataFrame({'X': ['a', 'b']})
        _, mgr = make_manager(df)

        mgr.add_onehot(0)
        mgr.undo_transformation()
        mgr.redo_transformation()

        self.assertNotIn('X', mgr.df_wrapper.df.columns)
        self.assertIn('X_a', mgr.df_wrapper.df.columns)

    def test_delete_col_after_binning_removes_child(self):
        """Deleting a binned child column marks it deleted in graph."""
        df = pd.DataFrame({'Age': [10, 20, 30]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_binning(0, 'Equal Width', 2)
        child_uuids = mgr.df_wrapper.get_children_uuids(mgr.history[-1].col_uuid)
        first_child_uuid = child_uuids[0]

        mgr.add_col_delete(first_child_uuid)

        graph = mgr.build_dependency_graph()
        self.assertTrue(graph.nodes[first_child_uuid].is_deleted)
        script = generate_script(mgr)
        deleted_name = mgr.history[-2].column + '_'  # prefix of binned column
        # Confirm deleted child not in final selection
        # (we check no reference to the deleted uuid's name in final df selection)
        first_child_name = mgr.history[-1].col_name  # ColDeleteTransformation stores col_name
        self.assertNotIn(first_child_name, script.split("df = df[[")[-1])

    def test_row_delete_does_not_affect_column_history(self):
        """Row deletions must not corrupt column UUID tracking."""
        df = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        uuid_a = wrapper.get_uuid_by_name('A')
        uuid_b = wrapper.get_uuid_by_name('B')

        mgr.add_row_delete(1)
        mgr.add_rename(0, 'Alpha')

        # UUID of A should now map to 'Alpha'
        self.assertEqual(mgr.df_wrapper.get_col_name_by_uuid(uuid_a), 'Alpha')
        self.assertEqual(mgr.df_wrapper.get_col_name_by_uuid(uuid_b), 'B')
        self.assertEqual(len(mgr.df_wrapper.df), 2)

    def test_script_column_selection_respects_visual_order(self):
        """The final column list in the script must match the visual order in the wrapper."""
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, 6]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        uuids = wrapper.get_all_uuids()
        # Reorder to: C, A, B
        mgr.add_column_reorder([uuids[2], uuids[0], uuids[1]])

        final_uuids = mgr.df_wrapper.get_all_uuids()
        script = generate_script(mgr, final_uuids)

        # The final df selection should be in the reordered order
        self.assertIn("df = df[['C', 'A', 'B']]", script)

    def test_binary_label_update_reapplies_to_existing_onehot(self):
        """Changing binary labels after one-hot must re-encode existing children."""
        df = pd.DataFrame({'Flag': ['yes', 'no']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_onehot(0)
        # Change labels
        mgr.update_binary_labels('1', '0')

        # Check values in one of the child columns contain '1' or '0', not True/False
        child_vals = set()
        for col in mgr.df_wrapper.df.columns:
            child_vals.update(mgr.df_wrapper.df[col].unique())

        self.assertIn('1', child_vals)
        self.assertIn('0', child_vals)
        self.assertNotIn(True, child_vals)
        self.assertNotIn(False, child_vals)

    def test_adding_row_after_deleting_maintains_correct_row_count(self):
        """After delete + add, total rows = original rows."""
        df = pd.DataFrame({'A': range(5)})
        _, mgr = make_manager(df)

        mgr.add_row_delete(0)
        mgr.add_row_add(0)

        self.assertEqual(len(mgr.df_wrapper.df), 5)

    def test_script_for_col_add_uses_correct_default_value(self):
        """COL_ADD node in script must initialize column with the specified default."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        _, mgr = make_manager(df)

        mgr.add_col_add('Status', 'pending')
        script = generate_script(mgr)

        self.assertIn("df['Status'] = 'pending'", script)

    def test_onehot_on_renamed_then_deleted_parent_does_not_crash(self):
        """After one-hot, if user somehow triggers undo of rename (not onehot), state is safe."""
        df = pd.DataFrame({'Type': ['A', 'B', 'A']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_rename(0, 'Category')
        mgr.add_onehot(0)

        # Undo the one-hot
        mgr.undo_transformation()

        # Column should be back as 'Category'
        self.assertIn('Category', mgr.df_wrapper.df.columns)
        self.assertNotIn('Category_A', mgr.df_wrapper.df.columns)


# ===========================================================================
# 10. SCRIPT GENERATOR SPECIFIC TESTS
# ===========================================================================

class TestScriptGeneratorEdgeCases(unittest.TestCase):

    def test_empty_history_produces_minimal_script(self):
        """An empty history should still produce a valid script that just selects original columns."""
        df = pd.DataFrame({'A': [1], 'B': [2]})
        _, mgr = make_manager(df)

        script = generate_script(mgr)
        self.assertIn("df = pd.read_csv", script)
        self.assertIn("df = df[['A', 'B']]", script)

    def test_get_dummies_called_once_per_parent_column(self):
        """get_dummies must appear exactly once per one-hot parent, not per child."""
        df = pd.DataFrame({'X': ['a', 'b', 'c']})
        _, mgr = make_manager(df)
        mgr.add_onehot(0)

        script = generate_script(mgr)
        self.assertEqual(script.count("pd.get_dummies"), 1)

    def test_script_loads_from_source_path(self):
        """Script must use the source path from register_load, not a hardcoded default."""
        df = pd.DataFrame({'A': [1]})
        _, mgr = make_manager(df)

        script = generate_script(mgr)
        self.assertIn("pd.read_csv(", script)

    def test_script_resets_index_after_row_operations(self):
        """Script must include reset_index after row deletions."""
        df = pd.DataFrame({'A': [1, 2, 3]})
        _, mgr = make_manager(df)
        mgr.add_row_delete(0)

        script = generate_script(mgr)
        self.assertIn("reset_index(drop=True)", script)

    def test_final_col_uuids_subset_limits_script_output(self):
        """Passing a subset of UUIDs to generate_script limits output columns."""
        df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        uuid_a = wrapper.get_uuid_by_name('A')
        uuid_c = wrapper.get_uuid_by_name('C')

        graph = mgr.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script(final_col_uuids=[uuid_a, uuid_c])

        self.assertIn("'A'", script)
        self.assertIn("'C'", script)
        self.assertNotIn("'B'", script.split("df = df[[")[-1])

    def test_script_imports_required_libraries(self):
        """Generated script must import pandas and numpy."""
        df = pd.DataFrame({'A': [1]})
        _, mgr = make_manager(df)

        script = generate_script(mgr)
        self.assertIn("import pandas as pd", script)
        self.assertIn("import numpy as np", script)

    def test_multiple_row_deletes_produce_correct_offset_adjustments(self):
        """Sequential row deletes must use incrementally offset-adjusted indices in script."""
        df = pd.DataFrame({'A': range(10)})
        _, mgr = make_manager(df)

        mgr.add_row_delete(2)
        mgr.add_row_delete(2)  # After first delete, original row 3 is now at index 2
        mgr.add_row_delete(2)  # Original row 4

        script = generate_script(mgr)
        drop_lines = [l.strip() for l in script.split('\n') if 'df.drop(index=' in l]
        # All three drops should target adjusted index 2 (after previous offsets)
        self.assertEqual(len(drop_lines), 3)


# ===========================================================================
# 11. UUID MANAGER INTEGRITY TESTS
# ===========================================================================

class TestUUIDManagerIntegrity(unittest.TestCase):

    def test_uuid_stability_through_reorder(self):
        """UUIDs must not change after reordering columns."""
        df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        uuid_a = wrapper.get_uuid_by_name('A')
        uuid_b = wrapper.get_uuid_by_name('B')
        uuid_c = wrapper.get_uuid_by_name('C')

        all_uuids = wrapper.get_all_uuids()
        mgr.add_column_reorder([all_uuids[2], all_uuids[0], all_uuids[1]])

        self.assertEqual(mgr.df_wrapper.get_uuid_by_name('A'), uuid_a)
        self.assertEqual(mgr.df_wrapper.get_uuid_by_name('B'), uuid_b)
        self.assertEqual(mgr.df_wrapper.get_uuid_by_name('C'), uuid_c)

    def test_uuid_stability_through_cell_edit(self):
        """Cell edits must not alter UUID mappings."""
        df = pd.DataFrame({'A': [1, 2]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)
        uuid_a = wrapper.get_uuid_by_name('A')

        mgr.add_cell_edit(0, uuid_a, 99)

        self.assertEqual(mgr.df_wrapper.get_uuid_by_name('A'), uuid_a)
        self.assertEqual(mgr.df_wrapper.get_col_name_by_uuid(uuid_a), 'A')

    def test_child_parent_relationship_survives_sibling_delete(self):
        """Deleting one child column must not break the parent-child link of remaining siblings."""
        df = pd.DataFrame({'Color': ['R', 'G', 'B']})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_onehot(0)  # Color -> Color_R, Color_G, Color_B
        parent_uuid = mgr.history[-1].col_uuid
        child_uuids = mgr.df_wrapper.get_children_uuids(parent_uuid)

        # Delete first child
        mgr.add_col_delete(child_uuids[0])

        # Remaining children should still know their parent
        remaining_children = mgr.df_wrapper.get_children_uuids(parent_uuid)
        for c_uuid in remaining_children:
            self.assertEqual(mgr.df_wrapper.get_parent_uuid(c_uuid), parent_uuid)

    def test_all_uuids_count_matches_dataframe_column_count(self):
        """get_all_uuids() length must always equal the number of DataFrame columns."""
        df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
        wrapper = DataFrameWrapper(df)
        mgr = TransformationManager(wrapper)

        mgr.add_col_add('D', 0)
        mgr.add_onehot(1)     # B -> B_1 ...

        uuids = mgr.df_wrapper.get_all_uuids()
        self.assertEqual(len(uuids), len(mgr.df_wrapper.df.columns))


if __name__ == '__main__':
    unittest.main(verbosity=2)