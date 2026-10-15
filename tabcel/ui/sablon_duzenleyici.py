"""Şablon Düzenleyici (Faz 11): kullanıcı kendi şablonunu (sorular, modüller, sütunlar, kurallar, ayarlar) liste tabanlı yazar.
Mantık/doğrulama/kayıt `sablon/duzenleme.py`da (Qt yok); burada yalnız arayüz. Doğrulama Faz 10a'nın doğrulayıcısıdır: her değişiklikte
(gecikmeli) çalışır, hatalar altta listelenir; **Kaydet** hata ya da Tablo Sağlık Kontrolü sorunu varken engellenir (kural 22).
Ham JSON ("İleri" sekmesi) aynı taslağı doğrudan düzenler."""
import copy
import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ..sablon import duzenleme, sema
from . import theme

TURLER = list(sema.TURLER)
SIDDETLER = list(sema.SIDDETLER)
HATA_RENGI = "#c00000"


class Kolon:
    """Tablo sütun tanımı: `yol` taslak sözlüğündeki anahtar (iç içe için demet), `tip`: metin | bool | sayi | secim | liste | baglanti."""

    def __init__(self, yol, baslik: str, tip: str = "metin", secenekler=None, genislik: int = 110, ipucu: str = ""):
        self.yol = (yol,) if isinstance(yol, str) else tuple(yol)
        self.baslik, self.tip, self.secenekler, self.genislik, self.ipucu = baslik, tip, secenekler or [], genislik, ipucu


def _al(d: dict, yol):
    for k in yol:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def _koy(d: dict, yol, deger) -> None:
    """`deger` boşsa (None/""/[]/False/{}) anahtar silinir; iç içe kabın boşalması kabı da siler."""
    bos = deger is None or deger is False or (isinstance(deger, (str, list, dict)) and len(deger) == 0)
    zincir = [d]
    for k in yol[:-1]:
        if not isinstance(zincir[-1].get(k), dict):
            if bos:
                return
            zincir[-1][k] = {}
        zincir.append(zincir[-1][k])
    if bos:
        zincir[-1].pop(yol[-1], None)
        for i in range(len(yol) - 1, 0, -1):
            if not zincir[i]:
                zincir[i - 1].pop(yol[i - 1], None)
    else:
        zincir[-1][yol[-1]] = deger


