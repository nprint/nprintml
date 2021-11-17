"""nPrint installation bootstrapping command"""
import argparse
import enum
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

import argparse_formatter

import nprintml


NPRINT_RELEASE_NAME = f'nprint-{nprintml.__nprint_version__}'

NPRINT_ARCHIVE_NAME = f'{NPRINT_RELEASE_NAME}.tar.gz'

NPRINT_ARCHIVE_URL = (
    'https://github.com/nprint/nprint/releases/download/'
    f'v{nprintml.__nprint_version__}/{NPRINT_ARCHIVE_NAME}'
)

USER_LOCAL_PATH = pathlib.Path.home() / '.local'

PYENV_PATH = os.getenv('PYENV_ROOT') or pathlib.Path.home() / '.pyenv'

BUILD_COMMANDS = (
    ('sh', 'configure', '--prefix={prefix}'),
    ('make',),
    ('make', 'install'),
)

BUILD_DEPENDENCIES = (
    'argp',
    'pcap',
)


class PathOption(str, enum.Enum):
    """system installation path options"""

    system_global = ('system-globally', None)
    current_user = ('for the current user only', USER_LOCAL_PATH)
    same_environ = ('into the same environment as nprintML', sys.prefix)
    user_specified = ('under another arbitrary path', None)

    def __new__(cls, description, target):
        # we really want to treat these as str (description)
        # (with attributes set elsewhere)
        obj = super().__new__(cls, description)
        obj._value_ = description
        return obj

    def __init__(self, description, target):
        self.description = description
        self.target = target

    @classmethod
    def get_path_defaults(cls):
        """Select most appropriate default installation path given
        system context.

        """
        # if run as root assume they want to install globally
        try:
            geteuid = os.geteuid
        except AttributeError:
            # windows :/
            pass
        else:
            if geteuid() == 0:
                return cls.system_global

        # if python's environment prefix is writable --
        # likely a virtual environment --
        # default to installing alongside there
        if os.access(sys.prefix, os.W_OK):
            return cls.same_environ

        # finally -- safest -- default to the user's home path
        return cls.current_user

    @property
    def help_text(self):
        """verbose representation for help text"""
        help_text = self.description
        if self.target:
            help_text += f" ({self.target})"
        return help_text


def execute(argv=None, **parser_kwargs):
    """Execute the nPrint-installation CLI command."""
    path_option_default = PathOption.get_path_defaults()

    parser = argparse.ArgumentParser(
        description=(
            "install nPrint\n\n"

            "installation path:\n\n"

            "  Commands such as nPrint are frequently installed \"globally\" to a system – "
            "often under /usr/local/.\n\n"

            "  Specify any of the following options to install nPrint either:\n\n"

            + '\n\n'.join(f'    • {option}' for option in PathOption) + "\n\n" +

            "  For the current invocation and without options nPrint will be installed "
            f"by default {path_option_default.help_text}."
        ),
        formatter_class=argparse_formatter.FlexiFormatter,
        **parser_kwargs,
    )

    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help="ignore dependency errors",
    )

    installation_path = parser.add_mutually_exclusive_group()
    installation_path.add_argument(
        '-p', '--prefix',
        metavar='PATH',
        help="specify an arbitrary installation path prefix "
             "(generally an alternative to /usr/local/)",
    )
    installation_path.add_argument(
        '-g', '--global',
        action='store_const',
        const=None,
        dest='prefix',
        help="install system-globally (generally under /usr/local/ – may require sudo)",
    )
    installation_path.add_argument(
        '-u', '--user',
        action='store_const',
        const=PathOption.current_user.target,
        dest='prefix',
        help=f"install for current user only (under {PathOption.current_user.target})",
    )
    installation_path.add_argument(
        '-s', '--same',
        action='store_const',
        const=PathOption.same_environ.target,
        dest='prefix',
        help=f"install into same environment as nprintML (under {PathOption.same_environ.target})",
    )
    installation_path.set_defaults(
        prefix=path_option_default.target,
    )

    args = parser.parse_args(argv)

    (build_commands, missing_commands) = get_build_commands(prefix=args.prefix)

    if missing_commands:
        parser.error('missing requirement(s): ' + ', '.join(missing_commands))

    missing_dependencies = get_missing_dependencies()

    if missing_dependencies:
        dependencies_message = (
            'missing dependenc(ies): ' +
            ', '.join(missing_dependencies) +
            '\nconsult: https://github.com/nprint/nprint/wiki/2.-Installation'
        )
        if args.force:
            print('[warn]', dependencies_message, file=sys.stderr)
        else:
            parser.error(dependencies_message)

    execute_bootstrap(build_commands)

    # check for pyenv tip
    if args.prefix:
        try:
            pathlib.Path(args.prefix).relative_to(PYENV_PATH)
        except ValueError:
            # no apparent association with pyenv
            pass
        else:
            print('\nℹ nPrint appears to have been installed into a Pyenv environment – '
                  'rehash may be required before it is available for use:\n\n'
                  '\tpyenv rehash\n')


def get_build_commands(**kwargs):
    """Check for system availability of and return the system commands
    required to build nPrint.

    Command options may be populated via keyword argument. Unpopulated
    or null options are discarded.

    """
    context = {key: value for (key, value) in kwargs.items()
               if value is not None}

    def generate_command_args(args):
        for arg in args:
            try:
                yield arg.format_map(context)
            except KeyError:
                continue

    build_commands = [
        (shutil.which(cmd),) + tuple(generate_command_args(args))
        for (cmd, *args) in BUILD_COMMANDS
    ]

    missing_commands = {
        cmd for (found, cmd) in zip(
            (command[0] for command in build_commands),
            (command[0] for command in BUILD_COMMANDS),
        )
        if not found
    }

    return (
        build_commands,
        missing_commands,
    )


def get_missing_dependencies():
    """Look up dependencies & return those which could not be located."""
    whereis = shutil.which('whereis')

    if whereis is None:
        print('[warn] whereis command unavailable – '
              'cannot execute check for build dependencies',
              file=sys.stderr)

        return []

    dependency_results = (subprocess.check_output([whereis, lib]) for lib in BUILD_DEPENDENCIES)

    dependency_locations = (re.sub(rf'^{lib}: ?', '', result.decode())
                            for (lib, result) in zip(BUILD_DEPENDENCIES, dependency_results))

    try:
        return [
            lib for (lib, location) in zip(BUILD_DEPENDENCIES, dependency_locations)
            if not location.strip()
        ]
    except subprocess.CalledProcessError:
        print('[warn] whereis command failed – '
              'cannot execute check for build dependencies',
              file=sys.stderr)

        return []


def execute_bootstrap(commands):
    """Retrieve nPrint release & execute given installation commands."""
    with tempfile.TemporaryDirectory(prefix=f'{__name__}.') as tempdir:
        temp_path = pathlib.Path(tempdir)
        release_path = temp_path / NPRINT_RELEASE_NAME
        archive_path = temp_path / NPRINT_ARCHIVE_NAME

        urllib.request.urlretrieve(NPRINT_ARCHIVE_URL, archive_path)

        with tarfile.open(archive_path) as release_archive:
            release_archive.extractall(tempdir)

        for command in commands:
            print('→', *command, end='\n\n')

            try:
                subprocess.run(
                    command,
                    cwd=release_path,
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                print('\n✕ failed')
                sys.exit(exc.returncode)
            else:
                print()

    print('✓ success')


if __name__ == '__main__':
    execute()
