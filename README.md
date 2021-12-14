# nPrintML

## Overview

nPrintML bridges the gap between [nPrint](https://nprint.github.io/nprint.html), which generates standard fingerprints for packets, and AutoML, which allows for optimized model training and traffic analysis. nPrintML enables users with network traffic and labels to perform optimized packet-level traffic analysis **without writing any code**.

For a high-level overview, installation instructions, and detailed usage information, please visit [the project's homepage](https://nprint.github.io/nprintml.html).

For brief [installation](#set-up) and [usage](#usage) instructions, or for the [Docker container demo](#demo), see below.


## Set-up

### Dependencies

Python versions 3.6 through 3.8 are supported.

You might check what versions of Python are installed on your system, _e.g._:

    ls -1 /usr/bin/python*

As needed, consult your package manager or [python.org](https://python.org/).

Depending on your situation, consider [pyenv](https://github.com/pyenv/pyenv) for easy installation and management of arbitrary versions of Python.

nPrintML further requires nPrint (see below).

### Installation

nPrintML itself is available for download from the [Python Package Index (PyPI)](https://pypi.org/project/nprintml/) and via `pip`, _e.g._:

    python -m pip install nprintml

(Note: The `python` or `pip` executable used to install nPrintML depends upon your system and as discussed in the [preceding section](#dependencies). And, for example, your system might supply a `python3` command, but _not_ a `python` command. As such, the above may be adapted to your system.)

This downloads, builds and installs the `nprintml` console command. If you're happy to manage your Python (virtual) environment, you're all set with the above.

That said, installation of this command via a tool such as [pipx](https://pipxproject.github.io/pipx/) is strongly encouraged. pipx will ensure that nPrintML is installed into its own virtual environment, such that its third-party libraries do not conflict with any others installed on your system.

(Note that nPrint and nPrintML are unrelated to the PyPI distribution named "nprint.")

### Post-installation

nPrintML depends on the nPrint command, which may be installed separately, (with reference to the [nPrint documentation](https://github.com/nprint/nprint/wiki/2.-Installation)).

For quick-and-easy satisfaction of this requirement, nPrintML supplies the bootstrapping command `nprint-install`, which is made available to your environment with nPrintML installed. This command will inspect its execution environment and attempt to retrieve, compile and install nPrint with the most appropriate defaults:

    nprint-install

nPrint may thereby be installed system-globally, to the user environment, to the (virtual) environment to which nPrintML was installed, or to a specified path prefix. Consult the command's `--help` for more information.

`nprint-install` is identically available through its Python module (no different from `pip` above):

    python -m nprintml.net.install

### Further set-up

nPrintML leverages [AutoGluon](https://auto.gluon.ai/) to manage AutoML. However, it _does not_ by default install additional libraries required for **all** models supported by AutoGluon. If you wish to test these models, you will need to install their requirements manually.

AutoGluon will itself note which models it is unable to generate – and how to satisfy their requirements – during operation.

For more information, consult the [AutoGluon documentation](https://auto.gluon.ai/).


## Usage

nPrintML supplies the top-level shell command `nprintml` &ndash;

    nprintml ...

&ndash; as well as its terse alias `nml` &ndash;

    nml ...

In case of command path ambiguity and in support of debugging, the `nprintml` command is also available through its Python module:

    python -m nprintml ...

For detailed usage information with full examples of how to run nPrintML, please visit our [homepage](https://nprint.github.io/nprintml_walk.html).


## Demo

A Docker container demo is provided of each nPrintML release to aid prospective users in trying out the tool.

Note: The container is intended for users of as-yet-unsupported platforms and users of atypically-configured systems. nPrintML _should_ install easily for most users, as described in the [preceding section](#set-up); and, for day-to-day use, it is **strongly recommended** that nPrintML be installed _without_ virtualization. nPrintML users requiring support in installing the tool should consult [the project's homepage](https://nprint.github.io/nprintml.html) and then consider [reaching out for help](https://github.com/nprint/nprintML/issues/new/choose). Users of unsupported platforms should consider creating a [feature request](https://github.com/nprint/nprintML/issues/new/choose) or a [pull request](https://github.com/nprint/nprintML/pulls).

### Dependencies

The container demo requires [Docker](https://www.docker.com/).

### Usage

The container entrypoint is the `nprintml` command, and as such takes the same arguments:

    docker run [...] ghcr.io/nprint/nprintml ...

Note, however, that any argument references to the host filesystem must be mapped to the container filesystem. For this reason, the `nprintml-docker` script is recommended.

#### Demo script

The `nprintml-docker` script is the recommended interface to the container demo. Argument references to the host filesystem are mapped and rewritten for the container filesystem; outputs are written to the host filesystem and given user ownership, _etc._

`nprintml-docker` requires Python v3.6 or greater.

The script is available for download from the [nPrintML repository](https://raw.githubusercontent.com/nprint/nprintML/main/image/nprintml-docker). It may be placed anywhere on your system, and made executable or invoked with either `python` or `python3`.

A reasonable installation of the script (globally) might include the following:

    DEST="/usr/local/bin"

    curl --output-dir "$DEST" -O https://raw.githubusercontent.com/nprint/nprintML/main/image/nprintml-docker

    chmod +x "$DEST"/nprintml-docker

The script should then be available for execution, even without reference to its full path, (so long as `DEST` above is itself in your environment's `PATH`):

    nprintml-docker ...

Note: In the above example, the script is installed to the system _globally_. This will likely require `root` permission &ndash; _e.g._ `sudo curl …` and `sudo chmod …`.

Alternatively, set a different `DEST`. The script may be placed wherever you have write access &ndash; including user directories which are also commonly placed on `PATH`: `$HOME/.local/bin`, `$HOME/bin`, _etc._

If `DEST` is not on `PATH`, the script may be invoked via its full download path, _e.g._:

    ~/Downloads/nprintml-docker ...

And if the script is not made executable, it may be invoked via any available `python` (v3.6+):

    python ~/Downloads/nprintml-docker ...

##### Environment variables

The script's interface is forwarded to `nprintml` within the demo container. The script itself may be configured via the following environment variables.

| Name | Values | Description |
| ---- | ------ | ----------- |
| `NPRINTML_DOCKER_CHOWN` | `0`, `1`\* | Outputs owned by `root` are given user ownership via `chown` (`1`) |
| `NPRINTML_DOCKER_DEBUG` | `0`\*, `1` | Enable debug-level logging to standard output (`1`) |
| `NPRINTML_DOCKER_REMOVE` | `0`, `1`\* | Container is removed after each run (`1`) |
| `NPRINTML_DOCKER_REPOSITORY` | (repository: `ghcr.io/nprint/nprintml`\*) | nPrintML repository of image |
| `NPRINTML_DOCKER_VERSION` | (version: `latest`\*) | nPrintML image version tag |

\* `default value`


## Development

Development requirements may be installed via the `dev` extra (below assuming a source checkout):

    pip install --editable .[dev]

(Note: The installation flag `--editable` is also used above to instruct `pip` to place the source checkout directory itself onto the Python path, to ensure that any changes to the source are reflected in Python imports.)

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
