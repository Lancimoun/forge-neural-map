"""The README's headline numbers must match the data file it describes.

The README (and Lance's GitHub profile front door) advertise "2,778 stars ·
7,295 connections · 157 systems". Those are real, verified numbers -- and
nothing checks them.

That matters because `nodes.json` is BAKED output: `bake.py` regenerates it from
a private knowledge-graph of a codebase that keeps changing. The next bake moves
every number, the README keeps the old ones, and the repo starts advertising a
figure that no longer describes the file sitting next to it. Nobody notices,
because a stale number renders exactly like a fresh one.

Two layers, because there are two ways to lie here:
  1. `meta` vs the actual arrays -- the file's own summary of itself can drift
     from its contents (meta is hand-maintainable; the arrays are not).
  2. README vs the data -- prose drift, the same failure LOOPKIT's CI catches.

Checking the README against `meta` alone would be circular: both could be wrong
together. The arrays are the ground truth; meta and the README are both claims
about them.

Stdlib only, no install, no network.
"""

import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODES = os.path.join(REPO, "nodes.json")
README = os.path.join(REPO, "README.md")


def load():
    with open(NODES, encoding="utf-8") as fh:
        return json.load(fh)


def readme_text():
    with open(README, encoding="utf-8") as fh:
        return fh.read()


def truth(data):
    """Counts derived from the arrays themselves -- the only ground truth here.

    gl is a FLAT list of index pairs (source, target, source, target, ...), so
    the link count is len(gl)//2. cm is a per-node community id; the number of
    'systems' is how many distinct ones exist.
    """
    return {
        "nodes": len(data["gR"]),
        "links": len(data["gl"]) // 2,
        "communities": len(set(data["cm"])),
    }


class MetaDescribesItsOwnFile(unittest.TestCase):
    """Layer 1: nodes.json's summary must match nodes.json's contents."""

    def setUp(self):
        self.data = load()
        self.actual = truth(self.data)

    def test_meta_counts_match_the_arrays(self):
        meta = self.data["meta"]
        for key, actual in self.actual.items():
            with self.subTest(key=key):
                self.assertEqual(
                    meta.get(key), actual,
                    "nodes.json meta says %s=%r but the arrays contain %d. meta is "
                    "hand-maintainable and the arrays are generated, so meta is the "
                    "one that drifts." % (key, meta.get(key), actual),
                )

    def test_every_per_node_array_is_the_same_length(self):
        # A bake that truncated one parallel array would silently mis-colour or
        # mis-place nodes rather than crash: index N of `c` would describe a
        # different star than index N of `gR`.
        n = self.actual["nodes"]
        ragged = {
            k: len(v)
            for k, v in self.data.items()
            if isinstance(v, list) and k not in ("files", "gl") and len(v) != n
        }
        self.assertEqual(
            ragged, {}, "per-node arrays disagree on how many nodes exist "
                        "(expected %d): %s" % (n, ragged)
        )

    def test_link_pairs_are_pairs_and_point_at_real_nodes(self):
        gl = self.data["gl"]
        self.assertEqual(len(gl) % 2, 0, "gl has an odd length -- it is a flat list of pairs")
        n = self.actual["nodes"]
        bad = [i for i in gl if not isinstance(i, int) or i < 0 or i >= n]
        self.assertEqual(bad[:5], [], "gl contains %d index(es) outside 0..%d" % (len(bad), n - 1))


class ReadmeMatchesTheData(unittest.TestCase):
    """Layer 2: the prose must match the file it describes."""

    def setUp(self):
        self.actual = truth(load())
        self.text = readme_text()

    def _stated(self, label):
        """Pull the number the README states next to a word, e.g. '7,295 connections'."""
        m = re.search(r"([\d,]+)\s*(?:real\s+)?" + label, self.text)
        self.assertIsNotNone(
            m, "README no longer states a number before %r -- if the wording "
               "changed deliberately, update this test with it." % label
        )
        return int(m.group(1).replace(",", ""))

    def test_star_count_matches(self):
        self.assertEqual(
            self._stated("stars"), self.actual["nodes"],
            "README advertises a star count that nodes.json does not contain. "
            "This number is also on Lance's GitHub profile front door.",
        )

    def test_connection_count_matches(self):
        self.assertEqual(
            self._stated("connections"), self.actual["links"],
            "README advertises a connection count that nodes.json does not "
            "contain (len(gl)//2).",
        )

    def test_system_count_matches(self):
        self.assertEqual(
            self._stated("systems"), self.actual["communities"],
            "README advertises a system count that does not match the distinct "
            "community ids in nodes.json.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
