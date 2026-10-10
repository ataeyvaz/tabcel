"""Grafik işlemleri (Faz 6 / 6f; `faz6_tasarim.md` §6): seçimden grafik kurma, Satır/Sütun Değiştir, renk
şemaları, Excel yazımlı aralık başvurusu çözme. Qt yok.

Hepsi `Grafik` nesnesi üretir; sayfaya yazma (`NesneEkle`/`NesneDegis`) arayüz tarafında yapılır.
"""
from dataclasses import replace
from typing import List, Optional, Tuple

from .adres import AdresHatasi, Aralik, aralik_coz
from .grafik import Grafik, Referans, Seri
from .grafik_cizim import palet_rengi, ton
from .grafik_verisi import seriler_tahmin

# galeri düzeni: (tur, alt_tur) -> menü metni (Ekle sekmesi ve "Grafik Türünü Değiştir")
GALERI = {
    "sutun": (("kumelenmis", "Kümelenmiş Sütun"), ("yigili", "Yığılmış Sütun"), ("yuzde_yigili", "%100 Yığılmış Sütun")),
    "cubuk": (("kumelenmis", "Kümelenmiş Çubuk"), ("yigili", "Yığılmış Çubuk"), ("yuzde_yigili", "%100 Yığılmış Çubuk")),
    "cizgi": (("kumelenmis", "Çizgi"), ("yigili", "Yığılmış Çizgi")),
    "pasta": (("kumelenmis", "Pasta"),),
    "halka": (("kumelenmis", "Halka"),),
    "alan": (("kumelenmis", "Alan"), ("yigili", "Yığılmış Alan")),
    "dagilim": (("kumelenmis", "Dağılım (XY)"),),
}
TUR_ADLARI = {"sutun": "Sütun", "cubuk": "Çubuk", "cizgi": "Çizgi", "pasta": "Pasta", "halka": "Halka",
              "alan": "Alan", "dagilim": "Dağılım"}
TEK_SERILI = ("pasta", "halka")

# renk şemaları: ad -> temel renk (None = Office paleti); tonlar koyudan açığa dağılır
RENK_SEMALARI = {"Office": None, "Mavi Tonları": "#4472C4", "Yeşil Tonları": "#70AD47",
                 "Turuncu Tonları": "#ED7D31", "Gri Tonları": "#7F7F7F"}


def alt_tur_gecerli(tur: str, alt_tur: str) -> str:
    """Türe uymayan alt tür kümelenmişe iner (ör. pasta + yığılmış)."""
    return alt_tur if any(a == alt_tur for a, _ in GALERI[tur]) else "kumelenmis"


def grafik_kur(sayfa, aralik: Aralik, tur: str, alt_tur: str = "kumelenmis",
               satirda_seri: Optional[bool] = None) -> Grafik:
    """Seçili aralıktan grafik (konum sonra atanır). Sayısal veri yoksa `ValueError` (`seriler_tahmin`)."""
    seriler, _ = seriler_tahmin(sayfa, aralik, tur, satirda_seri)
    return Grafik(tur=tur, alt_tur=alt_tur_gecerli(tur, alt_tur), seriler=tuple(seriler))


def tur_degistir(grafik: Grafik, tur: str, alt_tur: str = "kumelenmis") -> Grafik:
    """Türü değiştirir; pasta/halkaya geçerken yalnız ilk seri kalır (Excel gibi). Eksen sınırları sıfırlanmaz."""
    seriler = grafik.seriler[:1] if tur in TEK_SERILI else grafik.seriler
    return grafik.degistir(tur=tur, alt_tur=alt_tur_gecerli(tur, alt_tur), seriler=seriler)


# ------------------------------------------------------------------ satır / sütun değiştir
def _ters(a: Aralik) -> Aralik:
    return Aralik(a.ilk_sutun, a.ilk_satir, a.son_sutun, a.son_satir)


def _ters_ref(r: Optional[Referans]) -> Optional[Referans]:
    return None if r is None else Referans(r.sayfa_kimlik, _ters(r.aralik))


def _sutunlar_seri_mi(g: Grafik) -> bool:
    """Her serinin değeri tek sütunluk dikey aralık mı (birden çok satır ya da tek hücre)?"""
    return all(s.deger is not None and s.deger.aralik.ilk_sutun == s.deger.aralik.son_sutun for s in g.seriler)


def _sutundan_satira(g: Grafik) -> Grafik:
    """Seriler sütunlardayken (her seri dikey bir aralık) satırlara çevirir. Başlık hücreleri (`ad_ref`) yeni
    kategoriler, kategori sütunu yeni seri adları olur."""
    ilk = g.seriler[0].deger
    sayfa, r1, r2 = ilk.sayfa_kimlik, ilk.aralik.ilk_satir, ilk.aralik.son_satir
    sutlar = []
    for s in g.seriler:
        d = s.deger
        if d.sayfa_kimlik != sayfa or d.aralik.ilk_satir != r1 or d.aralik.son_satir != r2:
            raise ValueError("Seriler aynı satırları kapsamıyor")
        sutlar.append(d.aralik.ilk_sutun)
    c1, c2 = min(sutlar), max(sutlar)
    if sorted(sutlar) != list(range(c1, c2 + 1)):
        raise ValueError("Seri sütunları bitişik değil")
    kat = g.seriler[0].kategori
    kat_ok = (kat is not None and kat.sayfa_kimlik == sayfa and kat.aralik.ilk_sutun == kat.aralik.son_sutun
              and kat.aralik.son_satir - kat.aralik.ilk_satir == r2 - r1)
    # yeni kategoriler = eski seri adları (başlık hücreleri tek satırda bitişikse)
    yeni_kat = None
    refs = [s.ad_ref for s in g.seriler]
    if all(r is not None and r.sayfa_kimlik == sayfa for r in refs):
        satirlar = {r.aralik.ilk_satir for r in refs}
        sut = [r.aralik.ilk_sutun for r in refs]
        if len(satirlar) == 1 and sorted(sut) == list(range(c1, c2 + 1)) and sut == sorted(sut):
            h = satirlar.pop()
            yeni_kat = Referans(sayfa, Aralik(h, c1, h, c2))
    yeniler: List[Seri] = []
    for i in range(r2 - r1 + 1):
        r = r1 + i
        ad_ref = Referans(sayfa, Aralik(kat.aralik.ilk_satir + i, kat.aralik.ilk_sutun,
                                        kat.aralik.ilk_satir + i, kat.aralik.ilk_sutun)) if kat_ok else None
        yeniler.append(Seri(ad_ref=ad_ref,
                            deger=Referans(sayfa, Aralik(r, c1, r, c2)), kategori=yeni_kat))
    return replace(g, seriler=tuple(yeniler))


