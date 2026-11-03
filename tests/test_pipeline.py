import csv
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from metroeats.analysis import run_analysis
from metroeats.database import build_database
from metroeats.generator import generate_dataset
from metroeats.models import DatasetConfig
from metroeats.validation import validate_dataset


class PipelineTest(unittest.TestCase):
    def test_catalogue_decodes_in_isolated_mode(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "decoded"
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(repository / "tools" / "catalogue_codec.py"),
                    "decode",
                    "--repository",
                    str(repository),
                    "--destination",
                    str(destination),
                ],
                cwd=repository,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {"record_count": 9})
            for report in repository.joinpath("reports").iterdir():
                if report.suffix in {".csv", ".json"}:
                    decoded = destination / report.name
                    self.assertEqual(decoded.read_bytes(), report.read_bytes())

    def test_struct_entrypoint(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary_directory:
            help_result = subprocess.run(
                [sys.executable, str(repository / "struct.py"), "--help"],
                cwd=temporary_directory,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("validate", help_result.stdout)

    def test_generate_validate_build_and_analyze(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data = root / "data"
            database = root / "var" / "metroeats.sqlite"
            reports = root / "reports"
            generated = generate_dataset(
                DatasetConfig(
                    output_directory=data,
                    seed=73,
                    restaurant_count=50,
                    customer_count=200,
                    order_count=400,
                )
            )
            self.assertEqual(generated.row_counts["restaurants.csv"], 50)
            self.assertEqual(generated.row_counts["customers.csv"], 200)
            self.assertEqual(generated.row_counts["orders.csv"], 400)
            self.assertEqual(generated.row_counts["payments.csv"], 400)
            report = validate_dataset(data)
            self.assertTrue(report.valid, report.to_dict())
            self.assertGreater(report.row_counts["order_items.csv"], 400)
            self.assertGreater(report.row_counts["delivery_events.csv"], 800)
            built = build_database(data, database)
            self.assertEqual(built, database)
            connection = sqlite3.connect(database)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 400)
            connection.close()
            summary, report_rows = run_analysis(database, reports)
            self.assertEqual(summary["marketplace"]["orders"], 400)
            self.assertEqual(report_rows["monthly_performance.csv"], 12)
            self.assertTrue((reports / "city_performance.csv").is_file())

    def test_generation_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "first"
            second = root / "second"
            settings = {
                "seed": 91,
                "restaurant_count": 25,
                "customer_count": 80,
                "order_count": 120,
            }
            one = generate_dataset(DatasetConfig(output_directory=first, **settings))
            two = generate_dataset(DatasetConfig(output_directory=second, **settings))
            self.assertEqual(one.checksums, two.checksums)
            first_manifest = json.loads((first / "dataset_manifest.json").read_text(encoding="utf-8"))
            second_manifest = json.loads((second / "dataset_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(first_manifest, second_manifest)

    def test_csv_fields_are_parseable(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data = Path(temporary_directory) / "data"
            generate_dataset(
                DatasetConfig(
                    output_directory=data,
                    seed=17,
                    restaurant_count=20,
                    customer_count=60,
                    order_count=100,
                )
            )
            with (data / "orders.csv").open("r", encoding="utf-8", newline="") as stream:
                row = next(csv.DictReader(stream))
            self.assertTrue(row["order_id"].startswith("ORD2025"))
            self.assertGreater(float(row["total_inr"]), 0)
            self.assertIn(row["order_status"], {"delivered", "cancelled_by_customer", "cancelled_by_restaurant", "delivery_failed"})


if __name__ == "__main__":
    unittest.main()
