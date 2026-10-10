"""Koşullu biçim pencereleri (Faz 5 / 5h; faz5_tasarim.md §8.4): Kural penceresi (hızlı kurallar ve Yeni/Düzenle
için tek pencere), Özel Biçim, Kuralları Yönet.

Değer alanları Türkçe yazılır: sayı `2,5`, metin düz, formül `=A1*2`; saklanan biçime çevrilir (`=2.5`,
`="Ali"`, `=A1*2`). Formüller etkin hücreye göre yazılır; çapaya kaydırmayı çağıran yapar
(`Izgara.kosullu_kural_ekle`).
"""
import re
from dataclasses import replace
from typing import List, Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ..formul import ceviri
from ..formul.sozcuk import FormulHatasi
from ..model.adres import aralik_yaz
from ..model.kosullu import KosulluKural, RENK_OLCEKLERI, VERI_CUBUGU_RENKLERI
from ..model.stil import StilYama

HAZIR_BICIMLER = (
    ("Koyu Kırmızı Metinli Açık Kırmızı Dolgu", StilYama(yazi_rengi="#9C0006", dolgu="#FFC7CE")),
    ("Koyu Sarı Metinli Sarı Dolgu", StilYama(yazi_rengi="#9C5700", dolgu="#FFEB9C")),
    ("Koyu Yeşil Metinli Yeşil Dolgu", StilYama(yazi_rengi="#006100", dolgu="#C6EFCE")),
    ("Açık Kırmızı Dolgu", StilYama(dolgu="#FFC7CE")),
    ("Kırmızı Metin", StilYama(yazi_rengi="#9C0006")),
    ("Kırmızı Kenarlık", StilYama(kenar={y: ("ince", "#9C0006") for y in ("ust", "alt", "sol", "sag")})),
)
TURLER = (
    ("hucre_degeri", "Hücre değeri"), ("metin", "Belirli metin"), ("bos", "Boşluklar"),
    ("bos_degil", "Boş olmayanlar"), ("hata", "Hatalar"), ("hata_degil", "Hatasızlar"),
    ("yinelenen", "Yinelenen değerler"), ("benzersiz", "Benzersiz değerler"), ("ilk", "İlk N"), ("son", "Son N"),
    ("ortalama_ustu", "Ortalamanın üstünde"), ("ortalama_alti", "Ortalamanın altında"),
    ("formul", "Formül"), ("renk_olcegi_2", "2 renkli ölçek"), ("renk_olcegi_3", "3 renkli ölçek"),
    ("veri_cubugu", "Veri çubuğu"),
)
ISLEC_ADLARI = (("arasinda", "arasında"), ("arasinda_degil", "arasında değil"), ("esit", "eşit"),
                ("esit_degil", "eşit değil"), ("buyuk", "büyük"), ("kucuk", "küçük"),
                ("buyuk_esit", "büyük veya eşit"), ("kucuk_esit", "küçük veya eşit"))
METIN_ISLEC_ADLARI = (("icerir", "içerir"), ("icermez", "içermez"), ("baslar", "ile başlar"), ("biter", "ile biter"))
RENK_ADLARI = (("mavi", "Mavi"), ("yesil", "Yeşil"), ("kirmizi", "Kırmızı"), ("turuncu", "Turuncu"),
               ("acik_mavi", "Açık Mavi"), ("mor", "Mor"))
_SAYI = re.compile(r"^=-?[\d.,E+-]+$")


def deger_formulu(metin: str, kitap, ad: str = "Değer") -> str:
    """Kullanıcının yazdığı değer → saklanan formül. `=` ile başlıyorsa formül; sayı `=n`; aksi metin `="…"`."""
    from ..model.girdi import akilli_coz
    metin = metin.strip()
    if metin == "":
        raise ValueError(f"{ad} boş bırakılamaz.")
    try:
        if metin.startswith("="):
            return ceviri.girdiden(metin, kitap)
        h, _ = akilli_coz(metin)
    except FormulHatasi as e:
        raise ValueError(f"Bu formülde bir sorun var: {e}") from e
    if h is not None and h.formul is None and isinstance(h.deger, (int, float)) and not isinstance(h.deger, bool):
        return "=" + format(float(h.deger), ".15g")
    return '="' + metin.replace('"', '""') + '"'


