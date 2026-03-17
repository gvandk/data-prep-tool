import unittest
import pandas as pd
import numpy as np
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.core.script_generator import ScriptGenerator
from data_prep_tool.transformation.binning_transformation import BinningTransformation

class TestBinningTransformation(unittest.TestCase):
    def setUp(self):
        # Create data with a clear range for easy binning verification
        # 0, 10, 20, ... 90
        self.data = pd.DataFrame({'Score': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]})
        self.wrapper = DataFrameWrapper(self.data)
        self.score_uuid = self.wrapper.get_uuid_by_name('Score')
        self.col_index = 0 # 'Score' is at index 0

    def test_equal_width_apply(self):
        """Test standard Equal Width binning (now one-hot encoded)."""
        transform = BinningTransformation(self.col_index, "Equal Width", 2, true_label=1, false_label=0)
        self.wrapper = transform.apply(self.wrapper)

        # 1. Check Rename
        # Expected bins for 0-90 with 2 bins: (-0.09, 45.0] and (45.0, 90.0]
        # Column names should involve these intervals
        self.assertNotIn('Score', self.wrapper.df.columns)
        self.assertEqual(len(self.wrapper.df.columns), 2)
        
        # 2. Check Data
        # 0, 10, 20, 30, 40 -> Bin 1
        # 50, 60, 70, 80, 90 -> Bin 2
        
        # Identify columns dynamically since exact string might vary by system/version
        col1 = self.wrapper.df.iloc[:, 0]
        col2 = self.wrapper.df.iloc[:, 1]
        
        # They should be complementary
        self.assertEqual(col1.sum(), 5)
        self.assertEqual(col2.sum(), 5)
        
        # Row 0 (value 0) should be 1 in first col, 0 in second (or vice versa depending on sort)
        # pd.cut usually sorts bins
        
        self.assertEqual(self.wrapper.df.iloc[0].sum(), 1) # One-hot property

    def test_equal_frequency_apply(self):
        """Test Equal Frequency binning (pd.qcut)."""
        # Create skewed data: many 0s, few 100s
        data = pd.DataFrame({'Skewed': [0, 0, 0, 0, 100, 100, 100, 100]})
        wrapper = DataFrameWrapper(data)
        uuid = wrapper.get_uuid_by_name('Skewed')
        
        transform = BinningTransformation(0, "Equal Frequency", 2, true_label=1, false_label=0)
        wrapper = transform.apply(wrapper)

        # Should result in 2 buckets of 4 items each, across 2 columns
        self.assertEqual(len(wrapper.df.columns), 2)
        
        counts1 = wrapper.df.iloc[:, 0].sum()
        counts2 = wrapper.df.iloc[:, 1].sum()
        
        self.assertEqual(counts1, 4)
        self.assertEqual(counts2, 4)

    def test_ordinal_apply(self):
        """Test Ordinal binning (labels=False)."""
        transform = BinningTransformation(self.col_index, "Ordinal", 5)
        self.wrapper = transform.apply(self.wrapper)

        # Should result in multiple boolean/one-hot columns for distinct integer codes 0, 1, 2, 3, 4
        # Since data is perfect 0-90, we expect strict distribution
        
        # Check that we have multiple columns
        self.assertGreater(len(self.wrapper.df.columns), 1)
        
        # Check that columns contain boolean-like values (as per default true/false label)
        # We don't check for specific column names as they might be prefix_0, prefix_1, etc.
        first_col = self.wrapper.df.iloc[:, 0]
        self.assertIn(str(first_col.iloc[0]), ["True", "False", "1", "0"])

    def test_undo_restores_state(self):
        """Test that undo restores name and original float data."""
        original_data = self.wrapper.df['Score'].copy()
        
        transform = BinningTransformation(self.col_index, "Equal Width", 2)
        self.wrapper = transform.apply(self.wrapper)
        
        # Apply Undo
        self.wrapper = transform.undo(self.wrapper)
        
        # Verify Name
        self.assertIn('Score', self.wrapper.df.columns)
        self.assertNotIn('Score_binned', self.wrapper.df.columns)
        
        # Verify Data Equality
        pd.testing.assert_series_equal(self.wrapper.df['Score'], original_data)


class TestBinningIntegration(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({'A': [1, 5, 10]})
        self.wrapper = DataFrameWrapper(self.data)
        self.manager = TransformationManager(self.wrapper)

    def test_script_generation_equal_width(self):
        self.manager.add_binning(0, "Equal Width", 3)
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        self.assertIn("numeric_vals = pd.to_numeric(df['A'], errors='coerce')", script)
        self.assertIn("binned = pd.cut(numeric_vals, bins=3)", script)
        self.assertIn("df.drop(columns=['A'], inplace=True)", script)

    def test_script_generation_equal_frequency(self):
        self.manager.add_binning(0, "Equal Frequency", 4)
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        self.assertIn("binned = pd.qcut(numeric_vals, q=4, duplicates='drop')", script)

    def test_script_generation_ordinal(self):
        self.manager.add_binning(0, "Ordinal", 5)
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        self.assertIn("binned_codes = pd.cut(numeric_vals, bins=5, labels=False)", script)
        self.assertIn("(binned_codes >= i)", script)

    def test_complex_flow_rename_then_bin(self):
        """Test consistency when renaming BEFORE binning."""
        # 1. Rename 'A' -> 'Age'
        self.manager.add_rename(0, 'Age')
        
        # 2. Bin 'Age' (Index is still 0)
        self.manager.add_binning(0, "Equal Width", 2)
        
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        # Script should rename first
        self.assertIn("df.rename(columns={'A': 'Age'}, inplace=True)", script)
        
        # Then bin 'Age'
        self.assertIn("numeric_vals = pd.to_numeric(df['Age'], errors='coerce')", script)
        self.assertIn("binned = pd.cut(numeric_vals, bins=2)", script)
        self.assertIn("df.drop(columns=['Age'], inplace=True)", script)

if __name__ == "__main__":
    unittest.main()