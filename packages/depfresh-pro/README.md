# depfresh-pro

Automated dependency-update **PRs/MRs** for [depfresh](https://github.com/hpamanji/depfresh):
clone a repo, bump outdated declared manifests in place, push branch(es), and
open a pull request (GitHub) or merge request (GitLab) — idempotently.

This package builds on the MIT-licensed `depfresh` core and **depends downward**
on it; the core never depends on this package.

```console
pip install depfresh-pro          # also installs the depfresh core
depfresh update https://github.com/me/app --token "$GITHUB_TOKEN" --dry-run
```

Installing this package makes `depfresh update` available on the `depfresh` CLI
(via an entry point); you can also call `depfresh-pro` directly.

## License

**Dual-licensed:** GNU AGPL-3.0-or-later ([LICENSE](LICENSE)) **OR** a commercial
license ([COMMERCIAL.md](COMMERCIAL.md)). Choose AGPL for free/open use, or buy a
commercial license if AGPL's terms don't fit your organization.

© Hemachandar Pamanji
