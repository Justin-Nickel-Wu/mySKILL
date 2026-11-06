#!/usr/bin/env python3
"""Create, discover, and safely remove Codex code-review session directories.

Only this skill's marked session directory is cleaned; no source/Git files touched.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

MARKER_NAME = ".code-review-session"
MARKER_VALUE = "codex-code-review-v1\n"


def digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def repo_path(value: str) -> Path:
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ValueError(f"not a repository directory: {path}")
    return path


def session_root(args: argparse.Namespace) -> Path:
    """Locate session storage within the explicitly selected workspace."""
    workspace = repo_path(args.workspace)
    root = (workspace / ".ai" / "sessions" / "review").resolve()
    # Reject symlinks that redirect session writes outside the workspace.
    if not root.is_relative_to(workspace):
        raise ValueError(f"session storage resolves outside workspace: {root}")
    return root


def start(args: argparse.Namespace) -> None:
    """Create or resume one review without overwriting existing state."""
    repo = repo_path(args.repo)
    if not args.series.strip():
        raise ValueError("nonempty --series is required")
    path = session_root(args) / ("repo-" + digest(str(repo))) / ("series-" + digest(args.series))
    marker = path / MARKER_NAME
    state = path / "state.md"
    if path.exists():
        if not marker.is_file() or marker.read_text(encoding="utf-8") != MARKER_VALUE:
            raise ValueError(f"unmanaged session directory; refusing to overwrite: {path}")
        if not state.is_file():
            raise ValueError(f"missing state.md; refusing to overwrite: {path}")
        print(f"RESUMED {state}")
        return
    path.mkdir(parents=True, exist_ok=False)
    marker.write_text(MARKER_VALUE, encoding="utf-8")
    state.write_text(
        "# Review state\n"
        f"Repository: {repo}\n"
        f"Series key: {args.series}\n"
        "Git base/tip: (fill after verification)\n"
        "Commits in order: (fill after full-series pre-read)\n"
        "Series understanding: (pending)\n"
        "Current commit: (pending)\n"
        "Current stage: prepare\n"
        "Findings: (none yet)\n"
        "Historical issues detected: unknown\n"
        "Final comment candidates: (none)\n"
        "Gerrit drafts saved: (none)\n"
        "Pending actions / decisions: complete full-series pre-read\n",
        encoding="utf-8",
    )
    print(f"CREATED {state}")


def list_sessions(args: argparse.Namespace) -> None:
    """List matching review sessions in the selected workspace."""
    root = session_root(args)
    if not root.exists():
        print("No review sessions found.")
        return
    if args.repo:
        repo = repo_path(args.repo)
        repo_dirs = [root / ("repo-" + digest(str(repo)))]
    else:
        repo_dirs = sorted(root.glob("repo-*"))
    found = False
    for rd in repo_dirs:
        if not rd.is_dir():
            continue
        for sd in sorted(rd.glob("series-*")):
            marker, state = sd / MARKER_NAME, sd / "state.md"
            if (marker.is_file() and state.is_file()
                    and marker.read_text(encoding="utf-8") == MARKER_VALUE):
                print(state)
                for line in state.read_text(encoding="utf-8").splitlines():
                    if line.startswith(("Repository:", "Series key:", "Current commit:", "Current stage:")):
                        print("  " + line)
                found = True
    if not found:
        print("No review sessions found.")


def finish(args: argparse.Namespace) -> None:
    """Remove only one marked session within the selected workspace."""
    if not args.yes:
        raise ValueError("finish requires --yes after user-approved review completion")
    if not args.session_dir:
        raise ValueError("--session-dir must be an explicit absolute path")
    raw = Path(args.session_dir).expanduser()
    if not raw.is_absolute() or raw.is_symlink():
        raise ValueError("session directory must be absolute and not a symlink")
    root = session_root(args)
    # Resolve once and validate exact depth and pattern; never accept the root itself.
    sd = raw.resolve(strict=True)
    if (sd.parent.parent != root or not sd.name.startswith("series-")
            or not sd.parent.name.startswith("repo-")):
        raise ValueError(f"refusing to clean outside a single managed session: {sd}")
    marker, state = sd / MARKER_NAME, sd / "state.md"
    if not marker.is_file() or marker.is_symlink() or marker.read_text(encoding="utf-8") != MARKER_VALUE:
        raise ValueError("missing/invalid managed-session marker")
    if not state.is_file() or state.is_symlink():
        raise ValueError("missing/invalid state.md")
    others = {p.name for p in sd.iterdir()} - {MARKER_NAME, "state.md"}
    if others:
        raise ValueError(f"unexpected files; will not delete session: {sorted(others)}")
    state.unlink()
    marker.unlink()
    sd.rmdir()
    try:
        sd.parent.rmdir()  # only if empty, preserving other series
    except OSError:
        pass
    print(f"REMOVED one verified review session: {sd}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("start", help="create or resume one session")
    s.add_argument("--repo", required=True)
    s.add_argument("--series", required=True)
    l = sub.add_parser("list", help="list managed sessions")
    l.add_argument("--repo")
    f = sub.add_parser("finish", help="delete only one managed completed session")
    f.add_argument("--session-dir", required=True)
    f.add_argument("--yes", action="store_true")
    for command in (s, l, f):
        command.add_argument("--workspace", default=".",
                             help="workspace directory for session storage (default: current directory)")
    args = parser.parse_args()
    try:
        if args.command == "start":
            start(args)
        elif args.command == "list":
            list_sessions(args)
        else:
            finish(args)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
