import argparse
import base64
import csv
import hashlib
import io
import json
import os
import tempfile
import zlib
from pathlib import Path, PurePosixPath


CODEC = {
    "compression": "zlib",
    "encoding": "base85",
    "transform_order": ["zlib", "base85"],
}


def build_catalogue(repository, reports, output, manifest_path, accession_map_path):
    repository = repository.resolve()
    reports = _inside(repository, reports)
    output = _inside(repository, output)
    manifest_path = _inside(repository, manifest_path)
    accession_map_path = _inside(repository, accession_map_path)
    report_paths = sorted(
        path
        for path in reports.iterdir()
        if path.is_file() and path.suffix in {".csv", ".json"}
    )
    if not report_paths:
        raise ValueError(f"no reports found in {reports}")

    records = []
    accession_rows = []
    for report_path in report_paths:
        decoded = report_path.read_bytes()
        encoded = _wrap(base64.b85encode(zlib.compress(decoded, level=9)))
        archive_path = output / f"{report_path.stem}.b85"
        _write_atomic(archive_path, encoded)
        accession_id = f"METROEATS-2025-{report_path.stem.replace('_', '-').upper()}"
        media_type = "application/json" if report_path.suffix == ".json" else "text/csv"
        record = {
            "accession_id": accession_id,
            "archive_path": archive_path.relative_to(repository).as_posix(),
            "decoded_bytes": len(decoded),
            "decoded_sha256": hashlib.sha256(decoded).hexdigest(),
            "encoded_bytes": len(encoded),
            "encoded_sha256": hashlib.sha256(encoded).hexdigest(),
            "media_type": media_type,
            "source_path": report_path.relative_to(repository).as_posix(),
        }
        records.append(record)
        accession_rows.append(
            {
                "accession_id": accession_id,
                "archive_path": record["archive_path"],
                "media_type": media_type,
                "source_path": record["source_path"],
            }
        )

    manifest = {
        "catalogue": "MetroEats 2025 analytical report archive",
        "codec": CODEC,
        "record_count": len(records),
        "records": records,
        "schema_version": 1,
    }
    _write_atomic(
        manifest_path,
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    _write_accession_map(accession_map_path, accession_rows)
    return manifest


def verify_catalogue(repository, manifest_path):
    repository = repository.resolve()
    manifest_path = _inside(repository, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("codec") != CODEC:
        raise ValueError("unsupported catalogue manifest")
    records = manifest.get("records")
    if not isinstance(records, list) or manifest.get("record_count") != len(records):
        raise ValueError("catalogue record count mismatch")
    decoded_records = []
    for record in records:
        archive_path = _manifest_path(repository, record["archive_path"])
        encoded = archive_path.read_bytes()
        if len(encoded) != record["encoded_bytes"]:
            raise ValueError(f"encoded size mismatch: {record['accession_id']}")
        if hashlib.sha256(encoded).hexdigest() != record["encoded_sha256"]:
            raise ValueError(f"encoded digest mismatch: {record['accession_id']}")
        decoded = zlib.decompress(base64.b85decode(b"".join(encoded.split())))
        if len(decoded) != record["decoded_bytes"]:
            raise ValueError(f"decoded size mismatch: {record['accession_id']}")
        if hashlib.sha256(decoded).hexdigest() != record["decoded_sha256"]:
            raise ValueError(f"decoded digest mismatch: {record['accession_id']}")
        decoded_records.append((record, decoded))
    return manifest, decoded_records


def decode_catalogue(repository, manifest_path, destination):
    repository = repository.resolve()
    destination = destination.resolve()
    manifest, decoded_records = verify_catalogue(repository, manifest_path)
    for record, decoded in decoded_records:
        source = PurePosixPath(record["source_path"])
        if source.is_absolute() or ".." in source.parts or not source.name:
            raise ValueError(f"unsafe source path: {record['source_path']}")
        _write_atomic(destination / source.name, decoded)
    return manifest


def _inside(repository, path):
    resolved = path if path.is_absolute() else repository / path
    resolved = resolved.resolve()
    resolved.relative_to(repository)
    return resolved


def _manifest_path(repository, value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive path: {value}")
    return _inside(repository, Path(*path.parts))


def _wrap(value, width=100):
    return b"\n".join(value[index : index + width] for index in range(0, len(value), width)) + b"\n"


def _write_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _write_accession_map(path, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=["accession_id", "archive_path", "media_type", "source_path"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    _write_atomic(path, stream.getvalue().encode("utf-8"))


def build_parser():
    parser = argparse.ArgumentParser(prog="catalogue_codec.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build")
    build.add_argument("--repository", type=Path, default=Path.cwd())
    build.add_argument("--reports", type=Path, default=Path("reports"))
    build.add_argument("--output", type=Path, default=Path("encoded/catalogue"))
    build.add_argument("--manifest", type=Path, default=Path("encoded/catalogue_manifest.json"))
    build.add_argument("--accession-map", type=Path, default=Path("encoded/accession-map.csv"))

    verify = subparsers.add_parser("verify")
    verify.add_argument("--repository", type=Path, default=Path.cwd())
    verify.add_argument("--manifest", type=Path, default=Path("encoded/catalogue_manifest.json"))

    decode = subparsers.add_parser("decode")
    decode.add_argument("--repository", type=Path, default=Path.cwd())
    decode.add_argument("--manifest", type=Path, default=Path("encoded/catalogue_manifest.json"))
    decode.add_argument("--destination", type=Path, required=True)
    return parser


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    if arguments.command == "build":
        manifest = build_catalogue(
            arguments.repository,
            arguments.reports,
            arguments.output,
            arguments.manifest,
            arguments.accession_map,
        )
    elif arguments.command == "verify":
        manifest, _ = verify_catalogue(arguments.repository, arguments.manifest)
    else:
        manifest = decode_catalogue(arguments.repository, arguments.manifest, arguments.destination)
    print(json.dumps({"record_count": manifest["record_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
