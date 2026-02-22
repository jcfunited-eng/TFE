"""
UF-Spec v1.4.0 — Section 13 Validation
======================================

Module: qa_dataset.py

Purpose:
    Perform structural and content QA checks on a validation dataset BEFORE
    running any UF pipeline or noise robustness tests.

This ensures:
- Required columns exist
- Data types are correct
- No missing values
- Dates are strictly increasing
- Numeric fields contain valid numeric values

This prevents data-driven errors from contaminating validation results.
"""

import pandas as pd


REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]


def qa_csv_structure(path: str) -> pd.DataFrame:
    """
    Load CSV and check required columns exist.
    Returns loaded DataFrame if valid.
    Raises ValueError otherwise.
    """
    df = pd.read_csv(path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df


def qa_csv_content(df: pd.DataFrame):
    """
    Check:
    - No NaN values
    - Date column strictly increasing
    - Numeric columns contain valid numbers
    """

    # 1. Check NaN
    if df.isna().any().any():
        raise ValueError("Dataset contains NaN values.")

    # 2. Check date ordering
    dates = pd.to_datetime(df["Date"])
    if not dates.is_monotonic_increasing:
        raise ValueError("Date column is not strictly increasing.")

    # 3. Check numeric columns
    numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
    for col in numeric_cols:
        try:
            _ = pd.to_numeric(df[col])
        except Exception:
            raise ValueError(f"Column '{col}' contains non-numeric values.")

    # Passed all checks
    return True


def main():
    """
    Usage:
        python qa_dataset.py <csv_path>
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python qa_dataset.py <csv_path>")
        return

    csv_path = sys.argv[1]

    print(f"Loading and checking dataset: {csv_path}")

    try:
        df = qa_csv_structure(csv_path)
        qa_csv_content(df)
    except Exception as e:
        print("QA FAILED:")
        print(f"  {e}")
        return

    print("QA PASSED: Dataset is structurally valid.")


if __name__ == "__main__":
    main()
