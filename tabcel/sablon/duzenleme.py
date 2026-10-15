"""Şablon Düzenleyici çekirdeği (Faz 11). Qt yok. Kullanıcının kendi şablonunu yazması: tanım = ham JSON sözlükleri (`Taslak`),
doğrulama Faz 10a'nın doğrulayıcısıyla (tek kaynak: `sema`), kayıt kullanıcı klasörüne (`yukleyici.kullanici_klasoru`).

Kurallar (CLAUDE.md kural 22): şablon tanımı koddan çıkıp dosyada durur; yeni şablon **Tablo Sağlık Kontrolü'nden 0 bulguyla**
geçmeden kaydedilmez (`uretim_denetimi`). Yerleşik şablonlar değiştirilmez: düzenlemek için **kopyası** (`kopya`) alınır; kopyada modüllere
akış kimliğiyle önek verilir ki kullanıcı klasöründeki modüller yerleşik modüllerin yerini sessizce almasın.
"""
import copy
import itertools
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..metin_tr import kucuk
from . import sema, yukleyici
from .sema import Hata

_TR = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})
KIMLIK_ENCOK = 40


# ---------------------------------------------------------------- taslak
@dataclass
class Taslak:
    """Düzenlenen şablon: akış sözlüğü + (yalnız bu akışın) modül sözlükleri. Hepsi saf JSON verisi."""
    akis: Dict[str, Any]
    moduller: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    kaynak: Optional[str] = None                 # kopyalandığı şablonun iç kimliği (bilgi amaçlı)

    @property
    def kimlik(self) -> str:
        return str(self.akis.get("kimlik", ""))

    def modul_kimlikleri(self) -> List[str]:
        return [m.get("modul") for m in self.akis.get("moduller", []) if isinstance(m, dict)]


def kimlik_uret(ad: str, mevcut=()) -> str:
    """Ad → geçerli kimlik (`^[a-z][a-z0-9_]{0,39}$`): Türkçe harfler ASCII'ye, boşluk/noktalama `_`; çakışırsa `_2`, `_3`…"""
    s = kucuk(ad or "").translate(_TR)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    if not s or not s[0].isalpha():
        s = "k_" + s if s else "kayit"
    s = s[:KIMLIK_ENCOK].rstrip("_") or "kayit"
    taban, n, mevcut = s, 2, set(mevcut)
    while s in mevcut:
        ek = f"_{n}"
        s = taban[:KIMLIK_ENCOK - len(ek)] + ek
        n += 1
    return s


def bos_taslak(ad: str, kategori: str = "Diğer", kullanilan_akis_kimlikleri=()) -> Taslak:
    """Tek modüllü, iki sütunlu başlangıç şablonu (hemen geçerlidir; kullanıcı üzerine ekler)."""
    ak = kimlik_uret(ad, kullanilan_akis_kimlikleri)
    mk = kimlik_uret(ad)
    modul = {"surum": 1, "tur": "modul", "kimlik": mk, "ad": ad, "tekil_ad": "Kayıt",
             "aciklama": f"{ad} kayıtları; her kayıt ayrı satır.", "sayfa_adi": ad[:31],
             "gorunen": ["ad"],
             "sutunlar": [{"kimlik": "ad", "ad": "Ad", "tur": "metin", "zorunlu": True},
                          {"kimlik": "aciklama", "ad": "Açıklama", "tur": "metin"}]}
    kokler = [k for k in re.split(r"\s+", kucuk(ad)) if len(k) >= 3]
    akis = {"surum": 1, "tur": "akis", "kimlik": ak, "ad": ad, "kategori": kategori,
            "aciklama": f"{ad} takibi için kendi hazırladığım şablon.",
            "anahtar_kelimeler": {"kokler": kokler or [kucuk(ad)[:5] or "kayit"], "es_anlamlilar": [], "agirlik": 1.0},
            "sorular": [], "moduller": [{"modul": mk}], "bayraklar": {}, "ayarlar": [],
            "nasil_kullanilir": [{"baslik": "Başlarken", "metin": "Kayıt Formu'nu (Veri ▸ Kayıt Formu) ya da tabloyu doğrudan kullanın."}],
            "ornek_veri": False}
    return Taslak(akis, {mk: modul})


