from PyQt6.QtCore import QItemSelectionModel, Qt
from PyQt6.QtWidgets import QApplication, QAbstractItemView


def clear_row_selection_state(selected_rows: set[int]) -> None:
    """Clear stored row multi-selection state."""
    selected_rows.clear()


def clear_header_selection_state(header_selected_columns: set[int]) -> None:
    """Clear stored header multi-selection state."""
    header_selected_columns.clear()


def reset_all_selection_state(
    selected_rows: set[int],
    header_selected_columns: set[int],
) -> tuple[None, None, int]:
    """Reset both row and header selection state values."""
    selected_rows.clear()
    header_selected_columns.clear()
    return None, None, -1


def set_single_selection_mode(table_view) -> None:
    """Set single-selection mode and clear the current table selection."""
    table_view.clearSelection()
    table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)


def set_column_extended_selection_mode(table_view) -> None:
    """Configure the table for extended column selection."""
    table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectColumns)
    table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)


def set_row_extended_selection_mode(table_view) -> None:
    """Configure the table for extended row selection."""
    table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)


def set_item_single_selection_mode(table_view) -> None:
    """Configure the table for single-cell selection."""
    table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
    table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)


def select_single_index(table_view, index) -> None:
    """Select a single model index as current."""
    selection_model = table_view.selectionModel()
    if selection_model:
        selection_model.setCurrentIndex(
            index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )


def update_header_selection_from_click(
    logical_index: int,
    header_selected_columns: set[int],
    last_header_clicked_column: int | None,
    table_view,
) -> tuple[list[int], int | None]:
    """Update selected columns from a header click and return selected columns plus anchor."""
    modifiers = QApplication.keyboardModifiers()
    is_ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
    is_shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

    if is_shift and last_header_clicked_column is not None:
        start = min(last_header_clicked_column, logical_index)
        end = max(last_header_clicked_column, logical_index)
        if not is_ctrl:
            header_selected_columns.clear()
        for col_index in range(start, end + 1):
            header_selected_columns.add(col_index)
    elif is_ctrl:
        if logical_index in header_selected_columns:
            header_selected_columns.remove(logical_index)
        else:
            header_selected_columns.add(logical_index)
        last_header_clicked_column = logical_index
    else:
        header_selected_columns.clear()
        header_selected_columns.add(logical_index)
        last_header_clicked_column = logical_index

    if not header_selected_columns:
        header_selected_columns.add(logical_index)
        last_header_clicked_column = logical_index

    selected_columns = sorted(header_selected_columns)

    selection_model = table_view.selectionModel()
    model = table_view.model()
    if selection_model and model and model.rowCount() > 0:
        selection_model.clearSelection()
        for col_index in selected_columns:
            index = model.index(0, col_index)
            selection_model.select(
                index,
                QItemSelectionModel.SelectionFlag.Columns | QItemSelectionModel.SelectionFlag.Select,
            )

    return selected_columns, last_header_clicked_column


def update_row_selection_from_click(
    logical_index: int,
    selected_rows: set[int],
    last_row_clicked: int | None,
    table_view,
) -> tuple[list[int], int | None]:
    """Update selected rows from a row-header click and return selected rows plus anchor."""
    modifiers = QApplication.keyboardModifiers()
    is_ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
    is_shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

    if is_shift and last_row_clicked is not None:
        start = min(last_row_clicked, logical_index)
        end = max(last_row_clicked, logical_index)
        if not is_ctrl:
            selected_rows.clear()
        for row_index in range(start, end + 1):
            selected_rows.add(row_index)
    elif is_ctrl:
        if logical_index in selected_rows:
            selected_rows.remove(logical_index)
        else:
            selected_rows.add(logical_index)
        last_row_clicked = logical_index
    else:
        selected_rows.clear()
        selected_rows.add(logical_index)
        last_row_clicked = logical_index

    if not selected_rows:
        selected_rows.add(logical_index)
        last_row_clicked = logical_index

    normalized_rows = sorted(selected_rows)

    selection_model = table_view.selectionModel()
    model = table_view.model()
    if selection_model and model and model.columnCount() > 0:
        selection_model.clearSelection()
        for row_index in normalized_rows:
            if row_index >= model.rowCount():
                continue
            index = model.index(row_index, 0)
            selection_model.select(
                index,
                QItemSelectionModel.SelectionFlag.Rows | QItemSelectionModel.SelectionFlag.Select,
            )

    return normalized_rows, last_row_clicked