def deger_gosterimi(formul: Optional[str], kitap) -> str:
    """Saklanan değer formülünün düzenleme metni (`=2.5` → `2,5`, `="Ali"` → `Ali`, diğerleri Türkçe formül)."""
    if formul is None:
        return ""
    g = ceviri.gosterime(formul, kitap)
    if _SAYI.match(g):
        return g[1:]
    if len(g) >= 3 and g.startswith('="') and g.endswith('"') and '"' not in g[2:-1].replace('""', ""):
        return g[2:-1].replace('""', '"')
    return g


def bicim_ozeti(yama: Optional[StilYama]) -> str:
    if yama is None or yama.bos_mu():
        return "Biçim ayarlanmadı"
    for ad, h in HAZIR_BICIMLER:
        if h == yama:
            return ad
    return "Özel biçim"


def kural_aciklamasi(k: KosulluKural, kitap=None) -> str:
    """Kuralları Yönet listesinin "Kural" sütunu."""
    isl = dict(ISLEC_ADLARI)
    t = k.tur
    if t == "hucre_degeri":
        a = deger_gosterimi(k.formul1, kitap)
        b = deger_gosterimi(k.formul2, kitap) if k.formul2 is not None else ""
        return f"Hücre değeri {isl[k.islec]} {a}" + (f" ve {b}" if k.islec in ("arasinda", "arasinda_degil") else "")
    if t == "metin":
        return f"Metin {dict(METIN_ISLEC_ADLARI)[k.islec]}: {k.metin}"
    if t == "yinelenen":
        return "Benzersiz değerler" if k.benzersiz else "Yinelenen değerler"
    if t == "ilk_son":
        return f"{'Son' if k.alt else 'İlk'} {k.n}{'%' if k.yuzde else ''}"
    if t == "ortalama":
        return f"Ortalamanın {'üstü' if k.ustu else 'altı'}" + (f" ({k.std} std. sapma)" if k.std else "")
    if t == "formul":
        return "Formül: " + deger_gosterimi(k.formul1, kitap)
    if t == "renk_olcegi":
        return f"{len(k.noktalar)} renkli ölçek"
    if t == "veri_cubugu":
        return "Veri çubuğu"
    return dict(TURLER).get(t, t)


class OzelBicimPenceresi(QDialog):
    """Yazı rengi, dolgu, kalın/italik/üstü çizili/altı çizili (yazı tipi adı/boyutu değiştirilemez — Excel gibi)."""

    def __init__(self, parent=None, yama: Optional[StilYama] = None):
        super().__init__(parent)
        self.setWindowTitle("Hücreleri Biçimlendir")
        self._yazi, self._dolgu = None, None
        a = dict(yama._alanlar) if yama is not None else {}
        self._yazi, self._dolgu = a.get("yazi_rengi"), a.get("dolgu")
        self.kalin, self.italik = QCheckBox("Kalın"), QCheckBox("İtalik")
        self.ustu_cizili, self.alti_cizili = QCheckBox("Üstü çizili"), QCheckBox("Altı çizili")
        self.kalin.setChecked(bool(a.get("kalin")))
        self.italik.setChecked(bool(a.get("italik")))
        self.ustu_cizili.setChecked(bool(a.get("ustu_cizili")))
        self.alti_cizili.setChecked(a.get("alti_cizili", "yok") != "yok")
        self.yazi_dugmesi, self.dolgu_dugmesi = QPushButton(), QPushButton()
        self.yazi_dugmesi.clicked.connect(lambda: self._renk_sec("yazi"))
        self.dolgu_dugmesi.clicked.connect(lambda: self._renk_sec("dolgu"))
        f = QFormLayout()
        f.addRow("Yazı rengi:", self.yazi_dugmesi)
        f.addRow("Dolgu rengi:", self.dolgu_dugmesi)
        f.addRow(self.kalin)
        f.addRow(self.italik)
        f.addRow(self.ustu_cizili)
        f.addRow(self.alti_cizili)
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.accepted.connect(self.accept)
        dugmeler.rejected.connect(self.reject)
        v = QVBoxLayout(self)
        v.addLayout(f)
        v.addWidget(dugmeler)
        self._renkleri_goster()

    def _renkleri_goster(self) -> None:
        for d, renk, yok in ((self.yazi_dugmesi, self._yazi, "Otomatik"), (self.dolgu_dugmesi, self._dolgu, "Renk yok")):
            d.setText(renk.upper() if renk else yok)
            d.setStyleSheet(f"background:{renk};" if renk else "")

    def _renk_sec(self, hangisi: str) -> None:
        mevcut = self._yazi if hangisi == "yazi" else self._dolgu
        c = QColorDialog.getColor(QColor(mevcut or "#000000"), self, "Renk")
        if c.isValid():
            if hangisi == "yazi":
                self._yazi = c.name()
            else:
                self._dolgu = c.name()
            self._renkleri_goster()

    def renkleri_ayarla(self, yazi: Optional[str], dolgu: Optional[str]) -> None:
        self._yazi, self._dolgu = yazi, dolgu
        self._renkleri_goster()

    def yama(self) -> StilYama:
        a = {}
        if self._yazi:
            a["yazi_rengi"] = self._yazi
        if self._dolgu:
            a["dolgu"] = self._dolgu
        if self.kalin.isChecked():
            a["kalin"] = True
        if self.italik.isChecked():
            a["italik"] = True
        if self.ustu_cizili.isChecked():
            a["ustu_cizili"] = True
        if self.alti_cizili.isChecked():
            a["alti_cizili"] = "tek"
        return StilYama(**a)


