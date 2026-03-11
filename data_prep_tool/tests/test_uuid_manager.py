import pandas as pd
import sys
from core.col_uuid_manager import ColUUIDManager

def test_basic_initialization():
    print("Testing: Basic Initialization")
    df = pd.DataFrame({'Name': ['Alice'], 'Age': [25], 'City': ['NYC']})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    assert len(manager.uuid_to_name) == 3
    assert len(manager.name_to_uuid) == 3
    
    for col_name in df.columns:
        col_uuid = manager.get_uuid_by_name(col_name)
        assert col_uuid is not None
        assert manager.get_name_by_uuid(col_uuid) == col_name
    
    print("Basic initialization works\n")


def test_get_uuid_by_index():
    print("Testing: Get UUID by Index")
    df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    uuid_a = manager.get_uuid_by_index(df, 0)
    assert manager.get_name_by_uuid(uuid_a) == 'A'
    
    assert manager.get_uuid_by_index(df, -1) is None
    assert manager.get_uuid_by_index(df, 99) is None
    
    print("Get UUID by index works\n")


def test_rename_column():
    print("Testing: Column Rename")
    df = pd.DataFrame({'OldName': [1, 2, 3]})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    old_uuid = manager.get_uuid_by_name('OldName')
    manager.rename_column('OldName', 'NewName')
    
    assert manager.get_uuid_by_name('NewName') == old_uuid
    assert manager.get_name_by_uuid(old_uuid) == 'NewName'
    assert manager.get_uuid_by_name('OldName') is None
    
    print("Column rename works\n")


def test_add_child_columns():
    print("Testing: Add Child Columns")
    df = pd.DataFrame({'Color': ['Red', 'Blue']})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    parent_uuid = manager.get_uuid_by_name('Color')
    child_names = ['Color_Red', 'Color_Blue', 'Color_Green']
    manager.add_child_columns('Color', child_names)
    
    for child_name in child_names:
        child_uuid = manager.get_uuid_by_name(child_name)
        assert child_uuid is not None
        assert manager.get_parent_uuid(child_uuid) == parent_uuid
        assert manager.is_child(child_uuid)
    
    assert manager.is_parent(parent_uuid)
    assert len(manager.get_children_uuids(parent_uuid)) == 3
    assert set(manager.get_children_names(parent_uuid)) == set(child_names)
    
    print("Add child columns works\n")


def test_one_hot_encoding_workflow():
    print("Testing: One-Hot Encoding Workflow (Apply)")
    df = pd.DataFrame({'Color': ['Red', 'Blue']})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    parent_uuid = manager.get_uuid_by_name('Color')
    
    # Step 1: Add children
    child_names = ['Color_Red', 'Color_Blue']
    manager.add_child_columns('Color', child_names)
    
    # Step 2: Remove parent (becomes ghost)
    manager.remove_column(parent_uuid)
    
    # Verify ghost parent state
    assert manager.get_uuid_by_name('Color') is None, "Column name should be gone"
    assert manager.get_name_by_uuid(parent_uuid) is None, "Name should not resolve"
    assert manager.is_parent(parent_uuid), "Should still be a parent"
    assert len(manager.get_children_uuids(parent_uuid)) == 2, "Should still have children"
    
    # Verify children still know their parent
    child_uuid = manager.get_uuid_by_name('Color_Red')
    assert manager.get_parent_uuid(child_uuid) == parent_uuid
    
    # get_children_names should still work
    children_names = manager.get_children_names(parent_uuid)
    assert set(children_names) == set(child_names), "Should get children names even with ghost parent"
    
    print("One-hot encoding apply works\n")


def test_one_hot_encoding_undo():
    print("Testing: One-Hot Encoding Undo")
    df = pd.DataFrame({'Color': ['Red']})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    parent_uuid = manager.get_uuid_by_name('Color')
    
    # Apply encoding
    manager.add_child_columns('Color', ['Color_Red', 'Color_Blue'])
    
    manager.remove_column(parent_uuid)
    
    # Undo encoding
    manager.restore_parent(parent_uuid, 'Color')
    
    # Verify parent is restored
    result = manager.get_uuid_by_name('Color')
    assert result == parent_uuid, f"Expected {parent_uuid}, got {result}"
    
    result = manager.get_name_by_uuid(parent_uuid)
    assert result == 'Color', f"Expected 'Color', got {result}"
    
    # Verify children are removed
    result = manager.get_uuid_by_name('Color_Red')
    assert result is None, f"Color_Red should be None, got {result}"
    
    result = manager.get_uuid_by_name('Color_Blue')
    assert result is None, f"Color_Blue should be None, got {result}"
    
    # Verify parent is no longer a parent
    result = manager.is_parent(parent_uuid)
    assert not result, f"Should not be parent, is_parent returned {result}"
    
    print("One-hot encoding undo works\n")


