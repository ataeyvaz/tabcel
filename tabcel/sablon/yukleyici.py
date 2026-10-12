"""Şablon tanımı yükleme: dosya → doğrulama → sürüm göçü → yerleşik + kullanıcı deposu. Qt yok.

Hatalı dosya uygulamayı çökertmez: atlanır, nedeni `YuklemeRaporu`na Türkçe satırlarla yazılır (hangi dosya, hangi alan).
Aynı kimlik hem yerleşikte hem kullanıcı klasöründe varsa ikisi de listelenir (yerleşik sessizce değişmez).
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .. import resource_dir, veri_klasoru
from . import sema
from .sema import Akis, Hata, Modul

# Sürüm göçü: GOCLER[tur][eski_surum] = f(sözlük) → bir üst sürümün sözlüğü. Şema yükseldikçe buraya eklenir.
GOCLER: Dict[str, Dict[int, Callable[[dict], dict]]] = {"modul": {}, "akis": {}}

YERLESIK = "yerlesik"
KULLANICI = "kullanici"


@dataclass
class RaporSatiri:
    dosya: str
    hata: Hata

    def __str__(self):
        return f"{self.dosya} — {self.hata}" + (" (uyarı)" if self.hata.uyari else "")


@dataclass
class YuklemeRaporu:
    satirlar: List[RaporSatiri] = field(default_factory=list)
    yuklenen: int = 0

    def ekle(self, dosya: str, hatalar):
        for h in hatalar:
            self.satirlar.append(RaporSatiri(dosya, h))

    @property
    def hatalar(self) -> List[RaporSatiri]:
        return [s for s in self.satirlar if not s.hata.uyari]

    @property
    def temiz(self) -> bool:
        return not self.hatalar

    def metin(self) -> str:
        return "\n".join(str(s) for s in self.satirlar)


@dataclass
class Sablon:
    ic_kimlik: str                      # "yerlesik:stok_takibi" / "kullanici:stok_takibi"
    kaynak: str
    etiket: str
    akis: Akis
    moduller: Dict[str, Modul]          # yalnız bu akışın kullandığı modüller
    dosya: str = ""


@dataclass
class Depo:
    sablonlar: List[Sablon] = field(default_factory=list)
    rapor: YuklemeRaporu = field(default_factory=YuklemeRaporu)

    def bul(self, ic_kimlik: str) -> Optional[Sablon]:
        return next((s for s in self.sablonlar if s.ic_kimlik == ic_kimlik), None)

    def akislar(self) -> List[Akis]:
        return [s.akis for s in self.sablonlar]


def yerlesik_klasor() -> Path:
    return resource_dir() / "tabcel" / "sablonlar"


def kullanici_klasoru() -> Path:
    return veri_klasoru() / "sablonlar"


# ---------------------------------------------------------------- tek dosya
def json_oku(yol: Path) -> Tuple[Optional[Any], List[Hata]]:
    try:
        ham = Path(yol).read_bytes()
    except OSError as e:
        return None, [Hata("", f"dosya okunamadı ({e.strerror or e})")]
    try:
        metin = ham.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, [Hata("", "dosya UTF-8 kodlamasında değil")]
    try:
        return json.loads(metin), []
    except json.JSONDecodeError as e:
        return None, [Hata("", f"JSON bozuk: satır {e.lineno}, sütun {e.colno} — {e.msg}")]


def goc_et(d: dict, tur: str) -> Tuple[Optional[dict], List[Hata]]:
    """Sürümü uygulamanın sürümüne yükseltir. Daha yeni sürüm ya da eksik göç → hata."""
    s = d.get("surum")
    if isinstance(s, bool) or not isinstance(s, int) or s < 1:
        return d, []                                     # asıl hata doğrulayıcıdan gelir
    if s > sema.SURUM:
        return None, [Hata("surum", f"dosya sürümü {s}, bu uygulama en çok {sema.SURUM} sürümünü anlıyor "
                                    f"(uygulamayı güncelleyin)")]
    while s < sema.SURUM:
        f = GOCLER.get(tur, {}).get(s)
        if f is None:
            return None, [Hata("surum", f"{s}. sürümden {s + 1}. sürüme dönüştürücü yok")]
        try:
            d = f(dict(d))
        except Exception as e:                             # göç hatası dosya hatasıdır, çökme değil
            return None, [Hata("surum", f"{s}. sürümden dönüştürülürken hata: {e}")]
        s += 1
        d["surum"] = s
    return d, []


def tanim_yukle(yol: Path, beklenen_tur: str) -> Tuple[Optional[Any], List[Hata]]:
    """Dosyayı oku → göç → ayrıştır. (Modul | Akis | None, hatalar+uyarılar)."""
    d, hatalar = json_oku(yol)
    if d is None:
        return None, hatalar
    if not isinstance(d, dict):
        return None, [Hata("", "dosyanın en dışı nesne ({…}) olmalı")]
    d, goc_hata = goc_et(d, beklenen_tur)
    if d is None:
        return None, goc_hata
    ayristir = sema.modul_ayristir if beklenen_tur == "modul" else sema.akis_ayristir
    tanim, h = ayristir(d)
    return tanim, h


# ---------------------------------------------------------------- klasör / depo
def _json_dosyalari(klasor: Path) -> List[Path]:
    try:
        return sorted(p for p in klasor.iterdir() if p.is_file() and p.suffix.lower() == ".json")
    except OSError:
        return []


def _kaynak_yukle(kok: Path, kaynak: str, rapor: YuklemeRaporu):
    """Bir kaynağın (yerleşik/kullanıcı) modül ve akışlarını yükler: ({kimlik: Modul}, [(dosya, Akis)])."""
    moduller: Dict[str, Modul] = {}
    for p in _json_dosyalari(kok / "moduller"):
        ad = f"{kaynak}/moduller/{p.name}"
        m, h = tanim_yukle(p, "modul")
        rapor.ekle(ad, h)
        if m is None:
            continue
        if m.kimlik in moduller:
            rapor.ekle(ad, [Hata("kimlik", f'"{m.kimlik}" modül kimliği başka bir dosyada da var (bu dosya atlandı)')])
            continue
        moduller[m.kimlik] = m
    akislar: List[Tuple[str, Akis]] = []
    for p in _json_dosyalari(kok / "akislar"):
        ad = f"{kaynak}/akislar/{p.name}"
        a, h = tanim_yukle(p, "akis")
        rapor.ekle(ad, h)
        if a is None:
            continue
        if any(x.kimlik == a.kimlik for _, x in akislar):
            rapor.ekle(ad, [Hata("kimlik", f'"{a.kimlik}" akış kimliği başka bir dosyada da var (bu dosya atlandı)')])
            continue
        akislar.append((ad, a))
    return moduller, akislar


def depo_yukle(yerlesik: Optional[Path] = None, kullanici: Optional[Path] = None) -> Depo:
    """Yerleşik + kullanıcı şablonlarını yükler. Hatalı dosyalar atlanır; neden `depo.rapor`da."""
    depo = Depo()
    yerlesik = Path(yerlesik) if yerlesik is not None else yerlesik_klasor()
    kullanici = Path(kullanici) if kullanici is not None else kullanici_klasoru()
    y_mod, y_akis = _kaynak_yukle(yerlesik, YERLESIK, depo.rapor)
    k_mod, k_akis = _kaynak_yukle(kullanici, KULLANICI, depo.rapor) if kullanici.is_dir() else ({}, [])
    yerlesik_kimlikler = {a.kimlik for _, a in y_akis}
    for kaynak, moduller, akislar, yedek in ((YERLESIK, y_mod, y_akis, {}), (KULLANICI, k_mod, k_akis, y_mod)):
        # kullanıcı akışı kendi modülünü, yoksa yerleşik modülü kullanır
        havuz = {**yedek, **moduller}
        for dosya, a in akislar:
            hatalar = sema.akis_modul_denetle(a, havuz)
            depo.rapor.ekle(dosya, hatalar)
            if any(not h.uyari for h in hatalar):
                continue
            etiket = a.ad
            if kaynak == KULLANICI and a.kimlik in yerlesik_kimlikler:
                etiket += " (benim sürümüm)"
            kullanilan = {m: havuz[m] for m, _ in a.moduller}
            depo.sablonlar.append(Sablon(f"{kaynak}:{a.kimlik}", kaynak, etiket, a, kullanilan, dosya))
            depo.rapor.yuklenen += 1
    return depo
