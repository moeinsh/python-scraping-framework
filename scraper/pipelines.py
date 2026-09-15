"""Item pipelines: every scraped item goes to CSV *and* SQLite."""
import csv
import os
import re
import sqlite3


def _safe_col(name):
    return re.sub(r"\W", "_", name).strip("_") or "col"


class CSVPipeline:
    """Append items to output/<spider>.csv (UTF-8, header row)."""

    def __init__(self, output_dir, spider_name, fields):
        os.makedirs(output_dir, exist_ok=True)
        self.path = os.path.join(output_dir, f"{spider_name}.csv")
        self.fields = fields
        self.count = 0
        self._file = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=fields)
        self._writer.writeheader()

    def process_item(self, item):
        self._writer.writerow({f: item.get(f, "") for f in self.fields})
        self.count += 1

    def close(self):
        self._file.close()
        return self.path, self.count


class SQLitePipeline:
    """Insert items into output/<spider>.db, table `items` (all TEXT)."""

    def __init__(self, output_dir, spider_name, fields):
        os.makedirs(output_dir, exist_ok=True)
        self.path = os.path.join(output_dir, f"{spider_name}.db")
        self.fields = fields
        self.cols = [_safe_col(f) for f in fields]
        self.count = 0
        if os.path.exists(self.path):
            os.remove(self.path)  # fresh DB per run
        self._conn = sqlite3.connect(self.path)
        coldefs = ", ".join(f'"{c}" TEXT' for c in self.cols)
        self._conn.execute(f'CREATE TABLE items ({coldefs})')
        self._conn.commit()

    def process_item(self, item):
        placeholders = ", ".join("?" for _ in self.cols)
        values = [str(item.get(f, "")) for f in self.fields]
        self._conn.execute(
            f'INSERT INTO items VALUES ({placeholders})', values
        )
        self.count += 1

    def close(self):
        self._conn.commit()
        self._conn.close()
        return self.path, self.count
