"""Hücre stili: değişmez `Stil`, kısmi uygulama `StilYama`, kitap başına paylaşımlı `StilHavuzu`. Qt yok.

Tasarım: faz3_tasarim.md §1. Stil hücrenin girdisinden (`Hucre`) ayrı saklanır; hücre yalnız havuzdaki
stilin kimlik numarasını (int) taşır (0 = varsayılan). Aynı stil her zaman aynı kimliği alır
(*interning*), böylece 100.000 hücreye aynı yama uygulamak sözlük aramasıdır.
"""
import re
from dataclasses import dataclass, field, fields, replace
from typing import Any, Dict, List, Optional, Tuple

ALTI_CIZILI = ("yok", "tek", "cift")
YATAY = ("genel", "sol", "orta", "sag", "doldur", "iki_yana", "secim_ortasi")
DIKEY = ("ust", "orta", "alt")
CIZGILER = ("ince", "orta", "kalin", "kesikli", "noktali", "cift", "sac")
KENAR_YONLERI = ("ust", "alt", "sol", "sag")

_RENK = re.compile(r"^#[0-9a-fA-F]{6}$")
Cizgi = Tuple[str, str]          # (çizgi türü, "#RRGGBB")


def renk_normallestir(renk: Optional[str]) -> Optional[str]:
    if renk is None:
        return None
    if not isinstance(renk, str) or not _RENK.match(renk):
        raise ValueError(f"Renk '#RRGGBB' biçiminde olmalı: {renk!r}")
    return renk.upper()


def _cizgi_dogrula(c: Optional[Cizgi]) -> Optional[Cizgi]:
    if c is None:
        return None
    tur, renk = c
    if tur not in CIZGILER:
        raise ValueError(f"Bilinmeyen kenarlık çizgisi: {tur!r}")
    return (tur, renk_normallestir(renk) or "#000000")


@dataclass(frozen=True)
class Kenarlik:
    """Dört kenar; her biri `(çizgi, renk)` ya da None (kenarlık yok)."""
    ust: Optional[Cizgi] = None
    alt: Optional[Cizgi] = None
    sol: Optional[Cizgi] = None
    sag: Optional[Cizgi] = None

    def __post_init__(self):
        for y in KENAR_YONLERI:
            object.__setattr__(self, y, _cizgi_dogrula(getattr(self, y)))

    def bos_mu(self) -> bool:
        return not any(getattr(self, y) for y in KENAR_YONLERI)

    def degistir(self, **yonler) -> "Kenarlik":
        return replace(self, **yonler)


@dataclass(frozen=True)
class Stil:
    """Hücre biçimi. Her alanın varsayılanı Excel'inki (`Stil()` = "Normal")."""
    yazi_tipi: Optional[str] = None
    boyut: Optional[float] = None
    kalin: bool = False
    italik: bool = False
    ustu_cizili: bool = False
    alti_cizili: str = "yok"
    yazi_rengi: Optional[str] = None
    dolgu: Optional[str] = None
    kenar: Kenarlik = field(default_factory=Kenarlik)
    yatay: str = "genel"
    dikey: str = "alt"
    girinti: int = 0
    kaydir: bool = False
    sayi_bicimi: str = "General"          # KANONİK kod (İngilizce-ABD ayırıcılı)

    def __post_init__(self):
        if self.alti_cizili not in ALTI_CIZILI:
            raise ValueError(f"alti_cizili şunlardan biri olmalı: {ALTI_CIZILI}")
        if self.yatay not in YATAY:
            raise ValueError(f"yatay şunlardan biri olmalı: {YATAY}")
        if self.dikey not in DIKEY:
            raise ValueError(f"dikey şunlardan biri olmalı: {DIKEY}")
        if not (isinstance(self.girinti, int) and 0 <= self.girinti <= 15):
            raise ValueError("girinti 0–15 arasında tam sayı olmalı")
        if self.boyut is not None and not (isinstance(self.boyut, (int, float)) and 1 <= self.boyut <= 409):
            raise ValueError("yazı boyutu 1–409 punto olmalı")
        if not isinstance(self.sayi_bicimi, str) or not self.sayi_bicimi:
            raise ValueError("sayi_bicimi boş olamaz ('General' varsayılan)")
        object.__setattr__(self, "yazi_rengi", renk_normallestir(self.yazi_rengi))
        object.__setattr__(self, "dolgu", renk_normallestir(self.dolgu))
        if self.boyut is not None:
            object.__setattr__(self, "boyut", float(self.boyut))

    def degistir(self, **alan) -> "Stil":
        return replace(self, **alan)

    def varsayilan_mi(self) -> bool:
        return self == VARSAYILAN


