"""Vaka dosyası (JSON) → gerçek Excel (COM, görünmez örnek) ve Tabcel'de çalıştırıp karşılaştırır (2026-10-15).
Kullanım: .venv\\Scripts\\python araclar\\excel_vaka.py <vakalar.json>

Vaka: {"id": "x1", "formul": "=…" (kanonik İngilizce) | "deger": 1.5, "hucreler": {"A1": 5, "B1": "metin", "C1": "=A1*2"},
       "bicim": "kanonik sayı biçimi kodu"}. Excel'e biçim YEREL (Türkçe) kodla verilir (`yerele`). Fark yoksa sessiz kalır;
farkları "FARK" satırlarıyla yazar. Excel'in sütun darlığı (####) etkilemesin diye sütun genişliği 60 yapılır.
Excel kullanıcının açık kitaplarına dokunmaz (yeni örnek, iş sonunda Quit). Yaklaşık 1 sn/vaka; sonuç yanına .excel.tsv yazılır.
Üreticiler: araclar/excel_vaka_uret.py (293 işlev vakası). Excel Türkçe arayüzlüdür: biçim kodu, hata adı, işlev adı gerçeği
buradan okunur (kural 4/7)."""
import json
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
os.chdir(KOK)

from tabcel.formul.motor import Hesaplayici                      # noqa: E402
from tabcel.model.adres import hucre_coz                         # noqa: E402
from tabcel.model.deger import Hata                              # noqa: E402
from tabcel.model.gosterim import goster                         # noqa: E402
from tabcel.model.sayfa import CalismaKitabi, Hucre              # noqa: E402
from tabcel.model.sayi_bicimi import bicimle, yerele             # noqa: E402

ARACLAR = os.path.join(KOK, "araclar")


def main(yol: str) -> int:
    vakalar = json.load(open(yol, encoding="utf-8"))
    cikti = yol + ".excel.tsv"
    yerel_yol = yol + ".yerel.json"
    json.dump([dict(v, bicim=yerele(v["bicim"])) if v.get("bicim") else v for v in vakalar],
              open(yerel_yol, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    os.path.join(ARACLAR, "excel_vaka.ps1"), yerel_yol, cikti], check=True)
    excel = {}
    for satir in open(cikti, encoding="utf-8"):
        p = satir.rstrip("\n").split("\t")
        excel[p[0]] = p[1:]
    fark = 0
    for v in vakalar:
        kitap = CalismaKitabi()
        sayfa = kitap.sayfalar[0]
        motor = Hesaplayici(kitap)

        def koy(r, c, deger):
            if isinstance(deger, str) and deger.startswith("="):
                sayfa.ata(r, c, Hucre(formul=deger))
            elif deger is not None:
                sayfa.ata(r, c, Hucre(deger if isinstance(deger, (bool, str)) else float(deger)))
        for ad, deger in (v.get("hucreler") or {}).items():
            h = hucre_coz(ad)
            koy(h.satir, h.sutun, deger)
        if v.get("formul") is not None:
            koy(1, 26, v["formul"])
        elif v.get("deger") is not None:
            koy(1, 26, v["deger"])
        motor.tumunu_hesapla()
        d = sayfa.deger(1, 26)
        try:
            metin = bicimle(d, v.get("bicim") or "General").metin
        except Exception as e:                                    # noqa: BLE001
            metin = f"<{e}>"
        if isinstance(d, Hata):
            tur, sv = "hata", goster(d)
        elif d is None:
            tur, sv = "bos", ""
        elif isinstance(d, bool):
            tur, sv = "bool", str(d)
        elif isinstance(d, str):
            tur, sv = "metin", d
        else:
            tur, sv = "sayi", repr(float(d))
        e = excel.get(v["id"], ["YOK", "", ""])
        tur_ok = e[0] == tur
        if tur == "sayi" and e[0] == "sayi":
            try:
                deger_ok = abs(float(e[1]) - float(sv)) <= 1e-12 * max(1, abs(float(e[1])))
            except ValueError:
                deger_ok = False
        else:
            deger_ok = e[1].upper() == sv.upper() if tur == "bool" else e[1] == sv
        metin_ok = e[2] == metin if v.get("metin_kontrol", True) else True
        if not (tur_ok and deger_ok and metin_ok):
            fark += 1
            print(f"FARK {v['id']}: {v.get('formul', v.get('deger'))!r} biçim={v.get('bicim')} | "
                  f"Excel: {e[0]} {e[1]!r} metin={e[2]!r} | Tabcel: {tur} {sv!r} metin={metin!r}")
    print("toplam", len(vakalar), "fark", fark)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
