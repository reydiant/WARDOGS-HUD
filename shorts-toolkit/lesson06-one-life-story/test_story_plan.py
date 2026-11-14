#!/usr/bin/env python3
"""Break the example plan one rule at a time and make sure the checker catches each one.

  python test_story_plan.py
"""
import copy, json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import story_plan as SP
import story_rules as R

CFG = json.load(open(os.path.join(HERE, "events.example.json"), encoding="utf-8"))
BEATS = json.load(open(os.path.join(HERE, "beats.example.json"), encoding="utf-8"))


def fresh():
    return SP.build(copy.deepcopy(CFG), copy.deepcopy(BEATS))


def seg(plan, section, n=0):
    return [s for s in plan["segments"] if s["section"] == section][n]


def fails(plan):
    F, _ = SP.check(plan, copy.deepcopy(CFG))
    return " | ".join(F)


class StoryPlanChecks(unittest.TestCase):
    def test_example_passes(self):
        p = fresh()
        self.assertEqual(fails(p), "")
        self.assertLessEqual(p["total"], R.MAX_TOTAL)

    def test_over_40_seconds(self):
        p = fresh()
        seg(p, "payoff")["pieces"][-1]["src_out"] += 1.0
        SP.layout_again(p)
        self.assertIn("over 40 s", fails(p))

    def test_first_frame_not_a_kill(self):
        p = fresh()
        h = seg(p, "hook")["pieces"][0]
        h["src_in"] -= 0.5
        h["src_out"] -= 0.5
        self.assertIn("first frame is not a kill", fails(p))

    def test_number_not_in_events(self):
        p = fresh()
        seg(p, "payoff")["texts"][0]["text"] = "150M TO SAVE THE ZONE"
        self.assertIn("number 150 is not in events.json", fails(p))

    def test_number_from_a_cut_kill(self):
        p = fresh()                       # kill 3 (18m) is cut from the Short, so 18 can't be on screen
        seg(p, "beat", 0)["texts"][0]["text"] = "18M FIRST CONTACT"
        self.assertIn("number 18 is not in events.json", fails(p))

    def test_label_not_in_events(self):
        p = fresh()
        seg(p, "setup")["texts"][0]["text"] = "FLANK THE BASE"
        self.assertIn("word 'FLANK' is not in events.json", fails(p))

    def test_banned_word(self):
        p = fresh()
        seg(p, "risky")["texts"][0]["text"] = "INSANE PUSH"
        self.assertIn("banned: 'insane'", fails(p))

    def test_counter_does_not_match_cuts(self):
        p = fresh()
        p["counter"]["steps"].pop(2)
        self.assertIn("kill counter lists kills", fails(p))
        p = fresh()
        p["counter"]["steps"][-1]["cash"] += 1350
        self.assertIn("kill counter step", fails(p))

    def test_beat_under_2s_readable(self):
        p = fresh()
        b = seg(p, "beat", 2)            # the speed-ramp beat: make almost all of it fast-forward
        k = CFG["events"][3]["t"]
        b["pieces"] = [SP.play(k - 9.0, k - 0.6, 6.0), SP.play(k - 0.6, k + 0.6)]
        SP.layout_again(p)
        self.assertIn("readable footage", fails(p))

    def test_same_edit_twice_in_a_row(self):
        b = copy.deepcopy(BEATS)
        b["beats"][1]["effect"] = "hold"
        p = SP.build(copy.deepcopy(CFG), b)
        self.assertIn("two beats in a row use 'hold'", fails(p))

    def test_text_too_small_for_a_phone(self):
        p = fresh()
        seg(p, "setup")["texts"][0]["size"] = 40
        self.assertIn("too small for a phone", fails(p))

    def test_text_too_short_to_read(self):
        p = fresh()
        seg(p, "setup")["texts"][0]["dur"] = 0.3
        self.assertIn("needs 1.30 s to read", fails(p))

    def test_end_card(self):
        p = fresh()
        seg(p, "end")["texts"][0]["text"] = "subscribe"
        f = fails(p)
        self.assertIn("missing @crazynando", f)
        self.assertIn("no subscribe ask", f)

    def test_beats_out_of_match_order(self):
        b = copy.deepcopy(BEATS)
        b["beats"][0], b["beats"][1] = b["beats"][1], b["beats"][0]
        p = SP.build(copy.deepcopy(CFG), b)
        self.assertIn("match order", fails(p))

    def test_spanish_word_limit(self):
        p = fresh()
        seg(p, "setup")["texts"][0]["text"] = "DALE WEPA HOLD THE ZONE"
        self.assertIn("Spanish", fails(p))
        p = fresh()
        seg(p, "setup")["texts"][0]["text"] = "DALE, HOLD THE ZONE"
        self.assertEqual(fails(p), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