def _modul_adi_degistir(t: Taslak, eski: str, yeni: str) -> None:
    """Modül kimliğini taslağın her yerinde değiştirir: akış listesi, bağlantılar, formül yer tutucuları (`[eski.x]`, `[eski]`)."""
    if eski not in t.moduller or yeni in t.moduller:
        raise ValueError(f'"{yeni}" modül kimliği zaten var')
    t.moduller = {(yeni if k == eski else k): v for k, v in t.moduller.items()}
    for m in t.akis.get("moduller", []):
        if m.get("modul") == eski:
            m["modul"] = yeni
    yer = re.compile(r"\[" + re.escape(eski) + r"(?=[.\]])")

    def duzelt(f):
        return yer.sub("[" + yeni, f) if isinstance(f, str) else f
    for k, m in t.moduller.items():
        if k == yeni:
            m["kimlik"] = yeni
        for s in m.get("sutunlar", []):
            b = s.get("baglanti")
            if isinstance(b, dict) and b.get("modul") == eski:
                b["modul"] = yeni
            if "formul" in s:
                s["formul"] = duzelt(s["formul"])
        for kr in m.get("kurallar", []):
            if "formul" in kr:
                kr["formul"] = duzelt(kr["formul"])


def modul_yeniden_adlandir(t: Taslak, eski: str, yeni: str) -> None:
    _modul_adi_degistir(t, eski, yeni)


def kopya(sablon, yeni_ad: str, kullanilan_akis_kimlikleri=()) -> Taslak:
    """Bir şablonun (yerleşik ya da kullanıcı) düzenlenebilir kopyası: yeni akış kimliği + modüllere önek."""
    ak = kimlik_uret(yeni_ad, set(kullanilan_akis_kimlikleri))
    akis = copy.deepcopy(sablon.akis.ham)
    akis["kimlik"], akis["ad"] = ak, yeni_ad
    t = Taslak(akis, {k: copy.deepcopy(m.ham) for k, m in sablon.moduller.items()}, sablon.ic_kimlik)
    onek = (ak[:14].rstrip("_") + "_")
    for eski in list(t.moduller):
        yeni = (onek + eski)[:KIMLIK_ENCOK]
        n = 2
        while yeni in t.moduller:
            yeni = (onek + eski)[:KIMLIK_ENCOK - 2] + f"_{n}"
            n += 1
        _modul_adi_degistir(t, eski, yeni)
    return t


# ---------------------------------------------------------------- doğrulama
def ayristir(t: Taslak):
    """(Akis | None, {kimlik: Modul}, hatalar) — her sözlük yükleyiciyle aynı yoldan (göç + doğrulama) geçer."""
    hatalar: List[Hata] = []
    moduller: Dict[str, Any] = {}
    for mk, ham in t.moduller.items():
        m, h = yukleyici.tanim_ayristir(copy.deepcopy(ham), "modul")
        hatalar += [Hata(f"modül {mk}: {x.yol}".rstrip(": "), x.mesaj, x.uyari) for x in h]
        if m is not None:
            moduller[mk] = m
            if m.kimlik != mk:
                hatalar.append(Hata(f"modül {mk}", f'dosya anahtarı "{mk}" ile kimlik "{m.kimlik}" uyuşmuyor'))
    a, h = yukleyici.tanim_ayristir(copy.deepcopy(t.akis), "akis")
    hatalar += [Hata(f"akış: {x.yol}".rstrip(": "), x.mesaj, x.uyari) for x in h]
    if a is not None and not any(not x.uyari for x in hatalar):
        hatalar += [Hata(x.yol, x.mesaj, x.uyari) for x in sema.akis_modul_denetle(a, moduller)]
        ak_set = {m for m, _ in a.moduller}
        for mk in t.moduller:
            if mk not in ak_set:
                hatalar.append(Hata(f"modül {mk}", "bu modül akışta kullanılmıyor", True))
    return a, moduller, hatalar


