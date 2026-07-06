# TENON full-corpus regression sweep
import subprocess, sys, pathlib, re, os

FIXTURES_DIR = pathlib.Path("tests/fixtures")
fixtures = sorted(d for d in FIXTURES_DIR.iterdir()
                  if d.is_dir() and not d.name.startswith("_"))

env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
board = []

for fx in fixtures:
    result = subprocess.run(
        [sys.executable, "tests/check_match.py", str(fx)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    print(f"\n=== {fx.name} ===")
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    def grab(label):
        m = re.search(rf"{label}:\s+(\d+)", result.stdout)
        return int(m.group(1)) if m else None

    correct = grab("Correct")
    extra   = grab("Extra")
    missing = grab("Missing-rule")

    if None in (correct, extra, missing):
        print(f"!! could not parse counts for {fx.name}", file=sys.stderr)
        continue

    board.append((fx.name, correct, extra, missing))

print("\n=== SUMMARY ===")
print(f"{'Fixture':<28} {'Correct':>8} {'Extra':>6} {'Missing':>8}")
tc = te = tm = 0
for name, c, e, m in board:
    print(f"{name:<28} {c:>8} {e:>6} {m:>8}")
    tc += c; te += e; tm += m
print(f"{'-'*28} {'-'*8} {'-'*6} {'-'*8}")
print(f"{'TOTAL':<28} {tc:>8} {te:>6} {tm:>8}")

ak_total = tc + tm
pred_total = tc + te
if ak_total:
    print(f"\nRecall:    {tc/ak_total:.1%}  ({tc}/{ak_total})")
if pred_total:
    print(f"Precision: {tc/pred_total:.1%}  ({tc}/{pred_total})")