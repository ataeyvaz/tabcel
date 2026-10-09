"""Hesaplama motoru: bağımlılık, kirli işaretleme, döngü, değişken fonksiyon, olaylar (Qt yok)."""
import itertools

import pytest

from tabcel.formul import fonksiyonlar
from tabcel.formul.motor import Hesaplayici
from tabcel.model import deger as D
from tabcel.model.komutlar import GeriAlYigini, HucrelerDegis, SayfaSil
from tabcel.model.sayfa import CalismaKitabi, Hucre


def F(metin):
    return Hucre(None, metin)


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def s(kitap):
    return kitap.sayfalar[0]


def test_ilk_kurulumda_hesaplar(kitap, s):
    s.ata(1, 1, Hucre(2.0))
    s.ata(1, 2, F("=A1*10"))
    Hesaplayici(kitap)
    assert s.deger(1, 2) == 20.0


def test_degisiklik_bagimlilara_yayilir(kitap, s):
    m = Hesaplayici(kitap)
    s.ata(1, 1, Hucre(1.0))
    s.ata(2, 1, F("=A1+1"))
    s.ata(3, 1, F("=A2*2"))
    s.ata(4, 1, F("=SUM(A1:A3)"))
    assert [s.deger(r, 1) for r in (2, 3, 4)] == [2.0, 4.0, 7.0]
    s.ata(1, 1, Hucre(10.0))
    assert [s.deger(r, 1) for r in (2, 3, 4)] == [11.0, 22.0, 43.0]
    assert not m.donguler


def test_yalniz_etkilenenler_hesaplanir(kitap, s, monkeypatch):
    m = Hesaplayici(kitap)
    s.ata(1, 1, Hucre(1.0))
    s.ata(1, 2, F("=A1+1"))
    s.ata(5, 5, F("=1+1"))
    sayac = []
    eski = m._degerle
    monkeypatch.setattr(m, "_degerle", lambda a: (sayac.append(a), eski(a))[1])
    s.ata(1, 1, Hucre(5.0))
    assert sayac == [(s.kimlik, 1, 2)]


def test_sira_bagimsiz_yazim(kitap, s):
    """Formül, öncülünden ÖNCE yazılsa da doğru sonuç (topolojik sıra)."""
    Hesaplayici(kitap)
    s.toplu_yaz({(1, 1): F("=B1+C1"), (1, 2): F("=C1*2"), (1, 3): Hucre(3.0)})
    assert s.deger(1, 1) == 9.0


def test_aralik_bagimliligi_ve_tam_sutun(kitap, s):
    Hesaplayici(kitap)
    s.ata(1, 3, F("=SUM(A:A)"))
    s.ata(1, 4, F("=SUM(A2:B5)"))
    s.ata(3, 1, Hucre(4.0))
    assert s.deger(1, 3) == 4.0 and s.deger(1, 4) == 4.0
    s.ata(100, 1, Hucre(1.0))                      # A100: A2:B5 dışında
    assert s.deger(1, 3) == 5.0 and s.deger(1, 4) == 4.0


def test_formul_silinince_bagimlilar_guncellenir(kitap, s):
    m = Hesaplayici(kitap)
    s.ata(1, 1, F("=2*3"))
    s.ata(1, 2, F("=A1+1"))
    assert s.deger(1, 2) == 7.0
    s.ata(1, 1, None)
    assert s.deger(1, 2) == 1.0
    s.ata(1, 1, Hucre("x"))
    assert s.deger(1, 2) == D.DEGER_HATASI
    assert (s.kimlik, 1, 1) not in m._kayit