def dogrula(t: Taslak) -> List[Hata]:
    return ayristir(t)[2]


def ciddi_mi(hatalar) -> bool:
    return any(not h.uyari for h in hatalar)


def sablon_olustur(t: Taslak) -> Optional[yukleyici.Sablon]:
    a, moduller, hatalar = ayristir(t)
    if a is None or ciddi_mi(hatalar):
        return None
    return yukleyici.Sablon(f"{yukleyici.KULLANICI}:{a.kimlik}", yukleyici.KULLANICI, a.ad, a,
                            {m: moduller[m] for m, _ in a.moduller})


def uretim_denetimi(t: Taslak, en_cok_kombinasyon: int = 16) -> List[str]:
    """Şablonu üretip (cevap kombinasyonları: ≤ 4 soruda hepsi, fazlasında varsayılan/hepsi evet/hepsi hayır) **Tablo Sağlık Kontrolü**ne
    sokar; sorun satırlarını döndürür (boş liste = temiz, kaydedilebilir). Kural 22."""
    from ..formul import saglik
    from ..formul.motor import Hesaplayici
    from .uretici import UretimHatasi, uret
    s = sablon_olustur(t)
    if s is None:
        return ["Şablon tanımı hatalı; önce doğrulama hatalarını düzeltin."]
    sorular = [x.kimlik for x in s.akis.sorular]
    if len(sorular) <= 4:
        kombolar = [dict(zip(sorular, k)) for k in itertools.product([False, True], repeat=len(sorular))] or [{}]
    else:
        kombolar = [{}, {k: True for k in sorular}, {k: False for k in sorular}]
    sorunlar: List[str] = []
    for c in kombolar[:en_cok_kombinasyon]:
        ad = ", ".join(f"{k}={'evet' if v else 'hayır'}" for k, v in c.items()) or "varsayılan cevaplar"
        try:
            r = uret(s, c, ornek_veri=True)
            motor = Hesaplayici(r.kitap)
            motor.tumunu_hesapla()
            for b in saglik.Tarayici(r.kitap, motor).tara():
                sorunlar.append(f"[{ad}] {b.adres}: {b.baslik} — {b.aciklama}")
        except UretimHatasi as e:
            sorunlar.append(f"[{ad}] üretim hatası: {e}")
        except Exception as e:                                          # noqa: BLE001 — tanım hatası çökme değildir
            sorunlar.append(f"[{ad}] beklenmeyen hata: {e}")
    return sorunlar


# ---------------------------------------------------------------- kullanıcı klasörü
def _atomik_yaz(yol: Path, metin: str) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(yol.suffix + ".tmp")
    gecici.write_text(metin, encoding="utf-8")
    os.replace(gecici, yol)


def _json(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, indent=2) + "\n"


class KayitHatasi(ValueError):
    """Kaydedilemedi; iletisi Türkçe ve kullanıcıya gösterilebilir."""


def _akis_modulleri(klasor: Path) -> Dict[str, List[str]]:
    """Kullanıcı klasöründeki {akış kimliği: [kullandığı modül kimlikleri]}."""
    cikti = {}
    for p in sorted((klasor / "akislar").glob("*.json")) if (klasor / "akislar").is_dir() else []:
        d, _ = yukleyici.json_oku(p)
        if isinstance(d, dict) and isinstance(d.get("kimlik"), str):
            cikti[d["kimlik"]] = [m.get("modul") for m in d.get("moduller", []) if isinstance(m, dict)]
    return cikti


