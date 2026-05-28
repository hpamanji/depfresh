# Installation

## Requirements

- **Python 3.11+** (depfresh uses the stdlib `tomllib`).
- **git** on your `PATH` — only needed for `depfresh update`; plain scanning and
  update-checking don't require it.

depfresh has **no third-party runtime dependencies**. Scanning and update checks
use only the standard library (`tomllib`, `json`, `xml.etree`, `urllib`).

## Install from GitHub

```console
pip install git+https://github.com/hpamanji/depfresh.git
```

## Install from a clone

```console
git clone https://github.com/hpamanji/depfresh.git
cd depfresh
pip install .
```

This installs a `depfresh` command. You can also run the module directly without
installing:

```console
python -m depfresh --version
```

## Verify

```console
depfresh --version
# depfresh 0.1.0
```

## Development install

To work on depfresh itself, install the dev extra (adds pytest, ruff, mypy):

```console
pip install -e ".[dev]"
pytest
```

See [Extending depfresh](extending.md) and the
[CONTRIBUTING guide](../CONTRIBUTING.md) for more.
