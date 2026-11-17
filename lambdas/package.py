"""Build the deployment zip of one Lambda function: build/lambdas/<function>.zip.

Usage (from the repository root, Windows):  py -3.13 lambdas/package.py <function>

Zip content (at the zip root): the function's files (lambda_function.py, other modules, data such as migrations/),
lambdas/shared/*.py, and the pinned requirements installed with --no-deps. Excluded: tests/, __pycache__, *.pyc,
requirements.txt, conftest.py. Fails if an installed requirement is not pure Python (the zip is built on Windows and
runs on Linux). Rules: the python-lambda skill.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

LAMBDAS = Path(__file__).resolve().parent
REPO = LAMBDAS.parent
SHARED = LAMBDAS / "shared"
BUILD = REPO / "build" / "lambdas"
EXCLUDED_DIRS = {"tests", "__pycache__", ".pytest_cache"}
EXCLUDED_FILES = {"requirements.txt", "conftest.py"}
BINARY_SUFFIXES = {".pyd", ".so", ".dll", ".dylib", ".exe"}
# Fixed timestamp so that unchanged sources give an identical zip.
ZIP_DATE = (2020, 1, 1, 0, 0, 0)


def _included(path: Path) -> bool:
    if path.is_dir():
        return path.name not in EXCLUDED_DIRS
    return path.name not in EXCLUDED_FILES and path.suffix != ".pyc"


def _copy_tree(source: Path, target: Path) -> None:
    for path in sorted(source.iterdir()):
        if not _included(path):
            continue
        if path.is_dir():
            _copy_tree(path, target / path.name)
        else:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target / path.name)


def _check_clash(entries: list[Path], staging: Path, origin: str) -> None:
    """Stop if a zip-root entry would overwrite or shadow one already staged (file `x.py` vs package `x/`, too)."""
    for entry in entries:
        module = entry.stem if entry.suffix == ".py" else entry.name
        if any((staging / name).exists() for name in {entry.name, module, f"{module}.py"}):
            raise SystemExit(f"name clash in build/lambdas/{staging.name}: {origin}/{entry.name}")


def _install_requirements(requirements: Path, target: Path) -> None:
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "--requirement", str(requirements),
            "--target", str(target),
            "--no-deps", "--no-compile", "--only-binary=:all:",
            # Wheels must support the Lambda runtime (Python 3.12), not only the build interpreter.
            "--python-version", "3.12",
            "--disable-pip-version-check", "--quiet",
        ],
        check=True,
    )
    binaries = [p for p in target.rglob("*") if p.suffix.lower() in BINARY_SUFFIXES]
    if binaries:
        names = ", ".join(str(p.relative_to(target)) for p in binaries)
        raise SystemExit(f"not pure Python, cannot build on Windows for Lambda: {names}")
    # pip's console scripts and caches are not needed at runtime.
    for extra in ("bin", "__pycache__"):
        shutil.rmtree(target / extra, ignore_errors=True)


def _write_zip(staging: Path, zip_path: Path) -> int:
    files = sorted(p for p in staging.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(staging).as_posix(), date_time=ZIP_DATE)
            info.external_attr = 0o644 << 16  # rw-r--r-- on Linux
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return len(files)


def build(function: str) -> Path:
    source = LAMBDAS / function
    if function in {"shared", ""} or not (source / "lambda_function.py").is_file():
        raise SystemExit(f"no function directory with lambda_function.py: lambdas/{function}")

    staging = BUILD / function
    zip_path = BUILD / f"{function}.zip"
    shutil.rmtree(staging, ignore_errors=True)
    zip_path.unlink(missing_ok=True)
    staging.mkdir(parents=True)

    requirements = source / "requirements.txt"
    if requirements.is_file():
        _install_requirements(requirements, staging)
    # Installed requirements first; a function or shared file must not overwrite or shadow any of them.
    _check_clash([p for p in sorted(source.iterdir()) if _included(p)], staging, f"lambdas/{function}")
    _copy_tree(source, staging)
    helpers = sorted(SHARED.glob("*.py"))
    _check_clash(helpers, staging, "lambdas/shared")
    for helper in helpers:
        shutil.copy2(helper, staging / helper.name)

    count = _write_zip(staging, zip_path)
    print(f"{zip_path.relative_to(REPO).as_posix()}: {count} files")
    return zip_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: py -3.13 lambdas/package.py <function>")
    build(sys.argv[1])
