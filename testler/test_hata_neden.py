"""T8: hata açıklamaları (`formul/hata_neden.py`, Qt yok). Tasarım: t8_tasarim.md.

Açıklama cümleleri bizim metnimiz (Excel'in hata denetimi iletilerinin çevirisi değil); testler
hatanın KAYNAĞINI (hücre, düğüm) ve cümlenin anahtar parçasını sınar."""
from tabcel.formul import ceviri
from tabcel.formul.hata_neden import acikla, metin
from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import hucre_coz
from tabcel.model.sayfa import CalismaKitabi, Hucre


def kur(veri, sayfa2=None):
    """veri: {"A1": girdi} — '=' ile başlayanlar Türkçe formül (kullanıcı yazımı)."""
    k = CalismaKitabi()
    if sayfa2 is not None:
        k.sayfa_ekle("Sayfa2")
    for ad, d in [(0, veri)] + ([(1, sayfa2)] if sayfa2 else []):
        s = k.sayfalar[ad]
        for adres, g in d.items():
            h = hucre_coz(adres)
            if isinstance(g, str) and g.startswith("="):
                s.ata(h.satir, h.sutun, Hucre(None, ceviri.girdiden(g, k)))
            else:
                s.ata(h.satir, h.sutun, Hucre(g))
    m = Hesaplayici(k)
    return k, m


def ac(k, adres, sayfa=0):
    h = hucre_coz(adres)
    s = k.sayfalar[sayfa]
    return acikla(s, h.satir, h.sutun)


def yazi(k, adres, sayfa=0):
    return metin(ac(k, adres, sayfa))


def adresler(z):
    from tabcel.model.adres import hucre_yaz
    return [hucre_yaz(h.satir, h.sutun) for h in z]


# ---------------------------------------------------------------- doğrudan nedenler
def test_metin_islenen_hucrede():
    k, _ = kur({"B3": "abc", "C1": "=B3+1"})
    assert yazi(k, "C1") == "#DEĞER!: B3 hücresinde sayı yerine metin var (\"abc\")."


def test_metin_islenen_formulde_sabit():
    k, _ = kur({"A1": '="x"*2'})
    assert yazi(k, "A1") == "#DEĞER!: Formülde sayı yerine metin var (\"x\")."


def test_bolen_sifir_ya_da_bos():
    k, _ = kur({"A1": 5.0, "C1": "=A1/B1"})
    assert yazi(k, "C1") == "#BÖL/0!: Bölen (B1) sıfır ya da boş."
    k, _ = kur({"C1": "=1/0"})
    assert yazi(k, "C1") == "#BÖL/0!: Bölen sıfır ya da boş."


def test_us_tanimsiz():
    k, _ = kur({"A1": "=0^0"})
    assert "Üs alma" in yazi(k, "A1") and yazi(k, "A1").startswith("#SAYI!")


def test_bilinmeyen_islev():
    k, _ = kur({"A1": "=TOPLAMM(1)"})
    assert yazi(k, "A1") == "#AD?: 'TOPLAMM' adlı bir işlev yok."


def test_arguman_sayisi():
    """Elle yazarken ayrıştırıcı reddeder; dosyadan gelen (kanonik) formülde #DEĞER! olur."""
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(None, "=SQRT(1,2)"))
    Hesaplayici(k)
    assert metin(acikla(s, 1, 1)) == "#DEĞER!: KAREKÖK 1 bağımsız değişken ister; 2 verildi."


def test_tanimsiz_ad():
    k, _ = kur({"A1": "=Gelir*2"})
    assert yazi(k, "A1") == "#AD?: 'Gelir' adı tanımlı değil."


def test_bos_kesisim():
    k, _ = kur({"A1": "=TOPLA(B1:B3 D1:D3)"})
    assert yazi(k, "A1") == "#BOŞ!: İki aralığın ortak hücresi yok."


def test_elle_yazilmis_hata():
    from tabcel.model import deger as D
    k, _ = kur({"A1": D.YOK, "B1": "=A1"})
    assert yazi(k, "A1") == "#YOK: Hücreye #YOK değeri yazılmış."
    assert yazi(k, "B1") == "#YOK: A1 hücresinden geliyor (B1 → A1). A1: Hücreye #YOK değeri yazılmış."


def test_hata_olmayan_ve_bos_hucre():
    k, _ = kur({"A1": 1.0, "B1": "=A1*2"})
    assert ac(k, "B1") is None and ac(k, "Z9") is None and metin(None) == ""


# ---------------------------------------------------------------- zincir
def test_zincir_iki_halka():
    k, _ = kur({"A1": "abc", "B3": "=A1*2", "C5": "=B3+1"})
    z = ac(k, "C5")
    assert adresler(z) == ["C5", "B3"]                         # A1 sabit metin (hata değil): hata B3'te doğar
    assert z[-1].neden == "A1 hücresinde sayı yerine metin var (\"abc\")."
    assert yazi(k, "C5") == ("#DEĞER!: B3 hücresinden geliyor (C5 → B3). "
                            "B3: A1 hücresinde sayı yerine metin var (\"abc\").")


def test_zincir_baska_sayfa():
    k, _ = kur({"A1": "=Sayfa2!B2+1"}, sayfa2={"B1": "x", "B2": "=B1*3"})
    z = ac(k, "A1")
    assert [(h.sayfa.ad, h.satir, h.sutun) for h in z] == [("Sayfa1", 1, 1), ("Sayfa2", 2, 2)]
    assert yazi(k, "A1") == ("#DEĞER!: Sayfa2!B2 hücresinden geliyor (A1 → Sayfa2!B2). "
                            "Sayfa2!B2: Sayfa2!B1 hücresinde sayı yerine metin var (\"x\").")


