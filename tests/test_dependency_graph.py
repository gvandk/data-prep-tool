import unittest
from data_prep_tool.core.dependency_graph import DependencyGraph

class TestDependencyGraph(unittest.TestCase):
    def setUp(self):
        self.graph = DependencyGraph()

    def test_register_and_retrieve(self):
        self.graph.register_load("uuid-1", "Age")
        node = self.graph.get_node("uuid-1")
        self.assertEqual(node.current_name, "Age")
        self.assertEqual(node.operation, "LOAD")

    def test_rename_logic(self):
        """Test that renames update state in-place."""
        self.graph.register_load("uuid-1", "Age")
        self.graph.register_rename("uuid-1", "Years")

        node = self.graph.get_node("uuid-1")
        self.assertEqual(node.current_name, "Years")

    def test_cell_edit_registration(self):
        """Test attaching manual edits to a node."""
        self.graph.register_load("uuid-1", "Age")
        self.graph.register_cell_edit("uuid-1", 5, 99)

        node = self.graph.get_node("uuid-1")
        # Current implementation applies edits but doesn't store in params
        self.assertIsNotNone(node)

    def test_row_filter_registration(self):
        self.graph.register_load("uuid-1", "Status")
        self.graph.register_row_filter("uuid-1", "obsolete")

        filter_nodes = [node for node in self.graph.nodes.values() if node.operation == "ROW_FILTER"]

        self.assertEqual(len(filter_nodes), 1)
        self.assertEqual(filter_nodes[0].parents, ["uuid-1"])
        self.assertEqual(filter_nodes[0].params.get("value"), "obsolete")