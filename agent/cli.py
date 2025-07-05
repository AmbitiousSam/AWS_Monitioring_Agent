from pathlib import Path
import typer
from rich import print

from .config import Settings
from .orchestrator import run_collection

app = typer.Typer(help="AWS diagnostic agent – local-first MVP")
DEFAULT_REPORTS_DIR = Path(__file__).parent.parent / "reports"


@app.command()
def collect(
    profile: str = typer.Option(None, help="AWS CLI profile name"),
    lookback: int = typer.Option(None, help="Hours to look back"),
    threads: int = typer.Option(None, help="Thread pool size (0=auto)"),
    reports_dir: Path = typer.Option(DEFAULT_REPORTS_DIR),
):
    """Run the diagnostics collection."""
    settings = Settings.load(
        {
            "aws.profile": profile,
            "aws.lookback_hours": str(lookback) if lookback else None,
            "aws.threads": str(threads) if threads is not None else None,
        }
    )
    json_path = run_collection(settings, reports_dir)
    print(f"[green]✔ Diagnostic run completed. JSON saved to {json_path}[/]")


@app.callback()
def main():
    """Root command callback (no options yet)."""
    pass


if __name__ == "__main__":
    app()
