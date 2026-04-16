import unittest
import pandas as pd

from data_prep_tool.core.dependency_graph import DependencyGraph
from data_prep_tool.core.script_generator import ScriptGenerator
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.transformation.one_hot_encode import oneHotEncodeTransformation

class TestDependencyGraph(unittest.TestCase):
    def setUp(self):
        self.graph = DependencyGraph()

    def test_rename_optimization(self):
        """Test that multiple renames are merged into one state."""
        uuid = "uuid-1"
        self.graph.register_load(uuid, "OriginalName")


        self.graph.register_rename(uuid, "TempName")
        self.graph.register_rename(uuid, "FinalName")

        node = self.graph.nodes[uuid]
        self.assertEqual(node.current_name, "FinalName")
        self.assertEqual(node.operation, "LOAD")

    def test_soft_delete(self):
        """Test that deleted nodes are marked but not removed."""
        uuid = "uuid-1"
        self.graph.register_load(uuid, "ColA")
        self.graph.mark_deleted(uuid)

        active = self.graph.get_active_nodes()
        self.assertEqual(len(active), 0)
        self.assertTrue(self.graph.nodes[uuid].is_deleted)

    def test_one_hot_registration(self):
        """Test registering a one-hot splits 1 parent into N children."""
        parent_uuid = "p-1"
        child_uuids = ["c-1", "c-2"]
        child_names = ["Color_Red", "Color_Blue"]

        self.graph.register_load(parent_uuid, "Color")
        self.graph.register_one_hot(parent_uuid, child_uuids, child_names, prefix="Color")


        self.assertIn("c-1", self.graph.nodes)
        self.assertIn("c-2", self.graph.nodes)
        self.assertEqual(self.graph.nodes["c-1"].parents, ["p-1"])


class TestScriptGenerator(unittest.TestCase):
    def setUp(self):
        self.graph = DependencyGraph()
        self.generator = ScriptGenerator(self.graph)

    def test_simple_load_script(self):
        """Test script for just loading data."""
        self.graph.register_load("u1", "Age")
        script = self.generator.generate_script()

        self.assertIn("df = pd.read_csv(sys.stdin)", script)
        self.assertIn("df = pd.read_csv(input_arg)", script)
        self.assertIn("df[['Age']]", script)

    def test_rename_script_generation(self):
        """Test that script generates the specific rename line."""
        self.graph.register_load("u1", "Age")
        self.graph.register_rename("u1", "Years")

        script = self.generator.generate_script()


        self.assertIn("df.rename(columns={'Age': 'Years'}", script)

        self.assertIn("df = df[['Years']]", script)

    def test_one_hot_script_optimization(self):
        """Test that get_dummies is called ONCE for the group, not per child."""
        self.graph.register_load("p1", "Color")
        self.graph.register_one_hot("p1", ["c1", "c2"], ["Color_A", "Color_B"], prefix="Color")
        self.graph.mark_deleted("p1")

        script = self.generator.generate_script()


        self.assertIn("pd.get_dummies", script)



        self.assertEqual(script.count("pd.get_dummies"), 1)


class TestIntegration(unittest.TestCase):
    def setUp(self):

        df = pd.DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        self.wrapper = DataFrameWrapper(df)
        self.manager = TransformationManager(self.wrapper)

    def test_build_graph_from_history(self):
        """
        Verify that replaying history correctly builds the graph.
        We simulate a history of: Rename A->Alpha, then OneHot B.
        """


        uuid_a = self.wrapper.get_uuid_by_name('A')
        self.manager.add_rename(uuid_a, 'Alpha')








        oh_transform = oneHotEncodeTransformation(1)


        self.wrapper = oh_transform.apply(self.wrapper)


        if not hasattr(oh_transform, 'child_uuids'):

             parent_uuid = oh_transform.col_uuid
             oh_transform.child_uuids = self.wrapper.get_children_uuids(parent_uuid)


        self.manager.history.append(oh_transform)


        graph = self.manager.build_dependency_graph()



        node_a = graph.nodes[uuid_a]
        self.assertEqual(node_a.current_name, 'Alpha')








        active_nodes = graph.get_active_nodes()
        active_names = [n.current_name for n in active_nodes]

        self.assertIn('Alpha', active_names)
        self.assertTrue(any("B_" in name for name in active_names))


class TestAdvancedScenarios(unittest.TestCase):
    def setUp(self):

        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        self.wrapper = DataFrameWrapper(df)
        self.manager = TransformationManager(self.wrapper)

    def test_undo_consistency(self):
        """
        Verify that undoing an action removes it completely from the exported graph.
        """
        uuid_a = self.wrapper.get_uuid_by_name('A')

        self.manager.add_rename(uuid_a, 'Alpha')


        self.manager.add_onehot(1)


        self.manager.undo_transformation()


        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()



        self.assertIn("'A': 'Alpha'", script)


        self.assertNotIn("pd.get_dummies", script)


        active_names = [n.current_name for n in graph.get_active_nodes()]
        self.assertIn('Alpha', active_names)
        self.assertIn('B', active_names)

    def test_column_swap_shell_game(self):
        """
        Test swapping column names: A -> Temp, B -> A, Temp -> B.
        The UUIDs should track the data, not the names.
        """

        uuid_a = self.wrapper.get_uuid_by_name('A')
        uuid_b = self.wrapper.get_uuid_by_name('B')

        self.manager.add_rename(uuid_a, 'Temp')
        self.manager.add_rename(uuid_b, 'A')
        self.manager.add_rename(uuid_a, 'B')


        graph = self.manager.build_dependency_graph()



        self.assertEqual(graph.nodes[uuid_a].current_name, 'B')


        self.assertEqual(graph.nodes[uuid_b].current_name, 'A')


        script = ScriptGenerator(graph).generate_script()




        self.assertIn("'A': 'B'", script)
        self.assertIn("'B': 'A'", script)

if __name__ == '__main__':
    unittest.main()