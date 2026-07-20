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

    def test_reduced_motion_css_rule_covers_flight_streaks(self):
        """The CSS half of reduced motion: #flightTrail and the loader.

        SCOPE, stated because this test used to be named as though it proved the
        whole feature: a stylesheet can only reach CSS animations. It cannot stop
        a requestAnimationFrame loop, so it says nothing about whether the galaxy
        keeps turning. This test was green for the entire period during which the
        scene spun, the sibling galaxies turned, and the intro flew the camera
        through space for a visitor who had asked for less motion.
        `test_reduced_motion_stops_autonomous_scene_motion` covers that.
        """
        self.assertIn("prefers-reduced-motion:reduce", re.sub(r"\s+", "", self.text))
        self.assertIn("#flightTrail", self.text)

    def test_reduced_motion_stops_autonomous_scene_motion(self):
        """The JS half: the preference must actually reach the render loop.

        An interactive scene answers reduced motion by removing the movement the
        visitor did not ask for, NOT by stopping — you must still be able to drag
        to orbit and scroll to fly. So the contract is:

          * the preference is read in JavaScript (`matchMedia`), since CSS cannot
            reach the loop at all;
          * a derived `spin` switch multiplies every autonomous rotation, so no
            `rotation.<axis> += dt` survives ungated;
          * the ~16s cinematic camera sweep starts already complete;
          * the 540-star warp tunnel is skipped rather than played.
        """
        self.assertIn("matchMedia", self.text)
        self.assertRegex(self.text, r"const\s+spin\s*=\s*reduceMotion\s*\?\s*0\s*:\s*1")
        self.assertNotRegex(
            self.text, r"rotation\.[xyz]\s*\+=\s*dt",
            "an autonomous rotation is not gated on the reduced-motion switch",
        )
        self.assertRegex(self.text, r"introT=\(reduceMotion\?1:0\)")
        self.assertRegex(self.text, r"if\(reduceMotion\)\{\s*warp\.style\.opacity=0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
