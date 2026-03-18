import pandas as pd
import sys
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper

def test_basic_initialization():
    print("Testing: Basic Initialization")

    df = pd.DataFrame({
        'Name': ['Alice', 'Bob'],
        'Age': [25, 30],
        'City': ['NYC', 'LA']
    })

    wrapper = DataFrameWrapper(df)


    assert wrapper.df is not None
    assert len(wrapper.df.columns) == 3
    assert list(wrapper.df.columns) == ['Name', 'Age', 'City']


    for col in df.columns:
        uuid = wrapper.get_uuid_by_name(col)
        assert uuid is not None, f"UUID for {col} should exist"
        assert wrapper.get_col_name_by_uuid(uuid) == col

    print("Basic initialization works\n")


def test_initialization_with_none():
    print("Testing: Initialization with None")

    wrapper = DataFrameWrapper(None)

    assert wrapper.df is None
    assert wrapper.uuid_manager is not None

    print("Initialization with None works\n")


def test_get_uuid_by_index():
    print("Testing: Get UUID by Index")

    df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
    wrapper = DataFrameWrapper(df)

    uuid_a = wrapper.get_uuid_by_index(0)
    uuid_b = wrapper.get_uuid_by_index(1)
    uuid_c = wrapper.get_uuid_by_index(2)

    assert wrapper.get_col_name_by_uuid(uuid_a) == 'A'
    assert wrapper.get_col_name_by_uuid(uuid_b) == 'B'
    assert wrapper.get_col_name_by_uuid(uuid_c) == 'C'


    assert wrapper.get_uuid_by_index(-1) is None
    assert wrapper.get_uuid_by_index(99) is None

    print("Get UUID by index works\n")


def test_get_col_data_by_uuid():
    print("Testing: Get Column Data by UUID")

    df = pd.DataFrame({
        'Numbers': [1, 2, 3],
        'Letters': ['a', 'b', 'c']
    })
    wrapper = DataFrameWrapper(df)

    numbers_uuid = wrapper.get_uuid_by_name('Numbers')
    data = wrapper.get_col_data_by_uuid(numbers_uuid)

    assert data is not None
    assert list(data) == [1, 2, 3]


    fake_data = wrapper.get_col_data_by_uuid('fake-uuid-123')
    assert fake_data is None

    print("Get column data by UUID works\n")


def test_rename_column():
    print("Testing: Rename Column")

    df = pd.DataFrame({'OldName': [1, 2, 3]})
    wrapper = DataFrameWrapper(df)

    old_uuid = wrapper.get_uuid_by_name('OldName')


    wrapper.rename_column(old_uuid, 'NewName')


    assert 'NewName' in wrapper.df.columns
    assert 'OldName' not in wrapper.df.columns


    assert wrapper.get_col_name_by_uuid(old_uuid) == 'NewName'
    assert wrapper.get_uuid_by_name('NewName') == old_uuid
    assert wrapper.get_uuid_by_name('OldName') is None

    print("Rename column works\n")


def test_add_columns():
    print("Testing: Add Columns")

    df = pd.DataFrame({'A': [1, 2]})
    wrapper = DataFrameWrapper(df)


    wrapper.add_columns({
        'B': [3, 4],
        'C': [5, 6]
    })


    assert 'B' in wrapper.df.columns
    assert 'C' in wrapper.df.columns
    assert list(wrapper.df['B']) == [3, 4]
    assert list(wrapper.df['C']) == [5, 6]


    uuid_b = wrapper.get_uuid_by_name('B')
    uuid_c = wrapper.get_uuid_by_name('C')
    assert uuid_b is not None
    assert uuid_c is not None

    print("Add columns works\n")


def test_add_columns_with_duplicate_name():
    print("Testing: Add Columns with Duplicate Name (Should Fail)")

    df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    wrapper = DataFrameWrapper(df)


    try:
        wrapper.add_columns({'B': [5, 6], 'C': [7, 8]})
        assert False, "Expected ValueError when adding column with duplicate name"
    except ValueError as e:
        assert "already exist" in str(e)

        assert 'C' not in wrapper.df.columns
        assert list(wrapper.df['B']) == [3, 4]

    print("Add columns with duplicate name correctly throws error\n")


def test_add_columns_independent_data():
    print("Testing: Add Columns Have Independent Data")

    df = pd.DataFrame({'A': [1, 2, 3]})
    wrapper = DataFrameWrapper(df)


    shared_data = [10, 20, 30]
    wrapper.add_columns({'B': shared_data, 'C': shared_data})


    wrapper.df.loc[0, 'B'] = 100


    assert wrapper.df.loc[0, 'B'] == 100
    assert wrapper.df.loc[0, 'C'] == 10

    print("Columns have independent data\n")


