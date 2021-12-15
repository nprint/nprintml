"""nprintml"""
import pathlib

from pkg_resources import parse_requirements
from setuptools import find_packages, setup


DIR_PATH = pathlib.Path(__file__).parent

README_PATH = DIR_PATH / 'README.md'

REQUIREMENTS_PATH = DIR_PATH / 'requirement'


def get_requirements(path):
    with path.open() as fd:
        return list(map(str, parse_requirements(fd)))


_DEV_REQUIRES = get_requirements(REQUIREMENTS_PATH / 'dev.txt')

_TESTS_REQUIRE = get_requirements(REQUIREMENTS_PATH / 'test.txt')

EXTRAS_REQUIRE = {
    'dev': _DEV_REQUIRES + _TESTS_REQUIRE,
    'test': _TESTS_REQUIRE,
}


INSTALL_REQUIRES = [
    'argparse-formatter ~= 1.4',

    'Dickens ~= 2.0.0',

    'autogluon.tabular ~= 0.6.0',

    # autogluon *also* requires numpy and pandas so match autogluon:
    'numpy == 1.23.5; python_version >= "3.8"',
    'numpy == 1.21.6; python_version < "3.8"',

    'pandas == 1.5.1; python_version >= "3.8"',
    'pandas == 1.3.5; python_version < "3.8"',

    'pyarrow ~= 10.0.1',

    'matplotlib ~= 3.6.2; python_version >= "3.8"',
    'matplotlib ~= 3.5.3; python_version < "3.8"',

    'seaborn ~= 0.12.1',

    'toml ~= 0.10.2',
]


setup(name='nprintml',
      version='1.1.2',
      description='Fully automated traffic analysis with nPrint',
      long_description=README_PATH.read_text(),
      long_description_content_type="text/markdown",
      url='https://github.com/nprint/nprintml',
      license='License :: OSI Approved :: Apache Software License',
      python_requires='>=3.7,<3.10',
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Intended Audience :: Education',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'Intended Audience :: System Administrators',
          'Intended Audience :: Telecommunications Industry',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Topic :: Internet',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Scientific/Engineering',
          'Topic :: Scientific/Engineering :: Artificial Intelligence',
          'Topic :: System :: Networking :: Monitoring',
          'Topic :: Security',
          'Topic :: Terminals',
      ],
      packages=find_packages('src'),
      package_dir={'': 'src'},
      entry_points={
          'console_scripts': [
              'nml=nprintml.cli:execute',
              'nprintml=nprintml.cli:execute',
              'nprint-install=nprintml.net.install:execute',
            ],
      })
