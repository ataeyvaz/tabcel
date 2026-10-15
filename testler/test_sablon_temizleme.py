"""Faz 10c: KVKK Paylaşım Temizleyici çok gizli `_tabcel` sayfasını da tarar ve temiz kopyada maskeler. Yalnız sentetik veri (kural 19)."""
import zipfile
from pathlib import Path

import pytest

from sentetik import tc_uret
from tabcel.io import temiz_dosya, xlsx_io
from tabcel.model import kimlik, temizle
from tabcel.sablon import saklama, yukleyici
from tabcel.sablon.uretici import uret

TC = tc_uret()


@pytest.fixture
def kitap():
    sb = yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), Path("yok_klasor")).bul("yerlesik:stok_takibi")
    k = uret(sb, ornek_veri=True).kitap
    # kullanıcı şablonunun örnek verisine yanlışlıkla gerçek kimlik girmiş gibi
    k.sablon.ham_moduller["urunler"]["ornek_veri"][0]["ad"] = f"Müşteri {TC}"
    k.sablon.uretici = "Tabcel 0.1 / Ayşe Örnek"
    return k


def test_tarama_cok_gizli_sablonu_bulur(kitap):
    kay = temizle.Tarayici(kitap).tara()
    s = [x for x in kay if x.yer.tur == temizle.SABLON]
    assert len(s) == 1 and s[0].tur == kimlik.TC and s[0].yer.gizli == "çok gizli sayfa" and s[0].bulgu.metin == TC


def test_temiz_kopya_sablonu_maskeler_ozgun_degismez(kitap):
    kay = temizle.Tarayici(kitap).tara()
    tk = temizle.temiz_kopya(kitap, kay, temizle.Plan(), motor_kur=False)
    metin = saklama.json_yaz(tk.kitap.sablon)
    assert TC not in metin and f"Müşteri {TC[:2]}*" in metin
    assert tk.kitap.sablon.uretici == "" and tk.kitap.sablon_ham is None
    assert TC in saklama.json_yaz(kitap.sablon) and kitap.sablon.uretici.startswith("Tabcel")      # özgün aynı
    assert tk.kitap.sablon.akis_kimligi == "stok_takibi"                                            # şablon bilgisi korunur


def test_sil_eylemi_ve_dosyada_ozgun_deger_yok(kitap, tmp_path):
    yol = str(tmp_path / "ozgun.xlsx")
    xlsx_io.kaydet(kitap, yol)
    k, _ = xlsx_io.ac(yol)
    kay = temizle.Tarayici(k).tara()
    plan = temizle.Plan()
    plan.eylem[kimlik.TC] = temizle.SIL
    tk = temizle.temiz_kopya(k, kay, plan, motor_kur=False)
    hedef = str(tmp_path / "temiz.xlsx")
    temiz_dosya.temiz_yaz(tk, hedef, ozgun_yol=yol)            # doğrulama _tabcel dahil tüm XML'de arar
    with zipfile.ZipFile(hedef) as z:
        butun = b"".join(z.read(a) for a in z.namelist()).decode("utf-8", "ignore")
    assert TC not in butun and "Ayşe Örnek" not in butun
    k3, _ = xlsx_io.ac(hedef)
    assert k3.sablon is not None and k3.sablon_denetim.aktif                         # temiz dosyada şablon yine çalışır
    with zipfile.ZipFile(yol) as z:                                                   # özgün dosya değişmedi
        assert TC in b"".join(z.read(a) for a in z.namelist()).decode("utf-8", "ignore")


def test_bozuk_json_olusturan_eylem_bilgiyi_atar(kitap):
    """Metin değişimi JSON'u bozarsa şablon bilgisi kopyaya taşınmaz (veri sızmasın)."""
    kay = temizle.Tarayici(kitap).tara()
    s = next(x for x in kay if x.yer.tur == temizle.SABLON)
    orijinal = temizle._yeni_metin

    def boz(grup, plan, maske_karakteri=None):
        return "{bozuk"
    temizle._yeni_metin = boz
    try:
        tk = temizle.temiz_kopya(kitap, [s], temizle.Plan(), motor_kur=False)
    finally:
        temizle._yeni_metin = orijinal
    assert tk.kitap.sablon is None
