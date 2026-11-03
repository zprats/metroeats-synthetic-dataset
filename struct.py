def _main():
    import os
    import sys
    from pathlib import Path

    repository = Path(__file__).resolve().parent
    source = repository / "src"
    os.chdir(repository)
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from metroeats.cli import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_main())
