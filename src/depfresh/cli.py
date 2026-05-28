"""Command-line interface for depfresh."""

from __future__ import annotations

import argparse
import json
import sys

from depfresh import __version__
from depfresh.bump import BumpPlan, build_bump_plan
from depfresh.config import DepfreshConfig, RegistryConfig, load_config, merge
from depfresh.models import ScanResult
from depfresh.forge.base import ForgeError
from depfresh.resolver import (
    CURRENT,
    ERROR,
    NOT_FOUND,
    OUTDATED,
    UNKNOWN,
    UpdateInfo,
    check_updates,
)
from depfresh.scanner import scan
from depfresh.updater import GROUPINGS, UpdateError, UpdateRun, run_update
from depfresh.vcs import GitError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="depfresh",
        description="Scan a project for dependency manifests and list their dependencies.",
    )
    # Flags default to None so an unset flag falls through to the config file;
    # boolean flags use the --flag/--no-flag form so the CLI can override a
    # config-enabled value in either direction.
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="File or directory to scan (default: current directory).",
    )
    parser.add_argument(
        "--json",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Emit results as JSON instead of a table.",
    )
    parser.add_argument(
        "-e",
        "--ecosystem",
        action="append",
        default=None,
        metavar="NAME",
        help="Only report this ecosystem (repeatable), e.g. -e python -e node.",
    )
    parser.add_argument(
        "--manifests-only",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="List the detected manifest files without their dependencies.",
    )
    parser.add_argument(
        "--flat",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="List every package as a flat record paired with its source file.",
    )
    parser.add_argument(
        "-u",
        "--check-updates",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Query registries for the latest version and flag outdated deps (network).",
    )
    parser.add_argument(
        "--outdated-only",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show only outdated dependencies (implies --check-updates).",
    )
    parser.add_argument(
        "--bump-plan",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Group outdated deps by package across manifests (implies --check-updates).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Per-request registry timeout when checking updates (default: 10).",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=None,
        metavar="N",
        help="Parallel registry requests when checking updates (default: 16).",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to a depfresh JSON config file (default: auto-discover depfresh.json / ~/.depfresh.json).",
    )
    parser.add_argument(
        "--registry",
        action="append",
        metavar="ECO=URL",
        help="Override a registry base URL, e.g. --registry python=https://pypi.acme.com (repeatable).",
    )
    parser.add_argument(
        "--registry-token",
        action="append",
        metavar="ECO=TOKEN",
        help="Bearer token for a registry, e.g. --registry-token node=$NPM_TOKEN (repeatable).",
    )
    parser.add_argument(
        "--exit-code",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Exit with status 1 if any outdated dependency is found.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"depfresh {__version__}",
    )
    return parser


def _parse_kv(items: list[str] | None) -> dict[str, str]:
    """Parse repeatable ``KEY=VALUE`` CLI args into a dict (key lower-cased)."""
    out: dict[str, str] = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise ValueError(f"expected ECO=VALUE, got: {item!r}")
        out[key.strip().lower()] = value
    return out


def _config_from_args(args) -> DepfreshConfig:
    """Combine file/env config with --registry / --registry-token overrides."""
    base = load_config(explicit_path=args.config, scan_path=getattr(args, "path", None))
    cli_config = DepfreshConfig()
    for ecosystem, url in _parse_kv(args.registry).items():
        cli_config.registries.setdefault(ecosystem, RegistryConfig()).base_url = url
    for ecosystem, token in _parse_kv(args.registry_token).items():
        cli_config.registries.setdefault(ecosystem, RegistryConfig()).token = token
    return merge(base, cli_config)


def _filter_ecosystems(result: ScanResult, ecosystems: list[str] | None) -> ScanResult:
    if not ecosystems:
        return result
    wanted = {e.lower() for e in ecosystems}
    result.manifests = [m for m in result.manifests if m.ecosystem.lower() in wanted]
    return result


def _keep_outdated_only(result: ScanResult, updates: dict[tuple[str, str], UpdateInfo]) -> None:
    for manifest in result.manifests:
        manifest.dependencies = [
            d
            for d in manifest.dependencies
            if (info := updates.get((d.ecosystem, d.name))) and info.status == OUTDATED
        ]
    result.manifests = [m for m in result.manifests if m.dependencies]


