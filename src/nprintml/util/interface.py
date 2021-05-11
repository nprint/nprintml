import argparse
import os
import pathlib


class HelpAction(argparse.Action):
    """Pluggable "help" action.

    Based on the built-in "help" action, enabling the definition of
    additional "--help-*" flags.

    Help output must be printed by the given callable `help_action`.

    When the flag is set, `help_action` is invoked and then the process
    is exited.

    """
    def __init__(self,
                 option_strings,
                 *,
                 help_action,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

        self.help_action = help_action

    def __call__(self, parser, namespace, values, option_string=None):
        self.help_action(parser, namespace, values, option_string)
        parser.exit()


class NumericRangeType:
    """Argument type validating that given value is of configured
    numeric type and bounds.

    Bounds may be specified as either `list` or `tuple`, the convention
    indicating whether bounds are "inclusive" or "non-inclusive",
    respectively.

    Either the lower or upper bound may be specified as `None`,
    indicating no bound.

    For example:

        parser.add_argument(
            '--test-size',
            default=0.3,
            metavar='FLOAT',
            type=NumericRangeType(float, (0, 1)),
        )

    The above argument, `--test-size`, will cast its input to `float`,
    (or print an error for non-float input). Moreover, a "not in range"
    error will be printed for inputs equal to zero or equal to or
    greater than one.

        parser.add_argument(
            '--threads',
            default=1,
            metavar='INTEGER',
            type=NumericRangeType(int, (0, None)),
        )

    In the above example, inputs are instead enforced as `int`; and,
    there is _only_ a lower bound -- inputs must only be greater than
    zero.

        parser.add_argument(
            '-q', '--quality',
            default=0,
            metavar='INTEGER',
            type=NumericRangeType(int, [0, 4]),
        )

    Arguments may also be given inclusive bounds, as above -- inputs to
    this example must be greater than or equal to zero, and less than or
    equal to four.

    """
    bounds_message = "upper and lower bounds must be list or tuple of two elements"

    def __init__(self, numeric_type, bounds):
        self.numeric_type = numeric_type

        try:
            (self.lower_bound, self.upper_bound) = bounds
        except ValueError as exc:
            raise ValueError(f"{self.bounds_message} not: {bounds!r}") from exc
        except TypeError as exc:
            raise TypeError(
                f"{self.bounds_message} not {bounds.__class__.__name__}: {bounds!r}"
            ) from exc

        if isinstance(bounds, tuple):
            self.inclusive = False
        elif isinstance(bounds, list):
            self.inclusive = True
        else:
            raise TypeError(f"{self.bounds_message} not {bounds.__class__.__name__}: {bounds!r}")

    def __call__(self, value):
        try:
            number = self.numeric_type(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not {self.numeric_type.__name__}: {value!r}")

        if self.inclusive:
            if (
                (self.lower_bound is not None and number < self.lower_bound) or
                (self.upper_bound is not None and number > self.upper_bound)
            ):
                raise argparse.ArgumentTypeError(
                    f"not in range [{self.lower_bound}, {self.upper_bound}]: {number!r}"
                )
        else:
            if (
                (self.lower_bound is not None and number <= self.lower_bound) or
                (self.upper_bound is not None and number >= self.upper_bound)
            ):
                raise argparse.ArgumentTypeError(
                    f"not in range ({self.lower_bound}, {self.upper_bound}): {number!r}"
                )

        return number


class FileAccessType:
    """Argument type to test a supplied filesystem path for specified
    access.

    Access level is indicated by bit mask.

    `argparse.FileType` may be preferred when the path should be opened
    in-process. `FileAccessType` allows for greater flexibility -- such
    as passing the path on to a subprocess -- while still validating
    access to the path upfront.

    """
    modes = {
        os.X_OK: 'execute',
        os.W_OK: 'write',
        os.R_OK: 'read',
        os.R_OK | os.X_OK: 'read-execute',
        os.R_OK | os.W_OK: 'read-write',
        os.R_OK | os.W_OK | os.X_OK: 'read-write-execute',
    }

    def __init__(self, access):
        self.access = access

        if access not in self.modes:
            raise ValueError("bad mask", access)

    @property
    def mode(self):
        return self.modes[self.access]

    def __call__(self, path):
        if os.path.isfile(path) and os.access(path, self.access):
            return path

        raise argparse.ArgumentTypeError(f"can't access file at '{path}' ({self.mode})")


class DirectoryAccessType:
    """Argument type to test a supplied filesystem directory path."""

    def __init__(self, *, ext='', exists=None, empty=False, non_empty=False):
        if ext:
            non_empty = True

        if non_empty:
            exists = True

        if empty and non_empty:
            raise TypeError("directory cannot be both empty and non-empty")

        self.ext = ext
        self.exists = exists
        self.empty = empty
        self.non_empty = non_empty

    def __call__(self, value):
        path = pathlib.Path(value)

        if self.exists is not None:
            if self.exists:
                if not path.is_dir():
                    raise argparse.ArgumentTypeError(f"no such directory '{value}'")
            else:
                if path.exists():
                    raise argparse.ArgumentTypeError(f"path already exists '{value}'")

                if not os.access(path.parent, os.W_OK):
                    raise argparse.ArgumentTypeError(f"path not write-accessible '{value}'")

        if self.empty and any(path.glob('*')):
            raise argparse.ArgumentTypeError(f"directory is not empty '{value}'")

        if self.non_empty:
            count = 0
            for (count, child) in enumerate(path.rglob('*' + self.ext), 1):
                if not os.access(child, os.R_OK):
                    raise argparse.ArgumentTypeError(f"path(s) not read-accessible '{child}'")

            if count == 0:
                raise argparse.ArgumentTypeError("directory has no contents " +
                                                 (f"({self.ext}) " if self.ext else "") +
                                                 f"'{value}'")

        return path
