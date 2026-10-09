"""Türkçe fonksiyon adlarını Microsoft tr-tr işlev sayfalarının SÖZDİZİMİ satırına karşı tarar (CLAUDE.md kural 4).

Sayfa BAŞLIĞINA güvenme (makine çevirisi; ör. DATEDIF başlığı TARİHFARKI, doğrusu ETARİHLİ).
Çalıştır: .venv\Scripts\python araclar\adlar_dogrula.py   (internet gerekir; 403/404 verenler elle bakılır:
bazı sayfalar hız sınırına takılır, IS* ailesi "is-functions", EĞERSAY/BUL farklı adreslerde)
"""
import sys, re, html, urllib.request, concurrent.futures as cf
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from tabcel.formul.adlar import EN_TR
def norm(s): return s.replace("İ","i").replace("I","ı").lower().replace("i̇","i")
def kontrol(item):
    en, tr = item
    u = f"https://support.microsoft.com/tr-tr/excel/functions/{en.lower().replace('.','-')}-function"
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        t = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    except Exception as e:
        return en, tr, "SAYFA YOK", str(e)[:40]
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    n = norm(t)
    bulundu = re.search(re.escape(norm(tr)) + r"\s*\(", n) is not None
    # sözdizimi satırında geçen aday adlar (yanlışsa gerçek adı görmek için)
    m = re.search(r"S[öo]z\s*Dizimi\s+([^\s(]+)\s*\(", t)
    return en, tr, "OK" if bulundu else "UYUMSUZ", (m.group(1) if m else "")
with cf.ThreadPoolExecutor(6) as ex:
    sonuc = list(ex.map(kontrol, EN_TR.items()))
for r in sonuc:
    if r[2] != "OK": print(r)
print("toplam", len(sonuc), "ok", sum(1 for r in sonuc if r[2] == "OK"))