def _status_suffix(info: UpdateInfo | None) -> str:
    if info is None:
        return ""
    if info.status == OUTDATED:
        return f"-> {info.latest}  [OUTDATED]"
    if info.status == CURRENT:
        return "up to date"
    if info.status == UNKNOWN:
        return f"latest {info.latest} (constraint not comparable)"
    if info.status == NOT_FOUND:
        return "not found in registry"
    if info.status == ERROR:
        return f"lookup error: {info.error}"
    return ""


def _render_table(
    result: ScanResult,
    manifests_only: bool,
    updates: dict[tuple[str, str], UpdateInfo] | None,
) -> str:
    lines: list[str] = []
    lines.append(f"Scanned: {result.root}")
    summary = (
        f"Found {len(result.manifests)} manifest(s), "
        f"{result.dependency_count} dependencies "
        f"across {len(result.ecosystems)} ecosystem(s): "
        f"{', '.join(result.ecosystems) or '-'}"
    )
    if updates is not None:
        outdated = sum(1 for i in updates.values() if i.status == OUTDATED)
        summary += f"  |  {outdated} outdated"
    lines.append(summary)

    if not result.manifests:
        lines.append("")
        lines.append("No dependency manifests found.")
        return "\n".join(lines)

    for manifest in result.manifests:
        lines.append("")
        header = f"{manifest.path}  [{manifest.ecosystem}/{manifest.manager}]"
        lines.append(header)
        lines.append("-" * len(header))
        if manifest.error:
            lines.append(f"  ! error: {manifest.error}")
            continue
        if manifests_only:
            lines.append(f"  {len(manifest.dependencies)} dependencies")
            continue
        if not manifest.dependencies:
            lines.append("  (no dependencies declared)")
            continue
        name_w = max((len(d.name) for d in manifest.dependencies), default=4)
        ver_w = max((len(d.version or "*") for d in manifest.dependencies), default=1)
        for dep in manifest.dependencies:
            version = dep.version if dep.version is not None else "*"
            row = f"  {dep.name.ljust(name_w)}  {version.ljust(ver_w)}  ({dep.scope})"
            if updates is not None:
                suffix = _status_suffix(updates.get((dep.ecosystem, dep.name)))
                if suffix:
                    row += f"  {suffix}"
            lines.append(row)
    return "\n".join(lines)


def _flat_dependencies(result: ScanResult):
    rows = [dep for manifest in result.manifests for dep in manifest.dependencies]
    rows.sort(key=lambda d: (d.ecosystem, d.name.lower(), d.manifest or ""))
    return rows


def _render_flat(result: ScanResult, updates: dict[tuple[str, str], UpdateInfo] | None) -> str:
    rows = _flat_dependencies(result)
    lines = [f"Scanned: {result.root}", f"{len(rows)} package record(s)"]
    if not rows:
        lines.append("")
        lines.append("No dependencies found.")
        return "\n".join(lines)

    name_w = max(len(d.name) for d in rows)
    ver_w = max(len(d.version or "*") for d in rows)
    scope_w = max(len(d.scope) for d in rows)
    eco_w = max(len(d.ecosystem) for d in rows)
    lines.append("")
    for dep in rows:
        version = dep.version if dep.version is not None else "*"
        row = (
            f"  {dep.name.ljust(name_w)}  {version.ljust(ver_w)}  "
            f"{dep.scope.ljust(scope_w)}  {dep.ecosystem.ljust(eco_w)}  {dep.manifest}"
        )
        if updates is not None:
            suffix = _status_suffix(updates.get((dep.ecosystem, dep.name)))
            if suffix:
                row += f"  {suffix}"
        lines.append(row)
    return "\n".join(lines)


def _build_flat_json(result: ScanResult, updates: dict[tuple[str, str], UpdateInfo] | None) -> dict:
    records = []
    for dep in _flat_dependencies(result):
        record = dep.to_dict()
        if updates is not None:
            info = updates.get((dep.ecosystem, dep.name))
            if info is not None:
                record["latest"] = info.latest
                record["update_status"] = info.status
        records.append(record)
    return {
        "root": result.root,
        "summary": {
            "dependency_count": len(records),
            "ecosystems": result.ecosystems,
        },
        "dependencies": records,
    }


