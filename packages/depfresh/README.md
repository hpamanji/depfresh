# depfresh

A dependency scanner that finds and parses dependency manifests across many
ecosystems and checks registries for newer versions. **Stdlib-only**, no
third-party runtime dependencies.

This is the **MIT-licensed core**. Automated update PRs/MRs live in the separate
[`depfresh-pro`](https://github.com/hpamanji/depfresh/tree/main/packages/depfresh-pro)
package (AGPL-3.0 or commercial).

```console
pip install depfresh
depfresh --check-updates
```

See the [project README](https://github.com/hpamanji/depfresh) and
[docs](https://github.com/hpamanji/depfresh/tree/main/docs) for full usage.

## License

[MIT](LICENSE) © Hemachandar Pamanji
