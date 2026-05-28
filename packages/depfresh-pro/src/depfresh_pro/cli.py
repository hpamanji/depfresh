"""The `depfresh update` subcommand (registered as a depfresh add-on command).

Reuses the MIT core's config helpers (pro -> core is allowed) and drives the
AGPL update orchestrator in :mod:`depfresh_pro.updater`.
"""

from __future__ import annotations

import argparse
import json
import sys

from depfresh.cli import _config_from_args, _resolve  # core helpers (pro -> core OK)
from depfresh_pro.forge import ForgeError
from depfresh_pro.updater import GROUPINGS, UpdateError, UpdateRun, run_update
from depfresh_pro.vcs import GitError


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


def main_update(argv: list[str]) -> int:
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
