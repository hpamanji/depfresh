# Installation

## Requirements

- **Python 3.11+** (depfresh uses the stdlib `tomllib`).
- **git** on your `PATH` — only needed for `depfresh update`; plain scanning and
  update-checking don't require it.

depfresh has **no third-party runtime dependencies**. Scanning and update checks
use only the standard library (`tomllib`, `json`, `xml.etree`, `urllib`).

depfresh ships as two packages in one repo (an open-core monorepo): the MIT
**`depfresh`** core (scanning + update checks) and the AGPL/commercial
**`depfresh-pro`** add-on, which provides the `depfresh update` command.

## Install from GitHub

The packages live in subdirectories, so install them by subdirectory:

```console
# Core scanner (the `depfresh` command)
pip install "depfresh @ git+https://github.com/hpamanji/depfresh.git#subdirectory=packages/depfresh"

# Optional: the `depfresh update` add-on (also pulls in the core)
pip install "depfresh-pro @ git+https://github.com/hpamanji/depfresh.git#subdirectory=packages/depfresh-pro"
```

## Install from a clone

```console
git clone https://github.com/hpamanji/depfresh.git
cd depfresh
pip install packages/depfresh        # core only
pip install packages/depfresh-pro    # adds `depfresh update`
```

This installs a `depfresh` command. You can also run the core module directly
without installing:

```console
python -m depfresh --version
```

## Verify

```console
depfresh --version
# depfresh 0.1.1
```

## Development install

To work on depfresh itself, install both packages editable (the core's `dev`
extra adds pytest, ruff, mypy):

```console
pip install -e "packages/depfresh[dev]" -e packages/depfresh-pro
pytest
```

See [Extending depfresh](extending.md) and the
[CONTRIBUTING guide](../CONTRIBUTING.md) for more.
