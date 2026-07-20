"""Verify that a deployed Forge Neural Map matches the release contract.

The checker performs two read-only HTTP GETs: the public page and nodes.json.
It never opens Ask Maxima, submits a visitor star, uses credentials, or calls an
AI provider. The same validation functions are exercised offline in CI against
the repository artifacts.
"""

from argparse import ArgumentParser
from html.parser import HTMLParser
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://forge-neural-map-production.up.railway.app"
EXPECTED_COUNTS = {"nodes": 2778, "links": 7295, "communities": 157}
MAX_RESPONSE_BYTES = 32 * 1024 * 1024

RECOVERED_IDS = {
    "askBtn",
    "askClose",
    "askLiveGo",
    "askLiveIn",
    "askLiveKey",
    "askLiveStatus",
    "askPanel",
    "starBtn",
    "starClose",
    "starGo",
    "starMsg",
    "starMsgBox",
    "starName",
    "starPanel",
    "starRecent",
    "thoughtHUD",
}

RELEASE_IDS = RECOVERED_IDS | {
    "dFly",
    "flightDeck",
    "flightRange",
    "flightSpeed",
    "flightTarget",
    "flightTrail",
    "flyHint",
    "sInput",
    "sResults",
    "searchHelp",
}


class ReleaseVerificationError(RuntimeError):
    """The public artifact is reachable but does not match this release."""


class SurfaceProbe(HTMLParser):
    def __init__(self):
        super().__init__()
        self.by_id = {}
        self.labels_for = set()
        self.text = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.by_id[values["id"]] = (tag, values)
        if tag == "label" and values.get("for"):
            self.labels_for.add(values["for"])

    def handle_data(self, data):
        self.text.append(data)


def _require(condition, message):
    if not condition:
        raise ReleaseVerificationError(message)


