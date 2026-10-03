import dataclasses
from channelflow.pipeline.resample import resample
from channelflow.timeframes import parse as parse_timeframe
from tests.unit.test_resample import make_bar
M = 60_000_000_000
tf5, tf1 = parse_timeframe("5m"), parse_timeframe("1m")
now = 10**18
def run(label, bars):
    r = resample(bars, target=tf5, source_timeframe=tf1, now_ns=now)
    print(f"{label:46s} bars={len(r.bars)} refusals={len(r.refusals)}")
base = [make_bar(i * M) for i in range(5)]
run("complete window (control)", base)
run("4 distinct minutes + 1 minute twice", [make_bar(i * M) for i in (0, 1, 2, 3, 3)])
print("   -> a window MISSING minute 4 is folded into a bar" )
non_final = [make_bar(i * M, is_final=(i != 2)) for i in range(5)]
run("complete window, one source bar NOT final", non_final)
