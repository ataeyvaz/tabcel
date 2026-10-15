"""Excel'de ölçülmüş vaka sonuçlarını (vaka.json + vaka.json.excel.tsv) pytest dosyasına çevirir.
Kullanım: python araclar/vaka_teste.py araclar/vaka_parti1.json testler/test_kitaplik_parti1.py "açıklama"
Test dosyası Excel'e ihtiyaç duymaz; beklenen değerler gerçek Excel 16'dan (COM) alınmıştır."""
import json, sys
from pprint import pformat
vaka = json.load(open(sys.argv[1], encoding="utf-8"))
tsv = {}
for s in open(sys.argv[1] + ".excel.tsv", encoding="utf-8"):
    p = s.rstrip("\n").split("\t"); tsv[p[0]] = p[1:]
HATA = {"#DEĞER!": "#VALUE!", "#SAYI/0!": "#DIV/0!", "#SAYI!": "#NUM!", "#YOK": "#N/A", "#BAŞV!": "#REF!", "#AD?": "#NAME?", "#BOŞ!": "#NULL!"}
satirlar = []
for v in vaka:
    t, d, _ = tsv[v["id"]]
    if t == "sayi": b = ("sayi", float(d))
    elif t == "hata": b = ("hata", HATA.get(d, d))
    elif t == "bool": b = ("bool", d.upper() == "TRUE")
    elif t == "bos": b = ("bos", None)
    else: b = ("metin", d)
    if "ISFORMULA" in v["formul"]:
        continue
    satirlar.append((v["formul"], v.get("hucreler"), b))
out = f'''"""{sys.argv[4] if len(sys.argv) > 4 else "İşlev kitaplığı"} — beklenen değerler gerçek Excel 16'dan (COM, 2026-10-15) ölçüldü
(araclar/excel_vaka.py + araclar/vaka_teste.py üretti). Her işlev için normal/boş/hata/metin-sayı karışımı vakaları (kural 11)."""
import pytest

from _fonk import hesapla
from tabcel.model import deger as D
from tabcel.model.deger import Hata

VAKALAR = {pformat(satirlar, width=140)}


def _hata(kod):
    return D.hata_bul(kod)


@pytest.mark.parametrize("formul,hucreler,beklenen", VAKALAR, ids=[v[0] + "|" + str(i) for i, v in enumerate(VAKALAR)])
def test_excel_ile_ayni(formul, hucreler, beklenen):
    veri = {{k: (D.hata_bul("#DIV/0!") if x == "=1/0" else x) for k, x in (hucreler or {{}}).items() if x is not None}}
    s = hesapla(formul, veri)
    tur, deger = beklenen
    if tur == "sayi":
        assert isinstance(s, float) and not isinstance(s, bool), (formul, s)
        assert s == pytest.approx(deger, rel=1e-9, abs=1e-12), formul
    elif tur == "hata":
        assert isinstance(s, Hata) and s == _hata(deger), (formul, s)
    elif tur == "bool":
        assert s is deger, (formul, s)
    elif tur == "bos":
        assert s is None or s == 0.0
    else:
        assert s == deger, (formul, s)
'''
open(sys.argv[2], "w", encoding="utf-8").write(out)
print(len(satirlar))
