import pandas as pd
import sys
from core.dataframe_wrapper import DataFrameWrapper
from transformation.col_rename_transformation import ColumnRenameTransformation
from transformation.one_hot_encode import oneHotEncodeTransformation

def test_onehot_basic_apply():
    print("Testing: One-Hot Encoding Basic Apply")
    
    df = pd.DataFrame({
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Color': ['Red', 'Blue', 'Red']
    })
    wrapper = DataFrameWrapper(df)
    
    transform = oneHotEncodeTransformation(col_index=1)
    wrapper = transform.apply(wrapper)
    
    # Check parent removed
    assert 'Color' not in wrapper.df.columns, "Parent column 'Color' should be removed after one-hot encoding."
    
    # Check children created
    assert 'Color_Red' in wrapper.df.columns, "Child column 'Color_Red' should be created after one-hot encoding."
    assert 'Color_Blue' in wrapper.df.columns, "Child column 'Color_Blue' should be created after one-hot encoding."
    
    # Check values correct
    assert list(wrapper.df['Color_Red']) == [1, 0, 1], "Values in 'Color_Red' column are incorrect."
    assert list(wrapper.df['Color_Blue']) == [0, 1, 0], "Values in 'Color_Blue' column are incorrect."
    
    # Check column order: Name, Color_Red, Color_Blue
    assert list(wrapper.df.columns) == ['Name', 'Color_Red', 'Color_Blue'], "Column order is incorrect after one-hot encoding.{}".format(list(wrapper.df.columns))
    
    print("One-hot basic apply works\n")


def test_onehot_position_preservation():
    print("Testing: One-Hot Encoding Position Preservation")
    
    df = pd.DataFrame({
        'A': [1, 2],
        'B': [3, 4],
        'Category': ['X', 'Y'],
        'C': [5, 6],
        'D': [7, 8]
    })
    wrapper = DataFrameWrapper(df)
    
    transform = oneHotEncodeTransformation(col_index=2)  # Category
    wrapper = transform.apply(wrapper)
    
    # Children should be inserted where Category was
    expected_order = ['A', 'B', 'Category_X', 'Category_Y', 'C', 'D']
    assert list(wrapper.df.columns) == expected_order, f"Column order is incorrect after one-hot encoding. Expected {expected_order}, got {list(wrapper.df.columns)}"
    
    print("One-hot position preservation works\n")


def test_onehot_undo():
    print("Testing: One-Hot Encoding Undo")
    
    df = pd.DataFrame({
        'Name': ['Alice', 'Bob'],
        'Color': ['Red', 'Blue']
    })
    wrapper = DataFrameWrapper(df)
    
    transform = oneHotEncodeTransformation(col_index=1)
    wrapper = transform.apply(wrapper)
    
    # Undo
    wrapper = transform.undo(wrapper)
    
    # Check parent restored
    assert 'Color' in wrapper.df.columns
    assert list(wrapper.df['Color']) == ['Red', 'Blue']
    
    # Check children removed
    assert 'Color_Red' not in wrapper.df.columns
    assert 'Color_Blue' not in wrapper.df.columns
    
    # Check order: Name, Color
    assert list(wrapper.df.columns) == ['Name', 'Color']
    
    print("One-hot undo works\n")


def test_onehot_undo_position():
    print("Testing: One-Hot Encoding Undo Position")
    
    df = pd.DataFrame({
        'A': [1],
        'B': [2],
        'Cat': ['X'],
        'C': [3]
    })
    wrapper = DataFrameWrapper(df)
    
    transform = oneHotEncodeTransformation(col_index=2)
    wrapper = transform.apply(wrapper)
    
    # After apply: A, B, Cat_X, C
    assert list(wrapper.df.columns) == ['A', 'B', 'Cat_X', 'C']
    
    # Undo
    wrapper = transform.undo(wrapper)
    
    # Parent should be at first child's position
    assert list(wrapper.df.columns) == ['A', 'B', 'Cat', 'C']
    
    print("One-hot undo position works\n")


def test_onehot_multiple_categories():
    print("Testing: One-Hot Encoding Multiple Categories")
    
    df = pd.DataFrame({
        'Size': ['S', 'M', 'L', 'M', 'S']
    })
    wrapper = DataFrameWrapper(df)
    
    transform = oneHotEncodeTransformation(col_index=0)
    wrapper = transform.apply(wrapper)
    
    # Check all categories created
    assert 'Size_S' in wrapper.df.columns
    assert 'Size_M' in wrapper.df.columns
    assert 'Size_L' in wrapper.df.columns
    
    # Check values
    assert list(wrapper.df['Size_S']) == [1, 0, 0, 0, 1]
    assert list(wrapper.df['Size_M']) == [0, 1, 0, 1, 0]
    assert list(wrapper.df['Size_L']) == [0, 0, 1, 0, 0]
    
    print("One-hot multiple categories works\n")


def test_onehot_apply_undo_apply():
    print("Testing: One-Hot Apply → Undo → Apply Again")
    
    df = pd.DataFrame({'X': ['A', 'B', 'A']})
    wrapper = DataFrameWrapper(df)
    
    transform = oneHotEncodeTransformation(col_index=0)
    
    # Apply
    wrapper = transform.apply(wrapper)
    assert 'X_A' in wrapper.df.columns
    
    # Undo
    wrapper = transform.undo(wrapper)
    assert 'X' in wrapper.df.columns
    
    # Apply again
    transform2 = oneHotEncodeTransformation(col_index=0)
    wrapper = transform2.apply(wrapper)
    assert 'X_A' in wrapper.df.columns
    assert 'X' not in wrapper.df.columns
    
    print("One-hot apply-undo-apply works\n")