class SozlukTablosu(QWidget):
    """Sözlük listesini (ör. sütunlar) tablo olarak düzenler; her hücre değişikliği doğrudan sözlüğe yazılır. Satır ekle/sil/taşı düğmeleri."""
    degisti = Signal()

    def __init__(self, kolonlar: List[Kolon], yeni_satir: Callable[[], dict], en_cok: Optional[int] = None):
        super().__init__()
        self.kolonlar, self._yeni, self.en_cok = kolonlar, yeni_satir, en_cok
        self.veri: List[dict] = []
        self._doluyor = False
        d = QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        self.tablo = QTableWidget(0, len(kolonlar))
        self.tablo.setHorizontalHeaderLabels([k.baslik for k in kolonlar])
        self.tablo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        for i, k in enumerate(kolonlar):
            self.tablo.setColumnWidth(i, k.genislik)
            if k.ipucu:
                self.tablo.horizontalHeaderItem(i).setToolTip(k.ipucu)
        self.tablo.itemChanged.connect(self._oge_degisti)
        d.addWidget(self.tablo, 1)
        s = QHBoxLayout()
        self.ekle_dugme, self.sil_dugme = QPushButton("Ekle"), QPushButton("Sil")
        self.yukari_dugme, self.asagi_dugme = QPushButton("Yukarı"), QPushButton("Aşağı")
        for b in (self.ekle_dugme, self.sil_dugme, self.yukari_dugme, self.asagi_dugme):
            b.setAutoDefault(False)
            s.addWidget(b)
        s.addStretch(1)
        d.addLayout(s)
        self.ekle_dugme.clicked.connect(self.satir_ekle)
        self.sil_dugme.clicked.connect(self.satir_sil)
        self.yukari_dugme.clicked.connect(lambda: self.tasi(-1))
        self.asagi_dugme.clicked.connect(lambda: self.tasi(1))

    # --- veri bağlama
    def yukle(self, veri: List[dict]) -> None:
        self.veri = veri
        self.yenile()

    def yenile(self, secili: Optional[int] = None) -> None:
        self._doluyor = True
        self.tablo.setRowCount(len(self.veri))
        for r, d in enumerate(self.veri):
            for c, k in enumerate(self.kolonlar):
                self._hucre_kur(r, c, k, _al(d, k.yol))
        self._doluyor = False
        if secili is not None and 0 <= secili < len(self.veri):
            self.tablo.selectRow(secili)
        self.ekle_dugme.setEnabled(self.en_cok is None or len(self.veri) < self.en_cok)

    def _hucre_kur(self, r: int, c: int, k: Kolon, v: Any) -> None:
        if k.tip == "bool":
            o = QTableWidgetItem()
            o.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            o.setCheckState(Qt.Checked if v else Qt.Unchecked)
            self.tablo.setItem(r, c, o)
        elif k.tip == "secim":
            kutu = QComboBox()
            kutu.addItems(k.secenekler)
            if v in k.secenekler:
                kutu.setCurrentText(v)
            elif v is not None:
                kutu.addItem(str(v))
                kutu.setCurrentText(str(v))
            kutu.currentTextChanged.connect(lambda t, r_=r, c_=c: self._yaz(r_, c_, t))
            self.tablo.setCellWidget(r, c, kutu)
            self.tablo.setItem(r, c, QTableWidgetItem(""))
            self.tablo.item(r, c).setFlags(Qt.ItemIsEnabled)
        else:
            if k.tip == "liste":
                metin = ", ".join(str(x) for x in v) if isinstance(v, list) else ""
            elif k.tip == "baglanti":
                metin = f"{v.get('modul', '')}.{v.get('alan', '')}" if isinstance(v, dict) else ""
            elif v is None:
                metin = ""
            else:
                metin = str(v)
            self.tablo.setItem(r, c, QTableWidgetItem(metin))

    def _oge_degisti(self, oge: QTableWidgetItem) -> None:
        if self._doluyor:
            return
        k = self.kolonlar[oge.column()]
        if k.tip == "bool":
            self._yaz(oge.row(), oge.column(), oge.checkState() == Qt.Checked)
        elif k.tip != "secim":
            self._yaz(oge.row(), oge.column(), oge.text())

    def _yaz(self, r: int, c: int, ham) -> None:
        if self._doluyor or r >= len(self.veri):
            return
        k = self.kolonlar[c]
        if k.tip == "bool":
            v = bool(ham)
        elif k.tip == "sayi":
            m = str(ham).strip().replace(",", ".")
            try:
                v = None if not m else (int(float(m)) if float(m) == int(float(m)) else float(m))
            except ValueError:
                v = m                                                    # sayı değil: doğrulayıcı "sayı olmalı" der
        elif k.tip == "liste":
            v = [p.strip() for p in str(ham).replace(";", ",").split(",") if p.strip()]
        elif k.tip == "baglanti":
            modul, _, alan = str(ham).strip().partition(".")
            v = {"modul": modul.strip(), "alan": alan.strip()} if modul.strip() else None
        else:
            v = str(ham).strip() if k.tip == "metin" else ham
        _koy(self.veri[r], k.yol, v)
        self.degisti.emit()

    # --- satır işlemleri
    def secili_satir(self) -> int:
        s = self.tablo.currentRow()
        return s if 0 <= s < len(self.veri) else -1

    def satir_ekle(self) -> None:
        if self.en_cok is not None and len(self.veri) >= self.en_cok:
            return
        self.veri.append(self._yeni())
        self.yenile(len(self.veri) - 1)
        self.degisti.emit()

    def satir_sil(self) -> None:
        s = self.secili_satir()
        if s < 0:
            return
        del self.veri[s]
        self.yenile(min(s, len(self.veri) - 1))
        self.degisti.emit()

    def tasi(self, yon: int) -> None:
        s = self.secili_satir()
        t = s + yon
        if s < 0 or not 0 <= t < len(self.veri):
            return
        self.veri[s], self.veri[t] = self.veri[t], self.veri[s]
        self.yenile(t)
        self.degisti.emit()