def kaydet(t: Taslak, klasor: Optional[Path] = None, uzerine_yaz: bool = False, denetle: bool = True) -> List[Path]:
    """Taslağı kullanıcı klasörüne yazar (`akislar/<kimlik>.json`, `moduller/<kimlik>.json`; geçici dosyaya yaz → yerine koy).
    Doğrulama hatası, kural 22 (sağlık kontrolü) sorunu, kimlik çakışması varsa `KayitHatasi`."""
    klasor = Path(klasor) if klasor is not None else yukleyici.kullanici_klasoru()
    hatalar = dogrula(t)
    if ciddi_mi(hatalar):
        raise KayitHatasi("Şablon tanımında hata var:\n" + "\n".join(str(h) for h in hatalar if not h.uyari)[:1500])
    if denetle:
        sorunlar = uretim_denetimi(t)
        if sorunlar:
            raise KayitHatasi("Şablon Tablo Sağlık Kontrolü'nden temiz geçmedi:\n" + "\n".join(sorunlar[:8]))
    mevcut = _akis_modulleri(klasor)
    if t.kimlik in mevcut and not uzerine_yaz:
        raise KayitHatasi(f'"{t.kimlik}" kimlikli bir şablon zaten var (üzerine yazmak için onaylayın).')
    for mk in t.moduller:
        kullanan = [a for a, ms in mevcut.items() if mk in ms and a != t.kimlik]
        if kullanan:
            raise KayitHatasi(f'"{mk}" modülü "{kullanan[0]}" şablonunda da kullanılıyor; modül kimliğini değiştirin.')
    yazilan: List[Path] = []
    for mk, ham in t.moduller.items():
        p = klasor / "moduller" / f"{mk}.json"
        _atomik_yaz(p, _json(ham))
        yazilan.append(p)
    p = klasor / "akislar" / f"{t.kimlik}.json"
    _atomik_yaz(p, _json(t.akis))
    yazilan.append(p)
    return yazilan


def kullanici_sablonu_sil(akis_kimligi: str, klasor: Optional[Path] = None) -> List[Path]:
    """Kullanıcı şablonunu ve yalnız ona ait modül dosyalarını siler; silinen yolları döndürür. (Çağıran onay almalıdır.)"""
    klasor = Path(klasor) if klasor is not None else yukleyici.kullanici_klasoru()
    mevcut = _akis_modulleri(klasor)
    if akis_kimligi not in mevcut:
        return []
    silinen: List[Path] = []
    diger = {m for a, ms in mevcut.items() if a != akis_kimligi for m in ms}
    for mk in mevcut[akis_kimligi]:
        p = klasor / "moduller" / f"{mk}.json"
        if mk not in diger and p.is_file():
            p.unlink()
            silinen.append(p)
    p = klasor / "akislar" / f"{akis_kimligi}.json"
    if p.is_file():
        p.unlink()
        silinen.append(p)
    return silinen


def taslak_yukle(yol_akis: Path, klasor: Optional[Path] = None) -> Taslak:
    """Kullanıcı klasöründeki bir akış dosyasını (ve modüllerini) düzenlenebilir taslağa yükler."""
    klasor = Path(klasor) if klasor is not None else yol_akis.parent.parent
    d, h = yukleyici.json_oku(yol_akis)
    if d is None:
        raise KayitHatasi("; ".join(str(x) for x in h))
    t = Taslak(d)
    for mk in t.modul_kimlikleri():
        md, h = yukleyici.json_oku(klasor / "moduller" / f"{mk}.json")
        if md is None:
            raise KayitHatasi(f'"{mk}" modül dosyası okunamadı: ' + "; ".join(str(x) for x in h))
        t.moduller[mk] = md
    return t


# ---------------------------------------------------------------- kitaptan şablon
_PARA_RE = re.compile(r"[₺$€]|TL|USD|EUR")


@dataclass
class KitaptanSonuc:
    taslak: Taslak
    uyarilar: List[str] = field(default_factory=list)


def _bicim_turu(kod: str) -> Optional[str]:
    if not kod or kod == "General":
        return None
    from ..model import sayi_bicimi
    try:
        b = sayi_bicimi.kod_coz(kod)
    except Exception:                                                           # noqa: BLE001
        return None
    if b.tarih_mi:
        return "tarih"
    if "%" in kod:
        return "yuzde"
    if _PARA_RE.search(kod):
        return "para"
    return None


