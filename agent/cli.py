from pathlib import Path
import typer
from rich import print

from .config import Settings
from .orchestrator import run_collection, run_analysis_on_report

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


@app.command()
def reanalyze(
    report_path: Path = typer.Option(..., help="Path to the JSON report to re-analyze."),
    reports_dir: Path = typer.Option(DEFAULT_REPORTS_DIR),
):
    """Re-run analysis on an existing JSON report."""
    if not report_path.exists():
        print(f"[red]Error: Report file not found at {report_path}[/]")
        raise typer.Exit(code=1)

    settings = Settings.load({})  # Load default settings
    run_analysis_on_report(report_path, reports_dir, settings)


@app.callback()
def main():
    """Root command callback (no options yet)."""
    pass


if __name__ == "__main__":
    app()
