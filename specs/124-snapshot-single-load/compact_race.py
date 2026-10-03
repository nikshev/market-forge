"""Does compact() lose a row appended between its read and its overwrite?"""
import tempfile
from pathlib import Path
from pyiceberg.table import Table
from channelflow.lakehouse import catalog as open_catalog, IcebergTable
from tests.unit.lakehouse.conftest import trades_schema, trade

tmp = Path(tempfile.mkdtemp())
cat = open_catalog(uri=f"sqlite:///{tmp}/c.db", warehouse=str(tmp))
mk = lambda: IcebergTable(name="cex_trades", schema=trades_schema(), catalog=cat)
t, other = mk(), mk()
for i in range(1, 5):
    t.append([trade(i)])                       # 4 files -> compaction has work
before = t.read().num_rows

real_overwrite = Table.overwrite
state = {"done": False}
def overwrite_after_a_competitor(self, df, *a, **k):
    if not state["done"]:
        state["done"] = True
        other.append([trade(99)])              # lands between compact's read and its overwrite
    return real_overwrite(self, df, *a, **k)
Table.overwrite = overwrite_after_a_competitor

try:
    t.compact()
    print("compact: finished")
except Exception as e:
    print("compact raised:", type(e).__name__)
Table.overwrite = real_overwrite
rows = t.read()["event_time_ns"].to_pylist()
print("rows before compact:", before, "| competitor appended 1 | rows after:", len(rows))
print("competitor's row (t=99s) survived:", 99_000_000_000 in rows)
