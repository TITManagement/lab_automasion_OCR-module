"""Project root launcher for project-template."""

from src.app import main as _run


def main() -> int:
    return int(_run())


if __name__ == "__main__":
    raise SystemExit(main())
