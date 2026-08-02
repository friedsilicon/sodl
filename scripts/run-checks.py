#!/usr/bin/env python3
"""Run the SODL check suite over the whole example corpus.

Two halves, and the second is the one that matters:

  valid    every .sodl outside examples/invalid/ must pass cleanly
  invalid  every .sodl in examples/invalid/ must fail, producing exactly
           the error codes named in its .expected file

The invalid half exists because a checker that quietly stops firing is
worse than no checker. Asserting on codes rather than message text means
rewording a diagnostic does not churn the tests, while a rule that stops
firing -- or starts firing for the wrong reason -- still fails.

Usage: scripts/run-checks.py        (exit 1 if anything fails)
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
INVALID = EXAMPLES / "invalid"
CHECKER = ROOT / "scripts" / "check-sodl.py"

CODE = re.compile(r"\bE\d{3}\b")


def run(paths):
    r = subprocess.run(
        [sys.executable, str(CHECKER), *[str(p) for p in paths]],
        capture_output=True,
        text=True,
    )
    return r.returncode, r.stdout + r.stderr


def check_valid():
    files = sorted(p for p in EXAMPLES.rglob("*.sodl") if INVALID not in p.parents)
    if not files:
        print("no valid examples found")
        return False
    rc, out = run(files)
    if rc != 0:
        print(f"FAIL  {len(files)} valid file(s): expected all to pass")
        print("".join(f"      {line}\n" for line in out.splitlines() if line.strip()))
        return False
    print(f"ok    {len(files)} valid file(s) pass")
    return True


def check_invalid():
    files = sorted(INVALID.glob("*.sodl"))
    if not files:
        print("no invalid examples found")
        return False
    ok = True
    for src in files:
        expected_file = src.with_suffix(".expected")
        if not expected_file.exists():
            print(f"FAIL  {src.name}: no .expected file naming the codes it must produce")
            ok = False
            continue
        want = {c for c in expected_file.read_text().split() if CODE.fullmatch(c)}
        rc, out = run([src])
        got = set(CODE.findall(out))
        if rc == 0:
            print(f"FAIL  {src.name}: expected {sorted(want)}, but the file passed")
            ok = False
        elif got != want:
            print(f"FAIL  {src.name}: expected {sorted(want)}, got {sorted(got)}")
            for line in out.splitlines():
                if line.strip().startswith("E"):
                    print(f"        {line.strip()}")
            ok = False
    if ok:
        print(f"ok    {len(files)} invalid file(s) rejected with the expected codes")
    return ok


if __name__ == "__main__":
    results = [check_valid(), check_invalid()]
    sys.exit(0 if all(results) else 1)