def satir_sutun_degistir(grafik: Grafik) -> Grafik:
    """Excel'in "Satır/Sütun Değiştir"i: seriler sütunlardaysa satırlara, satırlardaysa sütunlara döner. Veri
    bloğu tek dikdörtgen değilse (bitişik olmayan seriler, başka sayfalar) `ValueError`. Renkler sıfırlanır.
    Pasta/halka tek seri olduğundan değiştirilemez (`ValueError`)."""
    if not grafik.seriler:
        raise ValueError("Grafikte seri yok")
    if grafik.tur in TEK_SERILI:
        raise ValueError("Pasta ve halka grafiklerinde satır/sütun değiştirilemez")
    if any(s.deger is None for s in grafik.seriler):
        raise ValueError("Değeri olmayan seri var")
    if _sutunlar_seri_mi(grafik):
        yeni = _sutundan_satira(grafik)
    else:
        ters = replace(grafik, seriler=tuple(replace(s, ad_ref=_ters_ref(s.ad_ref), deger=_ters_ref(s.deger),
                                                      kategori=_ters_ref(s.kategori)) for s in grafik.seriler))
        if not _sutunlar_seri_mi(ters):
            raise ValueError("Seriler tek sütun ya da tek satır değil")
        t = _sutundan_satira(ters)
        yeni = replace(t, seriler=tuple(replace(s, ad_ref=_ters_ref(s.ad_ref), deger=_ters_ref(s.deger),
                                                 kategori=_ters_ref(s.kategori)) for s in t.seriler))
    if grafik.tur in TEK_SERILI:
        yeni = replace(yeni, seriler=yeni.seriler[:1])
    return yeni


# ------------------------------------------------------------------ renkler
def renk_sema_renkleri(ad: str, n: int) -> List[Optional[str]]:
    """`n` seri için şema renkleri; Office → None (palet sırası). Tek renkli şemalar koyudan açığa."""
    if ad not in RENK_SEMALARI:
        raise ValueError(f"bilinmeyen renk şeması: {ad}")
    temel = RENK_SEMALARI[ad]
    if temel is None:
        return [None] * n
    if n <= 1:
        return [temel]
    return [ton(temel, -0.45 + 0.9 * i / (n - 1)) for i in range(n)]


def renk_sema_uygula(grafik: Grafik, ad: str) -> Grafik:
    renkler = renk_sema_renkleri(ad, len(grafik.seriler))
    return replace(grafik, seriler=tuple(replace(s, renk=r) for s, r in zip(grafik.seriler, renkler)))


def seri_rengi(grafik: Grafik, i: int) -> str:
    """Serinin görünen rengi (açık renk yoksa palet sırası)."""
    return grafik.seriler[i].renk or palet_rengi(i)


# ------------------------------------------------------------------ aralık başvurusu (Excel yazımı)
def referans_coz(kitap, metin: str, varsayilan_sayfa) -> Optional[Referans]:
    """`Sayfa1!$B$2:$B$5`, `'Sayfa 1'!B2:B5` ya da sayfasız `B2:B5` (varsayılan sayfa). Boş metin → None.
    Geçersiz adres/sayfa → `ValueError` (iletisi kullanıcıya gösterilir)."""
    m = metin.strip()
    if m.startswith("="):
        m = m[1:].strip()
    if not m:
        return None
    sayfa = varsayilan_sayfa
    if "!" in m:
        ad, _, m = m.rpartition("!")
        ad = ad.strip()
        if len(ad) >= 2 and ad[0] == ad[-1] == "'":
            ad = ad[1:-1].replace("''", "'")
        if ad.startswith("[") and "]" in ad:
            ad = ad.split("]", 1)[1]
        from .harmanla import tr_kucuk
        bulunan = next((s for s in kitap.sayfalar if tr_kucuk(s.ad) == tr_kucuk(ad)), None)
        if bulunan is None:
            raise ValueError(f"'{ad}' adlı sayfa yok")
        sayfa = bulunan
    try:
        aralik = aralik_coz(m.replace("$", ""))
    except AdresHatasi:
        raise ValueError(f"Geçersiz aralık: {metin.strip()}") from None
    return Referans(sayfa.kimlik, aralik)


def referans_yaz(kitap, ref: Optional[Referans]) -> str:
    """`Referans` → pencerede gösterilen Excel yazımı (`Sayfa1!$B$2:$B$5`); silinmiş sayfa → boş."""
    from .grafik import referans_metni
    if ref is None:
        return ""
    s = kitap.sayfa_kimlikle(ref.sayfa_kimlik)
    return referans_metni(ref, s.ad) if s is not None else ""
