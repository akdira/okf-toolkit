#!/usr/bin/env python3
"""Tests for okf-toolkit CLI."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

# Add the parent directory to the path so we can import okf
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from okf import (
    _parse_frontmatter,
    _find_md_files,
    _find_markdown_links,
    _rel_path,
    _safe_dump_yaml,
    RESERVED_NAMES,
    cmd_init,
    cmd_validate,
    cmd_list,
    cmd_search,
    cmd_stats,
    cmd_index,
    cmd_graph,
    build_parser,
    main,
)

# Path to the sample bundle
SAMPLE_BUNDLE = Path(__file__).resolve().parent.parent / "examples" / "sample-bundle"


class TestParseFrontmatter(unittest.TestCase):
    """Test _parse_frontmatter."""

    def test_valid_frontmatter(self):
        text = "---\ntype: Metric\ntitle: Test\n---\n\n# Body"
        fm, body = _parse_frontmatter(text)
        self.assertEqual(fm["type"], "Metric")
        self.assertEqual(fm["title"], "Test")
        self.assertEqual(body, "# Body")

    def test_no_frontmatter(self):
        text = "# Just a heading\n\nSome content"
        fm, body = _parse_frontmatter(text)
        self.assertEqual(fm, {})
        self.assertEqual(body, "# Just a heading\n\nSome content")

    def test_empty_frontmatter(self):
        text = "---\n---\n\nBody"
        fm, body = _parse_frontmatter(text)
        self.assertEqual(fm, {})
        self.assertEqual(body, "Body")

    def test_invalid_yaml(self):
        text = "---\n: invalid yaml\n---\n\nBody"
        fm, body = _parse_frontmatter(text)
        self.assertEqual(fm, {})
        # When YAML is invalid, the original text should be returned as body
        self.assertEqual(body, text)

    def test_closing_delimiter_on_same_line(self):
        text = "---\ntype: Test\n---\n# Body"
        fm, body = _parse_frontmatter(text)
        self.assertEqual(fm.get("type"), "Test")
        self.assertEqual(body, "# Body")


class TestFindMdFiles(unittest.TestCase):
    """Test _find_md_files."""

    def test_sample_bundle_has_files(self):
        files = _find_md_files(SAMPLE_BUNDLE)
        self.assertGreater(len(files), 0)

    def test_nonexistent_directory(self):
        files = _find_md_files(Path("/nonexistent/path"))
        self.assertEqual(files, [])


class TestFindMarkdownLinks(unittest.TestCase):
    """Test _find_markdown_links."""

    def test_standard_links(self):
        text = "See [orders](orders.md) and [customers](./customers.md)"
        links = _find_markdown_links(text)
        self.assertIn("orders.md", links)
        self.assertIn("./customers.md", links)

    def test_no_links(self):
        text = "Just some text without links"
        links = _find_markdown_links(text)
        self.assertEqual(links, [])

    def test_reference_links(self):
        text = "See [orders][ref]\n\n[ref]: orders.md"
        links = _find_markdown_links(text)
        self.assertIn("orders.md", links)


class TestReservedNames(unittest.TestCase):
    """Test RESERVED_NAMES."""

    def test_reserved_names(self):
        self.assertIn("index.md", RESERVED_NAMES)
        self.assertIn("log.md", RESERVED_NAMES)
        self.assertEqual(len(RESERVED_NAMES), 2)


class TestInit(unittest.TestCase):
    """Test cmd_init."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.bundle_path = Path(self.tmpdir.name) / "test-bundle"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_init_creates_structure(self):
        class Args:
            path = str(self.bundle_path)

        rc = cmd_init(Args())
        self.assertEqual(rc, 0)
        self.assertTrue(self.bundle_path.is_dir())
        self.assertTrue((self.bundle_path / "index.md").exists())
        self.assertTrue((self.bundle_path / "log.md").exists())

    def test_init_on_existing_empty_dir(self):
        self.bundle_path.mkdir(parents=True)
        class Args:
            path = str(self.bundle_path)

        rc = cmd_init(Args())
        self.assertEqual(rc, 0)
        self.assertTrue((self.bundle_path / "index.md").exists())

    def test_init_on_existing_nonempty_dir(self):
        self.bundle_path.mkdir(parents=True)
        (self.bundle_path / "existing.txt").write_text("hello")
        class Args:
            path = str(self.bundle_path)

        rc = cmd_init(Args())
        self.assertEqual(rc, 1)  # non-empty → error


