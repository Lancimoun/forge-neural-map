"""Static contracts for Forge's public interaction surface.

The site is intentionally a single-file WebGL experience. These checks keep
its accessible controls and production-only behavior hooks from disappearing
during visual work, without needing a JavaScript build tool or network access.
"""

from html.parser import HTMLParser
import os
import re
import unittest


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, "index.html")


def source():
    with open(INDEX, encoding="utf-8") as fh:
        return fh.read()


class SurfaceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.by_id = {}
        self.labels_for = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.by_id[values["id"]] = (tag, values)
        if tag == "label" and values.get("for"):
            self.labels_for.add(values["for"])


class ProductionBehaviorIsPreserved(unittest.TestCase):
    """The deployed surface had features newer than the old GitHub snapshot."""

    def setUp(self):
        self.text = source()
        self.dom = SurfaceParser()
        self.dom.feed(self.text)

    def test_recovered_live_features_keep_their_hooks(self):
        expected = {
            "askBtn", "askClose", "askLiveGo", "askLiveIn", "askLiveKey",
            "askLiveStatus", "askPanel", "starBtn", "starClose", "starGo",
            "starMsg", "starMsgBox", "starName", "starPanel", "starRecent",
            "thoughtHUD",
        }
        self.assertEqual(expected - self.dom.by_id.keys(), set())

    def test_core_search_and_flight_behavior_hooks_remain_wired(self):
        for hook in ("sInput", "sResults", "dSearch", "dFly", "flyHint"):
            with self.subTest(hook=hook):
                self.assertIn(hook, self.dom.by_id)
        self.assertIn("sInput.addEventListener('input',runSearch)", self.text)
        self.assertRegex(self.text, r"dFly.*addEventListener\('click'")
        self.assertIn("function enterFly()", self.text)
        self.assertIn("function exitFly()", self.text)
        self.assertIn("'wasdqe'.indexOf(k)", self.text)


class AccessibleSearchContract(unittest.TestCase):
    def setUp(self):
        self.text = source()
        self.dom = SurfaceParser()
        self.dom.feed(self.text)

    def test_search_has_a_persistent_name_and_instructions(self):
        self.assertIn("sInput", self.dom.labels_for)
        _, attrs = self.dom.by_id["sInput"]
        described_by = attrs.get("aria-describedby", "").split()
        self.assertIn("searchHelp", described_by)
        self.assertIn("searchHelp", self.dom.by_id)

    def test_results_announce_updates_without_stealing_focus(self):
        _, attrs = self.dom.by_id["sResults"]
        self.assertEqual(attrs.get("role"), "status")
        self.assertEqual(attrs.get("aria-live"), "polite")

    def test_recovered_live_forms_do_not_rely_on_placeholders(self):
        for control in ("askLiveIn", "starName", "starMsg"):
            with self.subTest(control=control):
                self.assertIn(control, self.dom.labels_for)


class CinematicFlightContract(unittest.TestCase):
    def setUp(self):
        self.text = source()
        self.dom = SurfaceParser()
        self.dom.feed(self.text)

    def test_flight_deck_exposes_live_status(self):
        for hook in ("flightDeck", "flightSpeed", "flightRange", "flightTarget"):
            with self.subTest(hook=hook):
                self.assertIn(hook, self.dom.by_id)
        _, attrs = self.dom.by_id["flightDeck"]
        self.assertEqual(attrs.get("role"), "status")
        self.assertEqual(attrs.get("aria-live"), "polite")

    def test_flight_state_is_visible_to_keyboard_and_assistive_tech(self):
        _, attrs = self.dom.by_id["dFly"]
        self.assertEqual(attrs.get("aria-pressed"), "false")
        self.assertRegex(self.text, r"dFly\.setAttribute\('aria-pressed',\s*'true'\)")
        self.assertRegex(self.text, r"dFly\.setAttribute\('aria-pressed',\s*'false'\)")
        self.assertIn("flightDeck.classList.add('show')", self.text)
        self.assertIn("flightDeck.classList.remove('show')", self.text)

    def test_reduced_motion_disables_nonessential_flight_streaks(self):
        self.assertIn("prefers-reduced-motion:reduce", re.sub(r"\s+", "", self.text))
        self.assertIn("#flightTrail", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
