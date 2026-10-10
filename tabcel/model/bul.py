"""Bul / Değiştir (faz5_tasarim.md §2.1). Qt yok; metin üreticisi ve çözücü dışarıdan verilir.

- `eslesmeler`: etkin hücreden SONRAKİ hücreden başlayıp satır (ya da sütun) sırasıyla sarar.
- `degistirme_plani` / `degistir_komutu`: yalnız "formül" metninde; "Tümünü Değiştir" tek geri al adımı.
"""
import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple

from .adres import Aralik, aralik_icinde
from .gosterim import goster
from .harmanla import tr_kucuk
from .sayfa import Hucre, Sayfa
from .stil import StilYama

Eslesme = Tuple[Sayfa, int, int]


@dataclass(frozen=True)
class BulSecenek:
    metin: str
    buyuk_kucuk: bool = False
    tam_hucre: bool = False
    bakilan: str = "formul"            # "formul" | "deger" | "not"
    kapsam: str = "sayfa"              # "sayfa" | "kitap"
    yon: str = "satir"                 # "satir" | "sutun"


def _desen(metin: str, tam: bool, buyuk_kucuk: bool):
    """Joker (`*` `?`, `~` kaçış) destekli düzenli ifade. `formul/fonksiyonlar/ortak._joker_regex`
    ile aynı kurallar (testle eşitlenir); alt dize aramasında `*` en kısa eşleşmeyi alır."""
    d = metin if buyuk_kucuk else tr_kucuk(metin)
    cikti, i = [], 0
    while i < len(d):
        c = d[i]
        if c == "~" and i + 1 < len(d) and d[i + 1] in "*?~":
            cikti.append(re.escape(d[i + 1]))
            i += 2
            continue
        cikti.append((".*" if tam else ".*?") if c == "*" else "." if c == "?" else re.escape(c))
        i += 1
    govde = "".join(cikti)
    return re.compile(f"^{govde}$" if tam else govde, re.S)


def joker_alt_dize(desen: str, tam: bool = False, buyuk_kucuk: bool = False) -> Callable[[str], bool]:
    """`desen` metinde (alt dize ya da `tam` ise tüm metin) geçiyor mu; Türkçe büyük/küçük harf
    duyarsız (`buyuk_kucuk=True` ise duyarlı)."""
    rx = _desen(desen, tam, buyuk_kucuk)
    if buyuk_kucuk:
        return lambda s: rx.search(s) is not None
    return lambda s: rx.search(tr_kucuk(s)) is not None


def gorunen_metin(sayfa: Sayfa, satir: int, sutun: int) -> Optional[str]:
    """Hücrenin ekranda görünen metni (sayı biçimi uygulanmış, `####` değil tam metin); boşsa None."""
    from .sayi_bicimi import BicimHatasi, bicimle
    v = sayfa.deger(satir, sutun)
    if v is None:
        return None
    kod = sayfa.stil(satir, sutun).sayi_bicimi
    if kod and kod != "General":
        try:
            return bicimle(v, kod).metin
        except (BicimHatasi, ArithmeticError, OverflowError, ValueError):
            pass
    return goster(v)


def not_metni(sayfa: Sayfa, satir: int, sutun: int) -> Optional[str]:
    n = sayfa.notlar.get((satir, sutun))
    if n is None:
        return None
    return n if isinstance(n, str) else getattr(n, "metin", str(n))


def _adaylar(sayfa: Sayfa, secenek: BulSecenek, secim) -> List[Tuple[int, int]]:
    if secenek.bakilan == "not":
        anahtarlar = list(sayfa.notlar)
    else:
        anahtarlar = [(r, c) for r, c, _ in sayfa.dolu_hucreler(sirali=False)]
    if secim:
        anahtarlar = [k for k in anahtarlar if any(aralik_icinde(a, k[0], k[1]) for a in secim)]
    if sayfa.birlesimler:      # birleşimin kapsanan (sol üst dışındaki) hücreleri atlanır
        anahtarlar = [k for k in anahtarlar
                      if (b := sayfa.birlesim(*k)) is None or (b.ilk_satir, b.ilk_sutun) == k]
    sutun_once = secenek.yon == "sutun"
    return sorted(anahtarlar, key=(lambda k: (k[1], k[0])) if sutun_once else None)