def _sutun_turu(degerler: List[Any], kod: str, baslik: str) -> Tuple[str, Dict[str, Any]]:
    from ..model import kimlik as kim
    dolu = [v for v in degerler if v is not None and v != ""]
    if not dolu:
        return "metin", {}
    if all(isinstance(v, bool) for v in dolu) or all(isinstance(v, str) and kucuk(v) in ("evet", "hayır", "hayir") for v in dolu):
        return "evet_hayir", {}
    if all(isinstance(v, float) and not isinstance(v, bool) for v in dolu):
        t = _bicim_turu(kod)
        if t:
            return t, {}
        return ("tam_sayi" if all(v == int(v) for v in dolu) else "ondalik"), {}
    metinler = [str(v).strip() for v in dolu if isinstance(v, str)]
    if len(metinler) == len(dolu):
        for tur, dogrulayici in (("tc_kimlik", kim.tc_gecerli), ("vergi_no", kim.vkn_gecerli), ("iban", kim.iban_gecerli),
                                 ("telefon", kim.telefon_gecerli), ("eposta", kim.eposta_gecerli)):
            if len(metinler) >= 2 and all(dogrulayici(m) for m in metinler):
                return tur, {}
        farkli = sorted(set(metinler), key=kucuk)
        if len(metinler) >= 6 and len(farkli) <= 6 and len(farkli) * 2 <= len(metinler) and all(len(x) <= 40 for x in farkli) \
                and "," not in "".join(farkli):
            return "liste", {"secenekler": farkli}
    return "metin", {}


_REF = re.compile(r'"[^"]*"|(?<![A-Za-z0-9_.!\[])\$?([A-Z]{1,3})\$?(\d+)(?![A-Za-z0-9_(!\[:])')


def _formulu_donustur(formul: str, satir: int, sutun_kimlikleri: Dict[int, str]) -> Optional[str]:
    """Aynı satırdaki hücre başvurularını `[@sütun]` yapar; aralık/başka satır/başka sayfa başvurusu varsa None (dönüştürülemez)."""
    from ..model.adres import harften_sutun
    if re.search(r"[A-Za-z0-9_'!]\![A-Za-z$]|:\$?[A-Z]{1,3}\$?\d|[A-Za-z]{1,3}\d+:", formul):
        return None
    bozuk = []

    def deg(m):
        if m.group(0).startswith('"'):
            return m.group(0)
        c, r = harften_sutun(m.group(1)), int(m.group(2))
        if r != satir or c not in sutun_kimlikleri:
            bozuk.append(m.group(0))
            return m.group(0)
        return f"[@{sutun_kimlikleri[c]}]"
    sonuc = _REF.sub(deg, formul)
    return None if bozuk else sonuc


