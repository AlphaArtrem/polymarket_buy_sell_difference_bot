import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_cli_help_lists_core_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "catalog-refresh" in result.stdout
    assert "record-live" in result.stdout
    assert "run-replay" in result.stdout
    assert "run-paper" in result.stdout


def test_python_module_help_invokes_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "polymarket_arb.cli", "--help"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src"},
    )
    assert result.returncode == 0
    assert "catalog-refresh" in result.stdout