def test_dongu(kitap, s):
    m = Hesaplayici(kitap)
    s.ata(1, 1, F("=B1+1"))
    s.ata(1, 2, F("=A1+1"))
    s.ata(1, 3, F("=A1*10"))                     # döngüye bağlı ama döngüde değil
    assert m.donguler == {(s.kimlik, 1, 1), (s.kimlik, 1, 2)}
    assert s.deger(1, 1) == 0.0 and s.deger(1, 2) == 0.0
    assert (s.kimlik, 1, 3) not in m.donguler
    s.ata(1, 2, Hucre(5.0))                       # döngü kırıldı
    assert not m.donguler
    assert s.deger(1, 1) == 6.0 and s.deger(1, 3) == 60.0


def test_kendine_basvuru(kitap, s):
    m = Hesaplayici(kitap)
    s.ata(2, 2, F("=B2+1"))
    assert m.donguler == {(s.kimlik, 2, 2)}
    s.ata(3, 3, F("=SUM(C1:C5)"))                 # aralık içinden kendine
    assert (s.kimlik, 3, 3) in m.donguler


def test_baska_sayfa_ve_sayfa_silme(kitap, s):
    m = Hesaplayici(kitap)
    s2 = kitap.sayfa_ekle("Veri")
    s2.ata(1, 1, Hucre(4.0))
    s.ata(1, 1, F(f"=[{s2.kimlik}]!A1*2"))
    assert s.deger(1, 1) == 8.0
    s2.ata(1, 1, Hucre(5.0))
    assert s.deger(1, 1) == 10.0
    yigin = GeriAlYigini()
    yigin.calistir(SayfaSil(kitap, s2))
    assert s.deger(1, 1) == D.BASV
    yigin.geri_al()
    assert s.deger(1, 1) == 10.0
    assert m.donguler == set()


def test_geri_al_yeniden_hesaplar(kitap, s):
    Hesaplayici(kitap)
    yigin = GeriAlYigini()
    s.ata(1, 2, F("=A1*2"))
    yigin.calistir(HucrelerDegis(s, {(1, 1): Hucre(3.0)}))
    assert s.deger(1, 2) == 6.0
    yigin.geri_al()
    assert s.deger(1, 2) == 0.0
    yigin.yinele()
    assert s.deger(1, 2) == 6.0


def test_satir_ekleyince_tumu_yeniden(kitap, s):
    Hesaplayici(kitap)
    s.ata(1, 1, Hucre(1.0))
    s.ata(2, 1, F("=A1+1"))
    s.satir_ekle(1)                     # başvuru düzeltme kaydir.py ile; burada yalnız tutarlılık
    assert s.deger(3, 1) == 1.0         # =A1 artık boş A1'e bakıyor (formül metni düzeltilmedi)


def test_degisken_fonksiyon_her_seferinde(kitap, s):
    sayac = itertools.count(1)
    fonksiyonlar.fonksiyon("TEST_SAYAC", degisken=True)(lambda b: float(next(sayac)))
    try:
        Hesaplayici(kitap)
        s.ata(1, 1, F("=TEST_SAYAC()"))
        ilk = s.deger(1, 1)
        s.ata(5, 5, Hucre(1.0))          # ilgisiz değişiklik de değişkenleri yeniler
        assert s.deger(1, 1) == ilk + 1
    finally:
        del fonksiyonlar.KAYIT["TEST_SAYAC"]


def test_toplu_yazim_tek_sonuc_olayi(kitap, s):
    Hesaplayici(kitap)
    olaylar = []
    kitap.dinle(lambda o: olaylar.append(o.tur))
    s.toplu_yaz({(r, 1): F(f"={r}*2") for r in range(1, 101)})
    assert olaylar.count("sonuc") == 1
    assert s.deger(100, 1) == 200.0


def test_bozuk_formul_ad_hatasi(kitap, s):
    Hesaplayici(kitap)
    s.ata(1, 1, F("=1+"))                  # kayıtlı ama ayrıştırılamayan (bozuk dosya vb.)
    assert s.deger(1, 1) == D.AD


