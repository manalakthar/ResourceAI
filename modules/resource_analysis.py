import pandas as pd

REQUIRED_COLUMNS = {
    "date", "location", "resource_type", "category",
    "unit", "available_quantity", "required_quantity", "source",
}


def load_data(path="data/processed/resource_data.csv",
              loc_path="data/processed/locations.csv"):
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    df = df.merge(pd.read_csv(loc_path), on="location", how="left")
    unknown = df[df["lat"].isna()]["location"].unique()
    if len(unknown):
        raise ValueError(f"Locations missing from locations.csv: {list(unknown)}")
    return df


def _risk(coverage):
    # Rule-based current-balance risk (NOT an ML prediction).
    if coverage < 0.8:
        return "High"
    if coverage < 1.0:
        return "Medium"
    return "Low"


def calculate_balance(df):
    """Balance = available - required. Positive = surplus, negative = deficit."""
    df = df.copy()
    df["balance"] = df["available_quantity"] - df["required_quantity"]
    df["status"] = df["balance"].apply(
        lambda b: "Surplus" if b > 0 else ("Deficit" if b < 0 else "Balanced"))
    df["coverage"] = (df["available_quantity"] /
                      df["required_quantity"].replace(0, float("nan"))).round(2)
    df["risk"] = df["coverage"].fillna(1).apply(_risk)
    return df


def split_surplus_deficit(df):
    return df[df["status"] == "Surplus"], df[df["status"] == "Deficit"]
