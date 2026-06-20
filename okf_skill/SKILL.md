# OKF (Open Knowledge Format) — Skill for AI Agents

This skill teaches AI agents how to read, traverse, create, and maintain knowledge bases stored in Google's Open Knowledge Format (OKF) using the `okf-toolkit` CLI.

## What is OKF?

The Open Knowledge Format (OKF) is an open, vendor-neutral specification for representing knowledge as a directory tree of markdown files with YAML frontmatter. Announced by Google Cloud on June 12, 2026, it is designed to be both human-readable and AI-agent-friendly.

Key concepts:
- **Bundle:** A directory tree of markdown files
- **Concept:** A single `.md` file = one unit of knowledge. Has YAML frontmatter between `---` delimiters
- **index.md:** Directory listing (no frontmatter)
- **log.md:** Update history (no frontmatter)
- **Linking:** Standard markdown links between concepts

### Frontmatter Fields

Required:
- `type` (string) — e.g., "BigQuery Table", "API Endpoint", "Metric", "Playbook", "Reference"

Recommended:
- `title` (string)
- `description` (string)
- `resource` (URI string)
- `tags` (YAML list)
- `timestamp` (ISO 8601 string)

## How Agents Should Use OKF

### 1. Reading and Traversing a Bundle

Start by reading the bundle's `index.md`. This file lists all top-level sections with links. Follow those links to discover individual concepts.

```markdown
# My Bundle

## Sections

- [Tables](tables/index.md)
- [Metrics](metrics/index.md)
```

To read a concept:
1. Open the `.md` file
2. Parse the YAML frontmatter between `---` delimiters
3. Read the markdown body for detailed information
4. Follow any markdown links to related concepts

### 2. Understanding a Concept

The `type` field tells you what kind of knowledge this is:
- `BigQuery Table` → Contains schema definitions, partitioning info, usage notes
- `Metric` → Contains a business metric definition, SQL query, business rules
- `Playbook` → Contains operational procedures, severity levels, step-by-step instructions
- `API Endpoint` → Contains request/response formats, authentication, examples

### 3. Creating New Concepts

Use the `okf-toolkit` CLI to create new concepts:

```bash
okf new <bundle-path> <concept-id>
```

This prompts for:
- `type` (required)
- `title`, `description`, `resource`, `tags` (optional)

Alternatively, create the file manually with proper frontmatter:

```markdown
---
type: API Endpoint
title: Create User
description: Creates a new user account
resource: https://api.example.com/v1/users
tags:
  - users
  - crud
timestamp: 2026-06-20T00:00:00Z
---

# Create User

POST /v1/users

## Request Body

...
```

### 4. Validating and Maintaining

Always validate after making changes:

```bash
okf validate <bundle-path>
```

This checks:
- All files are valid UTF-8
- Reserved filenames (index.md, log.md) don't have `type` frontmatter
- All concepts have required `type` field
- Frontmatter is valid YAML
- Cross-links are not broken (warnings)

### 5. Using the CLI Tool Effectively

```bash
# List all concepts
okf list <bundle>

# Show a specific concept with full frontmatter
okf show <bundle> <concept-id>

# Search across all concepts
okf search <bundle> <query>

# Auto-generate index.md files
okf index <bundle>

# Visualize link relationships
okf graph <bundle>

# Get statistics and tag cloud
okf stats <bundle>
```

## Best Practices for Knowledge Organization

1. **One concept per file.** Don't put multiple types of knowledge in one file.
2. **Use descriptive type values.** Be specific rather than generic. "BigQuery Table" is better than "Table".
3. **Link freely.** Cross-reference related concepts. This builds a traversable graph.
4. **Use tags for discoverability.** Tags like "core", "pii", "sensitive", "deprecated" help with filtering.
5. **Keep descriptions concise but informative.** The description is what shows up in list views and index files.
6. **Set timestamps.** This allows agents to understand how recent the knowledge is.
7. **Never modify index.md or log.md directly** — let `okf index` handle index files.
8. **Validate before committing.** Run `okf validate` to catch structural issues early.

## Cross-Linking Strategies

- **Relative links** (`./other-concept.md`) work best when concepts are in the same directory
- **Parent-relative** (`../other-dir/concept.md`) keeps links portable
- **Absolute links** (`/concepts/foo.md`) resolve from the bundle root
- Link fragments work too: `concept.md#section`
- Concept files can link to each other in both directions (orders links to customers, customers is referenced by orders)

## For OpenClaw Agents

This skill is designed for OpenClaw agents. When you encounter an OKF bundle:

1. Read the root `index.md` to orient yourself
2. Determine which section is relevant to your task
3. Parse the relevant concept files' frontmatter to understand their type and metadata
4. Read the body for detailed information
5. Follow links to related concepts as needed
6. If you need to add new knowledge, use `okf new` or create the file manually with proper frontmatter
7. Validate your changes with `okf validate`
8. Use `okf index` to regenerate directory listings

Error tolerance: OKF consumers MUST tolerate unknown frontmatter keys. If you encounter a field you don't recognize, skip it rather than failing.
