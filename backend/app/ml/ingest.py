"""Combine daily NEPSE CSV exports (backend/data/raw/*.csv) into one parquet file."""
import csv
import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "nepse_history.parquet"

FILENAME_DATE_RE = re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})")
DEBENTURE_RE = re.compile(r"[A-Za-z]\d+$")


def _normalize_col(col: str) -> str:
    col = col.strip().lower().replace("%", "pct")
    col = re.sub(r"[\s.\-]+", "_", col)
    return col.strip("_")


def _find_header_row(path: Path) -> int:
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.reader(f)):
            if "symbol" in [c.strip().lower() for c in row]:
                return i
    raise ValueError(f"No header row (containing 'Symbol') found in {path}")


def _clean_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().replace({"-": None, "": None, "nan": None})
    s = s.str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def read_daily_csv(path: Path) -> pd.DataFrame:
    header_row = _find_header_row(path)
    df = pd.read_csv(path, skiprows=header_row, encoding="utf-8-sig", on_bad_lines="skip")
    df.columns = [_normalize_col(c) for c in df.columns]
    df = df.dropna(how="all")
    df = df[df["symbol"].notna()]
    df["s_no"] = pd.to_numeric(df["s_no"], errors="coerce")
    df = df[df["s_no"].notna()]

    for col in df.columns:
        if col not in ("symbol", "s_no"):
            df[col] = _clean_numeric(df[col])

    df["symbol"] = df["symbol"].astype(str).str.strip()
    df = df[~df["symbol"].str.contains(DEBENTURE_RE, regex=True)]

    date_match = FILENAME_DATE_RE.search(path.stem)
    if not date_match:
        raise ValueError(f"Could not extract a YYYY-MM-DD date from filename {path.name}")
    df["date"] = pd.to_datetime("-".join(date_match.groups()))

    return df


def ingest() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")

    frames = [read_daily_csv(f) for f in files]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["date", "symbol"])
    combined = combined.sort_values(["symbol", "date"]).reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(OUT_PATH, index=False)

    print(f"Files processed: {len(files)}")
    print(f"Total rows: {len(combined)}")
    print(f"Unique equity symbols: {combined['symbol'].nunique()}")
    print(f"Date range: {combined['date'].min().date()} to {combined['date'].max().date()}")

    return combined


if __name__ == "__main__":
    ingest()
