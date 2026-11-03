import csv
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from metroeats.schema import TableSpec


@contextmanager
def atomic_csv_writer(directory, table):
    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{table.filename}.",
        suffix=".tmp",
        dir=target_directory,
        text=True,
    )
    stream = os.fdopen(descriptor, "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(stream, fieldnames=table.columns, lineterminator="\n")
    try:
        writer.writeheader()
        yield writer
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()
        Path(temporary_name).replace(target_directory / table.filename)
    except BaseException:
        stream.close()
        Path(temporary_name).unlink(missing_ok=True)
        raise


def read_rows(path, table):
    with Path(path).open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != table.columns:
            raise ValueError(f"unexpected header in {path}")
        yield from reader


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
        text=True,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    Path(temporary_name).replace(target)


def count_rows(path, table):
    return sum(1 for _ in read_rows(path, table))


def assert_table(path, table: TableSpec):
    rows = read_rows(path, table)
    first = next(rows, None)
    if first is None:
        raise ValueError(f"{path} contains no data rows")
