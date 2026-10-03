import tempfile
from pathlib import Path
from channelflow.lakehouse import catalog as open_catalog, IcebergTable
from tests.unit.lakehouse.conftest import trades_schema, trade

tmp = Path(tempfile.mkdtemp())
cat = open_catalog(uri=f"sqlite:///{tmp}/c.db", warehouse=str(tmp))
n = 0
orig = cat.load_table
def counting(*a, **k):
    global n; n += 1
    return orig(*a, **k)
cat.load_table = counting
t = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=cat)
t.append([trade(1)]); t.append([trade(2)]); t.append([trade(3)])
def loads(label, fn):
    global n; n = 0; fn(); print(f"{label:34s} {n} load(s)")
loads("snapshot_ids()", t.snapshot_ids)
loads("read()", t.read)
loads("read(snapshot_id=2)", lambda: t.read(snapshot_id=2))
loads("current()", t.current)
loads("snapshot(2)", lambda: t.snapshot(2))
loads("append([row])", lambda: t.append([trade(4)]))
