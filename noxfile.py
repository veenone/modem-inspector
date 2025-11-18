"""Nox automation configuration for Modem Inspector.

Provides automated testing, linting, formatting, and build tasks.
"""

import nox

# Default sessions to run
nox.options.sessions = ["lint", "tests"]
nox.options.reuse_existing_virtualenvs = True


@nox.session(python=["3.8", "3.9", "3.10", "3.11", "3.12"])
def tests(session):
    """Run the test suite."""
    session.install("-e", ".[dev]")
    session.run("pytest", *session.posargs)


@nox.session(python="3.10")
def tests_gui(session):
    """Run GUI-specific tests."""
    session.install("-e", ".[dev,gui]")
    session.run("pytest", "-m", "gui", *session.posargs)


@nox.session(python="3.10")
def coverage(session):
    """Run tests with coverage reporting."""
    session.install("-e", ".[dev]")
    session.run(
        "pytest",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        *session.posargs
    )


@nox.session(python="3.10")
def lint(session):
    """Run linters (flake8 and mypy)."""
    session.install("-e", ".[dev]")
    session.run("flake8", "src", "tests")
    session.run("mypy", "src")


@nox.session(python="3.10")
def format(session):
    """Format code with black."""
    session.install("black")
    session.run("black", "src", "tests", "main.py", "noxfile.py")


@nox.session(python="3.10")
def format_check(session):
    """Check code formatting with black."""
    session.install("black")
    session.run("black", "--check", "src", "tests", "main.py", "noxfile.py")


@nox.session(python="3.10")
def build(session):
    """Build distribution packages."""
    session.install("build", "twine")
    session.run("python", "-m", "build")
    session.run("twine", "check", "dist/*")


@nox.session(python="3.10")
def docs(session):
    """Build documentation."""
    session.install("-e", ".[dev]")
    session.install("sphinx", "sphinx-rtd-theme")
    session.run("sphinx-build", "-b", "html", "docs", "docs/_build/html")


@nox.session(python="3.10")
def validate_plugins(session):
    """Validate all plugin YAML files."""
    session.install("-e", ".")
    session.run("python", "main.py", "--validate-all-plugins")


@nox.session(python="3.10")
def tests_unit(session):
    """Run unit tests only."""
    session.install("-e", ".[dev]")
    session.run("pytest", "tests/unit", "-v", *session.posargs)


@nox.session(python="3.10")
def tests_integration(session):
    """Run integration tests only."""
    session.install("-e", ".[dev]")
    session.run("pytest", "tests/integration", "-v", *session.posargs)


@nox.session(python="3.10")
def tests_reports(session):
    """Run report generation tests only."""
    session.install("-e", ".[dev]")
    session.run("pytest", "tests/unit/test_report*.py", "tests/unit/test_*_reporter.py", "-v", *session.posargs)


@nox.session(python="3.10")
def tests_parsers(session):
    """Run parser layer tests only."""
    session.install("-e", ".[dev]")
    session.run("pytest", "-k", "parser", "-v", *session.posargs)


@nox.session(python="3.10")
def tests_at_engine(session):
    """Run AT command engine tests only."""
    session.install("-e", ".[dev]")
    session.run("pytest", "tests/unit/test_at_executor.py", "tests/unit/test_serial_handler.py", "tests/unit/test_command_response.py", "-v", *session.posargs)


@nox.session(python="3.10")
def tests_quick(session):
    """Quick test run (unit tests, no coverage, fast fail)."""
    session.install("-e", ".[dev]")
    session.run("pytest", "tests/unit", "-x", "--tb=short", *session.posargs)


@nox.session(python="3.10")
def ci(session):
    """Run full CI pipeline (tests + coverage + lint)."""
    session.install("-e", ".[dev]")
    session.run(
        "pytest",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "--cov-fail-under=80",
        "-v"
    )
    session.run("flake8", "src", "tests")
    session.run("mypy", "src", "--ignore-missing-imports")


@nox.session(python="3.10")
def clean(session):
    """Clean build artifacts and caches."""
    import shutil
    from pathlib import Path

    patterns = [
        "build",
        "dist",
        "*.egg-info",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".coverage",
        "htmlcov",
        ".nox"
    ]

    for pattern in patterns:
        for path in Path(".").rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                session.log(f"Removed directory: {path}")
            elif path.is_file():
                path.unlink()
                session.log(f"Removed file: {path}")
