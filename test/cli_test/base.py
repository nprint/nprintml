import contextlib
import functools
import io
import pathlib
import sys
import typing
import unittest

from nprintml import cli

from test.base import mktestdir


TEST_ROOT = pathlib.Path(__file__).parent.parent

TEST_DATA = TEST_ROOT / 'data'


def testdir(func):
    """Decorator to wrap given function such that a temporary directory
    is created and destroyed for each invocation.

    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with mktestdir(f'nprintml.{func.__module__}.{func.__name__}.') as tempdir:
            return func(*args, tempdir, **kwargs)

    return wrapper


class TeeIO:

    def __init__(self, *targets):
        self.targets = targets

    def write(self, content):
        for target in self.targets:
            target.write(content)


class CLITestCase(unittest.TestCase):

    class ExecutionResult(typing.NamedTuple):

        stdout: typing.Optional[str]
        stderr: typing.Optional[str]
        code: typing.Optional[int]

        @classmethod
        def from_stringio(cls, stdout, stderr, code):
            outputs = (None if output is None else output.getvalue()
                       for output in (stdout, stderr))
            return cls(*outputs, code)

    class CommandError(Exception):

        def __init__(self, code, result):
            super().__init__(code, result.stdout, result.stderr)
            self.code = code
            self.result = result

    def try_execute(self, *argv, raise_exc=True, stdout=False, stderr=False):
        with contextlib.ExitStack() as stack:
            outputs = []

            for (should_redirect, redirect_manager, output0) in (
                (stdout, contextlib.redirect_stdout, sys.stdout),
                (stderr, contextlib.redirect_stderr, sys.stderr),
            ):
                if should_redirect:
                    output1 = io.StringIO()
                    stack.enter_context(redirect_manager(TeeIO(output0, output1)))
                else:
                    output1 = None

                outputs.append(output1)

            code = None

            try:
                cli.execute(map(str, argv))
            except SystemExit as exc:
                code = exc.code

                if raise_exc and code > 0:
                    result = self.ExecutionResult.from_stringio(*outputs, code)
                    raise self.CommandError(exc.code, result) from exc

        return self.ExecutionResult.from_stringio(*outputs, code)
