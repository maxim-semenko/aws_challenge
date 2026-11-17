"""Unit tests of lambdas/package.py on a throw-away lambdas/ tree; pip is replaced by a stub (no network)."""

import zipfile

import pytest

import package


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A fake repository: lambdas/fn (function), lambdas/shared (helper), build/ output; 'installs' six + pg8000."""
    lambdas = tmp_path / "lambdas"
    function = lambdas / "fn"
    (function / "tests").mkdir(parents=True)
    (function / "lambda_function.py").write_text("import db\n", encoding="utf-8")
    (function / "requirements.txt").write_text("six==1.17.0\n", encoding="utf-8")
    (function / "tests" / "test_fn.py").write_text("", encoding="utf-8")
    (lambdas / "shared").mkdir()
    (lambdas / "shared" / "db.py").write_text("", encoding="utf-8")

    def fake_install(requirements, target):
        (target / "six.py").write_text("", encoding="utf-8")
        (target / "pg8000").mkdir()
        (target / "pg8000" / "__init__.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(package, "REPO", tmp_path)
    monkeypatch.setattr(package, "LAMBDAS", lambdas)
    monkeypatch.setattr(package, "SHARED", lambdas / "shared")
    monkeypatch.setattr(package, "BUILD", tmp_path / "build" / "lambdas")
    monkeypatch.setattr(package, "_install_requirements", fake_install)
    return function


def test_zip_holds_function_shared_helper_and_requirements_without_tests(tree):
    zip_path = package.build("fn")

    with zipfile.ZipFile(zip_path) as archive:
        names = sorted(archive.namelist())
    assert names == ["db.py", "lambda_function.py", "pg8000/__init__.py", "six.py"]


@pytest.mark.parametrize(
    ("create", "reported"),
    [
        (lambda fn: (fn / "six.py").write_text("", encoding="utf-8"), "lambdas/fn/six.py"),  # same file name
        (lambda fn: (fn / "pg8000.py").write_text("", encoding="utf-8"), "lambdas/fn/pg8000.py"),  # module vs package
        (lambda fn: (fn / "pg8000").mkdir(), "lambdas/fn/pg8000"),  # directory vs package
        (lambda fn: (fn / "six").mkdir(), "lambdas/fn/six"),  # directory vs module
    ],
)
def test_function_entry_named_like_an_installed_requirement_stops_the_build(tree, create, reported):
    create(tree)

    with pytest.raises(SystemExit) as raised:
        package.build("fn")

    assert str(raised.value) == f"name clash in build/lambdas/fn: {reported}"
    assert not (package.BUILD / "fn.zip").exists()


def test_requirements_are_resolved_for_the_lambda_runtime_python_3_12(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(package.subprocess, "run", lambda args, check: calls.append((args, check)))

    package._install_requirements(tmp_path / "requirements.txt", tmp_path)

    ((args, check),) = calls
    assert check is True
    assert args[args.index("--python-version") + 1] == "3.12"
    assert "--only-binary=:all:" in args and "--target" in args


def test_function_file_named_like_a_shared_helper_stops_the_build(tree):
    (tree / "db.py").write_text("", encoding="utf-8")

    with pytest.raises(SystemExit, match="^name clash in build/lambdas/fn: lambdas/shared/db.py$"):
        package.build("fn")