class KuralPenceresi(QDialog):
    """Hızlı kurallar (Büyüktür…, Metin İçerir… vb.) ve Yeni/Düzenle için tek pencere. `kural()`: araliklar boş
    `KosulluKural` (formüller etkin hücreye göre). Geçersiz alan → `ValueError` (Türkçe ileti)."""

    def __init__(self, kitap, parent=None, tur: str = "hucre_degeri", islec: Optional[str] = None,
                 kural: Optional[KosulluKural] = None, tur_sabit: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Yeni Biçimlendirme Kuralı")
        self.kitap = kitap
        self._ozel_yama: Optional[StilYama] = None
        self._sonuc: Optional[KosulluKural] = None
        self.tur_kutusu = QComboBox()
        for k, ad in TURLER:
            self.tur_kutusu.addItem(ad, k)
        self.islec_kutusu = QComboBox()
        self.deger1, self.deger2 = QLineEdit(), QLineEdit()
        self.metin = QLineEdit()
        self.n_kutusu = QSpinBox()
        self.n_kutusu.setRange(1, 1000)
        self.n_kutusu.setValue(10)
        self.yuzde = QCheckBox("Yüzde")
        self.std = QSpinBox()
        self.std.setRange(0, 3)
        self.formul = QLineEdit()
        self.renk_kutulari = [QComboBox(), QComboBox(), QComboBox()]
        for kt in self.renk_kutulari:
            for k, ad in RENK_ADLARI:
                kt.addItem(ad, VERI_CUBUGU_RENKLERI[k])
        self.cubuk_renk = QComboBox()
        for k, ad in RENK_ADLARI:
            self.cubuk_renk.addItem(ad, k)
        self.gradyan = QCheckBox("Gradyan dolgu")
        self.gradyan.setChecked(True)
        self.yalniz_cubuk = QCheckBox("Yalnızca çubuğu göster")
        self.bicim_kutusu = QComboBox()
        for ad, _ in HAZIR_BICIMLER:
            self.bicim_kutusu.addItem(ad)
        self.bicim_kutusu.addItem("Özel Biçim…")
        self.bicim_kutusu.activated.connect(self._bicim_secildi)
        self.dur = QCheckBox("Doğruysa durdur")

        f = QFormLayout()
        self._satirlar = {}
        for ad, w in (("tur", self.tur_kutusu), ("islec", self.islec_kutusu), ("deger1", self.deger1),
                      ("deger2", self.deger2), ("metin", self.metin), ("n", self.n_kutusu), ("yuzde", self.yuzde),
                      ("std", self.std), ("formul", self.formul), ("renk1", self.renk_kutulari[0]),
                      ("renk2", self.renk_kutulari[1]), ("renk3", self.renk_kutulari[2]),
                      ("cubuk_renk", self.cubuk_renk), ("gradyan", self.gradyan), ("yalniz", self.yalniz_cubuk)):
            etiket = QLabel({"tur": "Kural türü:", "islec": "Koşul:", "deger1": "Değer:", "deger2": "ve:",
                             "metin": "Metin:", "n": "Sayı:", "std": "Standart sapma:", "formul": "Formül:",
                             "renk1": "En küçük değer rengi:", "renk2": "Orta değer rengi:",
                             "renk3": "En büyük değer rengi:", "cubuk_renk": "Çubuk rengi:"}.get(ad, ""))
            f.addRow(etiket, w)
            self._satirlar[ad] = (f.labelForField(w), w)
        f.addRow("Biçim:", self.bicim_kutusu)
        f.addRow(self.dur)
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.accepted.connect(self._tamam)
        dugmeler.rejected.connect(self.reject)
        v = QVBoxLayout(self)
        v.addLayout(f)
        v.addWidget(dugmeler)

        self.tur_kutusu.currentIndexChanged.connect(self._duzeni_ayarla)
        self.islec_kutusu.currentIndexChanged.connect(self._duzeni_ayarla)
        if kural is not None:
            self._yukle(kural)
        else:
            self.tur_kutusu.setCurrentIndex(self.tur_kutusu.findData(tur))
        self._duzeni_ayarla()
        if islec is not None:
            self._islec_sec(islec)
        self.tur_kutusu.setEnabled(not tur_sabit)

    # --- düzen ---
    def tur(self) -> str:
        return self.tur_kutusu.currentData()

    def _islec_sec(self, islec: str) -> None:
        i = self.islec_kutusu.findData(islec)
        if i >= 0:
            self.islec_kutusu.setCurrentIndex(i)

    def _duzeni_ayarla(self) -> None:
        t = self.tur()
        # işleç listesi türe göre
        gerek = (METIN_ISLEC_ADLARI if t == "metin" else ISLEC_ADLARI if t == "hucre_degeri" else ())
        if [self.islec_kutusu.itemData(i) for i in range(self.islec_kutusu.count())] != [k for k, _ in gerek]:
            self.islec_kutusu.blockSignals(True)
            self.islec_kutusu.clear()
            for k, ad in gerek:
                self.islec_kutusu.addItem(ad, k)
            self.islec_kutusu.blockSignals(False)
        iki = t == "hucre_degeri" and self.islec_kutusu.currentData() in ("arasinda", "arasinda_degil")
        gorunen = {
            "islec": t in ("hucre_degeri", "metin"), "deger1": t == "hucre_degeri", "deger2": iki,
            "metin": t == "metin", "n": t in ("ilk", "son"), "yuzde": t in ("ilk", "son"),
            "std": t in ("ortalama_ustu", "ortalama_alti"), "formul": t == "formul",
            "renk1": t in ("renk_olcegi_2", "renk_olcegi_3"), "renk2": t == "renk_olcegi_3",
            "renk3": t in ("renk_olcegi_2", "renk_olcegi_3"), "cubuk_renk": t == "veri_cubugu",
            "gradyan": t == "veri_cubugu", "yalniz": t == "veri_cubugu"}
        for ad, (etiket, w) in self._satirlar.items():
            if ad == "tur":
                continue
            ac = gorunen.get(ad, False)
            w.setVisible(ac)
            if etiket is not None:
                etiket.setVisible(ac)
        renkli = t in ("renk_olcegi_2", "renk_olcegi_3", "veri_cubugu")
        self.bicim_kutusu.setEnabled(not renkli)
        self.dur.setEnabled(not renkli)
        if t == "renk_olcegi_2":
            self.renk_kutulari[0].setCurrentIndex(self.renk_kutulari[0].findData("#63BE7B"))

    def _bicim_secildi(self, i: int) -> None:
        if i == self.bicim_kutusu.count() - 1:
            pen = OzelBicimPenceresi(self, self._ozel_yama)
            if pen.exec() == QDialog.Accepted:
                self._ozel_yama = pen.yama()
            elif self._ozel_yama is None:
                self.bicim_kutusu.setCurrentIndex(0)

    def bicim_yamasi(self) -> StilYama:
        i = self.bicim_kutusu.currentIndex()
        if i == self.bicim_kutusu.count() - 1:
            return self._ozel_yama if self._ozel_yama is not None else StilYama()
        return HAZIR_BICIMLER[i][1]

    def ozel_bicim_ayarla(self, yama: StilYama) -> None:
        self._ozel_yama = yama
        self.bicim_kutusu.setCurrentIndex(self.bicim_kutusu.count() - 1)

    # --- dönüşümler ---
    def kural_olustur(self) -> KosulluKural:
        t = self.tur()
        d = self.kitap
        bicim, dur = self.bicim_yamasi(), self.dur.isChecked()
        kw = dict(araliklar=(), bicim=bicim, dur=dur)
        if t == "hucre_degeri":
            islec = self.islec_kutusu.currentData()
            f1 = deger_formulu(self.deger1.text(), d, "Değer")
            f2 = deger_formulu(self.deger2.text(), d, "İkinci değer") if islec in ("arasinda", "arasinda_degil") else None
            return KosulluKural(tur="hucre_degeri", islec=islec, formul1=f1, formul2=f2, **kw)
        if t == "metin":
            if self.metin.text() == "":
                raise ValueError("Metin boş bırakılamaz.")
            return KosulluKural(tur="metin", islec=self.islec_kutusu.currentData(), metin=self.metin.text(), **kw)
        if t in ("bos", "bos_degil", "hata", "hata_degil"):
            return KosulluKural(tur=t, **kw)
        if t in ("yinelenen", "benzersiz"):
            return KosulluKural(tur="yinelenen", benzersiz=t == "benzersiz", **kw)
        if t in ("ilk", "son"):
            return KosulluKural(tur="ilk_son", n=self.n_kutusu.value(), alt=t == "son",
                                yuzde=self.yuzde.isChecked(), **kw)
        if t in ("ortalama_ustu", "ortalama_alti"):
            return KosulluKural(tur="ortalama", ustu=t == "ortalama_ustu", std=self.std.value(), **kw)
        if t == "formul":
            f = self.formul.text().strip()
            if f == "":
                raise ValueError("Formül boş bırakılamaz.")
            try:
                f = ceviri.girdiden(f if f.startswith("=") else "=" + f, d)
            except FormulHatasi as e:
                raise ValueError(f"Bu formülde bir sorun var: {e}") from e
            return KosulluKural(tur="formul", formul1=f, **kw)
        if t in ("renk_olcegi_2", "renk_olcegi_3"):
            r1, r2, r3 = (kt.currentData() for kt in self.renk_kutulari)
            noktalar = ((("min", None, r1), ("max", None, r3)) if t == "renk_olcegi_2"
                        else (("min", None, r1), ("yuzdebirlik", "=50", r2), ("max", None, r3)))
            return KosulluKural(araliklar=(), tur="renk_olcegi", bicim=None, noktalar=noktalar)
        if t == "veri_cubugu":
            return KosulluKural(araliklar=(), tur="veri_cubugu", bicim=None,
                                renk=VERI_CUBUGU_RENKLERI[self.cubuk_renk.currentData()],
                                gradyan=self.gradyan.isChecked(), yalniz_cubuk=self.yalniz_cubuk.isChecked())
        raise ValueError("Bilinmeyen kural türü")

    def _yukle(self, k: KosulluKural) -> None:
        t = {"ilk_son": "son" if k.alt else "ilk", "yinelenen": "benzersiz" if k.benzersiz else "yinelenen",
             "ortalama": "ortalama_ustu" if k.ustu else "ortalama_alti",
             "renk_olcegi": f"renk_olcegi_{len(k.noktalar)}"}.get(k.tur, k.tur)
        self.tur_kutusu.setCurrentIndex(self.tur_kutusu.findData(t))
        self._duzeni_ayarla()
        d = self.kitap
        if k.tur in ("hucre_degeri", "metin"):
            self._islec_sec(k.islec)
        self.deger1.setText(deger_gosterimi(k.formul1, d) if k.tur == "hucre_degeri" else "")
        self.deger2.setText(deger_gosterimi(k.formul2, d))
        self.metin.setText(k.metin)
        self.n_kutusu.setValue(k.n)
        self.yuzde.setChecked(k.yuzde)
        self.std.setValue(k.std)
        if k.tur == "formul":
            self.formul.setText(ceviri.gosterime(k.formul1, d))
        self.dur.setChecked(k.dur)
        if k.bicim is not None:
            for i, (_, h) in enumerate(HAZIR_BICIMLER):
                if h == k.bicim:
                    self.bicim_kutusu.setCurrentIndex(i)
                    break
            else:
                self.ozel_bicim_ayarla(k.bicim)
        if k.tur == "renk_olcegi":
            for kt, n in zip(self.renk_kutulari, ((k.noktalar[0], k.noktalar[1], k.noktalar[2]) if len(k.noktalar) == 3
                                                  else (k.noktalar[0], k.noktalar[0], k.noktalar[1]))):
                i = kt.findData(n[2].upper()) if kt.findData(n[2].upper()) >= 0 else kt.findData(n[2])
                if i >= 0:
                    kt.setCurrentIndex(i)
        if k.tur == "veri_cubugu":
            for i in range(self.cubuk_renk.count()):
                if VERI_CUBUGU_RENKLERI[self.cubuk_renk.itemData(i)].lower() == k.renk.lower():
                    self.cubuk_renk.setCurrentIndex(i)
            self.gradyan.setChecked(k.gradyan)
            self.yalniz_cubuk.setChecked(k.yalniz_cubuk)

    def _tamam(self) -> None:
        try:
            self._sonuc = self.kural_olustur()
        except ValueError as e:
            QMessageBox.warning(self, "Koşullu Biçimlendirme", str(e))
            return
        self.accept()

    def kural(self) -> Optional[KosulluKural]:
        return self._sonuc


class KuralYoneticisi(QDialog):
    """Kuralları Yönet: liste (Kural, Biçim, Uygulandığı yer, Doğruysa Durdur), Yeni/Düzenle/Sil, öncelik oku.
    `liste()`: düzenlenmiş TAM liste (sıra = öncelik). Yeni kuralın formülleri aralığın sol üst hücresine göre
    yazılmış sayılır (etkin hücre)."""

    def __init__(self, kitap, sayfa, secim, aktif, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Koşullu Biçimlendirme Kuralları Yöneticisi")
        self.kitap, self.sayfa, self.secim, self.aktif = kitap, sayfa, list(secim), aktif
        self._liste: List[KosulluKural] = list(sayfa.kosullu)
        self.kapsam = QComboBox()
        self.kapsam.addItem("Geçerli Seçim", "secim")
        self.kapsam.addItem("Bu Sayfa", "sayfa")
        self.kapsam.setCurrentIndex(1 if not self._secimle_kesisen() else 0)
        self.kapsam.currentIndexChanged.connect(self._yenile)
        self.liste_kutusu = QListWidget()
        self.liste_kutusu.setMinimumSize(520, 220)
        yeni, duzenle, sil = QPushButton("Yeni Kural…"), QPushButton("Kuralı Düzenle…"), QPushButton("Kuralı Sil")
        yukari, asagi = QPushButton("▲"), QPushButton("▼")
        yeni.clicked.connect(lambda: self.yeni_kural())
        duzenle.clicked.connect(lambda: self.duzenle())
        sil.clicked.connect(self.sil)
        yukari.clicked.connect(lambda: self.tasi(-1))
        asagi.clicked.connect(lambda: self.tasi(1))
        yukari.setToolTip("Önceliği artır")
        asagi.setToolTip("Önceliği azalt")
        self.dur_kutusu = QCheckBox("Doğruysa durdur")
        self.dur_kutusu.toggled.connect(self._dur_degisti)
        ust = QHBoxLayout()
        ust.addWidget(QLabel("Biçimlendirme kurallarını göster:"))
        ust.addWidget(self.kapsam)
        ust.addStretch(1)
        dugmeler_satiri = QHBoxLayout()
        for d in (yeni, duzenle, sil, yukari, asagi):
            dugmeler_satiri.addWidget(d)
        dugmeler_satiri.addStretch(1)
        dugmeler_satiri.addWidget(self.dur_kutusu)
        alt = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        alt.button(QDialogButtonBox.Ok).setText("Tamam")
        alt.button(QDialogButtonBox.Cancel).setText("İptal")
        alt.accepted.connect(self.accept)
        alt.rejected.connect(self.reject)
        v = QVBoxLayout(self)
        v.addLayout(ust)
        v.addWidget(self.liste_kutusu)
        v.addLayout(dugmeler_satiri)
        v.addWidget(alt)
        self.liste_kutusu.currentRowChanged.connect(lambda _: self._dur_goster())
        self._yenile()

    # --- liste ---
    def _secimle_kesisen(self) -> bool:
        return any(not (a.son_satir < s.ilk_satir or a.ilk_satir > s.son_satir
                        or a.son_sutun < s.ilk_sutun or a.ilk_sutun > s.son_sutun)
                   for k in self._liste for a in k.araliklar for s in self.secim)

    def _gorunen_indeksler(self) -> List[int]:
        if self.kapsam.currentData() == "sayfa":
            return list(range(len(self._liste)))
        return [i for i, k in enumerate(self._liste)
                if any(not (a.son_satir < s.ilk_satir or a.ilk_satir > s.son_satir
                            or a.son_sutun < s.ilk_sutun or a.ilk_sutun > s.son_sutun)
                       for a in k.araliklar for s in self.secim)]

    def _yenile(self, secili: Optional[int] = None) -> None:
        self._idx = self._gorunen_indeksler()
        self.liste_kutusu.blockSignals(True)
        self.liste_kutusu.clear()
        for i in self._idx:
            k = self._liste[i]
            yer = ", ".join(aralik_yaz(a) for a in k.araliklar)
            ogr = QListWidgetItem(f"{kural_aciklamasi(k, self.kitap)}   |   {bicim_ozeti(k.bicim)}   |   {yer}"
                                  + ("   |   Durdur" if k.dur else ""))
            self.liste_kutusu.addItem(ogr)
        self.liste_kutusu.blockSignals(False)
        if self._idx:
            self.liste_kutusu.setCurrentRow(self._idx.index(secili) if secili in self._idx else 0)
        self._dur_goster()

    def _simdiki(self) -> Optional[int]:
        s = self.liste_kutusu.currentRow()
        return self._idx[s] if 0 <= s < len(self._idx) else None

    def _dur_goster(self) -> None:
        i = self._simdiki()
        self.dur_kutusu.blockSignals(True)
        self.dur_kutusu.setChecked(bool(i is not None and self._liste[i].dur))
        self.dur_kutusu.setEnabled(i is not None and self._liste[i].tur not in ("renk_olcegi", "veri_cubugu"))
        self.dur_kutusu.blockSignals(False)

    def _dur_degisti(self, v: bool) -> None:
        i = self._simdiki()
        if i is not None:
            self._liste[i] = replace(self._liste[i], dur=v)
            self._yenile(i)

    # --- eylemler ---
    def yeni_kural(self, sonuc: Optional[KosulluKural] = None) -> None:
        if sonuc is None:
            pen = KuralPenceresi(self.kitap, self)
            if pen.exec() != QDialog.Accepted:
                return
            sonuc = pen.kural()
        ar = tuple(self.secim)
        fr, fc = ar[0].ilk_satir - self.aktif[0], ar[0].ilk_sutun - self.aktif[1]
        if (fr, fc) != (0, 0):
            from ..formul.kaydir import kopyala
            kay = lambda f: kopyala(f, fr, fc) if f is not None and f.startswith("=") else f
            sonuc = replace(sonuc, formul1=kay(sonuc.formul1), formul2=kay(sonuc.formul2))
        self._liste.insert(0, replace(sonuc, araliklar=ar))
        self._yenile(0)

    def duzenle(self, sonuc: Optional[KosulluKural] = None) -> None:
        i = self._simdiki()
        if i is None:
            return
        if sonuc is None:
            pen = KuralPenceresi(self.kitap, self, kural=self._liste[i])
            if pen.exec() != QDialog.Accepted:
                return
            sonuc = pen.kural()
        self._liste[i] = replace(sonuc, araliklar=self._liste[i].araliklar)
        self._yenile(i)

    def sil(self) -> None:
        i = self._simdiki()
        if i is not None:
            del self._liste[i]
            self._yenile()

    def tasi(self, yon: int) -> None:
        i = self._simdiki()
        if i is None:
            return
        j = i + yon
        if 0 <= j < len(self._liste):
            self._liste[i], self._liste[j] = self._liste[j], self._liste[i]
            self._yenile(j)

    def liste(self) -> List[KosulluKural]:
        return list(self._liste)
