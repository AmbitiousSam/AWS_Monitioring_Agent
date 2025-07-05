import subprocess
from pathlib import Path


def test_help_runs():
    """CLI --help should exit 0."""
    result = subprocess.run(
        ["poetry", "run", "aws-diag", "--help"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
    )
    assert result.returncode == 0
