import unittest
import pandas as pd
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.core.script_generator import ScriptGenerator
from data_prep_tool.transformation.binning_transformation import BinningTransformation

class TestBinningTransformation(unittest.TestCase):
    def setUp(self):


        self.data = pd.DataFrame({'Score': [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]})
        self.wrapper = DataFrameWrapper(self.data)
        self.score_uuid = self.wrapper.get_uuid_by_name('Score')
        self.col_index = 0

    def test_equal_width_apply(self):
        """Test standard Equal Width binning (now one-hot encoded)."""
        transform = BinningTransformation(self.col_index, "Equal Width", 2, true_label=1, false_label=0)
        self.wrapper = transform.apply(self.wrapper)




        self.assertNotIn('Score', self.wrapper.df.columns)
        self.assertEqual(len(self.wrapper.df.columns), 2)






        col1 = self.wrapper.df.iloc[:, 0]
        col2 = self.wrapper.df.iloc[:, 1]


        self.assertEqual(col1.sum(), 5)
        self.assertEqual(col2.sum(), 5)




        self.assertEqual(self.wrapper.df.iloc[0].sum(), 1)

    def test_equal_frequency_apply(self):
        """Test Equal Frequency binning (pd.qcut)."""

        data = pd.DataFrame({'Skewed': [0, 0, 0, 0, 100, 100, 100, 100]})
        wrapper = DataFrameWrapper(data)
        uuid = wrapper.get_uuid_by_name('Skewed')

        transform = BinningTransformation(0, "Equal Frequency", 2, true_label=1, false_label=0)
        wrapper = transform.apply(wrapper)


        self.assertEqual(len(wrapper.df.columns), 2)

        counts1 = wrapper.df.iloc[:, 0].sum()
        counts2 = wrapper.df.iloc[:, 1].sum()

        self.assertEqual(counts1, 4)
        self.assertEqual(counts2, 4)

    def test_ordinal_apply(self):
        """Test Ordinal binning (labels=False)."""
        transform = BinningTransformation(self.col_index, "Ordinal", 5)
        self.wrapper = transform.apply(self.wrapper)





        self.assertGreater(len(self.wrapper.df.columns), 1)



        first_col = self.wrapper.df.iloc[:, 0]
        self.assertIn(str(first_col.iloc[0]), ["True", "False", "1", "0"])

    def test_undo_restores_state(self):
        """Test that undo restores name and original float data."""
        original_data = self.wrapper.df['Score'].copy()

        transform = BinningTransformation(self.col_index, "Equal Width", 2)
        self.wrapper = transform.apply(self.wrapper)


        self.wrapper = transform.undo(self.wrapper)


        self.assertIn('Score', self.wrapper.df.columns)
        self.assertNotIn('Score_binned', self.wrapper.df.columns)


        pd.testing.assert_series_equal(self.wrapper.df['Score'], original_data)

    def test_undo_restores_original_column_position(self):
        """Undo should place restored parent column back at its original index."""
        data = pd.DataFrame({
            'A': [1, 2, 3],
            'Score': [10, 20, 30],
            'B': [100, 200, 300]
        })
        wrapper = DataFrameWrapper(data)
        transform = BinningTransformation(1, "Equal Width", 2)

        wrapper = transform.apply(wrapper)
        wrapper = transform.undo(wrapper)

        self.assertEqual(list(wrapper.df.columns), ['A', 'Score', 'B'])


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

        self.manager.add_rename(0, 'Age')


        self.manager.add_binning(0, "Equal Width", 2)

        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()


        self.assertIn("df.rename(columns={'A': 'Age'}, inplace=True)", script)


        self.assertIn("numeric_vals = pd.to_numeric(df['Age'], errors='coerce')", script)
        self.assertIn("binned = pd.cut(numeric_vals, bins=2)", script)
        self.assertIn("df.drop(columns=['Age'], inplace=True)", script)

if __name__ == "__main__":
    unittest.main()