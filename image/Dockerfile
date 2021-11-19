FROM python:3.8.12-bullseye

ARG NML_VERSION

LABEL dockerfile_version="1"            \
      nml_version="$NML_VERSION"

ENV PYTHONUNBUFFERED="1"

# install libpcap for nPrint
RUN set -ex                                     \
    && apt-get update                           \
    && apt-get install -y libpcap0.8-dev        \
    && rm -rf /var/lib/apt/lists/*

# install nprintML and nPrint
RUN set -ex                                                             \
    && python -m pip install --no-cache-dir nprintml=="$NML_VERSION"    \
    && nprint-install

ENTRYPOINT ["nprintml"]
