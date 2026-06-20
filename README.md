# okf-toolkit

**CLI toolkit for working with Google's Open Knowledge Format (OKF)**

okf-toolkit is a command-line tool for creating, validating, traversing, and maintaining knowledge bases stored in the Open Knowledge Format (OKF). OKF is a vendor-neutral, human-and-agent-friendly format announced by Google Cloud on June 12, 2026. It represents knowledge as a directory tree of plain-text markdown files with YAML frontmatter, making knowledge bases portable, version-controllable, and accessible to both humans and AI agents.

## What is OKF?

The Open Knowledge Format is a specification for organizing structured and unstructured knowledge in a file-system-based bundle. Each unit of knowledge — a "concept" — lives in its own `.md` file with YAML frontmatter that provides typed metadata. Key principles:

- **Simplicity:** Everything is markdown. No databases, no proprietary schemas.
- **Portability:** A bundle is a directory tree. Copy it, commit it to Git, distribute it via any channel.
- **Agent-friendly:** Typed frontmatter and clear linking make it trivial for AI agents to traverse, understand, and augment knowledge bases.
- **Extensibility:** Producers can add any extra frontmatter keys; consumers tolerate unknown ones.
- **UTF-8 throughout:** No encoding guesswork.

## Features

okf-toolkit provides everything you need to work with OKF bundles:

| Command     | Description                                                                |
|-------------|----------------------------------------------------------------------------|
| `okf init`  | Scaffold a new OKF bundle directory with index.md and log.md               |
| `okf new`   | Interactively create a new concept with guided frontmatter prompts        |
| `okf validate` | Validate bundle structure: required fields, reserved names, UTF-8, links |
| `okf list`  | List all concepts with their type and description                          |
| `okf show`  | Display a concept's full frontmatter and body content                      |
| `okf index` | Auto-generate or refresh index.md files from concept frontmatter           |
| `okf search`| Full-text substring search across all concept bodies                       |
| `okf graph` | Output the link graph as Mermaid or ASCII for visualization                |
| `okf stats` | Bundle statistics: concept count, type breakdown, tag cloud, link counts   |

## Installation

```bash
# Clone the repository
git clone https://github.com/openclaw/okf-toolkit.git
cd okf-toolkit

# Install the dependency
pip install pyyaml>=6.0

# (optional) Install as a package
pip install -e .
```

Python 3.10 or newer is required. Only `pyyaml` is needed beyond the standard library.

## Quick Start

```bash
# Initialize a new bundle
okf init my-knowledge-base

# Navigate into it
cd my-knowledge-base

# Create a concept interactively
okf new . tables/user-sessions

# Validate the bundle
okf validate .

# List all concepts
okf list .

# Search across concepts
okf search . user

# Generate index.md files from frontmatter
okf index .

# Show the link graph
okf graph .

# Get bundle statistics
okf stats .
```

## Usage Examples

### Creating a New Knowledge Base

```bash
okf init docs/knowledge-base
```

This creates:
```
docs/knowledge-base/
├── index.md    # Directory listing (auto-editable)
└── log.md      # Update history
```

### Adding a Concept

```bash
okf new docs/knowledge-base api/checkout-endpoint
```

You'll be prompted for:
- `type` (required) — e.g., "API Endpoint", "BigQuery Table", "Playbook"
- `title` (optional)
- `description` (optional)
- `resource` (optional URI)
- `tags` (optional, comma-separated)

The tool generates a markdown file with proper YAML frontmatter and a template body.

### Validating a Bundle

```bash
okf validate docs/knowledge-base
```

Checks every `.md` file for:
- Valid UTF-8 encoding
- Reserved filename violations (`index.md` and `log.md` must not have a `type` field)
- Required frontmatter fields (`type`)
- YAML parseability
- Broken markdown cross-links (reported as warnings)
- Type correctness for `tags` (must be a list) and `timestamp` (must be a string)

Exits with code 1 if any errors found, 0 otherwise.

### Searching Across Concepts

```bash
okf search docs/knowledge-base revenue
```

Performs case-insensitive substring matching across all concept files (excluding `index.md` and `log.md`). Shows the matching file, its type, and a highlighted snippet around the match.

### Generating Index Files

```bash
okf index docs/knowledge-base
```

Walks every directory containing concepts and generates or updates an `index.md` with properly formatted links, titles, types, and descriptions pulled from frontmatter. Skips directories where nothing has changed.

### Visualizing the Link Graph

```bash
# Mermaid format (default) — paste into GitHub-flavored markdown
okf graph docs/knowledge-base

# ASCII format for terminal inspection
okf graph docs/knowledge-base --format ascii
```

## Why OKF Matters for AI Agents

AI agents that work with knowledge bases face two fundamental challenges: understanding the structure of the knowledge, and knowing how to add to it. OKF addresses both:

1. **Typed frontmatter gives agents semantic understanding.** When an agent encounters a concept file, the `type` field immediately tells it what kind of thing this is — a table, a metric, a playbook, a reference. This reduces hallucination and improves retrieval accuracy.

2. **Clear linking creates a traversable graph.** Agents can follow markdown links between concepts just like humans do, building a graph of related knowledge.

3. **The format is append-friendly.** An agent that discovers new knowledge can create a new `.md` file with proper frontmatter using the same tools a human would.

4. **Version control works out of the box.** Git tracks every change to every concept. Agents can see what changed, when, and why.

5. **No lock-in.** Unlike a proprietary knowledge graph or database, OKF bundles are plain files. Any tool — AI or otherwise — that can read markdown and YAML can work with OKF.

## Contributing

Contributions are welcome! Here's how to get started:

1. **Read the AGENTS.md** file in the repository root — it contains detailed instructions for AI agents and human contributors alike.
2. **Open an issue** to discuss your proposed change before writing code.
3. **Fork the repository** and create a feature branch.
4. **Write tests** for any new functionality. Tests live in `tests/` and use Python's `unittest` framework.
5. **Ensure existing tests pass** with `python3 -m unittest tests/test_okf.py -v`.
6. **Submit a pull request** with a clear description of what and why.

Conventions:
- Python 3.10+ only, stdlib-first approach
- `pyyaml` is the sole external dependency — keep it that way
- New CLI commands should follow the existing pattern (see `cmd_*` functions in `okf.py`)
- Keep ANSI color helpers in the `_color` / `green`/`red`/etc. functions

## Credits

Created and maintained by [akdira](https://www.akdira.id).

## License

Apache 2.0. See [LICENSE](LICENSE) for the full text.
