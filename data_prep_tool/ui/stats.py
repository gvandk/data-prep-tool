from typing import Callable

import pandas as pd


def calculate_stats(series: pd.Series, binary_true: str, binary_false: str) -> str:
    """Calculate formatted column stats for numeric, categorical, and binary-like data."""
    if series is None or series.empty:
        return "No data."

    total = len(series)
    nulls = series.isnull().sum()
    stats = f"Total Rows: {total}\nMissing: {nulls}\n"

    binary_counts = get_binary_counts(series, binary_true, binary_false)
    if binary_counts is not None:
        true_count, false_count = binary_counts
        stats += (
            "Type: Binary\n"
            f"{binary_true}: {true_count}\n"
            f"{binary_false}: {false_count}"
        )
        return stats

    if pd.api.types.is_numeric_dtype(series):
        try:
            describe_stats = series.describe()
            stats += (
                "Type: Numeric\n"
                f"Mean: {describe_stats['mean']:.4f}\n"
                f"Min: {describe_stats['min']}\n"
                f"Max: {describe_stats['max']}"
            )
        except Exception:
            stats += "Error calc stats"
    else:
        try:
            stats += (
                "Type: Categorical\n"
                f"Unique: {series.nunique()}\n"
                f"{build_categorical_top_counts(series)}"
            )
        except Exception:
            stats += "Error calc stats"

    return stats


def build_categorical_top_counts(series: pd.Series, top_n: int = 5) -> str:
    """Build a compact top-values summary for categorical distributions."""
    non_null = series.dropna()
    if non_null.empty:
        return "Top Values (count):\nNo non-missing values."

    counts = non_null.value_counts()
    top_counts = counts.head(top_n)

    lines = ["Top Values (count):"]
    for value, count in top_counts.items():
        label = format_category_label(value)
        lines.append(f"- {label}: {int(count)}")

    return "\n".join(lines)


def format_category_label(value, max_len: int = 32) -> str:
    """Convert values to short labels suitable for compact categorical summaries."""
    label = str(value).replace("\n", " ").strip()
    if len(label) <= max_len:
        return label
    return f"{label[: max_len - 3]}..."


def get_binary_counts(series: pd.Series, binary_true: str, binary_false: str):
    """Return (true_count, false_count) when a series is binary-like, else None."""
    if series is None:
        return None

    true_count = 0
    false_count = 0
    saw_binary_value = False

    for value in series.dropna():
        if isinstance(value, bool):
            saw_binary_value = True
            if value:
                true_count += 1
            else:
                false_count += 1
            continue

        if isinstance(value, (int, float)) and value in (0, 1):
            saw_binary_value = True
            if value == 1:
                true_count += 1
            else:
                false_count += 1
            continue

        if isinstance(value, str):
            token = value.strip()
            lowered = token.casefold()

            if lowered in ("true", "1") or token == binary_true:
                saw_binary_value = True
                true_count += 1
                continue

            if lowered in ("false", "0") or token == binary_false:
                saw_binary_value = True
                false_count += 1
                continue

        return None

    if not saw_binary_value:
        return None
    return true_count, false_count


def build_child_column_stats(
    parent_name: str,
    parent_series: pd.Series,
    child_name: str,
    child_series: pd.Series,
    binary_true: str,
    binary_false: str,
) -> str:
    """Build combined stats text for expanded child columns."""
    parent_label = parent_name or "Parent"
    child_label = child_name or "Expanded Column"

    parent_stats = calculate_stats(parent_series, binary_true, binary_false)

    binary_counts = get_binary_counts(child_series, binary_true, binary_false)
    if binary_counts is not None:
        true_count, false_count = binary_counts
        child_stats = (
            "Type: Binary\n"
            f"{binary_true}: {true_count}\n"
            f"{binary_false}: {false_count}"
        )
    else:
        child_stats = calculate_stats(child_series, binary_true, binary_false)

    return (
        f"Parent Column ({parent_label})\n"
        f"{parent_stats}\n\n"
        f"Expanded Column ({child_label})\n"
        f"{child_stats}"
    )


def get_display_dtype(series: pd.Series, is_binary_column: bool) -> str:
    """Return user-facing dtype label, mapping binary-like object columns to binary."""
    dtype_name = str(series.dtype)
    if dtype_name != "object":
        return dtype_name

    if is_binary_column:
        return "binary"

    return dtype_name


def build_general_stats_summary(
    df: pd.DataFrame,
    is_binary_column_by_name: Callable[[str], bool],
) -> tuple[int, str]:
    """Return total missing count and formatted column dtype summary text."""
    total_missing_values = int(df.isna().sum().sum())
    dtype_rows = [
        f'"{column_name}": {get_display_dtype(df[column_name], is_binary_column_by_name(column_name))}'
        for column_name in df.columns
    ]
    dtype_text = "\n".join(dtype_rows) if dtype_rows else "(none)"
    return total_missing_values, dtype_text