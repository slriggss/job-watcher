"""Open or update the day's GitHub Issue from the files the pipeline already wrote.

Kept apart from the fetch step so that only this step needs the GitHub token.

Run:  uv run python -m jobwatcher.issue --date YYYY-MM-DD
"""
import argparse
import csv
import json

from .build import DATA
from .pipeline import issue_parts, update_issue


def load_rows(path=DATA / "history.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["in_role"] = r["in_role"] == "true"
        r["first_run"] = r["first_run"] == "true"
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="the UTC run date the data carries (YYYY-MM-DD)")
    args = ap.parse_args()
    status = json.loads((DATA / "status.json").read_text(encoding="utf-8"))
    update_issue(args.date, issue_parts(load_rows(), args.date, status["sources"]))
    print(f"issue {args.date} updated")


if __name__ == "__main__":
    main()
