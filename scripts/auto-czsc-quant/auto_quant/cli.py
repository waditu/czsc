"""Command line entrypoint for auto-czsc-quant."""

from __future__ import annotations

from pathlib import Path

import typer

from auto_quant.goal_prompt import build_goal_prompt
from auto_quant.runner import run_experiment
from auto_quant.schema import load_config

app = typer.Typer(help="Run LLM-guided CZSC position experiments.")


@app.command()
def run(
    config: Path = typer.Option(..., "--config", "-c", exists=True, readable=True, help="Experiment config JSON/YAML"),
) -> None:
    """Validate candidates, run mock-data backtests, and write a leaderboard."""
    result = run_experiment(load_config(config))
    typer.echo(f"run_dir={result.run_dir}")
    typer.echo(f"leaderboard={result.leaderboard_path}")
    typer.echo(f"accepted={result.accepted_count} rejected={result.rejected_count}")


@app.command()
def prompt(
    run_dir: Path = typer.Option(..., "--run-dir", exists=True, file_okay=False, help="Previous experiment run dir"),
) -> None:
    """Print a narrow Claude Code /goal prompt for the next candidate round."""
    typer.echo(build_goal_prompt(run_dir))


if __name__ == "__main__":
    app()
