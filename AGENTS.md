# AGENTS.md — Instructions for AI Agents Working on okf-toolkit

This file provides operational instructions, architecture overview, coding conventions, and compliance rules for AI agents and human contributors working on the `okf-toolkit` project.

## Project Overview

`okf-toolkit` is a Python CLI tool for creating, validating, and managing knowledge bases stored in Google's Open Knowledge Format (OKF). The tool is designed to be lightweight (stdlib + PyYAML only) and suitable for both interactive terminal use and programmatic invocation by AI agents.

### Architecture

```
okf.py              # Single-file CLI — all commands defined as cmd_* functions
tests/test_okf.py   # Unit tests using unittest
examples/           # Sample OKF bundles for testing and demonstration
okf_skill/SKILL.md  # Skill definition for OpenClaw AI agents
```

The CLI uses `argparse` for argument parsing. Each sub-command maps to a `cmd_*` function with the signature `cmd_*(args: argparse.Namespace) -> int`. Return 0 for success, 1 for error.

### Key Modules and Patterns

- **`_parse_frontmatter()`** — Splits a markdown string into (frontmatter_dict, body). Returns ({}, text) if no valid YAML frontmatter found.
- **`_find_md_files()`** — Recursively discovers all `.md` files in a bundle directory.
- **`_find_markdown_links()`** — Extracts markdown link targets pointing to `.md` files from body text.
- **`_resolve_link()`** — Resolves relative or absolute markdown links against the bundle root.
- **`_rel_path()`** — Returns a file's path relative to the bundle root for display.
- **Color helpers** — `green()`, `red()`, `yellow()`, `cyan()`, `bold()`, `dim()` — all check `sys.stdout.isatty()` to avoid printing ANSI codes when output is piped.

## Coding Conventions

### Python

- **Target:** Python 3.10+. Use `str.removeprefix`, `str.removesuffix`, `match`/`case` sparingly (3.10+).
- **Style:** Follow PEP 8. 100-character line limit preferred, 120 acceptable.
- **Imports:** Standard library first, then third-party. Within stdlib, group alphabetically.
- **Type hints:** Use them for function signatures. Use `import collections` (not `from collections import ...`) inside functions to avoid circular issues.
- **No external dependencies beyond PyYAML.** This is a hard constraint. Any feature that requires a new third-party library must be approved by the project owner.
- **ANSI color:** Use the dedicated helper functions. Never embed raw escape codes in strings.
- **Error messages:** Print to stdout via `print()`. Use `red()` for errors, `yellow()` for warnings, `green()` for success.

### File Naming

- Concept files: `*.md` only
- Reserved: `index.md` and `log.md` — never write frontmatter with `type` in these files
- Test files: `tests/test_*.py`

### Adding New Commands

1. Define a `cmd_<name>(args: argparse.Namespace) -> int` function
2. Add a sub-parser in `build_parser()`
3. Register it in the `commands` dict inside `main()`
4. Add tests in `tests/test_okf.py`
5. Update README.md with the new command

### Testing Requirements

- All tests use Python's `unittest` framework
- Tests must run without network access
- Use the example bundle at `examples/sample-bundle/` as a test fixture where applicable
- For commands that modify files, use `tempfile.TemporaryDirectory` to create test bundles
- Run tests with: `python3 -m unittest tests/test_okf.py -v`

### PR and Commit Guidelines

- **Branch strategy:** Feature branches off `main`. No direct commits to `main`.
- **Commit messages:** `<what>: <why>` format. Example: `validate: add check for broken cross-links to improve bundle integrity checks`
- **PR description:** Include what changed, why, and how to test. Reference any related issues.
- **Pre-merge checklist:**
  - All tests pass
  - `okf.py --help` runs without errors
  - No new external dependencies
  - README.md and AGENTS.md are updated if the change affects user-facing behavior

## OKF Spec Compliance Rules

The tool must adhere to the OKF v0.1 specification at all times:

1. **Bundle:** A directory tree of markdown files with YAML frontmatter.
2. **Concept:** A single markdown file = one unit of knowledge. Must have YAML frontmatter.
3. **Required frontmatter field:** `type` (string). Any concept without `type` is invalid.
4. **Recommended frontmatter fields:** `title`, `description`, `resource` (URI), `tags` (YAML list), `timestamp` (ISO 8601).
5. **Reserved filenames:** `index.md` (directory listing) and `log.md` (update history) — cannot be concept documents. They must not have a `type` field.
6. **Linking:** Standard markdown links. Absolute from bundle root (`/path/to/concept.md`) or relative (`./other.md`).
7. **index.md:** No frontmatter. Uses markdown sections with bullet lists linking to concepts.
8. **log.md:** Chronological history. No frontmatter.
9. **Extensions:** Producers MAY add extra frontmatter keys. Consumers MUST tolerate unknown keys (the tool does).
10. **Encoding:** UTF-8 throughout.

### Validation Rules (mapped to `okf validate`)

| Rule                  | Check                    | Severity |
|-----------------------|--------------------------|----------|
| UTF-8 compliance      | Every file is valid UTF-8 | Error    |
| Reserved filename     | `index.md`/`log.md` has `type` | Error |
| Required field        | Every concept has `type`  | Error    |
| YAML parseability     | Frontmatter parses as YAML dict | Error |
| Tags type             | `tags` is a list if present | Warning |
| Timestamp type        | `timestamp` is a string if present | Warning |
| Cross-link resolution | All `.md` links resolve to existing files | Warning |

## Edge Cases to Handle

- **Empty bundles:** No markdown files → warning, exit 0
- **Missing frontmatter:** File exists but no `---` delimiter → warning, skip validation
- **Broken frontmatter:** YAML parse error → warning, skip further checks
- **Non-UTF-8 files:** Report error with path, skip further checks
- **Symlinks in bundle:** Not explicitly handled; `os.walk` defaults to `followlinks=False` so symlinks are NOT followed
- **Files outside bundle:** `_resolve_link` returns None → warning in validate, skip in graph

## Security Notes

- The tool reads and writes files only within the specified bundle directory
- No network access is performed
- No shell commands are executed
- YAML loading uses `yaml.safe_load` to prevent arbitrary code execution
- User-provided bundle paths are resolved with `Path.resolve()` to prevent path traversal

## For AI Agents Specifically

If you are an AI agent reading this file to understand how to contribute to or use `okf-toolkit`:

- **Traverse bundles** by reading `index.md` files, then following links to concepts.
- **Understand a concept** by parsing its YAML frontmatter (especially the `type` field) and reading its body.
- **Add knowledge** by using `okf new` or by creating a properly-formatted `.md` file manually.
- **Stay in bounds.** Do not modify `index.md` or `log.md` directly — let `okf index` handle index files, and let humans handle the log.
- **Validate before committing.** Always run `okf validate <bundle>` after making changes.