def test_remove_child_column():
    print("Testing: Remove Child Column")
    df = pd.DataFrame({'Color': ['Red']})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    parent_uuid = manager.get_uuid_by_name('Color')
    manager.add_child_columns('Color', ['Color_Red', 'Color_Blue'])
    
    child_uuid = manager.get_uuid_by_name('Color_Red')
    manager.remove_column(child_uuid)
    
    assert manager.get_uuid_by_name('Color_Red') is None
    assert len(manager.get_children_uuids(parent_uuid)) == 1
    assert manager.get_children_names(parent_uuid) == ['Color_Blue']
    
    print("Remove child column works\n")


def test_add_children_to_nonexistent_parent():
    print("Testing: Add Children to Non-existent Parent")
    df = pd.DataFrame({'A': [1]})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    manager.add_child_columns('DoesNotExist', ['Child1', 'Child2'])
    
    assert manager.get_uuid_by_name('Child1') is None
    assert manager.get_uuid_by_name('Child2') is None
    
    print("Add children to non-existent parent handled gracefully\n")


def test_complex_multi_encoding():
    print("Testing: Complex Multi-Encoding Scenario")
    df = pd.DataFrame({
        'Name': ['Alice'],
        'Color': ['Red'],
        'Size': ['M']
    })
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    # Encode Color
    color_uuid = manager.get_uuid_by_name('Color')
    manager.add_child_columns('Color', ['Color_Red', 'Color_Blue'])
    manager.remove_column(color_uuid)
    
    # Encode Size
    size_uuid = manager.get_uuid_by_name('Size')
    manager.add_child_columns('Size', ['Size_S', 'Size_M', 'Size_L'])
    manager.remove_column(size_uuid)
    
    # Verify both are ghost parents
    assert manager.get_uuid_by_name('Color') is None
    assert manager.get_uuid_by_name('Size') is None
    assert manager.is_parent(color_uuid)
    assert manager.is_parent(size_uuid)
    
    # Verify children know their parents
    color_red_uuid = manager.get_uuid_by_name('Color_Red')
    size_m_uuid = manager.get_uuid_by_name('Size_M')
    assert manager.get_parent_uuid(color_red_uuid) == color_uuid
    assert manager.get_parent_uuid(size_m_uuid) == size_uuid
    
    # Undo one encoding
    manager.restore_parent(color_uuid, 'Color')
    
    # Color should be back, its children gone
    assert manager.get_uuid_by_name('Color') == color_uuid
    assert manager.get_uuid_by_name('Color_Red') is None
    
    # Size encoding should be unaffected
    assert manager.get_uuid_by_name('Size_M') is not None
    assert manager.is_parent(size_uuid)
    
    print("Complex multi-encoding works\n")


def test_restore_parent_nonexistent():
    print("Testing: Restore Non-existent Parent")
    df = pd.DataFrame({'A': [1]})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    fake_uuid = "fake-uuid-123"
    manager.restore_parent(fake_uuid, 'FakeColumn')
    
    # Should not crash, should be a no-op
    assert manager.get_uuid_by_name('FakeColumn') is None
    
    print("Restore non-existent parent handled gracefully\n")


def test_reinitialize():
    print("Testing: Reinitialization")
    df1 = pd.DataFrame({'A': [1], 'B': [2]})
    manager = ColUUIDManager()
    manager.initialize_from_df(df1)
    
    a_uuid = manager.get_uuid_by_name('A')
    
    df2 = pd.DataFrame({'C': [3], 'D': [4]})
    manager.initialize_from_df(df2)
    
    assert manager.get_uuid_by_name('A') is None
    assert manager.get_name_by_uuid(a_uuid) is None
    assert manager.get_uuid_by_name('C') is not None
    
    print("Reinitialization works\n")


def test_is_child_is_parent():
    print("Testing: is_child and is_parent helpers")
    df = pd.DataFrame({'Parent': [1]})
    manager = ColUUIDManager()
    manager.initialize_from_df(df)
    
    parent_uuid = manager.get_uuid_by_name('Parent')
    assert not manager.is_parent(parent_uuid), "Should not be parent initially"
    assert not manager.is_child(parent_uuid), "Should not be child"
    
    manager.add_child_columns('Parent', ['Child1'])
    child_uuid = manager.get_uuid_by_name('Child1')
    
    assert manager.is_parent(parent_uuid), "Should be parent now"
    assert manager.is_child(child_uuid), "Child should be marked as child"
    assert not manager.is_parent(child_uuid), "Child should not be parent"
    
    print("is_child and is_parent work\n")


def run_all_tests():
    print("=" * 60)
    print("Running ColUUIDManager Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        test_basic_initialization,
        test_get_uuid_by_index,
        test_rename_column,
        test_add_child_columns,
        test_one_hot_encoding_workflow,
        test_one_hot_encoding_undo,
        test_remove_child_column,
        test_add_children_to_nonexistent_parent,
        test_complex_multi_encoding,
        test_restore_parent_nonexistent,
        test_reinitialize,
        test_is_child_is_parent,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAILED: {test.__name__}")
            print(f"  Assertion error: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}")
            print(f"  Exception: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)