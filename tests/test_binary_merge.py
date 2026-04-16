import pandas as pd
import pytest

from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.core.transformation_manager import TransformationManager
from data_prep_tool.core.script_generator import ScriptGenerator


def make_manager(df: pd.DataFrame) -> TransformationManager:
    return TransformationManager(DataFrameWrapper(df))


def generate_script(manager: TransformationManager, final_uuids=None) -> str:
    graph = manager.build_dependency_graph()
    return ScriptGenerator(graph).generate_script(final_uuids)


def test_binary_merge_or_logic_two_columns():
    df = pd.DataFrame(
        {
            "A": ["True", "False", "True", "False"],
            "B": ["False", "False", "True", "True"],
        }
    )
    manager = make_manager(df)

    uuid_a = manager.df_wrapper.get_uuid_by_name("A")
    uuid_b = manager.df_wrapper.get_uuid_by_name("B")

    manager.add_binary_column_merge([uuid_a, uuid_b], "Merged")

    assert list(manager.df_wrapper.df["Merged"]) == ["True", "False", "True", "True"]
    assert "A" not in manager.df_wrapper.df.columns
    assert "B" not in manager.df_wrapper.df.columns


def test_binary_merge_or_logic_multiple_columns():
    df = pd.DataFrame(
        {
            "A": ["False", "False", "True"],
            "B": ["False", "True", "False"],
            "C": ["False", "False", "False"],
        }
    )
    manager = make_manager(df)

    uuids = [manager.df_wrapper.get_uuid_by_name(name) for name in ["A", "B", "C"]]
    manager.add_binary_column_merge(uuids, "MergedAll")

    assert list(manager.df_wrapper.df["MergedAll"]) == ["False", "True", "True"]
    assert "A" not in manager.df_wrapper.df.columns
    assert "B" not in manager.df_wrapper.df.columns
    assert "C" not in manager.df_wrapper.df.columns


def test_binary_merge_can_keep_source_columns_when_requested():
    df = pd.DataFrame(
        {
            "A": ["True", "False", "True"],
            "B": ["False", "False", "True"],
        }
    )
    manager = make_manager(df)

    uuid_a = manager.df_wrapper.get_uuid_by_name("A")
    uuid_b = manager.df_wrapper.get_uuid_by_name("B")
    manager.add_binary_column_merge([uuid_a, uuid_b], "Merged", delete_source_columns=False)

    assert "A" in manager.df_wrapper.df.columns
    assert "B" in manager.df_wrapper.df.columns
    assert "Merged" in manager.df_wrapper.df.columns

    script = generate_script(manager)
    assert "_merge_binary_columns(" in script
    assert "delete_sources=False" in script


def test_binary_merge_rejects_non_binary_columns():
    df = pd.DataFrame(
        {
            "A": ["True", "False", "True"],
            "B": ["red", "blue", "green"],
        }
    )
    manager = make_manager(df)

    uuid_a = manager.df_wrapper.get_uuid_by_name("A")
    uuid_b = manager.df_wrapper.get_uuid_by_name("B")

    with pytest.raises(ValueError):
        manager.add_binary_column_merge([uuid_a, uuid_b], "Merged")


def test_binary_merge_undo_restores_sources_and_removes_created_column():
    df = pd.DataFrame(
        {
            "A": ["True", "False"],
            "B": ["False", "True"],
        }
    )
    manager = make_manager(df)

    uuid_a = manager.df_wrapper.get_uuid_by_name("A")
    uuid_b = manager.df_wrapper.get_uuid_by_name("B")

    manager.add_binary_column_merge([uuid_a, uuid_b], "Merged")
    assert "Merged" in manager.df_wrapper.df.columns
    assert "A" not in manager.df_wrapper.df.columns
    assert "B" not in manager.df_wrapper.df.columns

    manager.undo_transformation()

    assert "A" in manager.df_wrapper.df.columns
    assert "B" in manager.df_wrapper.df.columns
    assert "Merged" not in manager.df_wrapper.df.columns


def test_binary_merge_redo_reapplies_source_deletion():
    df = pd.DataFrame(
        {
            "A": ["True", "False"],
            "B": ["False", "True"],
        }
    )
    manager = make_manager(df)

    uuid_a = manager.df_wrapper.get_uuid_by_name("A")
    uuid_b = manager.df_wrapper.get_uuid_by_name("B")
    manager.add_binary_column_merge([uuid_a, uuid_b], "Merged")

    manager.undo_transformation()
    manager.redo_transformation()

    assert "A" not in manager.df_wrapper.df.columns
    assert "B" not in manager.df_wrapper.df.columns
    assert "Merged" in manager.df_wrapper.df.columns


def test_multiple_merges_undo_all_restores_original_columns_exactly():
    df = pd.DataFrame(
        {
            "A": ["True", "False", "True"],
            "B": ["False", "True", "False"],
            "C": ["True", "False", "False"],
            "D": ["False", "False", "True"],
        }
    )
    manager = make_manager(df)
    original_columns = list(manager.df_wrapper.df.columns)

    uuid_a = manager.df_wrapper.get_uuid_by_name("A")
    uuid_b = manager.df_wrapper.get_uuid_by_name("B")
    manager.add_binary_column_merge([uuid_a, uuid_b], "AB")

    uuid_c = manager.df_wrapper.get_uuid_by_name("C")
    uuid_d = manager.df_wrapper.get_uuid_by_name("D")
    manager.add_binary_column_merge([uuid_c, uuid_d], "CD")

    while manager.history:
        manager.undo_transformation()

    assert list(manager.df_wrapper.df.columns) == original_columns


def test_binary_merge_is_emitted_in_script():
    df = pd.DataFrame(
        {
            "A": ["True", "False"],
            "B": ["False", "True"],
        }
    )
    manager = make_manager(df)

    uuid_a = manager.df_wrapper.get_uuid_by_name("A")
    uuid_b = manager.df_wrapper.get_uuid_by_name("B")
    manager.add_binary_column_merge([uuid_a, uuid_b], "Merged")

    script = generate_script(manager)

    assert "# Merge binary columns [A, B] into: Merged" in script
    assert "_merge_binary_columns(" in script
    assert "_to_binary_flag(" in script
    assert "'Merged'" in script
    assert "delete_sources=True" in script