def _render_bump_plan(root: str, plan: BumpPlan) -> str:
    lines = [f"Scanned: {root}"]
    lines.append(
        f"Bump plan: {len(plan.items)} package(s) to update "
        f"across {plan.manifest_count} manifest(s)"
    )
    if not plan.items:
        lines.append("")
        lines.append("Nothing to bump — all checked dependencies are up to date.")
        return "\n".join(lines)

    for item in plan.items:
        lines.append("")
        count = item.manifest_count
        lines.append(
            f"{item.name}  ->  {item.latest}   [{item.ecosystem}]  "
            f"({count} file{'s' if count != 1 else ''})"
        )
        path_w = max(len(o.manifest) for o in item.occurrences)
        for occ in item.occurrences:
            current = occ.current if occ.current is not None else "*"
            lines.append(f"    {occ.manifest.ljust(path_w)}  {current}  ({occ.scope})")
    return "\n".join(lines)


def _build_json(result: ScanResult, updates: dict[tuple[str, str], UpdateInfo] | None) -> dict:
    payload = result.to_dict()
    if updates is None:
        return payload
    outdated = sum(1 for i in updates.values() if i.status == OUTDATED)
    payload["summary"]["outdated_count"] = outdated
    for manifest in payload["manifests"]:
        for dep in manifest["dependencies"]:
            info = updates.get((dep["ecosystem"], dep["name"]))
            if info is not None:
                dep["latest"] = info.latest
                dep["update_status"] = info.status
    return payload


def _resolve(cli_value, config_value, default):
    """CLI value wins, else config value, else built-in default."""
    if cli_value is not None:
        return cli_value
    if config_value is not None:
        return config_value
    return default


def build_update_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="depfresh update",
        description="Clone a repo, bump outdated dependencies, and open a PR/MR.",
    )
    parser.add_argument("repo", help="Repository URL (https) to update.")
    parser.add_argument(
        "--token",
        default=None,
        help="Forge access token (else DEPFRESH_FORGE_TOKEN_<KIND> or config).",
    )
    parser.add_argument(
        "--grouping",
        choices=GROUPINGS,
        default=None,
        help="Group updates into one MR (all), per ecosystem, or per dependency (default: all).",
    )
    parser.add_argument(
        "--branch-prefix", default=None, help="Branch name prefix (default: depfresh/)."
    )
    parser.add_argument(
        "--base", default=None, help="Target branch (default: the repo's default branch)."
    )
    parser.add_argument(
        "-e",
        "--ecosystem",
        action="append",
        default=None,
        metavar="NAME",
        help="Only update this ecosystem (repeatable).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="PKG",
        help="Package to leave untouched (repeatable).",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show the changes and planned MRs without pushing or opening anything.",
    )
    parser.add_argument(
        "--delete-branch",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Delete update branches once their PR/MR merges (default: enabled).",
    )
    parser.add_argument(
        "--json",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Emit the result as JSON.",
    )
    parser.add_argument("--timeout", type=float, default=None, metavar="SECONDS")
    parser.add_argument("--jobs", type=int, default=None, metavar="N")
    parser.add_argument("--config", metavar="PATH", help="Path to a depfresh JSON config file.")
    parser.add_argument("--registry", action="append", metavar="ECO=URL")
    parser.add_argument("--registry-token", action="append", metavar="ECO=TOKEN")
    return parser


def _build_update_json(run: UpdateRun) -> dict:
    return {
        "repo": run.repo,
        "base_branch": run.base_branch,
        "dry_run": run.dry_run,
        "groups": [
            {
                "key": g.key,
                "title": g.title,
                "branch": g.branch,
                "files_changed": g.files_changed,
                "request_url": g.request_url,
                "pushed": g.pushed,
                "skipped_reason": g.skipped_reason,
            }
            for g in run.groups
        ],
    }