def fetch_bytes(url, timeout=15.0):
    """Fetch one bounded public artifact with no authentication or cookies."""
    request = Request(
        url,
        headers={"User-Agent": "forge-release-verifier/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            _require(status == 200, "%s returned HTTP %s" % (url, status))
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise ReleaseVerificationError(
            "%s returned HTTP %s" % (url, exc.code)
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ReleaseVerificationError("could not fetch %s: %s" % (url, exc)) from exc

    _require(
        len(payload) <= MAX_RESPONSE_BYTES,
        "%s exceeded the %d-byte safety limit" % (url, MAX_RESPONSE_BYTES),
    )
    return payload


def verify_index(text):
    probe = SurfaceProbe()
    probe.feed(text)

    missing = sorted(RELEASE_IDS - probe.by_id.keys())
    _require(not missing, "index is missing release hook(s): %s" % ", ".join(missing))

    required_labels = {"sInput", "askLiveIn", "starName", "starMsg"}
    missing_labels = sorted(required_labels - probe.labels_for)
    _require(
        not missing_labels,
        "index is missing persistent label(s): %s" % ", ".join(missing_labels),
    )

    _, flight = probe.by_id["flightDeck"]
    _require(flight.get("role") == "status", "flightDeck must keep role=status")
    _require(
        flight.get("aria-live") == "polite",
        "flightDeck must keep aria-live=polite",
    )

    _, results = probe.by_id["sResults"]
    _require(results.get("role") == "status", "sResults must keep role=status")
    _require(
        results.get("aria-live") == "polite",
        "sResults must keep aria-live=polite",
    )

    _, fly = probe.by_id["dFly"]
    _require(fly.get("aria-pressed") == "false", "dFly must keep aria-pressed=false")
    _require(fly.get("aria-controls") == "flightDeck", "dFly must control flightDeck")

    visible_text = " ".join(" ".join(probe.text).split()).lower()
    _require(
        "neural flight telemetry" in visible_text,
        "index is missing the neural flight telemetry release marker",
    )

    compact = re.sub(r"\s+", "", text)
    _require(
        "prefers-reduced-motion:reduce" in compact,
        "index is missing reduced-motion protection",
    )

    behavior_markers = (
        "sInput.addEventListener('input',runSearch)",
        "function enterFly()",
        "function exitFly()",
        "flightDeck.classList.add('show')",
        "flightDeck.classList.remove('show')",
    )
    missing_behavior = [marker for marker in behavior_markers if marker not in text]
    _require(
        not missing_behavior,
        "index is missing behavior marker(s): %s" % ", ".join(missing_behavior),
    )

    return {
        "required_ids": len(RELEASE_IDS),
        "labels": len(required_labels),
        "cinematic_marker": "neural flight telemetry",
    }


def verify_nodes(data):
    _require(isinstance(data, dict), "nodes.json must contain a JSON object")
    for key in ("gR", "gl", "cm"):
        _require(isinstance(data.get(key), list), "nodes.json is missing list %r" % key)

    graph = data["gR"]
    links = data["gl"]
    communities = data["cm"]
    _require(len(links) % 2 == 0, "nodes.json gl must contain index pairs")

    actual = {
        "nodes": len(graph),
        "links": len(links) // 2,
        "communities": len(set(communities)),
    }
    for key, expected in EXPECTED_COUNTS.items():
        _require(
            actual[key] == expected,
            "nodes.json %s=%d; expected %d for this release"
            % (key, actual[key], expected),
        )

    meta = data.get("meta")
    _require(isinstance(meta, dict), "nodes.json is missing its meta object")
    for key, value in actual.items():
        _require(
            meta.get(key) == value,
            "nodes.json meta %s=%r but arrays contain %d"
            % (key, meta.get(key), value),
        )

    node_count = actual["nodes"]
    ragged = {
        key: len(value)
        for key, value in data.items()
        if isinstance(value, list)
        and key not in ("files", "gl")
        and len(value) != node_count
    }
    _require(not ragged, "nodes.json has ragged per-node arrays: %r" % ragged)

    bad_links = [
        value
        for value in links
        if not isinstance(value, int) or value < 0 or value >= node_count
    ]
    _require(
        not bad_links,
        "nodes.json contains %d invalid link index(es)" % len(bad_links),
    )
    return actual


def verify_release(base_url=DEFAULT_BASE_URL, timeout=15.0, fetcher=None):
    """Fetch and verify the two static production artifacts."""
    parsed = urlparse(base_url)
    _require(parsed.scheme in ("http", "https") and parsed.netloc, "invalid base URL")

    root = base_url.rstrip("/") + "/"
    index_url = root
    nodes_url = urljoin(root, "nodes.json")
    fetch = fetcher or (lambda url: fetch_bytes(url, timeout=timeout))

    index_payload = fetch(index_url)
    nodes_payload = fetch(nodes_url)
    _require(isinstance(index_payload, bytes), "index fetcher must return bytes")
    _require(isinstance(nodes_payload, bytes), "nodes fetcher must return bytes")

    try:
        index_text = index_payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReleaseVerificationError("index is not valid UTF-8") from exc
    try:
        nodes_data = json.loads(nodes_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseVerificationError("nodes.json is not valid UTF-8 JSON") from exc

    index_result = verify_index(index_text)
    index_result.update({"url": index_url, "bytes": len(index_payload)})
    nodes_result = verify_nodes(nodes_data)
    nodes_result.update({"url": nodes_url, "bytes": len(nodes_payload)})
    return {"base_url": root, "index": index_result, "nodes": nodes_result}


def parser():
    command = ArgumentParser(description=__doc__)
    command.add_argument("--base-url", default=DEFAULT_BASE_URL)
    command.add_argument("--timeout", type=float, default=15.0)
    command.add_argument("--json", action="store_true", dest="as_json")
    return command


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = verify_release(args.base_url, timeout=args.timeout)
    except ReleaseVerificationError as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("PASS: Forge release contract verified at %s" % result["base_url"])
        print(
            "  index: {bytes:,} bytes · {required_ids} hooks · {labels} labels".format(
                **result["index"]
            )
        )
        print(
            "  nodes: {nodes:,} · links: {links:,} · systems: {communities:,}".format(
                **result["nodes"]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
