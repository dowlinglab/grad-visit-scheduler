"""Data loading helpers."""
from __future__ import annotations

import pandas as pd


def load_visitor_csv(path: str):
    """Load the visitor preference CSV into a DataFrame."""
    return pd.read_csv(path)
