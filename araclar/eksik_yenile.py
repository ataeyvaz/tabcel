"""eksik_fonksiyonlar.md'yi kayıt defterine göre yeniler: kayıtlı işlevleri tablodan çıkarır, sayıları günceller.
Kullanım: .venv\\Scripts\\python araclar\\eksik_yenile.py"""
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
os.chdir(KOK)
from tabcel.formul.fonksiyonlar import KAYIT  # noqa: E402

m = open("eksik_fonksiyonlar.md", encoding="utf-8").read()
out = []
for ln in m.split("\n"):
    r = re.match(r"^\| `([^`]+)` \| `([^`]+)` \|$", ln)
    if r and r.group(1) in KAYIT:
        continue
    out.append(ln)
m = "\n".join(out)
parcalar = re.split(r"(?m)^## ", m)
yeni, toplam = [parcalar[0]], 0
for b in parcalar[1:]:
    ad = b.split("\n")[0]
    n = len(re.findall(r"^\| `", b, re.M))
    toplam += n
    if n == 0:
        continue
    yeni.append(b.replace(ad, re.sub(r"\(\d+\)", f"({n})", ad), 1))
m = "## ".join(yeni)
m = re.sub(r"Tabcel'de kayıtlı işlev sayısı: \d+\.", f"Tabcel'de kayıtlı işlev sayısı: {len(KAYIT)}.", m)
m = re.sub(r"hâlâ olmayan \d+ tanesidir", f"hâlâ olmayan {toplam} tanesidir", m)
open("eksik_fonksiyonlar.md", "w", encoding="utf-8").write(m)
print(len(KAYIT), toplam)
