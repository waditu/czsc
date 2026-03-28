import pandas as pd

__all__ = ["show_price_sensitive"]

def show_price_sensitive(
    df: pd.DataFrame, fee: float = 2.0, digits: int = 2, weight_type: str = "ts", n_jobs: int = 1, **kwargs
) -> tuple[pd.DataFrame, pd.DataFrame] | None: ...
