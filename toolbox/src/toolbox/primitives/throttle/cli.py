"""throttle primitive — explicit pacing for the rare flow that WANTS it.

Appears in no default chain (spec §9: speed is the optimization target; the
harness never throttles proactively). A flow opts in by adding a line like
`- throttle.wait: {seconds: 600}` between steps.
"""

from __future__ import annotations

import sys
import time

import typer

from toolbox.core import events

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _group():
    """throttle primitive."""


@app.command()
def wait(seconds: float = typer.Option(..., "--seconds")):
    events.emit("throttle.wait", seconds=seconds)
    time.sleep(seconds)


if __name__ == "__main__":
    sys.exit(app())