def test_rename_basic():
    print("Testing: Column Rename Basic")
    
    df = pd.DataFrame({
        'old_name': [1, 2, 3],
        'other': [4, 5, 6]
    })
    wrapper = DataFrameWrapper(df)
    
    transform = ColumnRenameTransformation(col_index=0, new_name='new_name')
    wrapper = transform.apply(wrapper)
    
    # Check renamed
    assert 'new_name' in wrapper.df.columns
    assert 'old_name' not in wrapper.df.columns
    assert list(wrapper.df['new_name']) == [1, 2, 3]
    
    print("Column rename basic works\n")


def test_rename_undo():
    print("Testing: Column Rename Undo")
    
    df = pd.DataFrame({'original': [10, 20]})
    wrapper = DataFrameWrapper(df)
    
    transform = ColumnRenameTransformation(col_index=0, new_name='changed')
    wrapper = transform.apply(wrapper)
    
    assert 'changed' in wrapper.df.columns
    
    # Undo
    wrapper = transform.undo(wrapper)
    
    assert 'original' in wrapper.df.columns
    assert 'changed' not in wrapper.df.columns
    
    print("Column rename undo works\n")


def test_rename_preserves_position():
    print("Testing: Column Rename Preserves Position")
    
    df = pd.DataFrame({
        'A': [1],
        'B': [2],
        'C': [3]
    })
    wrapper = DataFrameWrapper(df)
    
    transform = ColumnRenameTransformation(col_index=1, new_name='B_renamed')
    wrapper = transform.apply(wrapper)
    
    # Order should be preserved
    assert list(wrapper.df.columns) == ['A', 'B_renamed', 'C']
    
    print("Column rename preserves position\n")


def test_rename_multiple_sequential():
    print("Testing: Multiple Sequential Renames")
    
    df = pd.DataFrame({'col': [1, 2]})
    wrapper = DataFrameWrapper(df)
    
    transform1 = ColumnRenameTransformation(col_index=0, new_name='step1')
    wrapper = transform1.apply(wrapper)
    assert 'step1' in wrapper.df.columns
    
    transform2 = ColumnRenameTransformation(col_index=0, new_name='step2')
    wrapper = transform2.apply(wrapper)
    assert 'step2' in wrapper.df.columns
    
    transform3 = ColumnRenameTransformation(col_index=0, new_name='final')
    wrapper = transform3.apply(wrapper)
    assert 'final' in wrapper.df.columns
    
    print("Multiple sequential renames work\n")


def test_combined_rename_and_onehot():
    print("Testing: Combined Rename and One-Hot")
    
    df = pd.DataFrame({
        'id': [1, 2],
        'type': ['A', 'B']
    })
    wrapper = DataFrameWrapper(df)
    
    # Rename first
    rename_transform = ColumnRenameTransformation(col_index=1, new_name='category')
    wrapper = rename_transform.apply(wrapper)
    
    # Then one-hot
    onehot_transform = oneHotEncodeTransformation(col_index=1)
    wrapper = onehot_transform.apply(wrapper)
    
    # Check result
    assert 'category_A' in wrapper.df.columns
    assert 'category_B' in wrapper.df.columns
    assert 'category' not in wrapper.df.columns
    
    # Undo one-hot
    wrapper = onehot_transform.undo(wrapper)
    assert 'category' in wrapper.df.columns
    
    # Undo rename
    wrapper = rename_transform.undo(wrapper)
    assert 'type' in wrapper.df.columns
    
    print("Combined rename and one-hot works\n")


def test_onehot_to_script():
    print("Testing: One-Hot to_script")
    
    df = pd.DataFrame({'Color': ['Red', 'Blue']})
    wrapper = DataFrameWrapper(df)
    
    transform = oneHotEncodeTransformation(col_index=0)
    wrapper = transform.apply(wrapper)
    
    script = transform.to_script()
    
    assert 'Color' in script
    assert 'get_dummies' in script
    assert 'pd.concat' in script
    
    print("One-hot to_script works\n")


def test_edge_case_single_value():
    print("Testing: One-Hot with Single Unique Value")
    
    df = pd.DataFrame({'Same': ['X', 'X', 'X']})
    wrapper = DataFrameWrapper(df)
    
    transform = oneHotEncodeTransformation(col_index=0)
    wrapper = transform.apply(wrapper)
    
    # Should create only one dummy column
    assert 'Same_X' in wrapper.df.columns
    assert len(wrapper.df.columns) == 1
    
    print("One-hot single value works\n")


def run_all_tests():
    print("=" * 60)
    print("Running Transformation Test Suite")
    print("=" * 60 + "\n")
    
    tests = [
        test_onehot_basic_apply,
        test_onehot_position_preservation,
        test_onehot_undo,
        test_onehot_undo_position,
        test_onehot_multiple_categories,
        test_onehot_apply_undo_apply,
        test_rename_basic,
        test_rename_undo,
        test_rename_preserves_position,
        test_rename_multiple_sequential,
        test_combined_rename_and_onehot,
        test_onehot_to_script,
        test_edge_case_single_value,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAILED: {test.__name__}")
            print(f"  AssertionError: {e}")
            import traceback
            traceback.print_exc()
            print()
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}")
            print(f"  Exception: {e}")
            import traceback
            traceback.print_exc()
            print()
            failed += 1
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)