def _render_update(run: UpdateRun) -> str:
    lines = [f"Repository: {run.repo}", f"Base branch: {run.base_branch}"]
    if run.dry_run:
        lines.append("(dry run — no branches pushed, no MRs opened)")
    lines.append("")
    if not run.groups:
        lines.append("Everything is up to date — nothing to update.")
        return "\n".join(lines)
    for g in run.groups:
        lines.append(f"{g.title}")
        if g.skipped_reason:
            lines.append(f"  skipped: {g.skipped_reason}")
            lines.append("")
            continue
        lines.append(f"  branch: {g.branch}")
        lines.append(f"  files:  {', '.join(g.files_changed)}")
        if run.dry_run:
            lines.append("  (not pushed)")
        elif g.request_url:
            lines.append(f"  MR:     {g.request_url}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _main_update(argv: list[str]) -> int:
    args = build_update_parser().parse_args(argv)
    try:
        config = _config_from_args(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"depfresh: error: {exc}", file=sys.stderr)
        return 2
    s = config.settings

    grouping = _resolve(args.grouping, s.grouping, "all")
    branch_prefix = _resolve(args.branch_prefix, s.branch_prefix, "depfresh/")
    base = _resolve(args.base, s.base, None)
    dry_run = _resolve(args.dry_run, s.dry_run, False)
    delete_branch = _resolve(args.delete_branch, s.delete_branch, True)
    json_out = _resolve(args.json, s.json, False)
    timeout = _resolve(args.timeout, s.timeout, 10.0)
    jobs = _resolve(args.jobs, s.jobs, 16)
    exclude = args.exclude if args.exclude is not None else (s.exclude or [])
    ecosystems = args.ecosystem if args.ecosystem is not None else s.ecosystem

    try:
        run = run_update(
            args.repo,
            token=args.token,
            config=config,
            grouping=grouping,
            branch_prefix=branch_prefix,
            base=base,
            exclude=exclude,
            ecosystems=ecosystems,
            dry_run=dry_run,
            delete_branch=delete_branch,
            timeout=timeout,
            max_workers=jobs,
        )
    except (UpdateError, ForgeError, GitError, ValueError, FileNotFoundError) as exc:
        print(f"depfresh: error: {exc}", file=sys.stderr)
        return 2

    if json_out:
        print(json.dumps(_build_update_json(run), indent=2))
    else:
        print(_render_update(run))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "update":
        return _main_update(argv[1:])
    return _main_scan(argv)


def _main_scan(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    # Load config early: it can supply both registry settings and option
    # defaults. CLI flags still override anything from the config file.
    try:
        config = _config_from_args(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"depfresh: error: {exc}", file=sys.stderr)
        return 2
    s = config.settings

    path = _resolve(args.path, s.path, ".")
    json_out = _resolve(args.json, s.json, False)
    manifests_only = _resolve(args.manifests_only, s.manifests_only, False)
    flat = _resolve(args.flat, s.flat, False)
    do_check = _resolve(args.check_updates, s.check_updates, False)
    outdated_only = _resolve(args.outdated_only, s.outdated_only, False)
    bump_plan = _resolve(args.bump_plan, s.bump_plan, False)
    exit_code = _resolve(args.exit_code, s.exit_code, False)
    timeout = _resolve(args.timeout, s.timeout, 10.0)
    jobs = _resolve(args.jobs, s.jobs, 16)
    ecosystems = args.ecosystem if args.ecosystem is not None else s.ecosystem

    try:
        result = scan(path)
    except FileNotFoundError as exc:
        print(f"depfresh: error: {exc}", file=sys.stderr)
        return 2

    result = _filter_ecosystems(result, ecosystems)

    check = do_check or outdated_only or bump_plan
    updates: dict[tuple[str, str], UpdateInfo] | None = None
    if check:
        updates = check_updates(result, config=config, max_workers=jobs, timeout=timeout)

    # --outdated-only narrows the dependency set for every view (the bump plan
    # is already outdated-only by construction, so filtering it is a no-op).
    if outdated_only and updates is not None:
        _keep_outdated_only(result, updates)

    if bump_plan:
        plan = build_bump_plan(result, updates or {})
        if json_out:
            print(json.dumps({"root": result.root, "bump_plan": plan.to_dict()}, indent=2))
        else:
            print(_render_bump_plan(result.root, plan))
    elif flat:
        if json_out:
            print(json.dumps(_build_flat_json(result, updates), indent=2))
        else:
            print(_render_flat(result, updates))
    else:
        if json_out:
            payload = _build_json(result, updates)
            if manifests_only:
                for manifest in payload["manifests"]:
                    manifest.pop("dependencies", None)
            print(json.dumps(payload, indent=2))
        else:
            print(_render_table(result, manifests_only, updates))

    if exit_code and updates is not None:
        if any(i.status == OUTDATED for i in updates.values()):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
