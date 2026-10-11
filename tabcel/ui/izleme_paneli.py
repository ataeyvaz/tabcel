"""Hesap İzleme paneli (Faz 9b): seçili hücrenin değeri nereden geliyor / nerelerde kullanılıyor. Mantık `formul/izleme.py`da;
burası tembel ağaç görünümü. Panel yerleştirilebilir (dock), açılıp kapatılabilir; salt okunurdur (hücre değiştirmez)."""
from typing import Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QDockWidget, QLabel, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..formul.izleme import Dugum, Izleme
from . import theme

ROL_DUGUM = Qt.UserRole
ROL_YOL = Qt.UserRole + 1
ROL_DURUM = Qt.UserRole + 2                 # "tembel" (çocukları henüz yüklenmedi) | "daha" (sayfalama düğmesi) | "yuklu"
HATA_RENGI = QColor("#c00000")
DONGU_RENGI = QColor("#b45309")
KAYNAK_RENGI = QColor("#fde8e8")


class IzlemePaneli(QDockWidget):
    hucreyeGit = Signal(object, int, int)           # sayfa, satır, sütun (ızgarada o hücreye git + vurgula)

    def __init__(self, pencere):
        super().__init__("Hesap İzleme", pencere)
        self.setObjectName("izlemePaneli")
        self.pencere = pencere
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        govde = QWidget()
        d = QVBoxLayout(govde)
        d.setContentsMargins(6, 6, 6, 6)
        self.baslik = QLabel("Bir hücre seçin")
        self.baslik.setWordWrap(True)
        self.baslik.setTextFormat(Qt.PlainText)
        f = self.baslik.font()
        f.setBold(True)
        self.baslik.setFont(f)
        self.hata_etiketi = QLabel("")
        self.hata_etiketi.setWordWrap(True)
        self.hata_etiketi.setStyleSheet(f"color: {HATA_RENGI.name()};")
        self.hata_etiketi.hide()
        d.addWidget(self.baslik)
        d.addWidget(self.hata_etiketi)
        self.sekmeler = QTabWidget()
        self.agac = self._agac_yap()
        self.ters = self._agac_yap()
        self.sekmeler.addTab(self.agac, "Nereden geliyor?")
        self.sekmeler.addTab(self.ters, "Nerelerde kullanılıyor?")
        d.addWidget(self.sekmeler, 1)
        self.durum = QLabel("")
        self.durum.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        d.addWidget(self.durum)
        self.setWidget(govde)
        self.izleme: Optional[Izleme] = None
        self._bekleyen_ozetler = []                  # tembel aralık özeti bekleyen ağaç öğeleri
        self._git_yapiyor = False                   # panelin kendi gezintisi kökü değiştirmesin
        self._yeniden_kur = True
        self._zamanlayici = QTimer(self)
        self._zamanlayici.setSingleShot(True)
        self._zamanlayici.setInterval(120)
        self._zamanlayici.timeout.connect(self._calis)
        self.agac.itemExpanded.connect(self._ac)
        self.ters.itemExpanded.connect(self._ac)
        self.agac.itemClicked.connect(self._tikla)
        self.ters.itemClicked.connect(self._tikla)
        self.visibilityChanged.connect(lambda v: v and self.hucre_degisti())

    def _agac_yap(self) -> QTreeWidget:
        a = QTreeWidget()
        a.setColumnCount(3)
        a.setHeaderLabels(["Hücre", "Formül", "Değer"])
        a.setUniformRowHeights(True)
        a.setRootIsDecorated(True)
        a.setColumnWidth(0, 130)
        a.setColumnWidth(1, 150)
        a.header().setStretchLastSection(True)
        return a

    # ------------------------------------------------------------------ tetikleyiciler (pencere çağırır)
    def hucre_degisti(self) -> None:
        """Seçili hücre/sayfa değişti: kök yeniden kurulur (panel kendi gezintisindeyse dokunulmaz)."""
        if self._git_yapiyor or not self.isVisible():
            return
        self._yeniden_kur = True
        self._zamanlayici.start()

    def olay(self, olay) -> None:
        """Kitap olayı: formül/yapı değişince ağaç yeniden kurulur, yalnız sonuç değişince değerler tazelenir."""
        if not self.isVisible():
            return
        if olay.tur in ("hucre", "yapi", "sayfa", "ad", "ek"):
            self._yeniden_kur = True
        elif olay.tur != "sonuc":
            return
        self._zamanlayici.start()

    def _calis(self) -> None:
        if not self.isVisible():
            return
        if self._yeniden_kur:
            self._kur()
        else:
            self._tazele()

    # ------------------------------------------------------------------ kurulum
    def _kur(self) -> None:
        self._yeniden_kur = False
        p = self.pencere
        g = p.izgara()
        sayfa, (r, c) = g.sayfa, g._aktif
        self.izleme = Izleme(p.kitap, p.motor)
        self.agac.clear()
        self.ters.clear()
        kok = self.izleme.kok(sayfa, r, c)
        h = self.izleme.hata_kaynagi_metni()
        self.baslik.setText(f"{kok.etiket} = {kok.deger_metni}" + (f"\n{kok.formul}" if kok.formul else "\n(sabit değer)"))
        self.hata_etiketi.setVisible(bool(h))
        self.hata_etiketi.setText(f"Hatanın kaynağı: {h}" if h else "")
        oge = self._oge(kok, ())
        self.agac.addTopLevelItem(oge)
        self._yukle(oge, self.izleme.cocuklar)
        oge.setExpanded(True)
        for i in range(oge.childCount()):                       # 2. seviye: az sayıda çocuk varsa onlar da açılır
            if oge.childCount() <= 8 and oge.child(i).data(0, ROL_DURUM) == "tembel":
                oge.child(i).setExpanded(True)
        tk = self.izleme.bagimli_kok(sayfa, r, c)
        ters_oge = self._oge(tk, ())
        n = self.izleme.bagimli_sayisi(tk)
        ters_oge.setText(1, f"{n} formül bunu doğrudan kullanıyor" if n else "Bu hücreyi kullanan formül yok")
        self.ters.addTopLevelItem(ters_oge)
        self._yukle(ters_oge, self.izleme.bagimli_cocuklar)
        ters_oge.setExpanded(True)
        self.durum.setText("Düğüme tıklayınca ızgarada o hücreye gidilir.")
        self._ozet_planla()

    def _ozet_planla(self) -> None:
        """Özeti bekleyen büyük aralık düğümlerini (görünür ya da değil) topla; olay döngüsünde birer birer tamamla (arayüz donmaz)."""
        bekleyen = []
        for agac in (self.agac, self.ters):
            yigin = [agac.topLevelItem(i) for i in range(agac.topLevelItemCount())]
            while yigin:
                o = yigin.pop()
                d = o.data(0, ROL_DUGUM)
                if d is not None and d.tur == "aralik" and d.ozet_bekliyor:
                    bekleyen.append(o)
                yigin.extend(o.child(i) for i in range(o.childCount()))
        self._bekleyen_ozetler = bekleyen
        if bekleyen:
            QTimer.singleShot(0, self._ozet_sirasi)

    def _ozet_sirasi(self) -> None:
        while self._bekleyen_ozetler:
            o = self._bekleyen_ozetler.pop()
            try:
                d = o.data(0, ROL_DUGUM)
            except RuntimeError:                             # öğe silinmiş (ağaç yeniden kuruldu)
                continue
            if d is None or self.izleme is None or not d.ozet_bekliyor:
                continue
            y = self.izleme.ozet_tamamla(d)
            o.setData(0, ROL_DUGUM, y)
            self._doldur(o, y)
            if self._bekleyen_ozetler:
                QTimer.singleShot(0, self._ozet_sirasi)      # bir sonraki düğüm için olay döngüsüne dön
            return

    def _oge(self, d: Dugum, yol) -> QTreeWidgetItem:
        o = QTreeWidgetItem()
        o.setData(0, ROL_DUGUM, d)
        o.setData(0, ROL_YOL, yol)
        self._doldur(o, d)
        if d.tur == "daha":
            o.setData(0, ROL_DURUM, "daha")
        elif d.cocuk_var and not d.dongu:
            o.setData(0, ROL_DURUM, "tembel")
            o.addChild(QTreeWidgetItem(["…"]))
        return o

    def _doldur(self, o: QTreeWidgetItem, d: Dugum) -> None:
        if d.tur == "daha":
            o.setText(0, d.etiket)
            f = o.font(0)
            f.setItalic(True)
            o.setFont(0, f)
            return
        ad = d.etiket
        if d.hata_kaynagi:
            ad = "⚠ " + ad
        if d.dongu:
            ad = "↻ " + ad
        o.setText(0, ad)
        if d.tur == "aralik":
            o.setText(1, "")
            o.setText(2, d.ozet)
        else:
            o.setText(1, d.formul or ("taşan formülün parçası" if d.tasma_sahibi else "sabit"))
            o.setText(2, d.deger_metni + (" (döngü)" if d.dongu else ""))
        o.setToolTip(1, d.formul or "")
        o.setToolTip(2, d.deger_metni)
        renk = HATA_RENGI if d.hata else (DONGU_RENGI if d.dongu else None)
        for s in range(3):
            o.setForeground(s, QBrush(renk) if renk else QBrush())
            o.setBackground(s, QBrush(KAYNAK_RENGI) if d.hata_kaynagi else QBrush())
        if d.hata_kaynagi:
            f = o.font(0)
            f.setBold(True)
            o.setFont(0, f)

    def _yukle(self, ana: QTreeWidgetItem, kaynak, sayfa_no: int = 0) -> None:
        """`ana`nın çocuklarını (varsa yer tutucu yerine) `sayfa_no`. sayfadan yükler; kalan varsa “daha göster” düğmesi ekler."""
        if sayfa_no == 0:
            ana.takeChildren()                                   # yer tutucu (“…”) varsa kalksın
        d: Dugum = ana.data(0, ROL_DUGUM)
        yol = ana.data(0, ROL_YOL) or ()
        yol_yeni = yol + ((d.anahtar,) if d.tur == "hucre" else ())
        s = kaynak(d, yol, sayfa_no)
        for x in s.dugumler:
            ana.addChild(self._oge(x, yol_yeni))
        if any(x.tur == "aralik" and x.ozet_bekliyor for x in s.dugumler):
            QTimer.singleShot(0, self._ozet_planla)
        if s.sonraki:
            if s.toplam is None:
                etiket = "… daha göster"
            else:
                etiket = f"… {s.toplam - (sayfa_no + 1) * len(s.dugumler):,} tane daha göster".replace(",", ".")
            daha = Dugum("daha", etiket=etiket, ek={"ana": ana, "sayfa_no": sayfa_no + 1, "kaynak": kaynak})
            ana.addChild(self._oge(daha, yol_yeni))
        ana.setData(0, ROL_DURUM, "yuklu")

    def _ac(self, o: QTreeWidgetItem) -> None:
        if o.data(0, ROL_DURUM) != "tembel":
            return
        o.takeChildren()                                      # yer tutucu
        agac = o.treeWidget()
        kaynak = self.izleme.cocuklar if agac is self.agac else self.izleme.bagimli_cocuklar
        self._yukle(o, kaynak)

    def _tikla(self, o: QTreeWidgetItem, _kolon: int) -> None:
        d: Dugum = o.data(0, ROL_DUGUM)
        if d is None:
            return
        if d.tur == "daha":
            ana, sayfa_no, kaynak = d.ek["ana"], d.ek["sayfa_no"], d.ek["kaynak"]
            ana.removeChild(o)
            self._yukle(ana, kaynak, sayfa_no)
            ana.setData(0, ROL_DURUM, "yuklu")
            return
        self._git_yapiyor = True
        try:
            self.hucreyeGit.emit(d.sayfa, d.satir, d.sutun)
        finally:
            QTimer.singleShot(0, self._git_bitti)

    def _git_bitti(self) -> None:
        self._git_yapiyor = False

    # ------------------------------------------------------------------ değer tazeleme (formül yapısı değişmediyse)
    def _tazele(self) -> None:
        if self.izleme is None:
            return
        for agac in (self.agac, self.ters):
            for i in range(agac.topLevelItemCount()):
                self._tazele_oge(agac.topLevelItem(i))
        self._ozet_planla()
        r = self.izleme.guncelle(self.agac.topLevelItem(0).data(0, ROL_DUGUM)) if self.agac.topLevelItemCount() else None
        if r is not None:
            self.baslik.setText(f"{r.etiket} = {r.deger_metni}" + (f"\n{r.formul}" if r.formul else "\n(sabit değer)"))

    def _tazele_oge(self, o: QTreeWidgetItem) -> None:
        d: Dugum = o.data(0, ROL_DUGUM)
        if d is not None and d.tur in ("hucre", "aralik"):
            y = self.izleme.guncelle(d)
            y.dongu, y.hata_kaynagi = d.dongu, d.hata_kaynagi
            if d.tur == "aralik" and (d.ozet_bekliyor or d.kutu and (d.kutu[2] - d.kutu[0] + 1) * (d.kutu[3] - d.kutu[1] + 1) > 5000):
                y = self.izleme._aralik_dugumu(d.sayfa, d.kutu, False)        # büyük aralık: özet tembel yenilenir
            o.setData(0, ROL_DUGUM, y)
            self._doldur(o, y)
        for i in range(o.childCount()):
            self._tazele_oge(o.child(i))
