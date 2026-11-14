#!/usr/bin/env python3
"""Test --plan mode against a fake LM Studio server (no model needed).

The first draft has planted mistakes: a number from a cut kill, a word the footage doesn't show,
a hype word, three Spanish words and a missing beat caption. The bridge must reject all of them
and ask for a fix. The second draft is clean, and --apply must write a plan that passes the plan check.

  python test_story_mode.py
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
STORY = os.path.join(HERE, "..", "lesson06-one-life-story")

BAD = {"titles": ["5 kills, one life, no armor", "18m on the stairs. Insane.", "$10,800 and one life",
                  "One shot to save the zone", "141m to save the zone, one life"],
       "description": "A 141m headshot saved the zone.\n#wardogs #shorts #fps #gaming",
       "pinned_comment": "Smoke headshot or the 141m shot to save the zone?",
       "captions": ["ONE LIFE", "141M SHOT"],
       "beat_captions": {"hook": "ONE LIFE. NO ARMOR.", "setup": "DALE WEPA, HOLD THE ZONE",
                         "beat1": "FLANKED THE BASE", "beat2": "18M ON THE STAIRS", "risky": "PUSHED THE TRUCK",
                         "payoff": "141M TO SAVE THE ZONE"}}
GOOD = {"titles": ["5 kills, one life, no armor", "$10,800 with one life and no armor",
                   "141m headshot to save the zone. One life.", "One life, 5 kills, last one on the point",
                   "5 kills before the zone fell? Not this time"],
        "description": "A 141m headshot saved the zone on the last push.\n#wardogs #shorts #fps #gaming",
        "pinned_comment": "Smoke headshot or the 141m shot to save the zone?",
        "captions": ["ONE LIFE", "141M SHOT"],
        "beat_captions": {"hook": "ONE LIFE. NO ARMOR.", "setup": "DALE, HOLD THE ZONE",
                          "beat1": "FIRST CONTACT", "beat2": "HEADSHOT THROUGH THE SMOKE", "beat3": "106M ON THE RIDGE",
                          "risky": "PUSHED THE TRUCK ALONE", "payoff": "141M TO SAVE THE ZONE"}}
calls = []


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self.reply({"data": [{"id": "google/gemma-3-12b"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        calls.append(body)
        draft = BAD if len(calls) == 1 else GOOD
        self.reply({"choices": [{"message": {"content": json.dumps(draft)}}]})


def main():
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tmp = tempfile.mkdtemp()
    for f in ("events.example.json", "beats.example.json"):
        shutil.copy(os.path.join(STORY, f), tmp)
    subprocess.run([sys.executable, os.path.join(STORY, "story_plan.py"), "build", "events.example.json",
                    "beats.example.json", "--out", "plan.json"], cwd=tmp, check=True, capture_output=True)
    log = os.path.join(HERE, "hook_log.json")
    saved = open(log).read() if os.path.exists(log) else None
    try:
        if os.path.exists(log):
            os.remove(log)
        r = subprocess.run([sys.executable, os.path.join(HERE, "lm_bridge.py"), "events.example.json", "--plan",
                            "plan.json", "--apply", "--url", f"http://127.0.0.1:{srv.server_port}/v1"],
                           cwd=tmp, capture_output=True, text=True)
        out = r.stdout + r.stderr
        fix_request = calls[1]["messages"][1]["content"] if len(calls) > 1 else ""
        checks = {
            "story prompt sent": "One-life story mode" in calls[0]["messages"][0]["content"],
            "voice rules still sent": "Puerto Rican" in calls[0]["messages"][0]["content"],
            "facts only hold kills left in the plan": '"kill_count": 5' in calls[0]["messages"][1]["content"],
            "cut kill's 18m rejected": "number 18 is not in" in fix_request,
            "unshown word rejected": "word 'FLANKED' is not in events.json" in fix_request,
            "hype word rejected": "banned word" in fix_request,
            "Spanish limit enforced": "Spanish word" in fix_request,
            "missing beat caption caught": "beat_captions.beat3" in fix_request,
            "asked once for a fix": len(calls) == 2,
            "clean draft passes": "ALL CHECKS PASSED" in out,
            "captioned plan passes the plan check": "plan check PASSES" in out,
        }
        if os.path.exists(os.path.join(tmp, "plan.captioned.json")):
            p = json.load(open(os.path.join(tmp, "plan.captioned.json")))
            checks["caption applied"] = any(x["text"] == "DALE, HOLD THE ZONE" for s in p["segments"] for x in s["texts"])
        # hook rotation: a second one-life-story Short in a row is flagged
        json.dump(["one-life-story"], open(log, "w"))
        calls.clear()
        r2 = subprocess.run([sys.executable, os.path.join(HERE, "lm_bridge.py"), "events.example.json", "--plan",
                             "plan.json", "--url", f"http://127.0.0.1:{srv.server_port}/v1"],
                            cwd=tmp, capture_output=True, text=True)
        checks["same hook format twice is flagged"] = "never the same hook format twice" in r2.stdout
    finally:
        if saved is None:
            os.path.exists(log) and os.remove(log)
        else:
            open(log, "w").write(saved)
        shutil.rmtree(tmp, ignore_errors=True)
        srv.shutdown()
    for k, v in checks.items():
        print(("ok    " if v else "FAIL  ") + k)
    if not all(checks.values()):
        print("\n--- bridge output ---\n" + out)
        sys.exit(1)
    print("\nall story-mode checks passed")


if __name__ == "__main__":
    main()
