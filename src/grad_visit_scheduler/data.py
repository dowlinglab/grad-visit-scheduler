"""Data loading helpers."""
from __future__ import annotations

import pandas as pd


def load_visitor_csv(path: str):
    """Load visitor preference data from CSV.

    Parameters
    ----------
    path:
        Path to a CSV file containing visitor preferences.

    Returns
    -------
    pandas.DataFrame
        Loaded CSV contents.
    """
    return pd.read_csv(path)
