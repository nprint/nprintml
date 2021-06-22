# nprintML

nprintML bridges the gap between [nPrint](https://nprint.github.io/nprint/), which generates standard fingerprints for packets, and AutoML, which allows for optimized model training and traffic analysis. nprintML enables users with network traffic and labels to perform optimized packet-level traffic analysis **without writing any code**.


## Getting It

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


## Using It

nprintML supplies the top-level shell command `nprintml` &ndash;

    nprintml ...

&ndash; as well as its terse alias `nml` &ndash;

    nml ...

In case of command path ambiguity and in support of debugging, the `nprintml` command is also available through its Python module:

    python -m nprintml ...

The nPrintML traffic analysis pipeline is customizable. Traffic ingestion leverages nPrint, and as such supports its inputs. In addition, beyond a single PCAP file, nprintML may ingest multiple PCAP files and recursive directories of files, as outlined [in the wiki](https://github.com/nprint/nprintML/wiki).

A simple example involves per-packet machine learning given a single PCAP and IP address labels:

    nprintml --ipv4 --pcap-file test.pcap --label-file labels.txt --aggregator index

The above instructs nprintML to execute a traffic analysis pipeline considering each packet in the file `test.pcap` as a sample, and to attach labels to each source IP address (nPrint's default index) as specified in `labels.txt`.

The label file should be formatted as follows:

    Item,Label  # (optional header line)
    IP1,label1
    IP2,label2
    IP3,label3
    ...

Through this labeling scheme we can attach labels to ports, ip addresses, and entire flows with nPrintML. For more information and advanced usage see [the wiki](https://github.com/nprint/nprintML/wiki).

Another example of using nPrintML is running a machine learning pipeline where every PCAP is considered to contain a single sample. The following command &ndash; (this time using terse aliases) &ndash; will create a machine learning pipeline using every PCAP file in the directory `pcaps/` and the labels in `labels.txt` with IPv4 nPrints:

    nml -4 --pcap-dir pcaps/ -L labels.txt -a pcap

The label file for the above follows the same format as in single PCAP usage, with only the `Item` column changing to specify file names as opposed to IP addresses:

    item,label  # (optional header line)
    path/name1.pcap,label1
    path/name2.pcap,label2
    path/name3.pcap,label3
    ...

Note that the `path/` in the above example is the path relative to the directory specified by `--pcap-dir`, that is relative to the directory `pcaps/`.


## Development

Development requirements may be installed via the `dev` extra (below assuming a source checkout):

    pip install --editable .[dev]

(Note: the installation flag `--editable` is also used above to instruct `pip` to place the source checkout directory itself onto the Python path, to ensure that any changes to the source are reflected in Python imports.)

Development tasks are then managed via [argcmdr](https://github.com/dssg/argcmdr) sub-commands of `manage …`, (as defined by the repository module `manage.py`), _e.g._:

    manage version patch -m "initial release of nprintml" \
           --build                                        \
           --release
