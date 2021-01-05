"""Subprocessing interface to nPrint command"""
import shutil
import subprocess


def nprint(*args, stdin=None, stdout=None, stderr=None, check=True):
    """Execute the `nprint` command via `subprocess`.

    Argumentation reflects that of `subprocess.run`.

    The `PIPE` sentinel is made available via the callable object:

        nprint.PIPE

    If the `nprint` command cannot be found on the PATH, then
    `NoCommand` is raised. This exception is also made available on the
    callable object --

        nprint.NoCommand

    -- as is `CommandError`, raised from the `subprocess` package's
    `CalledProcessError`.

    Returns the resulting `subprocess.CompletedProcess`.

    """
    try:
        return subprocess.run(
            _nprint_args(*args),
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            check=check,
        )
    except subprocess.CalledProcessError as exc:
        raise CommandError from exc


def nPrintProcess(*args, stdin=None, stdout=None, stderr=None):
    """Construct a subprocess to execute the `nprint` command.

    Argumentation reflects that of `subprocess.Popen`.

    The `PIPE` sentinel is made available via the object of the
    constructor:

        nPrintProcess.PIPE

    If the `nprint` command cannot be found on the PATH, then
    `NoCommand` is raised. This exception is also made available on the
    constructor --

        nPrintProcess.NoCommand

    Returns the constructed `subprocess.Popen` object with which to
    monitor the running command.

    """
    return subprocess.Popen(
        _nprint_args(*args),
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


def _nprint_args(*args):
    # ensure we know what we're running via which
    cmd = shutil.which('nprint')

    if cmd is None:
        raise NoCommand

    return (cmd,) + args


class nPrintError(Exception):
    pass


class CommandError(nPrintError):
    pass


class NoCommand(nPrintError):
    pass


nprint.CommandError = CommandError
nprint.NoCommand = NoCommand
nprint.PIPE = subprocess.PIPE

nPrintProcess.NoCommand = NoCommand
nPrintProcess.PIPE = subprocess.PIPE