class TestValidate(unittest.TestCase):
    """Test cmd_validate."""

    def test_validate_sample_bundle(self):
        class Args:
            bundle = str(SAMPLE_BUNDLE)

        rc = cmd_validate(Args())
        self.assertEqual(rc, 0)

    def test_validate_missing_type(self):
        """Create a concept without 'type' field and validate it should error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Init first
            init_args = type("Args", (), {"path": tmpdir})()
            cmd_init(init_args)

            # Create a concept without type
            concept = Path(tmpdir) / "noconcept.md"
            concept.write_text("---\ntitle: No Type\n---\n\nBody", encoding="utf-8")

            class Args:
                bundle = tmpdir

            rc = cmd_validate(Args())
            self.assertEqual(rc, 1)  # Error: missing type

    def test_validate_reserved_filename(self):
        """index.md with type should error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Init first
            init_args = type("Args", (), {"path": tmpdir})()
            cmd_init(init_args)

            # Write index.md with a type field (should be invalid)
            index_path = Path(tmpdir) / "index.md"
            index_path.write_text("---\ntype: Concept\n---\n\n# Listing", encoding="utf-8")

            class Args:
                bundle = tmpdir

            rc = cmd_validate(Args())
            self.assertEqual(rc, 1)  # Error: reserved filename with type

    def test_validate_empty_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            class Args:
                bundle = tmpdir

            rc = cmd_validate(Args())
            self.assertEqual(rc, 0)  # Empty bundle → warning only

    def test_validate_non_bundle_dir(self):
        class Args:
            bundle = "/nonexistent/path"

        rc = cmd_validate(Args())
        self.assertEqual(rc, 1)  # Not a directory

    def test_validate_non_utf8(self):
        """File with invalid UTF-8 should trigger error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Init first
            init_args = type("Args", (), {"path": tmpdir})()
            cmd_init(init_args)

            # Write a file with invalid UTF-8 bytes
            bad_file = Path(tmpdir) / "bad.md"
            bad_file.write_bytes(b"\xff\xfe\x00\xff")

            class Args:
                bundle = tmpdir

            rc = cmd_validate(Args())
            self.assertEqual(rc, 1)  # Error: non-UTF-8


class TestList(unittest.TestCase):
    """Test cmd_list."""

    def test_list_sample_bundle(self):
        class Args:
            bundle = str(SAMPLE_BUNDLE)

        rc = cmd_list(Args())
        self.assertEqual(rc, 0)

    def test_list_empty_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            class Args:
                bundle = tmpdir

            rc = cmd_list(Args())
            self.assertEqual(rc, 0)  # No concepts found, but not an error


class TestSearch(unittest.TestCase):
    """Test cmd_search."""

    def test_search_orders(self):
        class Args:
            bundle = str(SAMPLE_BUNDLE)
            q = "orders"

        rc = cmd_search(Args())
        self.assertEqual(rc, 0)

    def test_search_nonexistent(self):
        class Args:
            bundle = str(SAMPLE_BUNDLE)
            q = "zzz_nonexistent_zzz"

        rc = cmd_search(Args())
        self.assertEqual(rc, 0)  # No results, but not an error

    def test_search_empty_query(self):
        class Args:
            bundle = str(SAMPLE_BUNDLE)
            q = ""

        rc = cmd_search(Args())
        self.assertEqual(rc, 1)  # Empty query is an error


class TestStats(unittest.TestCase):
    """Test cmd_stats."""

    def test_stats_sample_bundle(self):
        class Args:
            bundle = str(SAMPLE_BUNDLE)

        rc = cmd_stats(Args())
        self.assertEqual(rc, 0)

    def test_stats_empty_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            class Args:
                bundle = tmpdir

            rc = cmd_stats(Args())
            self.assertEqual(rc, 0)


class TestIndex(unittest.TestCase):
    """Test cmd_index."""

    def test_index_on_bundle(self):
        """Index should succeed on the sample bundle."""
        class Args:
            bundle = str(SAMPLE_BUNDLE)

        rc = cmd_index(Args())
        self.assertEqual(rc, 0)

    def test_index_on_empty_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            class Args:
                bundle = tmpdir

            rc = cmd_index(Args())
            self.assertEqual(rc, 0)


class TestGraph(unittest.TestCase):
    """Test cmd_graph."""

    def test_graph_mermaid(self):
        class Args:
            bundle = str(SAMPLE_BUNDLE)
            format = "mermaid"

        rc = cmd_graph(Args())
        self.assertEqual(rc, 0)

    def test_graph_ascii(self):
        class Args:
            bundle = str(SAMPLE_BUNDLE)
            format = "ascii"

        rc = cmd_graph(Args())
        self.assertEqual(rc, 0)

    def test_graph_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            class Args:
                bundle = tmpdir
                format = "mermaid"

            rc = cmd_graph(Args())
            self.assertEqual(rc, 0)


class TestSafeDumpYaml(unittest.TestCase):
    """Test _safe_dump_yaml."""

    def test_colon_in_description(self):
        """Colon+space in a string value should produce valid YAML."""
        fm = {
            "type": "Test",
            "description": "Personal identity information: phone numbers, addresses",
            "timestamp": "2026-06-21T17:00:00Z",
        }
        result = _safe_dump_yaml(fm)
        data = yaml.safe_load(result)
        self.assertEqual(data["type"], "Test")
        self.assertEqual(
            data["description"],
            "Personal identity information: phone numbers, addresses",
        )

    def test_hash_in_description(self):
        """Hash sign in a string value should produce valid YAML."""
        fm = {
            "type": "Activity",
            "description": "Step #1: do this",
            "timestamp": "2026-06-21T17:00:00Z",
        }
        result = _safe_dump_yaml(fm)
        data = yaml.safe_load(result)
        self.assertEqual(data["description"], "Step #1: do this")

    def test_no_special_chars(self):
        """Normal descriptions should still produce clean output."""
        fm = {
            "type": "Metric",
            "description": "Daily active users",
            "timestamp": "2026-06-21T17:00:00Z",
        }
        result = _safe_dump_yaml(fm)
        data = yaml.safe_load(result)
        self.assertEqual(data["description"], "Daily active users")


class TestRelPath(unittest.TestCase):
    """Test _rel_path."""

    def test_rel_path_relative(self):
        bundle = Path("/bundle")
        file_path = Path("/bundle/tables/orders.md")
        result = _rel_path(bundle, file_path)
        self.assertEqual(result, "tables/orders.md")

    def test_rel_path_root(self):
        bundle = Path("/bundle")
        file_path = Path("/bundle/index.md")
        result = _rel_path(bundle, file_path)
        self.assertEqual(result, "index.md")


class TestBuildParser(unittest.TestCase):
    """Test argument parser."""

    def test_parser_builds(self):
        parser = build_parser()
        self.assertIsNotNone(parser)

    def test_version(self):
        rc = main(["--version"])
        self.assertEqual(rc, 0)

    def test_help(self):
        rc = main([])  # No args shows help
        self.assertEqual(rc, 0)

    def test_unknown_command(self):
        with self.assertRaises(SystemExit):
            main(["unknown"])


if __name__ == "__main__":
    unittest.main()
