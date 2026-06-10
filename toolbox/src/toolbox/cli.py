"""`toolbox` — the umbrella CLI.

  toolbox auth login | connect <provider> | whoami
  toolbox run <skill> [-i key=value ...] [--yes]
  toolbox resume <run_id>
  toolbox fork <src> <dst>
"""

from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True, help=__doc__)
auth_app = typer.Typer(no_args_is_help=True, help="Per-person auth (Supabase).")
app.add_typer(auth_app, name="auth")


@auth_app.command("login")
def auth_login():
    """Sign in with Google; session is stored in the OS keychain."""
    from toolbox.core import auth

    auth.login()
    user = auth.whoami()
    typer.echo(f"Signed in as {user.get('email')}")


@auth_app.command("whoami")
def auth_whoami():
    from toolbox.core import auth

    user = auth.whoami()
    typer.echo(user.get("email", "<unknown>"))


@auth_app.command("connect")
def auth_connect(
    provider: str = typer.Argument(help="gmail | clay | anthropic"),
    org_shared: bool = typer.Option(False, help="Share this key with the whole org (team keys)."),
):
    """Connect an integration to YOUR account (spec §8)."""
    from toolbox.core import auth

    if provider == "gmail":
        url = auth.connect_oauth_start("gmail")
        typer.echo("Open this URL and grant Gmail access for the SENDING account")
        typer.echo("(armaan.priyadarshan.29@dartmouth.edu — see brain/company/connections.md):")
        typer.echo(f"\n  {url}\n")
        import webbrowser

        webbrowser.open(url)
    else:
        key = typer.prompt(f"{provider} API key", hide_input=True)
        auth.connect_api_key(provider, key, org_shared=org_shared)
        typer.echo(f"Stored {provider} key (org_shared={org_shared}).")


def _parse_overrides(pairs: list[str]) -> dict:
    out = {}
    for p in pairs:
        if "=" not in p:
            raise typer.BadParameter(f"expected key=value, got {p!r}")
        k, _, v = p.partition("=")
        out[k] = v
    return out


@app.command()
def run(
    skill: str,
    input_: list[str] = typer.Option([], "--input", "-i", help="Override an input: key=value"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Accept all input defaults (no clarify pause)."),
):
    """Execute a skill's flow.yaml as a new run."""
    from toolbox.core import runner

    run_dir, state = runner.run_skill(skill, _parse_overrides(input_), assume_yes=yes)
    typer.echo(f"{state}: {run_dir.name}")
    if state == "done":
        report = run_dir / "report.md"
        if report.exists():
            typer.echo(report.read_text(encoding="utf-8"))


@app.command()
def resume(
    run_id: str,
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Continue a paused or interrupted run (skips completed steps)."""
    from toolbox.core import runner

    state = runner.resume(run_id, assume_yes=yes)
    typer.echo(f"{state}: {run_id}")


@app.command()
def fork(src: str, dst: str):
    """Copy a skill (spec §6 fork reflex). Then edit inputs.yaml / flow.yaml and run."""
    from toolbox.core import runner

    path = runner.fork(src, dst)
    typer.echo(f"Forked → {path}\nEdit inputs.yaml (and delete any flow steps you don't want), then: toolbox run {dst}")


if __name__ == "__main__":
    app()
