"""nprintml"""
import pathlib

from pkg_resources import parse_requirements
from setuptools import find_packages, setup


DIR_PATH = pathlib.Path(__file__).parent

README_PATH = DIR_PATH / 'README.md'

REQUIREMENTS_PATH = DIR_PATH / 'requirement'

INSTALL_REQUIRES = [
    'argparse-formatter ~= 1.4',
    'Dickens ~= 1.0.1',

    'autogluon.tabular ~= 0.1.0',

    # autogluon.core *also* requires numpy, so match autogluon
    'numpy == 1.19.5',

    'pandas ~= 1.1.5',
    'pyarrow ~= 4.0.0',

    'matplotlib ~= 3.3.4',
    'seaborn ~= 0.11.1',

    'toml ~= 0.10.2',
]

with (REQUIREMENTS_PATH / 'dev.txt').open() as dev_fd:
    _DEV_REQUIRES = list(map(str, parse_requirements(dev_fd)))

_TESTS_REQUIRE = [
    'tox==3.23.0',
]

EXTRAS_REQUIRE = {
    'dev': _DEV_REQUIRES + _TESTS_REQUIRE,
    'test': _TESTS_REQUIRE,
}


setup(name='nprintml',
      version='1.1.1',
      description='Fully automated traffic analysis with nPrint',
      long_description=README_PATH.read_text(),
      long_description_content_type="text/markdown",
      url='https://github.com/nprint/nprintml',
      license='License :: OSI Approved :: Apache Software License',
      python_requires='>=3.6,<3.9',
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
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
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