def eslesmeler(kitap, sayfa: Sayfa, secim: Optional[Sequence[Aralik]], secenek: BulSecenek,
               metin_al: Callable[[Sayfa, int, int, str], Optional[str]],
               baslangic: Optional[Tuple[int, int]] = None) -> Iterator[Eslesme]:
    """Eşleşen hücreler, `baslangic` hücresinden SONRAKİ hücreden başlayarak (satır ya da sütun
    sırasıyla) sarılarak; sıra en sonda `baslangic` hücresine dönerek biter. `secim`: yalnız bu
    aralıklarda ara (None ya da tek hücre = tüm sayfa; yalnız `kapsam="sayfa"`). `kapsam="kitap"`:
    önce bu sayfanın kalanı, sonra diğer sayfalar (sekme sırasıyla), en sonda bu sayfanın başı.
    `metin_al(sayfa, satır, sütun, bakılan) -> str | None` aranacak metni verir."""
    if not secenek.metin:
        return
    eslestir = joker_alt_dize(secenek.metin, secenek.tam_hucre, secenek.buyuk_kucuk)
    if secim is not None:
        secim = list(secim)
        if len(secim) == 1 and secim[0].ilk_satir == secim[0].son_satir \
                and secim[0].ilk_sutun == secim[0].son_sutun:
            secim = None
    sutun_once = secenek.yon == "sutun"

    def sira(k):
        return (k[1], k[0]) if sutun_once else k

    parcalar: List[Tuple[Sayfa, List[Tuple[int, int]]]] = []
    ilk_ara = secim if secenek.kapsam == "sayfa" else None
    kendi = _adaylar(sayfa, secenek, ilk_ara)
    esik = sira(baslangic) if baslangic is not None else (0, 0)
    sonra = [k for k in kendi if sira(k) > esik]
    once = [k for k in kendi if sira(k) <= esik]
    parcalar.append((sayfa, sonra))
    if secenek.kapsam == "kitap" and kitap is not None:
        digerleri = [s for s in kitap.sayfalar if s is not sayfa]
        # Excel: bu sayfadan sonraki sayfalar sekme sırasıyla, baştakiler sona
        i = kitap.sayfalar.index(sayfa) if sayfa in kitap.sayfalar else -1
        sirali = [s for s in kitap.sayfalar[i + 1:]] + [s for s in kitap.sayfalar[:max(i, 0)]]
        digerleri = sirali if i >= 0 else digerleri
        for s in digerleri:
            parcalar.append((s, _adaylar(s, secenek, None)))
    parcalar.append((sayfa, once))
    for s, anahtarlar in parcalar:
        for r, c in anahtarlar:
            m = metin_al(s, r, c, secenek.bakilan)
            if m is not None and eslestir(m):
                yield s, r, c


# ------------------------------------------------------------------ değiştir
def yeni_metin(metin: str, secenek: BulSecenek, yeni: str) -> Optional[str]:
    """Düzenleme metninde aranan metni `yeni` ile değiştirir; eşleşme yoksa None.
    `tam_hucre`: metnin tamamı eşleşirse yeni metnin kendisi olur. Yoksa her eşleşme değişir
    (büyük/küçük harf duyarsız eşleşme Türkçe küçük harfle; yerine konan metin olduğu gibi)."""
    rx = _desen(secenek.metin, secenek.tam_hucre, secenek.buyuk_kucuk)
    aranan = metin if secenek.buyuk_kucuk else tr_kucuk(metin)
    if secenek.tam_hucre:
        return yeni if rx.search(aranan) else None
    parcalar, son, bulundu = [], 0, False
    for m in rx.finditer(aranan):
        if m.end() == m.start():
            continue
        parcalar.append(metin[son:m.start()])
        parcalar.append(yeni)
        son = m.end()
        bulundu = True
    if not bulundu:
        return None
    parcalar.append(metin[son:])
    return "".join(parcalar)


Cozucu = Callable[[Sayfa, int, int, str], Tuple[Optional[Hucre], Optional[str]]]


def degistirme_plani(bulunanlar: Sequence[Eslesme], secenek: BulSecenek, yeni: str,
                     metin_al: Callable[[Sayfa, int, int, str], Optional[str]],
                     coz: Cozucu):
    """Eşleşen hücrelerin yeni girdileri: `({Sayfa: {(r, c): (Hucre | None, sayı_biçimi_kodu | None)}},
    atlanan)`. `coz(sayfa, r, c, metin)` metni elle yazılmış gibi çözer (formül Türkçe → saklanan;
    akıllı giriş) ve geçersizse `ValueError` (örn. FormulHatasi) fırlatır → hücre atlanır. Sayı
    biçimi kodu yalnız hücre Genel iken önerilir (3g kuralı; `coz` bunu zaten denetleyip verir).
    Notlarda değiştirme yapılmaz (Excel: yalnız Formüller)."""
    plan: Dict[Sayfa, Dict[Tuple[int, int], Tuple[Optional[Hucre], Optional[str]]]] = {}
    atlanan = 0
    if secenek.bakilan != "formul":
        return plan, 0
    for s, r, c in bulunanlar:
        eski = metin_al(s, r, c, "formul")
        if eski is None:
            continue
        yt = yeni_metin(eski, secenek, yeni)
        if yt is None or yt == eski:
            continue
        try:
            plan.setdefault(s, {})[(r, c)] = coz(s, r, c, yt)
        except ValueError:
            atlanan += 1
    return plan, atlanan


def degistir_komutu(plan):
    """`degistirme_plani` çıktısından tek geri al adımlık komut (boş plan → None)."""
    from .komutlar import Grup, HucrelerDegis, bicim_komutu
    komutlar = []
    for s, hucreler in plan.items():
        if not hucreler:
            continue
        komutlar.append(HucrelerDegis(s, {k: h for k, (h, _) in hucreler.items()}))
        kodlar: Dict[str, List[Aralik]] = {}
        for (r, c), (_, kod) in hucreler.items():
            if kod is not None:
                kodlar.setdefault(kod, []).append(Aralik(r, c, r, c))
        for kod, araliklar in kodlar.items():
            komutlar.append(bicim_komutu(s, araliklar, StilYama(sayi_bicimi=kod)))
    return Grup(komutlar) if komutlar else None