def test_remove_column():
    print("Testing: Remove Column")

    df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
    wrapper = DataFrameWrapper(df)

    uuid_b = wrapper.get_uuid_by_name('B')
    wrapper.remove_column(uuid_b)


    assert 'B' not in wrapper.df.columns
    assert 'A' in wrapper.df.columns
    assert 'C' in wrapper.df.columns


    assert wrapper.get_uuid_by_name('B') is None
    assert wrapper.get_col_name_by_uuid(uuid_b) is None

    print("Remove column works\n")


def test_add_child_columns():
    print("Testing: Add Child Columns")

    df = pd.DataFrame({'Color': ['Red', 'Blue', 'Red']})
    wrapper = DataFrameWrapper(df)

    parent_uuid = wrapper.get_uuid_by_name('Color')


    wrapper.add_child_columns(parent_uuid, {
        'Color_Red': [1, 0, 1],
        'Color_Blue': [0, 1, 0]
    })


    assert 'Color_Red' in wrapper.df.columns
    assert 'Color_Blue' in wrapper.df.columns


    child_uuids = wrapper.get_children_uuids(parent_uuid)
    assert len(child_uuids) == 2

    for child_uuid in child_uuids:
        assert wrapper.get_parent_uuid(child_uuid) == parent_uuid

    print("Add child columns works\n")


def test_get_parent_and_children():
    print("Testing: Get Parent and Children")

    df = pd.DataFrame({'Parent': [1, 2]})
    wrapper = DataFrameWrapper(df)

    parent_uuid = wrapper.get_uuid_by_name('Parent')


    assert wrapper.get_children_uuids(parent_uuid) is None


    wrapper.add_child_columns(parent_uuid, {
        'Child1': [3, 4],
        'Child2': [5, 6]
    })


    child_uuids = wrapper.get_children_uuids(parent_uuid)
    assert child_uuids is not None
    assert len(child_uuids) == 2


    child1_uuid = wrapper.get_uuid_by_name('Child1')
    assert wrapper.get_parent_uuid(child1_uuid) == parent_uuid

    print("Get parent and children works\n")


def test_restore_parent():
    print("Testing: Restore Parent")

    df = pd.DataFrame({'Color': ['Red', 'Blue', 'Green']})
    wrapper = DataFrameWrapper(df)

    parent_uuid = wrapper.get_uuid_by_name('Color')
    original_data = wrapper.df['Color'].copy()


    wrapper.add_child_columns(parent_uuid, {
        'Color_Red': [1, 0, 0],
        'Color_Blue': [0, 1, 0],
        'Color_Green': [0, 0, 1]
    })
    wrapper.remove_column(parent_uuid)


    assert 'Color' not in wrapper.df.columns
    assert wrapper.get_uuid_by_name('Color') is None
    assert 'Color_Red' in wrapper.df.columns


    wrapper.restore_parent(parent_uuid, 'Color', original_data)


    assert 'Color' in wrapper.df.columns
    assert list(wrapper.df['Color']) == list(original_data)
    assert wrapper.get_uuid_by_name('Color') == parent_uuid


    assert 'Color_Red' not in wrapper.df.columns
    assert 'Color_Blue' not in wrapper.df.columns
    assert 'Color_Green' not in wrapper.df.columns

    print("Restore parent works\n")


def test_get_all_uuids():
    print("Testing: Get All UUIDs in Order")

    df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
    wrapper = DataFrameWrapper(df)

    all_uuids = wrapper.get_all_uuids()


    assert len(all_uuids) == 3


    assert wrapper.get_col_name_by_uuid(all_uuids[0]) == 'A'
    assert wrapper.get_col_name_by_uuid(all_uuids[1]) == 'B'
    assert wrapper.get_col_name_by_uuid(all_uuids[2]) == 'C'

    print("Get all UUIDs works\n")


def test_reorder_columns():
    print("Testing: Reorder Columns by UUID")

    df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
    wrapper = DataFrameWrapper(df)

    uuid_a = wrapper.get_uuid_by_name('A')
    uuid_b = wrapper.get_uuid_by_name('B')
    uuid_c = wrapper.get_uuid_by_name('C')


    wrapper.reorder_columns([uuid_c, uuid_a, uuid_b])


    assert list(wrapper.df.columns) == ['C', 'A', 'B']


    all_uuids = wrapper.get_all_uuids()
    assert all_uuids == [uuid_c, uuid_a, uuid_b]

    print("Reorder columns works\n")


