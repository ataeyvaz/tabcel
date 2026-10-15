"""Şablon üretici (Faz 10b): akış tanımı + cevaplar → `CalismaKitabi`. Qt yok. Tasarım: `sablon_tasarim.md` §4.

Üretilen kitap sıradan bir kitaptır (kural: form bilgisi kaybolsa da tablo çalışır): sayfalar, başlık satırı, sütun biçimleri,
veri doğrulama, açılır listeler, tanımlı adlar (`TR_M_<modül>_<sütun>`, `TR_V_<modül>`, `TR_MOD_<modül>`, `TR_AYAR_<ayar>`),
hesaplanan sütun formülleri, Ayarlar ve Nasıl Kullanılır sayfaları, isteğe bağlı örnek veri.

Sınırlar (bilinçli):
- Adlandırılmış aralıklar **sabit kapasitelidir** (`ARALIK_KAPASITESI` satır); hesaplanan sütunların formülleri yalnız ilk
  `formul_satiri` satıra yazılır (her satıra 20.000 formül yazmak kitabı yavaşlatır). Aşılırsa "Şablonu genişlet" (sonraki iş).
- Para biçimi, üretim anındaki "Para birimi" ayarına göre sabitlenir (ayar sonradan değişirse biçim değişmez).
- Satır düzeyi `kurallar` burada derlenmez (10f: form + kural motoru); sütun kısıtları doğrulamaya derlenir.
- Bağlantı (açılır liste) kaynak adlı aralığı boş satırları da içerir.
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..model import tarihseri
from ..model.ad import TanimliAd
from ..model.adres import Aralik, sutun_harfe
from ..model.dogrulama import Dogrulama, liste_sabiti_yaz
from ..model.sayfa import CalismaKitabi, Hucre, Sayfa
from ..model.stil import Stil
from . import saklama
from .sema import Akis, Modul, Sutun
from .yukleyici import Sablon

ARALIK_KAPASITESI = 20_000
FORMUL_SATIRI = 200
AYARLAR_SAYFASI = "Ayarlar"
NASIL_SAYFASI = "Nasıl Kullanılır"
BASLIK_DOLGU = "#217346"
EVET, HAYIR = "Evet", "Hayır"
_GENISLIK = {"tarih": 90, "tam_sayi": 80, "ondalik": 90, "para": 100, "yuzde": 80, "evet_hayir": 80, "liste": 110,
             "baglanti": 130, "hesaplanan": 110, "tc_kimlik": 110, "vergi_no": 100, "iban": 220, "telefon": 120, "eposta": 180}
_TOKEN = re.compile(r'"[^"]*"|\[[^\[\]]*\]|\bAYAR\.[A-Za-z_][A-Za-z0-9_]*')
_DOGRULAYICI = {"tc_kimlik": "TR_VALIDATE_TCKN", "vergi_no": "TR_VALIDATE_VKN", "iban": "TR_VALIDATE_IBAN",
                "telefon": "TR_VALIDATE_PHONE", "eposta": "TR_VALIDATE_EMAIL"}
_METIN_TURLERI = ("tc_kimlik", "vergi_no", "iban", "telefon")          # baştaki sıfır korunur (kural 15)
_PARA = {"TRY": '"₺"#,##0.00', "USD": '"$"#,##0.00', "EUR": '#,##0.00 "€"'}


class UretimHatasi(ValueError):
    """Tanım tutarsızlığı (ör. kapalı sütuna başvuran formül); iletisi kullanıcıya gösterilebilir."""


@dataclass
class ModulYeri:
    modul: Modul
    sayfa_kimligi: int
    sutunlar: Dict[str, int]                       # etkin sütun kimliği → sütun numarası
    ilk_satir: int = 2
    kapasite: int = ARALIK_KAPASITESI
    formul_satiri: int = 0

    @property
    def son_satir(self) -> int:
        return self.ilk_satir + self.kapasite - 1


@dataclass
class UretimSonucu:
    kitap: CalismaKitabi
    akis: Akis
    bayraklar: Dict[str, bool]
    yerler: Dict[str, ModulYeri] = field(default_factory=dict)
    ayar_yerleri: Dict[str, Tuple[int, int]] = field(default_factory=dict)      # ayar → (sayfa kimliği, satır); değer B sütunu
    ornek_satirlar: Dict[str, List[int]] = field(default_factory=dict)          # modül → örnek veri satırları
    uyarilar: List[str] = field(default_factory=list)


# ---------------------------------------------------------------- bayraklar
def bayraklari_coz(akis: Akis, cevaplar: Optional[Dict[str, bool]] = None) -> Dict[str, bool]:
    """Soru cevapları + türetilmiş bayraklar. Cevapsız soru varsayılanı alır; `eger`i yanlış soru `False` sayılır."""
    cevaplar = dict(cevaplar or {})
    bilinen = {s.kimlik for s in akis.sorular}
    for k in cevaplar:
        if k not in bilinen:
            raise UretimHatasi(f'Bilinmeyen soru: "{k}"')
    deger: Dict[str, bool] = {}
    for s in akis.sorular:
        v = bool(cevaplar.get(s.kimlik, s.varsayilan))
        if s.eger and not _eger(s.eger, deger):
            v = False
        deger[s.kimlik] = v
    for bayrak, soru in akis.bayraklar.items():
        deger[bayrak] = deger[soru]
    return deger


def _eger(ifade: Optional[str], bayraklar: Dict[str, bool]) -> bool:
    if not ifade:
        return True
    ters = ifade.startswith("!")
    return bayraklar.get(ifade.lstrip("!"), False) != ters


# ---------------------------------------------------------------- biçim / doğrulama
def para_kodu(sutun: Sutun, ayar_degerleri: Dict[str, Any]) -> str:
    pb = sutun.para_birimi or "TRY"
    if pb.startswith("ayar:"):
        v = ayar_degerleri.get(pb[5:])
        pb = v.strip().upper() if isinstance(v, str) and re.fullmatch(r"\s*[A-Za-z]{3}\s*", v) else "TRY"
    return _PARA.get(pb, f'#,##0.00 "{pb}"')


def sayi_bicimi(sutun: Sutun, ayar_degerleri: Dict[str, Any]) -> str:
    t = sutun.bicim if sutun.tur == "hesaplanan" and sutun.bicim else sutun.tur
    if t == "para":
        return para_kodu(sutun, ayar_degerleri)
    if t == "tam_sayi":
        return "#,##0"
    if t == "ondalik":
        return "#,##0.00"
    if t == "yuzde":
        return "0%"
    if t == "tarih":
        return "dd.mm.yyyy"
    if t in _METIN_TURLERI or t == "eposta" or sutun.barkod or (t == "metin" and sutun.benzersiz):
        return "@"                                  # kimlik/kod benzeri alanlar: baştaki sıfır korunur, sayı sanılmaz
    return "General"


def _sayi(v: Any) -> str:
    f = float(v)
    return str(int(f)) if f == int(f) else repr(f)


def _dogrulama(sutun: Sutun, harf: str, c: int, kapasite: int, ilk: int = 2) -> Optional[Dogrulama]:
    """Sütunun veri bölgesi için tek doğrulama kuralı (hücre başına en çok bir kural var)."""
    if sutun.tur == "hesaplanan":
        return None
    aralik = Aralik(ilk, c, ilk + kapasite - 1, c)
    ilk_hucre = f"{harf}{ilk}"
    mutlak = f"${harf}${ilk}:${harf}${ilk + kapasite - 1}"
    giris = (True, sutun.ad, sutun.aciklama) if sutun.aciklama else (False, "", "")
    k = sutun.kisit or {}
    mn, mx, uz = k.get("min"), k.get("max"), k.get("uzunluk")
    mesaj = f"“{sutun.ad}” alanına geçerli bir değer girin."
    ortak = dict(araliklar=(aralik,), bos_yoksay=not sutun.zorunlu, giris=giris)

    def kural(tur, islec="arasinda", f1=None, f2=None, liste=True, ileti=mesaj):
        return Dogrulama(tur=tur, islec=islec, formul1=f1, formul2=f2, acilir_liste=liste,
                         hata=(True, "durdur", "Geçersiz değer", ileti), **ortak)

    koşullar: List[str] = []
    if sutun.tur in _DOGRULAYICI:
        koşullar.append(f"{_DOGRULAYICI[sutun.tur]}({ilk_hucre})")
    if sutun.tur in ("tam_sayi", "ondalik", "para", "yuzde", "tarih"):
        if mn is not None:
            koşullar.append(f"{ilk_hucre}>={_sayi(mn)}")
        if mx is not None:
            koşullar.append(f"{ilk_hucre}<={_sayi(mx)}")
    if uz is not None and sutun.tur not in ("tam_sayi", "ondalik", "para", "yuzde", "tarih"):
        koşullar.append(f"LEN({ilk_hucre})<={uz}")
    if sutun.benzersiz:
        koşullar.insert(0, f"COUNTIF({mutlak},{ilk_hucre})=1")
    if sutun.zorunlu and (koşullar or sutun.tur in _DOGRULAYICI):
        koşullar.insert(0, f"LEN({ilk_hucre})>0")

    if sutun.tur == "liste":
        return kural("liste", f1=liste_sabiti_yaz(sutun.secenekler), ileti="Listeden bir değer seçin.")
    if sutun.tur == "evet_hayir":
        return kural("liste", f1=liste_sabiti_yaz([EVET, HAYIR]), ileti="Evet ya da Hayır seçin.")
    if sutun.tur == "baglanti":
        m, a = sutun.baglanti
        return kural("liste", f1=f"=TR_M_{m}_{a}", ileti="Listeden bir değer seçin.")
    if sutun.benzersiz or sutun.tur in _DOGRULAYICI:
        ileti = {"tc_kimlik": "Geçerli bir T.C. kimlik numarası girin.", "vergi_no": "Geçerli bir vergi kimlik numarası girin.",
                 "iban": "Geçerli bir IBAN girin.", "telefon": "Geçerli bir telefon numarası girin.",
                 "eposta": "Geçerli bir e-posta adresi girin."}.get(sutun.tur, mesaj)
        if sutun.benzersiz:
            ileti = f"Bu değer zaten var; “{sutun.ad}” benzersiz olmalı."
        return kural("ozel", f1="=AND(" + ",".join(koşullar) + ")" if len(koşullar) > 1 else "=" + koşullar[0], ileti=ileti)
    if sutun.tur in ("tam_sayi", "ondalik", "para", "yuzde"):
        tur = "tam_sayi" if sutun.tur == "tam_sayi" else "ondalik"
        if mn is not None and mx is not None:
            return kural(tur, "arasinda", f"={_sayi(mn)}", f"={_sayi(mx)}", ileti=f"{_sayi(mn)} ile {_sayi(mx)} arasında bir sayı girin.")
        if mn is not None:
            return kural(tur, "buyuk_esit", f"={_sayi(mn)}", ileti=f"{_sayi(mn)} ya da daha büyük bir sayı girin.")
        if mx is not None:
            return kural(tur, "kucuk_esit", f"={_sayi(mx)}", ileti=f"{_sayi(mx)} ya da daha küçük bir sayı girin.")
        return kural(tur, "arasinda", "=-1E+15", "=1E+15", ileti="Bir sayı girin.")
    if sutun.tur == "tarih":
        return kural("tarih", "buyuk_esit", f"={_sayi(mn) if mn is not None else 1}", ileti="Geçerli bir tarih girin.")
    if uz is not None:
        return kural("metin_uzunlugu", "kucuk_esit", f"={uz}", ileti=f"En çok {uz} karakter girin.")
    if sutun.zorunlu:
        return kural("metin_uzunlugu", "buyuk_esit", "=1", ileti="Bu alan boş bırakılamaz.")
    if giris[0]:
        return kural("her_deger", ileti=mesaj)
    return None


# ---------------------------------------------------------------- formül genişletme
def genislet(formul: str, satir: Optional[int], bu_modul: ModulYeri, yerler: Dict[str, ModulYeri], yol: str,
             ayarlar: Optional[set] = None, sabitler: Optional[Dict[str, str]] = None) -> str:
    """Yer tutucuları kanonik İngilizce, sıradan başvuru/ad biçimine çevirir (kitapta yer tutucu kalmaz).
    `[@x?]` / `[m.x?]` (isteğe bağlı): sütun kapalıysa `0` olur. `ayarlar`: üretilen (açık) ayar kimlikleri; None = denetleme yok.
    `sabitler`: {sütun kimliği: formül sabiti} — verilirse `[@x]` bu sabite çevrilir (kaydedilmemiş form taslağı; satır gerekmez)."""
    def degistir(m):
        t = m.group(0)
        if t.startswith('"'):
            return t
        if t.startswith("AYAR."):
            if ayarlar is not None and t[5:] not in ayarlar:
                raise UretimHatasi(f"{yol}: {t} ayarı bu çalıştırmada kapalı")
            return "TR_AYAR_" + t[5:]
        ic = t[1:-1]
        opsiyonel = ic.endswith("?")
        if opsiyonel:
            ic = ic[:-1]
        if ic.startswith("@"):
            if sabitler is not None and ic[1:] in sabitler:       # form taslağı (Faz 10f): `[@x]` yerine değer sabiti
                return sabitler[ic[1:]]
            sutun = bu_modul.sutunlar.get(ic[1:])
            if sutun is None:
                if opsiyonel and bu_modul.modul.sutun(ic[1:]) is not None:
                    return "0"
                raise UretimHatasi(f'{yol}: [@{ic[1:]}] başvurusu bu çalıştırmada kapalı ya da olmayan bir sütun')
            if satir is None:
                raise UretimHatasi(f"{yol}: [@{ic[1:]}] yalnız satır düzeyinde formülde kullanılır")
            return f"${sutun_harfe(sutun)}{satir}"
        modul, _, alan = ic.partition(".")
        hedef = yerler.get(modul)
        if hedef is None:
            if opsiyonel:
                return "0"
            raise UretimHatasi(f'{yol}: [{ic}] başvurusundaki "{modul}" modülü bu çalıştırmada kapalı')
        if not alan:
            return f"TR_V_{modul}"
        if alan not in hedef.sutunlar:
            if opsiyonel and hedef.modul.sutun(alan) is not None:
                return "0"
            raise UretimHatasi(f'{yol}: [{ic}] başvurusundaki "{alan}" sütunu bu çalıştırmada kapalı')
        return f"TR_M_{modul}_{alan}"
    return _TOKEN.sub(degistir, formul)


# ---------------------------------------------------------------- değer dönüşümü
def _ornek_hucre(sutun: Sutun, v: Any) -> Optional[Hucre]:
    if v is None:
        return None
    t = sutun.tur
    if t == "tarih":
        if isinstance(v, str):
            try:
                y, a, g = (int(x) for x in v.split("-"))
                return Hucre(float(tarihseri.ymd_seri(y, a, g)))
            except ValueError:
                raise UretimHatasi(f'Örnek veri: "{sutun.kimlik}" tarihi "yyyy-aa-gg" biçiminde olmalı ("{v}")')
        return Hucre(float(v))
    if t == "evet_hayir":
        return Hucre(EVET if v in (True, EVET, "evet", 1) else HAYIR)
    if t in ("tam_sayi", "ondalik", "para", "yuzde"):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise UretimHatasi(f'Örnek veri: "{sutun.kimlik}" sayı olmalı ("{v}")')
        return Hucre(float(v))
    return Hucre(str(v)) if isinstance(v, str) else Hucre(float(v) if not isinstance(v, bool) else v)


# ---------------------------------------------------------------- üretim
def uret(sablon: Sablon, cevaplar: Optional[Dict[str, bool]] = None, ornek_veri: Optional[bool] = None,
         formul_satiri: int = FORMUL_SATIRI, kapasite: int = ARALIK_KAPASITESI) -> UretimSonucu:
    """`ornek_veri`: None = akışın kararı; True/False = zorla. Hata → `UretimHatasi` (kitap yarım bırakılmaz: çağıran atar)."""
    akis = sablon.akis
    bayrak = bayraklari_coz(akis, cevaplar)
    kitap = CalismaKitabi()
    sonuc = UretimSonucu(kitap, akis, bayrak)
    acik_ayarlar = [a for a in akis.ayarlar if _eger(a.eger, bayrak)]
    ayar_degerleri = {a.kimlik: a.varsayilan for a in acik_ayarlar}

    aktif: List[Modul] = []
    for mk, eg in akis.moduller:
        if _eger(eg, bayrak):
            aktif.append(sablon.moduller[mk])
    adlar_ = [m.sayfa_adi for m in aktif] + ([AYARLAR_SAYFASI] if acik_ayarlar else []) + \
             ([NASIL_SAYFASI] if akis.nasil_kullanilir else [])
    gorulen = set()
    for a in adlar_:
        if a.casefold() in gorulen:
            raise UretimHatasi(f'"{a}" adlı sayfa birden çok kez oluşuyor')
        gorulen.add(a.casefold())

    # 1) sayfalar ve sütun yerleşimi
    ilk = True
    for m in aktif:
        if ilk:
            sayfa = kitap.sayfalar[0]
            kitap.yeniden_adlandir(sayfa, m.sayfa_adi)
            ilk = False
        else:
            sayfa = kitap.sayfa_ekle(m.sayfa_adi)
        etkin = [s for s in m.sutunlar if _eger(s.eger, bayrak)]
        yer = ModulYeri(m, sayfa.kimlik, {s.kimlik: i + 1 for i, s in enumerate(etkin)}, kapasite=kapasite,
                        formul_satiri=min(m.formul_satiri or formul_satiri, kapasite)
                        if any(s.tur == "hesaplanan" for s in etkin) else 0)
        sonuc.yerler[m.kimlik] = yer
    ayar_sayfasi = kitap.sayfa_ekle(AYARLAR_SAYFASI) if acik_ayarlar else None
    nasil_sayfasi = kitap.sayfa_ekle(NASIL_SAYFASI) if akis.nasil_kullanilir else None

    # bağlantı hedefi kapalıysa erken, anlaşılır hata
    for m in aktif:
        for s in m.sutunlar:
            if s.baglanti and s.kimlik in sonuc.yerler[m.kimlik].sutunlar:
                hedef = sonuc.yerler.get(s.baglanti[0])
                if hedef is None or s.baglanti[1] not in hedef.sutunlar:
                    raise UretimHatasi(f'{m.sayfa_adi}: "{s.ad}" sütununun bağlandığı "{s.baglanti[0]}.{s.baglanti[1]}" bu çalıştırmada kapalı')

    # 2) Ayarlar
    if ayar_sayfasi is not None:
        _ayarlar_yaz(ayar_sayfasi, acik_ayarlar, sonuc)
    # 3) modül sayfaları
    for m in aktif:
        yer = sonuc.yerler[m.kimlik]
        _modul_yaz(kitap, kitap.sayfa_kimlikle(yer.sayfa_kimligi), yer, sonuc, ayar_degerleri, set(ayar_degerleri))
    # 4) örnek veri
    if akis.ornek_veri if ornek_veri is None else ornek_veri:
        for m in aktif:
            _ornek_yaz(kitap.sayfa_kimlikle(sonuc.yerler[m.kimlik].sayfa_kimligi), sonuc.yerler[m.kimlik], sonuc)
    # 5) Nasıl Kullanılır
    if nasil_sayfasi is not None:
        _nasil_yaz(nasil_sayfasi, akis)
    # 6) şablon bilgisi (kitapta saklanır; .xlsx'te çok gizli `_tabcel`)
    kitap.sablon = saklama.kayit_olustur(sablon, sonuc)
    return sonuc


def _stil_id(kitap: CalismaKitabi, **alan) -> int:
    return kitap.stil_havuzu.kimlik(Stil(**alan))


def _ayarlar_yaz(sayfa: Sayfa, ayarlar: list, sonuc: UretimSonucu):
    kitap = sonuc.kitap
    baslik = _stil_id(kitap, kalin=True, yazi_rengi="#FFFFFF", dolgu=BASLIK_DOLGU)
    hucreler, stiller = {}, {}
    for c, t in enumerate(("Ayar", "Değer", "Açıklama"), 1):
        hucreler[(1, c)] = Hucre(t)
        stiller[(1, c)] = baslik
    kod = {"yuzde": "0%", "tam_sayi": "#,##0", "ondalik": "#,##0.00", "tarih": "dd.mm.yyyy", "para": '"₺"#,##0.00'}
    for i, a in enumerate(ayarlar, 2):
        hucreler[(i, 1)] = Hucre(a.ad)
        v = a.varsayilan
        if a.tur == "evet_hayir":
            v = EVET if v else HAYIR
        elif a.tur in ("yuzde", "tam_sayi", "ondalik", "para") and isinstance(v, (int, float)) and not isinstance(v, bool):
            v = float(v)
        if v is not None:
            hucreler[(i, 2)] = Hucre(v)
        if a.tur in kod:
            stiller[(i, 2)] = _stil_id(kitap, sayi_bicimi=kod[a.tur], yatay="sol")
        hucreler[(i, 3)] = Hucre(a.aciklama or "")
        sonuc.ayar_yerleri[a.kimlik] = (sayfa.kimlik, i)
        kitap.ad_yaz(TanimliAd(f"TR_AYAR_{a.kimlik}", f"=[{sayfa.kimlik}]!$B${i}", None, a.ad))
        if a.tur == "evet_hayir":
            sayfa.dogrulamalari_yaz(sayfa.dogrulamalar + [Dogrulama(
                araliklar=(Aralik(i, 2, i, 2),), tur="liste", formul1=liste_sabiti_yaz([EVET, HAYIR]))])
    sayfa.toplu_yaz({k: v for k, v in hucreler.items() if not v.bos_mu()})
    sayfa.bicim_yaz(hucreler=stiller)
    sayfa.sutun_genislik.update({1: 160, 2: 110, 3: 360})
    sayfa.gorunum_yaz(dondur=(2, 1))


def _nasil_yaz(sayfa: Sayfa, akis: Akis):
    kitap = sayfa.kitap
    baslik = _stil_id(kitap, kalin=True, boyut=14, yazi_rengi="#217346")
    altbaslik = _stil_id(kitap, kalin=True)
    govde = _stil_id(kitap, kaydir=True, dikey="ust")
    hucreler, stiller = {(1, 1): Hucre(f"{akis.ad} — nasıl kullanılır?")}, {(1, 1): baslik}
    hucreler[(2, 1)] = Hucre(akis.aciklama)
    stiller[(2, 1)] = govde
    satir = 4
    for b, metin in akis.nasil_kullanilir:
        hucreler[(satir, 1)], stiller[(satir, 1)] = Hucre(b), altbaslik
        hucreler[(satir + 1, 1)], stiller[(satir + 1, 1)] = Hucre(metin), govde
        satir += 3
    sayfa.toplu_yaz(hucreler)
    sayfa.bicim_yaz(hucreler=stiller)
    sayfa.sutun_genislik[1] = 640
    sayfa.gorunum_yaz(kilavuz=False)


def _modul_yaz(kitap: CalismaKitabi, sayfa: Sayfa, yer: ModulYeri, sonuc: UretimSonucu, ayar_degerleri: Dict[str, Any],
               acik_ayarlar: set):
    m = yer.modul
    etkin = [s for s in m.sutunlar if s.kimlik in yer.sutunlar]
    son_harf = sutun_harfe(len(etkin))
    baslik = _stil_id(kitap, kalin=True, yazi_rengi="#FFFFFF", dolgu=BASLIK_DOLGU, dikey="orta")
    hucreler: Dict[Tuple[int, int], Hucre] = {}
    stiller: Dict[Tuple[int, int], int] = {}
    sutun_stilleri: Dict[int, int] = {}
    dogrulamalar: List[Dogrulama] = []
    for s in etkin:
        c = yer.sutunlar[s.kimlik]
        harf = sutun_harfe(c)
        hucreler[(1, c)] = Hucre(s.ad)
        stiller[(1, c)] = baslik
        kod = sayi_bicimi(s, ayar_degerleri)
        if kod != "General":
            sutun_stilleri[c] = _stil_id(kitap, sayi_bicimi=kod)
        sayfa.sutun_genislik[c] = max(_GENISLIK.get(s.tur, 140), min(len(s.ad) * 9 + 28, 260))
        dv = _dogrulama(s, harf, c, yer.kapasite, yer.ilk_satir)
        if dv is not None:
            dogrulamalar.append(dv)
        kitap.ad_yaz(TanimliAd(f"TR_M_{m.kimlik}_{s.kimlik}", f"=[{sayfa.kimlik}]!${harf}${yer.ilk_satir}:${harf}${yer.son_satir}", None, s.ad))
        if s.tur == "hesaplanan":
            for r in range(yer.ilk_satir, yer.ilk_satir + yer.formul_satiri):
                hucreler[(r, c)] = Hucre(formul=genislet(s.formul, r, yer, sonuc.yerler, f"{m.sayfa_adi}/{s.ad}", acik_ayarlar))
    kitap.ad_yaz(TanimliAd(f"TR_MOD_{m.kimlik}", f"=[{sayfa.kimlik}]!$A$1:${son_harf}$1", None, m.ad))
    kitap.ad_yaz(TanimliAd(f"TR_V_{m.kimlik}", f"=[{sayfa.kimlik}]!$A${yer.ilk_satir}:${son_harf}${yer.son_satir}", None, m.ad))
    sayfa.toplu_yaz(hucreler)
    sayfa.bicim_yaz(hucreler=stiller, sutunlar=sutun_stilleri)
    sayfa.dogrulamalari_yaz(dogrulamalar)
    sayfa.satir_yukseklik[1] = 26
    sayfa.gorunum_yaz(dondur=(2, 1))


def _ornek_yaz(sayfa: Sayfa, yer: ModulYeri, sonuc: UretimSonucu):
    hucreler = {}
    satirlar = []
    for i, satir in enumerate(yer.modul.ornek_veri):
        r = yer.ilk_satir + i
        for kimlik, v in satir.items():
            c = yer.sutunlar.get(kimlik)
            if c is None:
                continue
            s = yer.modul.sutun(kimlik)
            if s.tur == "hesaplanan":
                continue
            h = _ornek_hucre(s, v)
            if h is not None:
                hucreler[(r, c)] = h
        satirlar.append(r)
    if hucreler:
        sayfa.toplu_yaz(hucreler)
        sonuc.ornek_satirlar[yer.modul.kimlik] = satirlar