VARSAYILAN = Stil()
_ALANLAR = {f.name for f in fields(Stil)}


class StilYama:
    """Kısmi stil: yalnız verilen alanlar uygulanır (`uygula(stil) -> Stil`). Hashlenebilir.

    `kenar` iki biçimde verilebilir: `Kenarlik` (hepsini değiştirir) ya da `{"ust": (çizgi, renk) | None,
    ...}` sözlüğü (yalnız adı geçen kenarlar; araç çubuğundaki "üst kenarlık" gibi).
    """
    __slots__ = ("_alanlar", "_anahtar")

    def __init__(self, **alan):
        bilinmeyen = set(alan) - _ALANLAR
        if bilinmeyen:
            raise ValueError(f"Bilinmeyen stil alanı: {sorted(bilinmeyen)}")
        kenar = alan.get("kenar")
        if isinstance(kenar, dict):
            kotu = set(kenar) - set(KENAR_YONLERI)
            if kotu:
                raise ValueError(f"Bilinmeyen kenar yönü: {sorted(kotu)}")
            alan["kenar"] = {y: _cizgi_dogrula(c) for y, c in kenar.items()}
        # geçerliliği bir Stil kurarak denetle (hatalı değer burada ValueError verir)
        Stil(**{k: v for k, v in alan.items() if k != "kenar"})
        self._alanlar = alan
        self._anahtar = tuple(sorted((k, self._hashable(v)) for k, v in alan.items()))

    @staticmethod
    def _hashable(v: Any):
        return tuple(sorted(v.items())) if isinstance(v, dict) else v

    def uygula(self, stil: Stil) -> Stil:
        alan = dict(self._alanlar)
        kenar = alan.get("kenar")
        if isinstance(kenar, dict):
            alan["kenar"] = stil.kenar.degistir(**kenar)
        return stil.degistir(**alan) if alan else stil

    def bos_mu(self) -> bool:
        return not self._alanlar

    def __eq__(self, diger):
        return isinstance(diger, StilYama) and self._anahtar == diger._anahtar

    def __hash__(self):
        return hash(self._anahtar)

    def __repr__(self):
        return f"StilYama({', '.join(f'{k}={v!r}' for k, v in self._alanlar.items())})"


class StilHavuzu:
    """Kitap başına stil havuzu: aynı `Stil` aynı kimliği alır; kimlik 0 = varsayılan stil.

    Havuz yalnız büyür (geri al eski kimlikleri kullanabilir); Faz 4 kaydederken yalnız kullanılanları
    yazar. `yama_uygula` önbelleklidir.
    """

    def __init__(self):
        self._stiller: List[Stil] = [VARSAYILAN]
        self._kimlikler: Dict[Stil, int] = {VARSAYILAN: 0}
        self._yama_onb: Dict[Tuple[int, StilYama], int] = {}

    def __len__(self) -> int:
        return len(self._stiller)

    def kimlik(self, stil: Stil) -> int:
        k = self._kimlikler.get(stil)
        if k is None:
            k = len(self._stiller)
            self._stiller.append(stil)
            self._kimlikler[stil] = k
        return k

    def stil(self, kimlik: int) -> Stil:
        return self._stiller[kimlik]

    def yama_uygula(self, kimlik: int, yama: StilYama) -> int:
        """`kimlik`teki stile yamayı uygulayıp yeni kimliği verir (önbellekli)."""
        anahtar = (kimlik, yama)
        k = self._yama_onb.get(anahtar)
        if k is None:
            k = self._yama_onb[anahtar] = self.kimlik(yama.uygula(self._stiller[kimlik]))
        return k

    def aktar(self, diger: "StilHavuzu", kimlik: int) -> int:
        """Başka havuzdaki bir kimliği bu havuza çevirir (sayfa başka kitaba bağlanırken)."""
        return self.kimlik(diger.stil(kimlik))
