"""assert-based self-check for ml/ingest.py — run with: python tests/test_ingest.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml import ingest

SAMPLE_CSV = """Some Disclaimer Title
Generated on 2024-03-04
S.No,Symbol,Conf.,Open,High,Low,Close,LTP,Close - LTP,Close - LTP %,VWAP,Vol,Prev. Close,Turnover,Trans.,Diff,Range,Diff %,Range %,VWAP %,120 Days,180 Days,52 Weeks High,52 Weeks Low
1,ACLBSL,31.71,920.00,927.00,915.00,925.00,925.00,0,0,921.10,584.00,916.00,"537,920.10",30,9,12.00,0.98,1.31,0.42,967.45,975.13,"1,240.00",827.90
2,ADBLD83,46.45,"1,070.00","1,084.90","1,066.00","1,084.90","1,084.90",0,0,"1,073.24","167,046.00","1,070.00","179,279,635.70",10,14.9,18.90,1.39,1.77,1.08,"1,086.97","1,092.00","1,160.00","1,022.00"
3,AHL,-,433.00,444.90,422.00,425.60,425.60,0,0,429.87,8109.00,435.00,3485781.40,84,-9.4,22.90,-2.16,5.43,-1,519.21,549.88,700.00,422.00

Disclaimer: figures are indicative only.
"""


def test_read_daily_csv():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "2024-03-04.csv"
        path.write_text(SAMPLE_CSV, encoding="utf-8")

        df = ingest.read_daily_csv(path)

        assert set(df["symbol"]) == {"ACLBSL", "AHL"}, "debenture ADBLD83 should be filtered out"
        assert df["date"].iloc[0] == __import__("pandas").Timestamp("2024-03-04")

        aclbsl = df[df["symbol"] == "ACLBSL"].iloc[0]
        assert aclbsl["turnover"] == 537920.10, "comma thousand-separator not stripped correctly"

        ahl = df[df["symbol"] == "AHL"].iloc[0]
        assert ahl["conf"] != ahl["conf"], "blank/'-' cell should become NaN"  # NaN != NaN

    print("test_read_daily_csv passed")


if __name__ == "__main__":
    test_read_daily_csv()