def test_uzun_zincir(kitap, s):
    """Özyineleme sınırına takılmadan uzun zincir (topolojik sıra)."""
    Hesaplayici(kitap)
    n = 5000
    yeni = {(1, 1): Hucre(1.0)}
    yeni.update({(r, 1): F(f"=A{r - 1}+1") for r in range(2, n + 1)})
    s.toplu_yaz(yeni)
    assert s.deger(n, 1) == float(n)
    s.ata(1, 1, Hucre(10.0))
    assert s.deger(n, 1) == float(n + 9)


def test_kapat_dinlemeyi_birakir(kitap, s):
    m = Hesaplayici(kitap)
    m.kapat()
    s.ata(1, 1, F("=1+1"))
    assert s.deger(1, 1) is None


# ---------------------------------------------------------------- Opus gözden geçirmesi: performans (bulgu 1, 2)
def test_bakiye_zinciri_dogrusal_surede_yeniden_hesaplanir(kitap, s):
    """Satır TOPLA + yürüyen bakiye: A1 değişince 4000 satır (eskiden ~20 sn, karesel). Sınır geniş
    tutuldu (yavaş makine); asıl doğrulama sonucun doğruluğu."""
    import time
    Hesaplayici(kitap)
    n = 4000
    veri = {}
    for r in range(1, n + 1):
        for c in range(1, 4):
            veri[(r, c)] = Hucre(float(r + c))
        veri[(r, 4)] = F(f"=SUM(A{r}:C{r})")
        veri[(r, 5)] = F(f"=E{r - 1}+D{r}" if r > 1 else "=D1")
    s.toplu_yaz(veri)
    beklenen = sum((r + 1) + (r + 2) + (r + 3) for r in range(1, n + 1))
    assert s.deger(n, 5) == pytest.approx(beklenen)
    t0 = time.perf_counter()
    s.ata(1, 1, Hucre(100.0))
    gecen = time.perf_counter() - t0
    assert s.deger(n, 5) == pytest.approx(beklenen - 2 + 100)       # A1: 2 → 100
    assert gecen < 3.0


def test_hareketli_ortalama_zinciri(kitap, s):
    Hesaplayici(kitap)
    n = 2000
    s.toplu_yaz({(r, 1): Hucre(float(r)) for r in range(1, n + 1)})
    s.toplu_yaz({(r, 2): F(f"=AVERAGE(A{r - 2}:A{r})") for r in range(3, n + 1)})
    assert s.deger(10, 2) == 9.0
    s.ata(5, 1, Hucre(50.0))
    assert [s.deger(r, 2) for r in (5, 6, 7, 8)] == [pytest.approx((3 + 4 + 50) / 3),
                                                     pytest.approx((4 + 50 + 6) / 3),
                                                     pytest.approx((50 + 6 + 7) / 3), 7.0]


def test_tam_sutun_toplami_kullanilan_alanla_sinirli(kitap, s):
    """=TOPLA(A:A) 1.048.576 satırı gezmez (eskiden her turda ~0,4 sn); sonuç doğru kalır."""
    import time
    Hesaplayici(kitap)
    for r in range(1, 11):
        s.ata(r, 1, Hucre(float(r)))
    t0 = time.perf_counter()
    s.ata(1, 2, F("=SUM(A:A)"))
    s.ata(3, 1, Hucre(30.0))
    assert time.perf_counter() - t0 < 0.15
    assert s.deger(1, 2) == 55.0 - 3 + 30
    s.ata(20, 1, Hucre(1000.0))                                      # kullanılan alan büyüdü
    assert s.deger(1, 2) == 55.0 - 3 + 30 + 1000
    s.ata(30, 3, Hucre(5.0))
    s.ata(2, 4, F("=SUM(C:C)"))
    assert s.deger(2, 4) == 5.0


def test_bos_sayfada_tam_sutun_toplami_sifir(kitap, s):
    Hesaplayici(kitap)
    s.ata(1, 2, F("=SUM(A:A)"))
    assert s.deger(1, 2) == 0.0