def kitaptan_taslak(kitap, sayfalar, ad: str, ornek_veri: bool = False, en_cok_ornek: int = 20,
                    kullanilan_akis_kimlikleri=()) -> KitaptanSonuc:
    """Çalışma kitabındaki sayfa(lar)dan şablon: her sayfa bir modül (1. satır başlık). Sütun türleri verilerden tahmin edilir
    (tarih/sayı/para/yüzde/evet-hayır/kısa liste/T.C.·vergi no·IBAN·telefon·e-posta); tüm veri satırları formülse ve yalnız
    aynı satırdaki hücrelere bakıyorsa `hesaplanan` sütun olur. Dönüşemeyenler için uyarı döner."""
    uy: List[str] = []
    ak = kimlik_uret(ad, set(kullanilan_akis_kimlikleri))
    moduller: Dict[str, Dict[str, Any]] = {}
    for sayfa in sayfalar:
        kul = sayfa.kullanilan_aralik()
        if kul is None:
            uy.append(f"“{sayfa.ad}” sayfası boş; atlandı.")
            continue
        r1, c1, r2, c2 = kul
        baslik = {}
        for c in range(c1, c2 + 1):
            v = sayfa.deger(r1, c)
            if isinstance(v, str) and v.strip():
                baslik[c] = v.strip()
        if len(baslik) < 1:
            uy.append(f"“{sayfa.ad}” sayfasının ilk satırında başlık yok; atlandı.")
            continue
        mk = kimlik_uret(sayfa.ad, moduller)
        kimlikler: Dict[int, str] = {}
        for c, b in baslik.items():
            kimlikler[c] = kimlik_uret(b, kimlikler.values())
        sutunlar = []
        veri_satirlari = list(range(r1 + 1, r2 + 1))
        for c, b in baslik.items():
            hucreler = [sayfa.hucre(r, c) for r in veri_satirlari]
            formullu = [h for h in hucreler if h is not None and h.formul]
            kod = sayfa.stil(r1 + 1, c).sayi_bicimi if veri_satirlari else "General"
            sut = {"kimlik": kimlikler[c], "ad": b}
            if veri_satirlari and len(formullu) >= max(1, int(0.8 * len(veri_satirlari))):
                r_f, h_f = next((r, h) for r, h in zip(veri_satirlari, hucreler) if h is not None and h.formul)
                f = _formulu_donustur(h_f.formul, r_f, {cc: k for cc, k in kimlikler.items() if cc != c})
                if f is not None:
                    sut.update({"tur": "hesaplanan", "formul": f})
                    bic = _bicim_turu(kod) or "ondalik"
                    sut["bicim"] = bic if bic in sema.BICIMLER else "ondalik"
                    sutunlar.append(sut)
                    continue
                uy.append(f"“{sayfa.ad}” sayfasında “{b}” sütununun formülü şablona dönüştürülemedi "
                          "(yalnız aynı satırdaki hücrelere bakan formüller dönüştürülür); sütun düz değer olarak alındı.")
            tur, ek = _sutun_turu([sayfa.deger(r, c) for r in veri_satirlari], kod, b)
            sut["tur"] = tur
            sut.update(ek)
            sutunlar.append(sut)
        if not sutunlar:
            continue
        modul = {"surum": 1, "tur": "modul", "kimlik": mk, "ad": sayfa.ad, "tekil_ad": "Kayıt",
                 "aciklama": f"“{sayfa.ad}” sayfasından oluşturuldu; her kayıt ayrı satır.", "sayfa_adi": sayfa.ad[:31],
                 "gorunen": [sutunlar[0]["kimlik"]], "sutunlar": sutunlar}
        if ornek_veri:
            ornek = []
            for r in veri_satirlari[:en_cok_ornek]:
                satir = {}
                for c, b in baslik.items():
                    s = next(x for x in sutunlar if x["kimlik"] == kimlikler[c])
                    v = sayfa.deger(r, c)
                    if v is None or v == "" or s["tur"] == "hesaplanan":
                        continue
                    if s["tur"] == "tarih" and isinstance(v, float):
                        from ..model.tarihseri import seri_ymd
                        y, a_, g_ = seri_ymd(int(v))
                        v = f"{y:04d}-{a_:02d}-{g_:02d}"
                    elif isinstance(v, float) and s["tur"] in ("tam_sayi",):
                        v = int(v)
                    satir[s["kimlik"]] = v
                if satir:
                    ornek.append(satir)
            if ornek:
                modul["ornek_veri"] = ornek
        moduller[mk] = modul
    if not moduller:
        raise KayitHatasi("Şablona dönüştürülebilir sayfa bulunamadı (her sayfanın ilk satırı başlık olmalı).")
    kokler = [k for k in re.split(r"\s+", kucuk(ad)) if len(k) >= 3]
    akis = {"surum": 1, "tur": "akis", "kimlik": ak, "ad": ad, "kategori": "Diğer",
            "aciklama": f"“{ad}”: mevcut bir çalışma kitabından oluşturuldu.",
            "anahtar_kelimeler": {"kokler": kokler or [kucuk(ad)[:5] or "kayit"], "es_anlamlilar": [], "agirlik": 1.0},
            "sorular": [], "moduller": [{"modul": m} for m in moduller], "bayraklar": {}, "ayarlar": [],
            "nasil_kullanilir": [{"baslik": "Başlarken", "metin": "Kayıt Formu'nu (Veri ▸ Kayıt Formu) ya da tabloyu doğrudan kullanın."}],
            "ornek_veri": bool(ornek_veri)}
    return KitaptanSonuc(Taslak(akis, moduller), uy)