def test_aralik_onculu_ilk_hatali_hucre():
    veri = {f"A{i}": float(i) for i in range(1, 1001)}
    veri["A700"] = "=1/0"
    veri["A900"] = "=1/0"
    veri["C1"] = "=TOPLA(A1:A1000)"
    k, _ = kur(veri)
    z = ac(k, "C1")
    assert adresler(z) == ["C1", "A700"] and z[-1].neden == "Bölen sıfır ya da boş."


def test_tembel_islev_secilen_dal():
    k, _ = kur({"A1": 1.0, "B1": "=EĞER(A1>0;1/0;2)"})
    assert yazi(k, "B1") == "#BÖL/0!: Bölen sıfır ya da boş."


def test_tembel_secilmeyen_daldaki_hata_suclanmaz():
    k, _ = kur({"A1": "x", "B1": 0.0, "C1": "=EĞER(B1=0;A1*2;1/0)"})
    assert yazi(k, "C1") == "#DEĞER!: A1 hücresinde sayı yerine metin var (\"x\")."


def test_tanimli_ad_icindeki_hata():
    from tabcel.model.ad import TanimliAd
    k, _ = kur({"A1": "abc"})
    s = k.sayfalar[0]
    k.ad_yaz(TanimliAd("Oran", f"=[{s.kimlik}]!$A$1*2"))
    s.ata(2, 1, Hucre(None, ceviri.girdiden("=Oran+1", k)))
    z = acikla(s, 2, 1)
    assert z is not None and "A1 hücresinde sayı yerine metin var" in z[-1].neden


# ---------------------------------------------------------------- işlev tablosu
def test_duseyara_bulamadi():
    k, _ = kur({"A1": "elma", "B1": 1.0, "D1": '=DÜŞEYARA("armut";A1:B1;2;YANLIŞ)'})
    assert yazi(k, "D1") == "#YOK: DÜŞEYARA aranan değeri (\"armut\") bulamadı."


def test_duseyara_tablodaki_ilgisiz_yok_suclanmaz():
    from tabcel.model import deger as D
    k, _ = kur({"A1": "elma", "B1": D.YOK, "D1": '=DÜŞEYARA("armut";A1:B1;2;YANLIŞ)'})
    assert yazi(k, "D1") == "#YOK: DÜŞEYARA aranan değeri (\"armut\") bulamadı."


def test_karekok_negatif():
    k, _ = kur({"A1": -4.0, "B1": "=KAREKÖK(A1)"})
    assert yazi(k, "B1") == "#SAYI!: KAREKÖK negatif sayı aldı (-4)."


def test_ortalama_bos_aralik():
    k, _ = kur({"B1": "=ORTALAMA(A1:A5)"})
    assert yazi(k, "B1") == "#BÖL/0!: ORTALAMA: ortalaması alınacak sayı yok."


def test_islev_metin_argumani():
    k, _ = kur({"A1": "abc", "B1": "=KAREKÖK(A1)"})
    assert yazi(k, "B1") == "#DEĞER!: KAREKÖK: A1 hücresinde sayı yerine metin var (\"abc\")."


def test_islev_genel_neden():
    k, _ = kur({"A1": "=TARİH(2026;1;1)*1E+300*1E+300"})
    assert yazi(k, "A1").startswith("#SAYI!: ")


# ---------------------------------------------------------------- sınırlar
def test_uzun_zincir_sinirli_ve_hizli():
    veri = {"A1": "x", "A2": "=A1*1"}
    for i in range(3, 3001):
        veri[f"A{i}"] = f"=A{i - 1}+1"
    k, _ = kur(veri)
    z = acikla(k.sayfalar[0], 3000, 1, sinir=5000)
    assert len(z) == 2999 and z[-1].satir == 2
    s = k.sayfalar[0]
    kisa = acikla(s, 3000, 1, sinir=10)
    assert len(kisa) == 11 and kisa[-1].neden.startswith("Zincir çok uzun")
    assert metin(kisa) == ("#DEĞER!: başka hücrelerden geliyor; zincir çok uzun (10 hücre izlendi, "
                           "son izlenen: A2990), kaynak bulunamadı.")


def test_degisken_islevde_cokmez():
    k, _ = kur({"A1": "=1/(S_SAYI_ÜRET()*0)"})
    z = ac(k, "A1")
    assert z is not None and z[-1].kod == "#DIV/0!"


def test_hesaplanmamis_hucrede_istisna_atmaz():
    from tabcel.formul.degerler import BEKLIYOR
    k, m = kur({"A1": "=1/0", "B1": "=C1*2+A1", "C1": "=1"})    # C1*2: C1'in değeri okunur
    m.kapat()                                                   # sonraki yazımlar yeniden hesaplanmasın
    s = k.sayfalar[0]
    s._sonuc[(1, 3)] = BEKLIYOR                                 # yarıda kalmış hesap işareti
    assert acikla(s, 1, 2) is None                              # tanı sessizce vazgeçer, istisna yok


def test_qt_ice_aktarmaz():
    import ast
    import pathlib
    kaynak = pathlib.Path(__file__).parent.parent / "tabcel" / "formul" / "hata_neden.py"
    agac = ast.parse(kaynak.read_text(encoding="utf-8"))
    modul = [n.module or "" for n in ast.walk(agac) if isinstance(n, ast.ImportFrom)]
    modul += [a.name for n in ast.walk(agac) if isinstance(n, ast.Import) for a in n.names]
    assert not any("PySide" in m or "Qt" in m for m in modul)
