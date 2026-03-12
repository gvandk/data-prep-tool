import unittest
import pandas as pd
from unittest.mock import MagicMock, patch

from core.dependency_graph import DependencyGraph
from core.script_generator import ScriptGenerator
from core.transformation_manager import TransformationManager
from core.dataframe_wrapper import DataFrameWrapper
from transformation.col_rename_transformation import ColumnRenameTransformation
from transformation.one_hot_encode import oneHotEncodeTransformation

class TestDependencyGraph(unittest.TestCase):
    def setUp(self):
        self.graph = DependencyGraph()

    def test_rename_optimization(self):
        """Test that multiple renames are merged into one state."""
        uuid = "uuid-1"
        self.graph.register_load(uuid, "OriginalName")
        
        # User renames "OriginalName" -> "TempName" -> "FinalName"
        self.graph.register_rename(uuid, "TempName")
        self.graph.register_rename(uuid, "FinalName")
        
        node = self.graph.nodes[uuid]
        self.assertEqual(node.current_name, "FinalName")
        self.assertEqual(node.operation, "LOAD") # Op type shouldn't change

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
        
        # Verify children exist
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
        
        self.assertIn("df = pd.read_csv('data.csv')", script)
        self.assertIn("df = df[['Age']]", script)

    def test_rename_script_generation(self):
        """Test that script generates the specific rename line."""
        self.graph.register_load("u1", "Age")
        self.graph.register_rename("u1", "Years")
        
        script = self.generator.generate_script()
        
        # Should contain rename logic
        self.assertIn("df.rename(columns={'Age': 'Years'}", script)
        # Should select final name
        self.assertIn("df = df[['Years']]", script)

    def test_one_hot_script_optimization(self):
        """Test that get_dummies is called ONCE for the group, not per child."""
        self.graph.register_load("p1", "Color")
        self.graph.register_one_hot("p1", ["c1", "c2"], ["Color_A", "Color_B"], prefix="Color")
        self.graph.mark_deleted("p1") # Parent is usually consumed
        
        script = self.generator.generate_script()
        
        # Check that get_dummies appears
        self.assertIn("pd.get_dummies", script)
        
        # Check that it appears only ONCE
        # (count should be 1)
        self.assertEqual(script.count("pd.get_dummies"), 1)


class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Create a real DataFrameWrapper with dummy data
        df = pd.DataFrame({'A': [1, 2], 'B': ['x', 'y']})
        self.wrapper = DataFrameWrapper(df)
        self.manager = TransformationManager(self.wrapper)

    def test_build_graph_from_history(self):
        """
        Verify that replaying history correctly builds the graph.
        We simulate a history of: Rename A->Alpha, then OneHot B.
        """
        # 1. Simulate Rename
        # Get UUID for 'A'
        uuid_a = self.wrapper.get_uuid_by_name('A')
        self.manager.add_rename(0, 'Alpha') # Rename 'A' at index 0
        
        # 2. Simulate OneHot
        # Get UUID for 'B' (now at index 1 because A is Alpha)
        # Note: OneHotTransform needs to have the 'child_uuids' fix we discussed!
        # For this test to pass, we assume you added 'self.child_uuids = ...' in one_hot_encode.py
        # If not, we manually inject it here to test the MANAGER logic, not the TRANSFORM logic.
        
        # Create the transform manually to inject the attribute if needed for test safety
        oh_transform = oneHotEncodeTransformation(1)
        
        # Apply it so wrapper updates
        self.wrapper = oh_transform.apply(self.wrapper)
        
        # MOCK the attribute usually set in apply() if your file isn't updated yet
        if not hasattr(oh_transform, 'child_uuids'):
             # Determine what children were created
             parent_uuid = oh_transform.col_uuid
             oh_transform.child_uuids = self.wrapper.get_children_uuids(parent_uuid)
             
        # Add to history manually (since we did apply manually)
        self.manager.history.append(oh_transform)

        # 3. BUILD GRAPH
        graph = self.manager.build_dependency_graph()
        
        # 4. Assertions
        # Check Rename
        node_a = graph.nodes[uuid_a]
        self.assertEqual(node_a.current_name, 'Alpha')
        
        # Check OneHot
        # The parent 'B' should be marked deleted
        # We need to find the UUID for original 'B'
        # Since 'B' is consumed, we can't find it by name in wrapper easily, 
        # but we can look at the graph nodes.
        
        # There should be children nodes
        active_nodes = graph.get_active_nodes()
        active_names = [n.current_name for n in active_nodes]
        
        self.assertIn('Alpha', active_names)
        self.assertTrue(any("B_" in name for name in active_names)) # Assuming prefix 'B_'
# ... existing imports ...

class TestAdvancedScenarios(unittest.TestCase):
    def setUp(self):
        # Setup wrapper with two columns 'A' and 'B'
        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        self.wrapper = DataFrameWrapper(df)
        self.manager = TransformationManager(self.wrapper)

    def test_undo_consistency(self):
        """
        Verify that undoing an action removes it completely from the exported graph.
        """
        # 1. Apply a Rename: A -> Alpha
        self.manager.add_rename(0, 'Alpha')
        
        # 2. Apply OneHot: B -> B_1, B_2...
        self.manager.add_onehot(1)
        
        # 3. UNDO the OneHot
        self.manager.undo_transformation()
        
        # 4. Build Graph
        graph = self.manager.build_dependency_graph()
        script = ScriptGenerator(graph).generate_script()
        
        # ASSERTIONS
        # The script should contain the rename
        self.assertIn("'A': 'Alpha'", script)
        
        # The script should NOT contain get_dummies
        self.assertNotIn("pd.get_dummies", script)
        
        # The OneHot should effectively be erased from history
        active_names = [n.current_name for n in graph.get_active_nodes()]
        self.assertIn('Alpha', active_names)
        self.assertIn('B', active_names) # B should be back

    def test_column_swap_shell_game(self):
        """
        Test swapping column names: A -> Temp, B -> A, Temp -> B.
        The UUIDs should track the data, not the names.
        """
        # UUIDs at start
        uuid_a = self.wrapper.get_uuid_by_name('A')
        uuid_b = self.wrapper.get_uuid_by_name('B')
        
        # 1. Rename A -> Temp
        idx_a = self.wrapper.df.columns.get_loc('A')
        self.manager.add_rename(idx_a, 'Temp')
        
        # 2. Rename B -> A
        idx_b = self.wrapper.df.columns.get_loc('B')
        self.manager.add_rename(idx_b, 'A')
        
        # 3. Rename Temp -> B
        idx_temp = self.wrapper.df.columns.get_loc('Temp')
        self.manager.add_rename(idx_temp, 'B')
        
        # 4. Build Graph
        graph = self.manager.build_dependency_graph()
        
        # ASSERTIONS
        # The node that WAS 'A' (uuid_a) should now be named 'B'
        self.assertEqual(graph.nodes[uuid_a].current_name, 'B')
        
        # The node that WAS 'B' (uuid_b) should now be named 'A'
        self.assertEqual(graph.nodes[uuid_b].current_name, 'A')
        
        # The script should generate valid rename logic
        script = ScriptGenerator(graph).generate_script()
        
        # Since we optimize renames in-place, the script might look simplistic 
        # (just renaming original source 'A' to final 'B'), which is valid!
        # It shouldn't generate 3 rename steps, just the mapping from start to end.
        self.assertIn("'A': 'B'", script)
        self.assertIn("'B': 'A'", script)

if __name__ == '__main__':
    unittest.main()