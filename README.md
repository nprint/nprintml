# Overview

For a high level overview, installation instructions, and detailed usage information, please visit [the project's homepage](https://nprint.github.io/nprintml.html)

## Installing nPrintML

### Dependencies

Python versions 3.6 through 3.8 are supported.

You might check what versions of Python are installed on your system, _e.g._:

    ls -1 /usr/bin/python*

As needed, consult your package manager or [python.org](https://python.org/).

Depending on your situation, consider [pyenv](https://github.com/pyenv/pyenv) for easy installation and management of arbitrary versions of Python.

nprintML further requires nPrint (see below).

### Installation

nprintML itself is available for download from the [Python Package Index (PyPI)](https://pypi.org/project/nprintml/) and via `pip`:

    python -m pip install nprintml

This downloads, builds and installs the `nprintml` console command. If you're happy to manage your Python (virtual) environment, you're all set with the above.

That said, installation of this command via a tool such as [pipx](https://pipxproject.github.io/pipx/) is strongly encouraged. pipx will ensure that nprintML is installed into its own virtual environment, such that its third-party libraries do not conflict with any others installed on your system.

(Note that nPrint and nprintML are unrelated to the PyPI distribution named "nprint.")

### Post-installation

nprintML depends on the nPrint command, which may be installed separately, (with reference to the [nPrint documentation](https://github.com/nprint/nprint/wiki/2.-Installation)).

For quick-and-easy satisfaction of this requirement, nprintML supplies the bootstrapping command `nprint-install`, which is made available to your environment with nprintML installed. This command will inspect its execution environment and attempt to retrieve, compile and install nPrint with the most appropriate defaults:

    nprint-install

nPrint may thereby be installed system-globally, to the user environment, to the (virtual) environment to which nprintML was installed, or to a specified path prefix. Consult the command's `--help` for more information.

`nprint-install` is identically available through its Python module (no different from `pip` above):

    python -m nprintml.net.install

### Further set-up

nprintML leverages [AutoGluon](https://auto.gluon.ai/) to manage AutoML. However, it _does not_ by default install additional libraries required for **all** models supported by AutoGluon. If you wish to test these models, you will need to install their requirements manually.

AutoGluon will itself note which models it is unable to generate – and how to satisfy their requirements – during operation.

For more information, consult the [AutoGluon documentation](https://auto.gluon.ai/).


## Usage 
nprintML supplies the top-level shell command `nprintml` &ndash;

    nprintml ...

&ndash; as well as its terse alias `nml` &ndash;

    nml ...

In case of command path ambiguity and in support of debugging, the `nprintml` command is also available through its Python module:

    python -m nprintml ...
    
For detailed usage information with full examples of how to run nPrintML, please visit our [homepage](https://nprint.github.io/nprintml_walk.html)


## Development

Development requirements may be installed via the `dev` extra (below assuming a source checkout):

    pip install --editable .[dev]

(Note: the installation flag `--editable` is also used above to instruct `pip` to place the source checkout directory itself onto the Python path, to ensure that any changes to the source are reflected in Python imports.)

Development tasks are then managed via [argcmdr](https://github.com/dssg/argcmdr) sub-commands of `manage …`, (as defined by the repository module `manage.py`), _e.g._:

    manage version patch -m "initial release of nprintml" \
           --build                                        \
           --release
           
           
           
## Citing nPrintML

```
@inproceedings{10.1145/3460120.3484758,
author = {Holland, Jordan and Schmitt, Paul and Feamster, Nick and Mittal, Prateek},
title = {New Directions in Automated Traffic Analysis},
year = {2021},
isbn = {9781450384544},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
url = {https://doi.org/10.1145/3460120.3484758},
doi = {10.1145/3460120.3484758},
pages = {3366–3383},
numpages = {18},
keywords = {machine learning on network traffic, automated traffic analysis, network traffic analysis},
location = {Virtual Event, Republic of Korea},
series = {CCS '21}
}
```