class DuzenleyiciPenceresi(QDialog):
    """Şablon Düzenleyici penceresi. `taslak` yerinde düzenlenir; `kaydet()` kullanıcı klasörüne yazar."""
    kaydedildi = Signal(list)

    def __init__(self, taslak: duzenleme.Taslak, klasor=None, ust=None, uzerine_yaz: bool = False):
        super().__init__(ust)
        self.taslak, self.klasor, self.uzerine_yaz = taslak, klasor, uzerine_yaz
        self.setWindowTitle(f"Şablon Düzenleyici — {taslak.akis.get('ad', '')}")
        self.setMinimumSize(900, 640)
        self.yazilan: List[Any] = []
        self._modul: Optional[str] = None
        self._zamanlayici = QTimer(self)
        self._zamanlayici.setSingleShot(True)
        self._zamanlayici.setInterval(350)
        self._zamanlayici.timeout.connect(self.dogrulama_yenile)
        self._kur()
        self.tablolari_yukle()
        self.dogrulama_yenile()

    # ------------------------------------------------------------------ kurulum
    def _kur(self) -> None:
        d = QVBoxLayout(self)
        self.sekmeler = QTabWidget()
        d.addWidget(self.sekmeler, 1)
        self.sekmeler.addTab(self._genel_sekmesi(), "Genel")
        self.sorular = SozlukTablosu(
            [Kolon("kimlik", "Kimlik", ipucu="küçük harf/rakam/_ ; ör. depo"), Kolon("metin", "Soru metni", genislik=300),
             Kolon("varsayilan", "Varsayılan evet", "bool", genislik=100), Kolon("emin_degilim", "“Emin değilim” olabilir", "bool", genislik=140),
             Kolon("eger", "Koşul (bayrak)", ipucu="boş = her zaman sorulur; !x = x hayırsa"), Kolon("aciklama", "Açıklama", genislik=200)],
            lambda: {"kimlik": f"soru{len(self.taslak.akis.setdefault('sorular', [])) + 1}", "metin": "Yeni soru?", "tur": "evet_hayir",
                     "varsayilan": False}, sema.EN_COK_SORU)
        self.sekmeler.addTab(self.sorular, "Sorular")
        self.sekmeler.addTab(self._moduller_sekmesi(), "Modüller")
        self.ayarlar = SozlukTablosu(
            [Kolon("kimlik", "Kimlik"), Kolon("ad", "Ad", genislik=180), Kolon("tur", "Tür", "secim", list(sema.AYAR_TURLERI), 100),
             Kolon("varsayilan", "Varsayılan"), Kolon("aciklama", "Açıklama", genislik=240), Kolon("eger", "Koşul (bayrak)")],
            lambda: {"kimlik": f"ayar{len(self.taslak.akis.setdefault('ayarlar', [])) + 1}", "ad": "Yeni ayar", "tur": "tam_sayi", "varsayilan": 0})
        self.sekmeler.addTab(self.ayarlar, "Ayarlar")
        self.nasil = SozlukTablosu([Kolon("baslik", "Başlık", genislik=200), Kolon("metin", "Metin", genislik=520)],
                                   lambda: {"baslik": "Yeni başlık", "metin": "Açıklama metni."})
        self.sekmeler.addTab(self.nasil, "Nasıl kullanılır")
        self.sekmeler.addTab(self._json_sekmesi(), "İleri (JSON)")
        for t in (self.sorular, self.ayarlar, self.nasil):
            t.degisti.connect(self.degisti)
        self.rapor = QPlainTextEdit()
        self.rapor.setReadOnly(True)
        self.rapor.setMaximumHeight(120)
        d.addWidget(self.rapor)
        alt = QHBoxLayout()
        self.onizle_dugme = QPushButton("Denetle (Tablo Sağlığı)")
        self.onizle_dugme.setToolTip("Şablonu tüm cevap kombinasyonlarında üretir ve Tablo Sağlık Kontrolü'nden geçirir")
        self.kaydet_dugme = QPushButton("Kaydet")
        kapat = QPushButton("Kapat")
        for b in (self.onizle_dugme, self.kaydet_dugme, kapat):
            b.setAutoDefault(False)
        self.onizle_dugme.clicked.connect(lambda: self.denetle())
        self.kaydet_dugme.clicked.connect(lambda: self.kaydet())
        kapat.clicked.connect(self.close)
        alt.addWidget(self.onizle_dugme)
        alt.addStretch(1)
        alt.addWidget(self.kaydet_dugme)
        alt.addWidget(kapat)
        d.addLayout(alt)

    def _genel_sekmesi(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        self.ad_kutusu, self.kategori_kutusu, self.aciklama_kutusu = QLineEdit(), QComboBox(), QLineEdit()
        self.kategori_kutusu.setEditable(True)
        self.kategori_kutusu.addItems(["Ticaret", "Finans", "Yönetim", "Eğitim", "Diğer"])
        self.kokler_kutusu, self.es_kutusu = QLineEdit(), QLineEdit()
        self.kokler_kutusu.setToolTip("Sihirbaz bu kelimelerle şablonu bulur (ekler önemsiz: stok → stoklarımı, stoğu)")
        self.ornek_kutusu = QCheckBox("Örnek veriyle başla (modüllerdeki ornek_veri kullanılır)")
        self.kimlik_etiketi = QLabel("")
        f.addRow("Şablon adı", self.ad_kutusu)
        f.addRow("Kimlik", self.kimlik_etiketi)
        f.addRow("Kategori", self.kategori_kutusu)
        f.addRow("Açıklama", self.aciklama_kutusu)
        f.addRow("Anahtar kelime kökleri", self.kokler_kutusu)
        f.addRow("Eş anlamlılar", self.es_kutusu)
        f.addRow("", self.ornek_kutusu)
        for k in (self.ad_kutusu, self.aciklama_kutusu, self.kokler_kutusu, self.es_kutusu):
            k.textChanged.connect(self._genel_yaz)
        self.kategori_kutusu.currentTextChanged.connect(self._genel_yaz)
        self.ornek_kutusu.toggled.connect(self._genel_yaz)
        return w

    def _moduller_sekmesi(self) -> QWidget:
        bol = QSplitter()
        sol = QWidget()
        s = QVBoxLayout(sol)
        s.setContentsMargins(0, 0, 0, 0)
        s.addWidget(QLabel("Modüller (her biri bir sayfa)"))
        self.modul_listesi = QListWidget()
        self.modul_listesi.currentRowChanged.connect(self._modul_secildi)
        s.addWidget(self.modul_listesi, 1)
        self.modul_ekle_dugme, self.modul_sil_dugme, self.modul_ad_dugme = (QPushButton("Modül ekle"), QPushButton("Sil"),
                                                                           QPushButton("Kimliği değiştir…"))
        for b in (self.modul_ekle_dugme, self.modul_sil_dugme, self.modul_ad_dugme):
            b.setAutoDefault(False)
            s.addWidget(b)
        self.modul_ekle_dugme.clicked.connect(self.modul_ekle)
        self.modul_sil_dugme.clicked.connect(self.modul_sil)
        self.modul_ad_dugme.clicked.connect(self.modul_kimligi_degistir)
        bol.addWidget(sol)
        sag = QTabWidget()
        self.modul_bilgi = self._modul_bilgi_sekmesi()
        sag.addTab(self.modul_bilgi, "Modül")
        self.sutunlar = SozlukTablosu(
            [Kolon("kimlik", "Kimlik", genislik=100), Kolon("ad", "Başlık", genislik=130),
             Kolon("tur", "Tür", "secim", TURLER, 110), Kolon("zorunlu", "Zorunlu", "bool", genislik=60),
             Kolon("benzersiz", "Benzersiz", "bool", genislik=70), Kolon(("kisit", "min"), "En az", "sayi", genislik=55),
             Kolon(("kisit", "max"), "En çok", "sayi", genislik=55), Kolon(("kisit", "uzunluk"), "Uzunluk", "sayi", genislik=60),
             Kolon("secenekler", "Seçenekler (virgülle)", "liste", genislik=130, ipucu="yalnız “liste” türü"),
             Kolon("baglanti", "Bağlantı (modül.alan)", "baglanti", genislik=130, ipucu="yalnız “baglanti” türü: ör. urunler.urun_kodu"),
             Kolon("formul", "Formül", genislik=200, ipucu='yalnız “hesaplanan”: ör. =[@miktar]*[@fiyat]'),
             Kolon("bicim", "Sonuç biçimi", "secim", [""] + list(sema.BICIMLER), 90), Kolon("eger", "Koşul (bayrak)", genislik=90),
             Kolon("barkod", "Barkod", "bool", genislik=55), Kolon("aciklama", "Açıklama", genislik=200)],
            lambda: {"kimlik": f"sutun{len(self._modul_ham().setdefault('sutunlar', [])) + 1}", "ad": "Yeni sütun", "tur": "metin"})
        sag.addTab(self.sutunlar, "Sütunlar")
        self.kurallar = SozlukTablosu(
            [Kolon("kimlik", "Kimlik", genislik=110), Kolon("ad", "Ad", genislik=140), Kolon("formul", "Formül (DOĞRU = geçerli)", genislik=260),
             Kolon("ne_zaman", "Ne zaman", genislik=120, ipucu="ör. hareket_turu=Çıkış"), Kolon("ileti", "İleti", genislik=220),
             Kolon("siddet", "Şiddet", "secim", SIDDETLER, 80)],
            lambda: {"kimlik": f"kural{len(self._modul_ham().setdefault('kurallar', [])) + 1}", "ad": "Yeni kural",
                     "formul": "=TRUE", "ileti": "Bu kayıt geçerli değil.", "siddet": "durdur"})
        sag.addTab(self.kurallar, "Kurallar")
        for t in (self.sutunlar, self.kurallar):
            t.degisti.connect(self.degisti)
        bol.addWidget(sag)
        bol.setStretchFactor(1, 4)
        return bol

    def _modul_bilgi_sekmesi(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        self.m_ad, self.m_tekil, self.m_sayfa, self.m_aciklama, self.m_gorunen = (QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit(),
                                                                                  QLineEdit())
        self.m_matris_satir, self.m_matris_sutun, self.m_matris_deger = QLineEdit(), QLineEdit(), QLineEdit()
        self.m_eger = QLineEdit()
        self.m_eger.setToolTip("Akışta bu modülün yalnız belli cevapta üretilmesi için bayrak; boş = her zaman")
        self.m_gorunen.setToolTip("Başka modülde seçim listesinde gösterilecek sütun kimlikleri (virgülle)")
        f.addRow("Ad", self.m_ad)
        f.addRow("Tekil ad", self.m_tekil)
        f.addRow("Sayfa adı", self.m_sayfa)
        f.addRow("Açıklama", self.m_aciklama)
        f.addRow("Görünen sütunlar", self.m_gorunen)
        f.addRow("Akışta koşul (bayrak)", self.m_eger)
        f.addRow("Matris: satır sütunu", self.m_matris_satir)
        f.addRow("Matris: sütun sütunu", self.m_matris_sutun)
        f.addRow("Matris: değer sütunu", self.m_matris_deger)
        for k in (self.m_ad, self.m_tekil, self.m_sayfa, self.m_aciklama, self.m_gorunen, self.m_eger,
                  self.m_matris_satir, self.m_matris_sutun, self.m_matris_deger):
            k.textChanged.connect(self._modul_bilgi_yaz)
        return w

    def _json_sekmesi(self) -> QWidget:
        w = QWidget()
        d = QVBoxLayout(w)
        d.addWidget(QLabel("Ham tanım (ileri düzey). Akış ya da seçili modül; “Uygula” doğrulayarak taslağa yazar."))
        s = QHBoxLayout()
        self.json_hedef = QComboBox()
        self.json_hedef.currentIndexChanged.connect(self.json_yukle)
        self.json_uygula_dugme = QPushButton("Uygula")
        self.json_uygula_dugme.setAutoDefault(False)
        self.json_uygula_dugme.clicked.connect(lambda: self.json_uygula())
        s.addWidget(self.json_hedef, 1)
        s.addWidget(self.json_uygula_dugme)
        d.addLayout(s)
        self.json_metin = QPlainTextEdit()
        d.addWidget(self.json_metin, 1)
        self.json_iletisi = QLabel("")
        self.json_iletisi.setStyleSheet(f"color: {HATA_RENGI};")
        d.addWidget(self.json_iletisi)
        return w

    # ------------------------------------------------------------------ taslak ↔ arayüz
    def _modul_ham(self) -> dict:
        return self.taslak.moduller[self._modul] if self._modul in self.taslak.moduller else {}

    def tablolari_yukle(self) -> None:
        a = self.taslak.akis
        self._genel_yukleniyor = True
        self.ad_kutusu.setText(a.get("ad", ""))
        self.kimlik_etiketi.setText(a.get("kimlik", ""))
        self.kategori_kutusu.setCurrentText(a.get("kategori", "Diğer"))
        self.aciklama_kutusu.setText(a.get("aciklama", ""))
        ak = a.get("anahtar_kelimeler", {}) if isinstance(a.get("anahtar_kelimeler"), dict) else {}
        self.kokler_kutusu.setText(", ".join(ak.get("kokler", [])))
        self.es_kutusu.setText(", ".join(ak.get("es_anlamlilar", [])))
        self.ornek_kutusu.setChecked(bool(a.get("ornek_veri")))
        self._genel_yukleniyor = False
        self.sorular.yukle(a.setdefault("sorular", []))
        self.ayarlar.yukle(a.setdefault("ayarlar", []))
        self.nasil.yukle(a.setdefault("nasil_kullanilir", []))
        self.modul_listesini_yenile()
        self.json_hedef_yenile()

    def modul_listesini_yenile(self, sec: Optional[str] = None) -> None:
        self.modul_listesi.blockSignals(True)
        self.modul_listesi.clear()
        kimlikler = self.taslak.modul_kimlikleri()
        for k in kimlikler:
            m = self.taslak.moduller.get(k, {})
            self.modul_listesi.addItem(f"{m.get('ad', k)}  ({k})")
        self.modul_listesi.blockSignals(False)
        hedef = sec if sec in kimlikler else (self._modul if self._modul in kimlikler else (kimlikler[0] if kimlikler else None))
        if hedef is not None:
            self.modul_listesi.setCurrentRow(kimlikler.index(hedef))
        self._modul_secildi(self.modul_listesi.currentRow())

    def _modul_secildi(self, satir: int) -> None:
        kimlikler = self.taslak.modul_kimlikleri()
        self._modul = kimlikler[satir] if 0 <= satir < len(kimlikler) else None
        m = self._modul_ham()
        self._modul_yukleniyor = True
        self.m_ad.setText(m.get("ad", ""))
        self.m_tekil.setText(m.get("tekil_ad", ""))
        self.m_sayfa.setText(m.get("sayfa_adi", ""))
        self.m_aciklama.setText(m.get("aciklama", ""))
        self.m_gorunen.setText(", ".join(m.get("gorunen", [])))
        ma = m.get("matris") or {}
        self.m_matris_satir.setText(ma.get("satir", ""))
        self.m_matris_sutun.setText(ma.get("sutun", ""))
        self.m_matris_deger.setText(ma.get("deger", ""))
        eg = next((x.get("eger") for x in self.taslak.akis.get("moduller", []) if x.get("modul") == self._modul), None)
        self.m_eger.setText(eg or "")
        self._modul_yukleniyor = False
        self.sutunlar.yukle(m.setdefault("sutunlar", []) if m else [])
        self.kurallar.yukle(m.setdefault("kurallar", []) if m else [])
        self.sutunlar.setEnabled(bool(m))
        self.kurallar.setEnabled(bool(m))

    def _genel_yaz(self, *_a) -> None:
        if getattr(self, "_genel_yukleniyor", True):
            return
        a = self.taslak.akis
        _koy(a, ("ad",), self.ad_kutusu.text().strip())
        _koy(a, ("kategori",), self.kategori_kutusu.currentText().strip())
        _koy(a, ("aciklama",), self.aciklama_kutusu.text().strip())
        a.setdefault("anahtar_kelimeler", {})
        ak = a["anahtar_kelimeler"]
        ak["kokler"] = [p.strip() for p in self.kokler_kutusu.text().replace(";", ",").split(",") if p.strip()]
        ak["es_anlamlilar"] = [p.strip() for p in self.es_kutusu.text().replace(";", ",").split(",") if p.strip()]
        ak.setdefault("agirlik", 1.0)
        a["ornek_veri"] = self.ornek_kutusu.isChecked()
        self.setWindowTitle(f"Şablon Düzenleyici — {a.get('ad', '')}")
        self.degisti()

    def _modul_bilgi_yaz(self, *_a) -> None:
        if getattr(self, "_modul_yukleniyor", True) or self._modul not in self.taslak.moduller:
            return
        m = self.taslak.moduller[self._modul]
        for anahtar, kutu in (("ad", self.m_ad), ("tekil_ad", self.m_tekil), ("sayfa_adi", self.m_sayfa), ("aciklama", self.m_aciklama)):
            m[anahtar] = kutu.text().strip()
        g = [p.strip() for p in self.m_gorunen.text().replace(";", ",").split(",") if p.strip()]
        _koy(m, ("gorunen",), g)
        ma = {k: v.text().strip() for k, v in (("satir", self.m_matris_satir), ("sutun", self.m_matris_sutun), ("deger", self.m_matris_deger))}
        _koy(m, ("matris",), ma if any(ma.values()) else None)
        for x in self.taslak.akis.get("moduller", []):
            if x.get("modul") == self._modul:
                _koy(x, ("eger",), self.m_eger.text().strip())
        self.degisti()

    # ------------------------------------------------------------------ modül işlemleri
    def modul_ekle(self, ad: Optional[str] = None) -> str:
        ad = ad or "Yeni modül"
        mk = duzenleme.kimlik_uret(ad, self.taslak.moduller)
        self.taslak.moduller[mk] = {"surum": 1, "tur": "modul", "kimlik": mk, "ad": ad, "tekil_ad": "Kayıt",
                                    "aciklama": f"{ad} kayıtları.", "sayfa_adi": ad[:31], "gorunen": ["ad"],
                                    "sutunlar": [{"kimlik": "ad", "ad": "Ad", "tur": "metin", "zorunlu": True}]}
        self.taslak.akis.setdefault("moduller", []).append({"modul": mk})
        self.modul_listesini_yenile(mk)
        self.json_hedef_yenile()
        self.degisti()
        return mk

    def modul_sil(self) -> bool:
        if self._modul is None:
            return False
        mk = self._modul
        self.taslak.moduller.pop(mk, None)
        self.taslak.akis["moduller"] = [x for x in self.taslak.akis.get("moduller", []) if x.get("modul") != mk]
        self._modul = None
        self.modul_listesini_yenile()
        self.json_hedef_yenile()
        self.degisti()
        return True

    def modul_kimligi_degistir(self, yeni: Optional[str] = None) -> bool:
        """Seçili modülün kimliğini değiştirir; bağlantılar ve formül yer tutucuları da güncellenir."""
        if self._modul is None:
            return False
        if yeni is None:
            from PySide6.QtWidgets import QInputDialog
            yeni, ok = QInputDialog.getText(self, "Modül kimliği", "Yeni kimlik (küçük harf, rakam, _):", text=self._modul)
            if not ok:
                return False
        yeni = yeni.strip()
        if not sema.KIMLIK_RE.match(yeni) or yeni in self.taslak.moduller:
            QMessageBox.warning(self, "Şablon Düzenleyici", "Geçersiz ya da kullanılan kimlik.")
            return False
        duzenleme.modul_yeniden_adlandir(self.taslak, self._modul, yeni)
        self.modul_listesini_yenile(yeni)
        self.json_hedef_yenile()
        self.degisti()
        return True

    # ------------------------------------------------------------------ JSON sekmesi
    def json_hedef_yenile(self) -> None:
        self.json_hedef.blockSignals(True)
        self.json_hedef.clear()
        self.json_hedef.addItem("Akış", None)
        for k in self.taslak.modul_kimlikleri():
            self.json_hedef.addItem(f"Modül: {k}", k)
        self.json_hedef.blockSignals(False)
        self.json_yukle()

    def json_yukle(self, *_a) -> None:
        hedef = self.json_hedef.currentData()
        ham = self.taslak.akis if hedef is None else self.taslak.moduller.get(hedef, {})
        self.json_metin.setPlainText(json.dumps(ham, ensure_ascii=False, indent=2))
        self.json_iletisi.setText("")

    def json_uygula(self) -> bool:
        hedef = self.json_hedef.currentData()
        try:
            d = json.loads(self.json_metin.toPlainText())
        except ValueError as e:
            self.json_iletisi.setText(f"JSON bozuk: {e}")
            return False
        if not isinstance(d, dict):
            self.json_iletisi.setText("En dışta nesne ({…}) olmalı.")
            return False
        if hedef is None:
            self.taslak.akis = d
        else:
            if d.get("kimlik") != hedef:
                self.json_iletisi.setText("Kimlik buradan değiştirilemez (Modüller sekmesinde “Kimliği değiştir”).")
                return False
            self.taslak.moduller[hedef] = d
        self.tablolari_yukle()
        self.degisti()
        return True

    # ------------------------------------------------------------------ doğrulama / kayıt
    def degisti(self) -> None:
        self._zamanlayici.start()

    def dogrulama_yenile(self) -> List[sema.Hata]:
        hatalar = duzenleme.dogrula(self.taslak)
        if not hatalar:
            self.rapor.setPlainText("Tanım geçerli. “Denetle” ile Tablo Sağlık Kontrolü'nü çalıştırabilir, “Kaydet” ile kaydedebilirsiniz.")
            self.rapor.setStyleSheet(f"color: {theme.ACCENT};")
        else:
            self.rapor.setPlainText("\n".join(("⚠ " if h.uyari else "✖ ") + str(h) for h in hatalar))
            self.rapor.setStyleSheet(f"color: {HATA_RENGI};" if duzenleme.ciddi_mi(hatalar) else f"color: {theme.UYARI};")
        self.kaydet_dugme.setEnabled(not duzenleme.ciddi_mi(hatalar))
        return hatalar

    def denetle(self) -> List[str]:
        """Şablonu üretip Tablo Sağlık Kontrolü'nden geçirir (kural 22); sorun varsa raporda gösterir."""
        h = self.dogrulama_yenile()
        if duzenleme.ciddi_mi(h):
            return ["Tanım hatalı."]
        sorunlar = duzenleme.uretim_denetimi(self.taslak)
        if sorunlar:
            self.rapor.setPlainText("Tablo Sağlık Kontrolü sorun buldu:\n" + "\n".join(sorunlar[:12]))
            self.rapor.setStyleSheet(f"color: {HATA_RENGI};")
        else:
            self.rapor.setPlainText("Tablo Sağlık Kontrolü temiz: tüm cevap kombinasyonlarında 0 bulgu.")
            self.rapor.setStyleSheet(f"color: {theme.ACCENT};")
        return sorunlar

    def kaydet(self) -> bool:
        try:
            yollar = duzenleme.kaydet(self.taslak, self.klasor, uzerine_yaz=self.uzerine_yaz)
        except duzenleme.KayitHatasi as e:
            self.rapor.setPlainText(str(e))
            self.rapor.setStyleSheet(f"color: {HATA_RENGI};")
            return False
        self.yazilan = yollar
        self.uzerine_yaz = True                                   # bu pencerede sonraki kayıt aynı şablonu günceller
        self.rapor.setPlainText("Kaydedildi: " + ", ".join(p.name for p in yollar))
        self.rapor.setStyleSheet(f"color: {theme.ACCENT};")
        self.kaydedildi.emit(yollar)
        return True


class KitaptanSablonPenceresi(QDialog):
    """Dosya ▸ Kitaptan Şablon Oluştur…: açık kitaptaki sayfaları seç → ad ver → taslak üretilir → Şablon Düzenleyici'de gözden geçirilip kaydedilir."""

    def __init__(self, kitap, ust=None, kullanilan_akis_kimlikleri=()):
        super().__init__(ust)
        self.kitap, self._kullanilan = kitap, set(kullanilan_akis_kimlikleri)
        self.setWindowTitle("Kitaptan Şablon Oluştur")
        self.setMinimumWidth(460)
        self.sonuc = None
        d = QVBoxLayout(self)
        d.addWidget(QLabel("Şablona dönüştürülecek sayfaları seçin (her sayfanın ilk satırı başlık olmalı). Sütun türleri verilerden tahmin edilir; "
                           "sonra düzenleyicide değiştirebilirsiniz."))
        self.liste = QListWidget()
        self.liste.setSelectionMode(QAbstractItemView.MultiSelection)
        for sayfa in kitap.sayfalar:
            self.liste.addItem(sayfa.ad)
        if self.liste.count():
            self.liste.item(0).setSelected(True)
        d.addWidget(self.liste, 1)
        f = QFormLayout()
        self.ad_kutusu = QLineEdit(getattr(kitap.sayfalar[0], "ad", "Şablonum") if kitap.sayfalar else "Şablonum")
        self.ornek_kutusu = QCheckBox("Verilerden örnek satırlar ekle (en çok 20)")
        f.addRow("Şablon adı", self.ad_kutusu)
        f.addRow("", self.ornek_kutusu)
        d.addLayout(f)
        self.ileti = QLabel("")
        self.ileti.setWordWrap(True)
        self.ileti.setStyleSheet(f"color: {HATA_RENGI};")
        d.addWidget(self.ileti)
        alt = QHBoxLayout()
        alt.addStretch(1)
        self.tamam = QPushButton("Düzenleyicide aç")
        iptal = QPushButton("İptal")
        for b in (self.tamam, iptal):
            b.setAutoDefault(False)
        self.tamam.clicked.connect(lambda: self.olustur())
        iptal.clicked.connect(self.reject)
        alt.addWidget(self.tamam)
        alt.addWidget(iptal)
        d.addLayout(alt)

    def secili_sayfalar(self):
        adlar = {i.text() for i in self.liste.selectedItems()}
        return [s for s in self.kitap.sayfalar if s.ad in adlar]

    def olustur(self) -> bool:
        ad = self.ad_kutusu.text().strip()
        if not ad:
            self.ileti.setText("Şablon adı yazın.")
            return False
        sayfalar = self.secili_sayfalar()
        if not sayfalar:
            self.ileti.setText("En az bir sayfa seçin.")
            return False
        try:
            self.sonuc = duzenleme.kitaptan_taslak(self.kitap, sayfalar, ad, self.ornek_kutusu.isChecked(),
                                                   kullanilan_akis_kimlikleri=self._kullanilan)
        except duzenleme.KayitHatasi as e:
            self.ileti.setText(str(e))
            return False
        self.accept()
        return True
