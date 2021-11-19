"""nprintML development management commands

This module populates ``manage`` sub-commands.

"""
import copy
import pathlib
import re

from argparse import REMAINDER

import argparse_formatter
from argcmdr import local, Local, localmethod, LocalRoot


DISTRO_NAME = 'nprintml'

REPO_OWNER = 'nprint'
REPO_NAME = 'nprintML'
REPO_URI = f'https://github.com/{REPO_OWNER}/{REPO_NAME}'

REGISTRY_URI = f'ghcr.io/{REPO_OWNER}/{DISTRO_NAME}'

REPO_ROOT = pathlib.Path(__file__).absolute().parent


class Manage(LocalRoot):
    """manage the nprintML repository"""


@Manage.register
@local('remainder', metavar='...', nargs=REMAINDER,
       help="additional arguments for tox (include a '-' to pass options)")
def test(self, args):
    """run tests"""
    if args.remainder and args.remainder[0] == '-':
        remainder = args.remainder[1:]
    else:
        remainder = args.remainder

    return (self.local.FG, self.local['tox'][remainder])


@Manage.register
class Version(Local):
    """bump version

    optionally: build & release

    """
    bump_default_message = "Bump version: {current_version} → {new_version}"

    formatter_class = argparse_formatter.ParagraphFormatter

    def __init__(self, parser):
        parser.add_argument(
            'part',
            choices=('major', 'minor', 'patch'),
            help="part of the version to be bumped",
        )
        parser.add_argument(
            '-m', '--message',
             help=f"Tag message (in addition to default: "
                  f"'{self.bump_default_message}')",
        )

        parser.add_argument(
            '--build',
            action='store_true',
            help='build the new version',
        )
        parser.add_argument(
            '--release',
            action='store_true',
            help='release the new build',
        )

    def prepare(self, args, parser):
        if args.message:
            tag_message = f"{self.bump_default_message}\n\n{args.message}"
        else:
            tag_message = self.bump_default_message

        (_code,
         stdout,
         _err) = yield self.local['bumpversion'][
            '--tag-message', tag_message,
            '--list',
            args.part,
        ]

        if args.build:
            yield self.root['build'].prepare()

            if args.release:
                rel_args = copy.copy(args)
                if stdout is None:
                    rel_args.versions = ('DRY-RUN',)
                else:
                    (version_match,) = re.finditer(
                        r'^new_version=([\d.]+)$',
                        stdout,
                        re.M,
                    )
                    rel_args.versions = version_match.groups()
                yield self.root['release'].prepare(rel_args)
        elif args.release:
            parser.error('will not release package without build')


@Manage.register
class Build(Local):
    """build package"""

    def prepare(self):
        return self.local.FG, self.local['python'][
            'setup.py',
            'sdist',
            'bdist_wheel',
        ]


@Manage.register
class Release(Local):
    """upload package(s) to pypi"""

    # TODO: add support for upload to test.pypi.org
    # (See also: https://github.com/bast/pypi-howto)
    #
    # NOTE: also, could set up a Github workflow that automatically builds for
    # us, (triggered by say a tag or *maybe* even a push); perhaps stores that
    # artifact in Github Packages; and even uploads it to PyPI, or at least to
    # test.pypi.org.
    # (This might be convenient. It also might alleviate set-up work -- and any
    # concerns -- over credentials sharing.)
    # (See also: https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

    def __init__(self, parser):
        parser.add_argument(
            'versions',
            metavar='version',
            nargs='*',
        )

    def prepare(self, args):
        if args.versions:
            target = [f'dist/{DISTRO_NAME}-{version}*' for version in args.versions]
        else:
            target = [f'dist/{DISTRO_NAME}-*']

        return self.local.FG, self.local['twine']['upload'][target]


@Manage.register
class Image(Local):
    """manage docker image"""

    @localmethod('version', help="version of nprintML to build (e.g. 1.0.4)")
    @localmethod('--no-latest', action='store_false', dest='latest',
                 help='do NOT tag image as "latest"')
    def build(self, args):
        """build image"""
        cmd = self.local['docker'][
            'build',
            '--label', f'org.opencontainers.image.source={REPO_URI}',
            '--build-arg', f'NML_VERSION={args.version}',
            '--tag', f'{REGISTRY_URI}:{args.version}',
        ]

        if args.latest:
            cmd = cmd['--tag', f'{REGISTRY_URI}:latest']

        return self.local.FG, cmd[REPO_ROOT / 'image']
