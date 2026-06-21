#!/usr/bin/env python3
"""
okf-toolkit — CLI for working with Google's Open Knowledge Format (OKF) bundles.

OKF is an open, vendor-neutral format for representing knowledge as a directory
tree of markdown files with YAML frontmatter. Each file (except index.md and
log.md) is a self-contained "concept" with typed metadata.

Commands:
  init      Initialize a new OKF bundle directory
  new       Interactively create a new concept
  validate  Validate bundle structure and frontmatter
  list      List all concepts with type and description
  show      Display a single concept's frontmatter and body
  index     Auto-generate index.md files from frontmatter
  search    Full-text search across concept bodies
  graph     Output the concept link graph
  stats     Bundle statistics
"""

import argparse
import hashlib
import os
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ── ANSI terminal helpers ────────────────────────────────────────────────

def _color(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def green(text: str) -> str:
    return _color("32", text)


def yellow(text: str) -> str:
    return _color("33", text)


def red(text: str) -> str:
    return _color("31", text)


def cyan(text: str) -> str:
    return _color("36", text)


def bold(text: str) -> str:
    return _color("1", text)


def dim(text: str) -> str:
    return _color("2", text)


# ── Constants ────────────────────────────────────────────────────────────

RESERVED_NAMES = {"index.md", "log.md"}
REQUIRED_FRONTMATTER_FIELDS = {"type"}


# ── OKF Bundle helpers ───────────────────────────────────────────────────

def _find_md_files(bundle_path: Path) -> list[Path]:
    """Return all .md files in the bundle recursively, sorted."""
    if not bundle_path.is_dir():
        return []
    files: list[Path] = []
    for root, _dirs, _names in os.walk(str(bundle_path)):
        for name in _names:
            if name.endswith(".md"):
                files.append(Path(root) / name)
    return sorted(files)


def _rel_path(bundle_path: Path, file_path: Path) -> str:
    """Return the path of *file_path* relative to *bundle_path*."""
    return str(file_path.relative_to(bundle_path))


def _safe_dump_yaml(fm: dict) -> str:
    """Dump frontmatter dict to YAML string, ensuring the result is valid YAML.

    Falls back to quoting all string values if the default dump produces
    invalid YAML (e.g., when descriptions contain colons, hash signs, etc.).
    """
    try:
        s = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
        yaml.safe_load(s)
        return s
    except yaml.YAMLError:
        # Fallback: dump with all strings quoted
        s = yaml.dump(
            fm, default_flow_style=False, allow_unicode=True,
            sort_keys=False, default_style="'"
        ).strip()
        return s


def _read_file(path: Path) -> str | None:
    """Read a file as UTF-8. Return None on encoding errors."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Split markdown text into (frontmatter_dict, body).
    Returns ({}, text) if no valid frontmatter is found.
    """
    if not text.startswith("---"):
        return {}, text
    # Find the closing ---. Must be on its own line.
    # The first --- is at index 0. We search for "\n---\n" or "\n---$"
    # to find the closing delimiter.
    after_first = text[3:]
    # Support both "---\n" and "--- " (inline) opening
    if after_first.startswith("\n"):
        rest = after_first[1:]
    else:
        # Opening --- not followed by newline — try to find closing anyway
        rest = after_first

    # Find the closing delimiter. It could be at position 0 (if opening was "---\n---")
    # or elsewhere preceded by newline.
    end = -1
    skip = 3  # number of chars to skip past "---"
    if rest.startswith("---"):
        # Closing delimiter immediately after the opening
        end = 0
        skip = 3
    else:
        pos = rest.find("\n---")
        if pos != -1:
            end = pos
            skip = 4  # skip \n + ---

    if end == -1:
        return {}, text

    fm_str = rest[:end]
    body = rest[end + skip:]  # skip past the delimiter
    body = body.lstrip("\n")

    # If fm_str has no content, return empty dict + full original text as body
    if not fm_str.strip():
        return {}, body

    try:
        if yaml is None:
            return {}, body
        data = yaml.safe_load(fm_str)
        if data is None:
            fm_str_clean = fm_str.strip()
            if not fm_str_clean:
                return {}, body
            return {}, body
        if not isinstance(data, dict):
            return {}, body
        return data, body
    except yaml.YAMLError:
        return {}, text


def _get_bundle_id(path: Path) -> str:
    """
    Return a stable, human-friendly identifier for a concept file.
    Uses the path relative to the bundle root, minus the .md extension.
    """
    return str(path.with_suffix("")).replace(os.sep, "/")


def _find_markdown_links(text: str) -> list[str]:
    """
    Extract all markdown link targets (wiki-style, standard, reference-style)
    that point to .md files.
    """
    links: list[str] = []
    # Standard [text](target)
    for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", text):
        target = m.group(2).split("#")[0].split("?")[0]
        if target.endswith(".md"):
            links.append(target)
    # Reference-style [text][ref] and [ref]: target
    # Links defined at bottom with [ref]: target
    for m in re.finditer(r"^\[([^\]]+)\]:\s*(\S+)", text, re.MULTILINE):
        target = m.group(2).split("#")[0].split("?")[0]
        if target.endswith(".md"):
            links.append(target)
    return links


def _resolve_link(source_path: Path, bundle_path: Path, target: str) -> Path | None:
    """
    Resolve a markdown link target (which may be absolute or relative)
    against the bundle root. Returns the absolute Path if it exists.
    """
    if target.startswith("/"):
        # Absolute from bundle root
        candidate = (bundle_path / target.lstrip("/")).resolve()
    else:
        # Relative to the source file's directory
        candidate = (source_path.parent / target).resolve()
    if candidate.exists():
        return candidate
    return None


# ── Commands ─────────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new OKF bundle at the given path."""
    bundle = Path(args.path).resolve()
    if bundle.exists():
        if not bundle.is_dir():
            print(red(f"Error: {bundle} exists and is not a directory"))
            return 1
        existing = list(bundle.iterdir())
        if existing:
            print(red(f"Error: {bundle} is not empty"))
            return 1
    else:
        bundle.mkdir(parents=True, exist_ok=True)

    index_path = bundle / "index.md"
    log_path = bundle / "log.md"

    if not index_path.exists():
        index_path.write_text(
            f"# {bundle.name}\n\n"
            "<!-- OKF Bundle -- auto-generated index.md -->\n\n"
            "## Sections\n\n"
            "<!-- Add links to sections here -->\n",
            encoding="utf-8",
        )

    if not log_path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_path.write_text(
            f"# Update Log\n\n## {timestamp}\n\n- Bundle initialized\n",
            encoding="utf-8",
        )

    print(green(f"OKF bundle initialized at {bundle}"))
    print(f"  {index_path}  (created)")
    print(f"  {log_path}  (created)")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Interactively create a new concept in the bundle."""
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        print(red(f"Error: {bundle} is not a directory"))
        return 1

    concept_id = args.id
    if not concept_id:
        print(red("Error: concept id is required"))
        return 1

    # Prevent creating index.md or log.md as concepts
    filename = os.path.basename(concept_id) if "/" not in concept_id else os.path.basename(concept_id.rstrip("/"))
    md_filename = filename if filename.endswith(".md") else f"{filename}.md"
    if md_filename in RESERVED_NAMES:
        print(red(f"Error: '{md_filename}' is a reserved filename (cannot be a concept)"))
        return 1

    target_path = (bundle / concept_id).resolve()
    if not target_path.suffix:
        target_path = target_path.with_suffix(".md")

    # Ensure parent dir exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.exists():
        print(yellow(f"Warning: {_rel_path(bundle, target_path)} already exists"))
        overwrite = input("Overwrite? [y/N] ").strip().lower()
        if overwrite != "y":
            print("Aborted.")
            return 0

    # Interactive frontmatter input
    print(cyan("Enter concept metadata (press Enter to skip optional fields):"))
    concept_type = ""
    while not concept_type.strip():
        concept_type = input(f"  {bold('type')} (required) [{green('e.g.')} BigQuery Table, Metric, Playbook]: ").strip()
        if not concept_type:
            print(red("  type is required"))

    title = input(f"  {bold('title')} [{green('optional')}]: ").strip()
    description = input(f"  {bold('description')} [{green('optional')}]: ").strip()
    resource = input(f"  {bold('resource')} [{green('optional')}]: ").strip()
    tags_input = input(f"  {bold('tags')} [{green('optional, comma-separated')}]: ").strip()

    tags = []
    if tags_input:
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build YAML frontmatter
    fm: dict = {"type": concept_type, "timestamp": timestamp}
    if title:
        fm["title"] = title
    if description:
        fm["description"] = description
    if resource:
        fm["resource"] = resource
    if tags:
        fm["tags"] = tags

    fm_str = _safe_dump_yaml(fm)

    header = f"# {title or concept_id}\n\n"
    body_placeholder = "<!-- Add concept body here -->\n"

    content = f"---\n{fm_str}\n---\n\n{header}{body_placeholder}"
    target_path.write_text(content, encoding="utf-8")

    rel = _rel_path(bundle, target_path)
    print(green(f"Created concept: {rel}"))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate an OKF bundle structure and frontmatter."""
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        print(red(f"Error: {bundle} is not a directory"))
        return 1

    md_files = _find_md_files(bundle)
    if not md_files:
        print(yellow(f"Warning: no markdown files found in {bundle}"))
        return 0

    errors = 0
    warnings = 0
    concept_count = 0

    for fpath in md_files:
        rel = _rel_path(bundle, fpath)
        fname = fpath.name

        # ── 1. UTF-8 encoding ──
        raw = _read_file(fpath)
        if raw is None:
            print(red(f"  UTF-8 ERROR: {rel}"))
            errors += 1
            continue

        # ── 2. Reserved filenames as concepts ──
        if fname in RESERVED_NAMES:
            # index.md and log.md are allowed, but they must NOT have frontmatter with 'type'
            fm, _body = _parse_frontmatter(raw)
            if fm.get("type"):
                print(red(f"  RESERVED FILENAME with type: {rel}"))
                errors += 1
            continue  # skip further validation for reserved files

        # ── 3. YAML validity ──
        fm, body = _parse_frontmatter(raw)
        if not fm:
            print(yellow(f"  WARN: No frontmatter in {rel}"))
            warnings += 1
            continue

        concept_count += 1

        # ── 4. Required fields ──
        for field in REQUIRED_FRONTMATTER_FIELDS:
            if field not in fm:
                print(red(f"  MISSING required field '{field}': {rel}"))
                errors += 1

        # ── 5. Broken cross-links (warnings only) ──
        links = _find_markdown_links(body)
        for link in links:
            resolved = _resolve_link(fpath, bundle, link)
            if resolved is None:
                print(yellow(f"  WARN: Broken link '{link}' in {rel}"))
                warnings += 1

        # ── 6. Extra checks ──
        if fm.get("tags") is not None and not isinstance(fm["tags"], list):
            print(yellow(f"  WARN: 'tags' should be a list in {rel}"))
            warnings += 1

        ts = fm.get("timestamp")
        if ts is not None:
            if isinstance(ts, str) and ts == "":
                print(yellow(f"  WARN: 'timestamp' is empty in {rel}"))
                warnings += 1

    print(f"\n{bold('Summary:')}")
    print(f"  Concepts:  {concept_count}")
    print(f"  Errors:    {red(str(errors)) if errors else green('0')}")
    print(f"  Warnings:  {yellow(str(warnings)) if warnings else green('0')}")

    if errors:
        return 1
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all concepts with their type and description."""
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        print(red(f"Error: {bundle} is not a directory"))
        return 1

    md_files = _find_md_files(bundle)
    if not md_files:
        print(yellow(f"No markdown files found in {bundle}"))
        return 0

    found = 0
    for fpath in md_files:
        rel = _rel_path(bundle, fpath)
        fname = fpath.name
        if fname in RESERVED_NAMES:
            continue

        raw = _read_file(fpath)
        if raw is None:
            continue

        fm, _body = _parse_frontmatter(raw)
        if not fm or "type" not in fm:
            continue

        found += 1
        ctype = fm.get("type", "?")
        desc = str(fm.get("description", "")).strip()
        if desc:
            print(f"  {bold(rel)}  {dim(f'[{ctype}]')}  {desc}")
        else:
            print(f"  {bold(rel)}  {dim(f'[{ctype}]')}")

    if found == 0:
        print(yellow("No concepts found (no markdown files with 'type' frontmatter)."))

    print(f"\n{found} concept(s)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Display a single concept's frontmatter and body."""
    bundle = Path(args.bundle).resolve()
    concept_id = args.id

    if not bundle.is_dir():
        print(red(f"Error: {bundle} is not a directory"))
        return 1

    # Resolve concept path: try as-is, then with .md suffix
    target = (bundle / concept_id).resolve()
    if not target.exists():
        target = target.with_suffix(".md")
    if not target.exists() or not target.is_file():
        print(red(f"Error: concept '{concept_id}' not found in {bundle}"))
        return 1

    raw = _read_file(target)
    if raw is None:
        print(red(f"Error: {target} is not valid UTF-8"))
        return 1

    fm, body = _parse_frontmatter(raw)
    rel = _rel_path(bundle, target)

    print(f"\n{bold('Concept:')} {rel}")
    print(f"{bold('Path:')}   {target}")

    if fm:
        print(f"\n{bold('Frontmatter:')}")
        # Pretty-print the frontmatter
        fm_lines = _safe_dump_yaml(fm)
        for line in fm_lines.split("\n"):
            print(f"  {dim(line)}")

    print(f"\n{bold('Body:')}")
    if body.strip():
        # Show first 50 lines
        body_lines = body.split("\n")
        for line in body_lines[:50]:
            print(f"  {line}")
        if len(body_lines) > 50:
            print(cyan(f"  ... ({len(body_lines) - 50} more lines)"))
    else:
        print(dim("  (empty)"))

    return 0


def cmd_index(args: argparse.Namespace) -> int:
    """Auto-generate index.md files for all directories that contain concepts."""
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        print(red(f"Error: {bundle} is not a directory"))
        return 1

    md_files = _find_md_files(bundle)

    # Collect concepts by parent directory
    concepts_by_dir: dict[Path, list[Path]] = {}
    for fpath in md_files:
        rel = _rel_path(bundle, fpath)
        if fpath.name in RESERVED_NAMES:
            continue
        raw = _read_file(fpath)
        if raw is None:
            continue
        fm, _body = _parse_frontmatter(raw)
        if not fm or "type" not in fm:
            continue
        parent = fpath.parent
        if parent not in concepts_by_dir:
            concepts_by_dir[parent] = []
        concepts_by_dir[parent].append(fpath)

    generated = 0
    for parent_dir, concept_paths in sorted(concepts_by_dir.items()):
        index_path = parent_dir / "index.md"
        rel_parent = _rel_path(bundle, parent_dir) if parent_dir != bundle else "."

        # Build index content
        lines = [f"# {parent_dir.name}", ""]
        lines.append(f"Auto-generated index for concepts in `{rel_parent}`.")
        lines.append("")

        for cp in sorted(concept_paths):
            raw = _read_file(cp)
            if raw is None:
                continue
            fm, _body = _parse_frontmatter(raw)
            if not fm:
                continue
            ctype = fm.get("type", "?")
            title = fm.get("title", cp.stem)
            desc = str(fm.get("description", "")).strip()
            link_rel = _rel_path(bundle, cp)
            if desc:
                lines.append(f"- [{title}]({link_rel}) — {desc}  [{ctype}]")
            else:
                lines.append(f"- [{title}]({link_rel})  [{ctype}]")

        lines.append("")
        content = "\n".join(lines)

        # Only write if content changed
        if index_path.exists():
            existing = index_path.read_text(encoding="utf-8")
            if existing.strip() == content.strip():
                continue

        index_path.write_text(content, encoding="utf-8")
        print(green(f"  Generated: {_rel_path(bundle, index_path)}"))
        generated += 1

    if generated == 0:
        print(yellow("No index.md files needed regeneration."))
    else:
        print(f"\n{generated} index.md file(s) generated.")

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Full-text search across all concept bodies and frontmatter."""
    bundle = Path(args.bundle).resolve()
    query = args.q.lower()
    if not bundle.is_dir():
        print(red(f"Error: {bundle} is not a directory"))
        return 1
    if not query:
        print(red("Error: search query is empty"))
        return 1

    md_files = _find_md_files(bundle)
    results: list[tuple[str, str, str]] = []  # (rel_path, type, matched_snippet)

    for fpath in md_files:
        if fpath.name in RESERVED_NAMES:
            continue
        raw = _read_file(fpath)
        if raw is None:
            continue
        # Search in entire file (frontmatter + body)
        lower = raw.lower()
        if query not in lower:
            continue
        fm, _body = _parse_frontmatter(raw)
        ctype = fm.get("type", "?") if fm else "?"
        rel = _rel_path(bundle, fpath)

        # Extract snippet around the match
        idx = lower.find(query)
        start = max(0, idx - 40)
        end = min(len(raw), idx + len(query) + 40)
        snippet = raw[start:end].replace("\n", " ").strip()
        if len(snippet) > 80:
            snippet = "..." + snippet[:77] + "..."

        results.append((rel, ctype, snippet))

    if not results:
        print(yellow(f'No results for "{args.q}".'))
        return 0

    for rel, ctype, snippet in results:
        highlight = snippet.replace(query, yellow(query), 1) if snippet else ""
        print(f"  {bold(rel)}  {dim(f'[{ctype}]')}")
        print(f"    {highlight}")
        print()

    print(f"{len(results)} match(es)")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    """Output the concept link graph."""
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        print(red(f"Error: {bundle} is not a directory"))
        return 1

    md_files = _find_md_files(bundle)
    concepts = {}  # rel_path -> concept_id (display name)
    edges = []     # (source_rel, target_rel)

    # Build concept lookup + collect links
    concept_paths = {}
    for fpath in md_files:
        if fpath.name in RESERVED_NAMES:
            continue
        raw = _read_file(fpath)
        if raw is None:
            continue
        fm, body = _parse_frontmatter(raw)
        if not fm or "type" not in fm:
            continue
        rel = _rel_path(bundle, fpath)
        concepts[rel] = fm.get("title", _get_bundle_id(fpath))
        concept_paths[rel] = fpath

        links = _find_markdown_links(body)
        for link in links:
            resolved = _resolve_link(fpath, bundle, link)
            if resolved:
                try:
                    target_rel = _rel_path(bundle, resolved)
                    if target_rel in concepts or resolved.exists():
                        edges.append((rel, target_rel))
                except ValueError:
                    pass

    if not concepts:
        print(yellow("No concepts found to graph."))
        return 0

    # Determine output format
    fmt = getattr(args, "format", "mermaid")

    if fmt == "mermaid":
        print(bold("Mermaid Graph:"))
        print("```mermaid")
        print("graph LR")
        for rel, title in sorted(concepts.items()):
            # Create a safe node ID
            node_id = f"n{abs(hash(rel)) % 10**9}"
            safe_title = title.replace('"', "'")
            print(f'  {node_id}["{safe_title}"]')
        for src, tgt in sorted(edges):
            src_id = f"n{abs(hash(src)) % 10**9}"
            tgt_id = f"n{abs(hash(tgt)) % 10**9}"
            if src_id != tgt_id:
                print(f"  {src_id} --> {tgt_id}")
        print("```")

    elif fmt == "ascii":
        print(bold("ASCII Link Graph:"))
        for rel, title in sorted(concepts.items()):
            print(f"\n  {title}")
            print(f"    Path: {dim(rel)}")
            outgoing = [(t, concepts.get(t, t)) for s, t in edges if s == rel]
            if outgoing:
                for _t, _ttl in outgoing:
                    print(f"    ├──→ {_ttl}")
            incoming = [(s, concepts.get(s, s)) for s, t in edges if t == rel]
            if incoming:
                for _s, _sttl in incoming:
                    print(f"    ├──← {_sttl}")

    print(f"\n{len(concepts)} concept(s), {len(edges)} edge(s)")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Print bundle statistics."""
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        print(red(f"Error: {bundle} is not a directory"))
        return 1

    md_files = _find_md_files(bundle)
    total_md = len(md_files)

    types: dict[str, int] = {}
    tags: dict[str, int] = {}
    total_links = 0
    total_size = 0
    concept_count = 0
    broken_links = 0
    missing_fm = 0

    for fpath in md_files:
        size = fpath.stat().st_size
        total_size += size

        if fpath.name in RESERVED_NAMES:
            continue

        raw = _read_file(fpath)
        if raw is None:
            continue

        fm, body = _parse_frontmatter(raw)
        if not fm or "type" not in fm:
            missing_fm += 1
            continue

        concept_count += 1
        ctype = str(fm.get("type", "unknown"))
        types[ctype] = types.get(ctype, 0) + 1

        tag_list = fm.get("tags", [])
        if isinstance(tag_list, list):
            for t in tag_list:
                t_str = str(t)
                tags[t_str] = tags.get(t_str, 0) + 1

        links = _find_markdown_links(body)
        total_links += len(links)
        for link in links:
            if _resolve_link(fpath, bundle, link) is None:
                broken_links += 1

    # Build size representation
    if total_size < 1024:
        size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    else:
        size_str = f"{total_size / 1024 / 1024:.1f} MB"

    print(f"\n{bold('Bundle Statistics')}")
    print(f"  {bold('Bundle root:')}    {bundle}")
    print(f"  {bold('Total files:')}     {total_md}")
    print(f"  {bold('Concepts:')}        {concept_count}")
    print(f"  {bold('No frontmatter:')}  {missing_fm}")
    print(f"  {bold('Total size:')}      {size_str}")
    print()

    if types:
        print(f"  {bold('By Type:')}")
        for t, count in sorted(types.items(), key=lambda x: -x[1]):
            bar = "█" * count
            print(f"    {t:25s}  {count:3d}  {bar}")
        print()

    if tags:
        print(f"  {bold('Tags Cloud:')}")
        max_tag_len = max(len(t) for t in tags)
        # Sort by frequency desc, then alphabetically
        sorted_tags = sorted(tags.items(), key=lambda x: (-x[1], x[0]))
        for t, count in sorted_tags:
            bar = "▓" * count
            print(f"    {t:{max_tag_len}s}  {count:3d}  {bar}")
        print()

    print(f"  {bold('Links:')}            {total_links} total, {broken_links} broken")
    return 0


# ── Main CLI ─────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="okf",
        description="okf-toolkit — CLI for Google's Open Knowledge Format (OKF)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            See https://github.com/akdira/okf-toolkit for full documentation.
            Report issues at https://github.com/akdira/okf-toolkit/issues.
            Created by akdira — https://www.akdira.id
        """),
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    sub = parser.add_subparsers(dest="command", title="Commands")

    p_init = sub.add_parser("init", help="Initialize a new OKF bundle")
    p_init.add_argument("path", help="Directory path for the new bundle")

    p_new = sub.add_parser("new", help="Create a new concept interactively")
    p_new.add_argument("bundle", help="Path to the OKF bundle")
    p_new.add_argument("id", help="Concept identifier (e.g. tables/orders)")

    p_validate = sub.add_parser("validate", help="Validate bundle structure and frontmatter")
    p_validate.add_argument("bundle", help="Path to the OKF bundle")

    p_list = sub.add_parser("list", help="List all concepts in the bundle")
    p_list.add_argument("bundle", help="Path to the OKF bundle")

    p_show = sub.add_parser("show", help="Display a single concept")
    p_show.add_argument("bundle", help="Path to the OKF bundle")
    p_show.add_argument("id", help="Concept identifier (e.g. tables/orders)")

    p_index = sub.add_parser("index", help="Auto-generate index.md files")
    p_index.add_argument("bundle", help="Path to the OKF bundle")

    p_search = sub.add_parser("search", help="Full-text search across concepts")
    p_search.add_argument("bundle", help="Path to the OKF bundle")
    p_search.add_argument("q", help="Search query")

    p_graph = sub.add_parser("graph", help="Output the concept link graph")
    p_graph.add_argument("bundle", help="Path to the OKF bundle")
    p_graph.add_argument("--format", choices=["mermaid", "ascii"], default="mermaid",
                         help="Output format (default: mermaid)")

    p_stats = sub.add_parser("stats", help="Bundle statistics")
    p_stats.add_argument("bundle", help="Path to the OKF bundle")

    return parser


def main(argv: list[str] | None = None) -> int:
    if yaml is None:
        print(red("Error: PyYAML is required. Install it with: pip install pyyaml"), file=sys.stderr)
        return 1

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("okf-toolkit v0.1.0")
        return 0

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "new": cmd_new,
        "validate": cmd_validate,
        "list": cmd_list,
        "show": cmd_show,
        "index": cmd_index,
        "search": cmd_search,
        "graph": cmd_graph,
        "stats": cmd_stats,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    print(red(f"Unknown command: {args.command}"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
