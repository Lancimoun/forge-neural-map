"""Provider-free contracts for the post-deploy release verifier."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
import unittest
from unittest import mock

import verify_release


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, "index.html")
NODES = os.path.join(REPO, "nodes.json")


def repository_payloads():
    with open(INDEX, "rb") as fh:
        index = fh.read()
    with open(NODES, "rb") as fh:
        nodes = fh.read()
    return index, nodes


class ReleaseVerifierContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index, cls.nodes = repository_payloads()

    def fake_fetcher(self, index=None, nodes=None):
        index = self.index if index is None else index
        nodes = self.nodes if nodes is None else nodes
        calls = []

        def fetch(url):
            calls.append(url)
            if url.endswith("nodes.json"):
                return nodes
            return index

        return fetch, calls

    def test_repository_artifacts_pass_the_same_contract_as_production(self):
        fetch, calls = self.fake_fetcher()

        result = verify_release.verify_release(
            "https://forge.example/preview", fetcher=fetch
        )

        self.assertEqual(
            calls,
            [
                "https://forge.example/preview/",
                "https://forge.example/preview/nodes.json",
            ],
        )
        self.assertEqual(result["nodes"]["nodes"], 2778)
        self.assertEqual(result["nodes"]["links"], 7295)
        self.assertEqual(result["nodes"]["communities"], 157)
        self.assertGreaterEqual(result["index"]["required_ids"], 25)

    def test_missing_cinematic_marker_fails_closed(self):
        broken = self.index.replace(b"neural flight telemetry", b"flight status", 1)
        fetch, _ = self.fake_fetcher(index=broken)

        with self.assertRaisesRegex(
            verify_release.ReleaseVerificationError,
            "neural flight telemetry",
        ):
            verify_release.verify_release("https://forge.example", fetcher=fetch)

    def test_missing_recovered_live_hook_fails_closed(self):
        broken = self.index.replace(b'id="thoughtHUD"', b'id="lostThoughtHUD"', 1)
        fetch, _ = self.fake_fetcher(index=broken)

        with self.assertRaisesRegex(
            verify_release.ReleaseVerificationError,
            "thoughtHUD",
        ):
            verify_release.verify_release("https://forge.example", fetcher=fetch)

    def test_wrong_dataset_fails_even_when_its_meta_is_self_consistent(self):
        data = json.loads(self.nodes)
        data["gR"].pop()
        data["cm"].pop()
        for key, value in list(data.items()):
            if (
                isinstance(value, list)
                and key not in ("files", "gl", "gR", "cm")
                and len(value) == 2778
            ):
                value.pop()
        data["meta"]["nodes"] = 2777
        mutated = json.dumps(data, separators=(",", ":")).encode()
        fetch, _ = self.fake_fetcher(nodes=mutated)

        with self.assertRaisesRegex(
            verify_release.ReleaseVerificationError,
            "expected 2778",
        ):
            verify_release.verify_release("https://forge.example", fetcher=fetch)

    def test_cli_returns_nonzero_and_a_concise_error(self):
        output = StringIO()
        error = verify_release.ReleaseVerificationError("missing release marker")
        with mock.patch.object(verify_release, "verify_release", side_effect=error):
            with redirect_stdout(output), redirect_stderr(output):
                code = verify_release.main(["--base-url", "https://forge.example"])

        self.assertEqual(code, 1)
        self.assertIn("FAIL: missing release marker", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