def test_reorder_columns_partial():
    print("Testing: Reorder Columns with Invalid UUIDs (Preserve Missing)")

    df = pd.DataFrame({'A': [1], 'B': [2], 'C': [3]})
    wrapper = DataFrameWrapper(df)

    uuid_a = wrapper.get_uuid_by_name('A')
    uuid_c = wrapper.get_uuid_by_name('C')


    wrapper.reorder_columns([uuid_c, 'fake-uuid', uuid_a])


    assert list(wrapper.df.columns) == ['C', 'A', 'B']

    print("Reorder with invalid UUIDs preserves unspecified columns\n")


def test_one_hot_encoding_workflow():
    print("Testing: Complete One-Hot Encoding Workflow")

    df = pd.DataFrame({
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Color': ['Red', 'Blue', 'Red']
    })
    wrapper = DataFrameWrapper(df)


    color_uuid = wrapper.get_uuid_by_name('Color')
    color_data = wrapper.df['Color'].copy()


    wrapper.add_child_columns(color_uuid, {
        'Color_Red': [1, 0, 1],
        'Color_Blue': [0, 1, 0]
    })


    wrapper.remove_column(color_uuid)


    assert 'Color' not in wrapper.df.columns, "Parent column should be removed"
    assert 'Color_Red' in wrapper.df.columns, "Child column Color_Red should exist"
    assert 'Color_Blue' in wrapper.df.columns, "Child column Color_Blue should exist"
    assert list(wrapper.df.columns) == ['Name', 'Color_Red', 'Color_Blue'], "DataFrame columns incorrect after encoding"


    wrapper.restore_parent(color_uuid, 'Color', color_data)


    assert 'Color' in wrapper.df.columns, "Parent column should be restored"
    assert 'Color_Red' not in wrapper.df.columns, "Child column Color_Red should be removed"
    assert 'Color_Blue' not in wrapper.df.columns, "Child column Color_Blue should be removed"
    assert list(wrapper.df['Color']) == ['Red', 'Blue', 'Red'], "Parent column data incorrect after restore"

    print("Complete one-hot encoding workflow works\n")


def test_complex_scenario():
    print("Testing: Complex Multi-Operation Scenario")

    df = pd.DataFrame({
        'ID': [1, 2, 3],
        'Name': ['Alice', 'Bob', 'Charlie'],
        'Category': ['A', 'B', 'A']
    })
    wrapper = DataFrameWrapper(df)


    name_uuid = wrapper.get_uuid_by_name('Name')
    wrapper.rename_column(name_uuid, 'CustomerName')


    wrapper.add_columns({'Score': [85, 90, 78]})


    category_uuid = wrapper.get_uuid_by_name('Category')
    category_data = wrapper.df['Category'].copy()
    wrapper.add_child_columns(category_uuid, {
        'Category_A': [1, 0, 1],
        'Category_B': [0, 1, 0]
    })
    wrapper.remove_column(category_uuid)


    id_uuid = wrapper.get_uuid_by_name('ID')
    customer_uuid = wrapper.get_uuid_by_name('CustomerName')
    score_uuid = wrapper.get_uuid_by_name('Score')
    cat_a_uuid = wrapper.get_uuid_by_name('Category_A')
    cat_b_uuid = wrapper.get_uuid_by_name('Category_B')

    wrapper.reorder_columns([
        customer_uuid, id_uuid, score_uuid, cat_a_uuid, cat_b_uuid
    ])


    expected_cols = ['CustomerName', 'ID', 'Score', 'Category_A', 'Category_B']
    assert list(wrapper.df.columns) == expected_cols


    assert list(wrapper.df['ID']) == [1, 2, 3]
    assert list(wrapper.df['Score']) == [85, 90, 78]

    print("Complex scenario works\n")


def test_dataframe_isolation():
    print("Testing: DataFrame Isolation (Copy vs Reference)")

    original_df = pd.DataFrame({'A': [1, 2, 3]})
    wrapper = DataFrameWrapper(original_df)


    wrapper.df['A'] = [4, 5, 6]


    assert list(original_df['A']) == [1, 2, 3]
    assert list(wrapper.df['A']) == [4, 5, 6]

    print("DataFrame isolation works\n")


def run_all_tests():
    print("=" * 60)
    print("Running DataFrameWrapper Test Suite")
    print("=" * 60 + "\n")

    tests = [
        test_basic_initialization,
        test_initialization_with_none,
        test_get_uuid_by_index,
        test_get_col_data_by_uuid,
        test_rename_column,
        test_add_columns,
        test_add_columns_with_duplicate_name,
        test_add_columns_independent_data,
        test_remove_column,
        test_add_child_columns,
        test_get_parent_and_children,
        test_restore_parent,
        test_get_all_uuids,
        test_reorder_columns,
        test_reorder_columns_partial,
        test_one_hot_encoding_workflow,
        test_complex_scenario,
        test_dataframe_isolation,
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