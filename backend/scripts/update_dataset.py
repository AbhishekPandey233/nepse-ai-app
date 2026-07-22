
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.ingest import ingest


def main(n: int) -> None:
    print("== Step 1/2: rebuilding parquet from raw CSVs ==")
    ingest()

    print(f"\n== Step 2/2: rebuilding market summary (top {n} by turnover) ==")
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("build_market_summary.py")), "--n", str(n)],
        check=True,
    )

    print("\nDone. A running server will serve the updated data automatically -- no restart needed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=50, help="market-summary universe size (default 50)")
    main(parser.parse_args().n)
