import unittest
import pandas as pd
from core.dataframe_wrapper import DataFrameWrapper
from core.transformation_manager import TransformationManager
from core.script_generator import ScriptGenerator

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