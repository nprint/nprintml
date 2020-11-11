"""Subprocessing interface to nPrint command"""
import shutil
import subprocess


class NoCommand(Exception):
    pass


def nprint(*args, stdin=None, stdout=None, stderr=None, check=True):
    """Execute the `nprint` command via `subprocess`.

    Argumentation reflects that of `subprocess.run`.

    The `PIPE` sentinel is made available via the callable object:

        nprint.PIPE

    If the `nprint` command cannot be found on the PATH, then
    `NoCommand` is raised. This exception is also made available on the
    callable object:

        nprint.NoCommand

    Returns the resulting `subprocess.CompletedProcess`.

    """
    # ensure we know what we're running via which
    cmd = shutil.which('nprint')

    if cmd is None:
        raise NoCommand

    return subprocess.run(
        (cmd,) + args,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        check=check,
    )


nprint.NoCommand = NoCommand
nprint.PIPE = subprocess.PIPE
