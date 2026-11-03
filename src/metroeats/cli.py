import argparse
import json
import unittest
from pathlib import Path

from metroeats.analysis import run_analysis
from metroeats.database import build_database
from metroeats.generator import generate_dataset
from metroeats.models import DatasetConfig
from metroeats.validation import validate_dataset


def build_parser():
    parser = argparse.ArgumentParser(prog="python3 struct.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--data-dir", type=Path, default=Path("data"))
    generate.add_argument("--seed", type=int, default=202501)
    generate.add_argument("--restaurants", type=_positive_int, default=5_000)
    generate.add_argument("--customers", type=_positive_int, default=30_000)
    generate.add_argument("--orders", type=_positive_int, default=60_000)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--data-dir", type=Path, default=Path("data"))
    validate.add_argument("--skip-checksums", action="store_true")

    database = subparsers.add_parser("build-db")
    database.add_argument("--data-dir", type=Path, default=Path("data"))
    database.add_argument("--database", type=Path, default=Path("var/metroeats.sqlite"))
    database.add_argument("--skip-validation", action="store_true")

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("--database", type=Path, default=Path("var/metroeats.sqlite"))
    analyze.add_argument("--reports", type=Path, default=Path("reports"))

    test = subparsers.add_parser("test")
    test.add_argument("--pattern", default="test*.py")

    run_all = subparsers.add_parser("run-all")
    run_all.add_argument("--data-dir", type=Path, default=Path("data"))
    run_all.add_argument("--database", type=Path, default=Path("var/metroeats.sqlite"))
    run_all.add_argument("--reports", type=Path, default=Path("reports"))
    run_all.add_argument("--seed", type=int, default=202501)
    run_all.add_argument("--restaurants", type=_positive_int, default=5_000)
    run_all.add_argument("--customers", type=_positive_int, default=30_000)
    run_all.add_argument("--orders", type=_positive_int, default=60_000)
    return parser


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    if arguments.command == "generate":
        generated = _generate(arguments)
        _print(
            {
                "directory": str(generated.directory),
                "row_counts": generated.row_counts,
                "byte_sizes": generated.byte_sizes,
            }
        )
        return 0
    if arguments.command == "validate":
        report = validate_dataset(arguments.data_dir, verify_checksums=not arguments.skip_checksums)
        _print(report.to_dict())
        return 0 if report.valid else 1
    if arguments.command == "build-db":
        if not arguments.skip_validation:
            _require_valid(arguments.data_dir)
        path = build_database(arguments.data_dir, arguments.database)
        _print({"database": str(path), "bytes": path.stat().st_size})
        return 0
    if arguments.command == "analyze":
        summary, rows = run_analysis(arguments.database, arguments.reports)
        _print({"summary": summary, "report_rows": rows})
        return 0
    if arguments.command == "test":
        suite = unittest.defaultTestLoader.discover("tests", pattern=arguments.pattern)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    if arguments.command == "run-all":
        generated = _generate(arguments)
        report = _require_valid(arguments.data_dir)
        database = build_database(arguments.data_dir, arguments.database)
        summary, rows = run_analysis(database, arguments.reports)
        _print(
            {
                "generated_rows": generated.row_counts,
                "validation": report.to_dict(),
                "database": str(database),
                "summary": summary,
                "report_rows": rows,
            }
        )
        return 0
    raise RuntimeError(f"unsupported command: {arguments.command}")


def _generate(arguments):
    config = DatasetConfig(
        output_directory=arguments.data_dir,
        seed=arguments.seed,
        restaurant_count=arguments.restaurants,
        customer_count=arguments.customers,
        order_count=arguments.orders,
    )
    return generate_dataset(config)


def _require_valid(directory):
    report = validate_dataset(directory)
    if not report.valid:
        details = "; ".join(f"{issue.table}:{issue.row_number} {issue.message}" for issue in report.errors[:10])
        raise RuntimeError(f"dataset validation failed: {details}")
    return report


def _positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _print(value):
    print(json.dumps(value, indent=2, sort_keys=True))
