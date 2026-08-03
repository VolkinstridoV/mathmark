import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from part1 import SECTIONS, ALGEBRA
from part2 import SEQ, TRIG
from part3 import CALC, LINALG
from part4 import GEOM, PROB
from part5 import MORE_ALG, COMPLEX, MORE_TRIG
from part6 import MORE_CALC, MORE_LIN, MORE_PROB, NUMER

items = (ALGEBRA + MORE_ALG + COMPLEX + SEQ + TRIG + MORE_TRIG +
         CALC + MORE_CALC + LINALG + MORE_LIN + GEOM + PROB + MORE_PROB + NUMER)
ids = [i["id"] for i in items]
assert len(ids) == len(set(ids)), "повторяющиеся id: " + str([x for x in ids if ids.count(x) > 1])
# Образцы первых карточек лежат отдельным файлом — их проставляли уже после
# первой сборки, и при пересборке они бы потерялись.
SAMPLES = pathlib.Path(__file__).with_name("samples.json")
extra = json.loads(SAMPLES.read_text(encoding="utf-8")) if SAMPLES.exists() else {}
for it in items:
    if "try" not in it and it["id"] in extra:
        it["try"] = extra[it["id"]]
missing = [i["id"] for i in items if "try" not in i]
assert not missing, "без образца: " + str(missing)

out = pathlib.Path(__file__).resolve().parents[2] / "shared" / "cards" / "catalog.json"
out.write_text(json.dumps({"version": 1, "sections": SECTIONS, "items": items},
                          ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
from collections import Counter
c = Counter(i["s"] for i in items)
for s in SECTIONS:
    print(f"  {s['n']['ru']:32} {c.get(s['id'], 0)}")
print("  ВСЕГО", len(items))
