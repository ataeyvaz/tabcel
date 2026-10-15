import sys, os, time
sys.path.insert(0, '.')
yol = sys.argv[1]
from tabcel.io import xlsx_io, xlsx_hizli
for ad, fn in (("özgün", xlsx_hizli.kapat), ("hızlı", xlsx_hizli.kur)):
    fn()
    t = time.perf_counter()
    k, r = xlsx_io.ac(yol)
    print(ad, round(time.perf_counter() - t, 2), "sn", "hücre:", sum(len(s._hucreler) for s in k.sayfalar), flush=True)
