"""nprintml"""
import pathlib

from setuptools import find_packages, setup


README_PATH = pathlib.Path(__file__).parent / 'README.md'

INSTALL_REQUIRES = [
    'argparse-formatter == 1.2',

    'numpy ~= 1.19.4',
    'pandas ~= 1.1.4',

    # for cuda, e.g.: mxnet_cu101 < 2.0.0
    'mxnet < 2.0.0',

    'autogluon ~= 0.0.15',
    'scikit-learn ~= 0.23.2',

    'matplotlib ~= 3.3.3',
    'seaborn ~= 0.11.0',
]

_DEV_REQUIRES = [
    'argcmdr==0.7.0',
    'bumpversion==0.6.0',
    'twine==3.2.0',
    'wheel==0.35.1',
]

_TESTS_REQUIRE = [
    'tox==3.20.1',
]

EXTRAS_REQUIRE = {
    'dev': _DEV_REQUIRES + _TESTS_REQUIRE,
    'test': _TESTS_REQUIRE,
}


setup(name='nprintml',
      version='0.0.7',
      description='Fully automated traffic analysis with nPrint',
      long_description=README_PATH.read_text(),
      long_description_content_type="text/markdown",
      url='https://github.com/nprint/nprintml',
      license='License :: OSI Approved :: Apache Software License',
      python_requires='>=3.6,<4',
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
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
