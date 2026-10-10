"""Çizim listesini (`model/grafik_cizim`) QPainter ile oynatır (Faz 6 / 6d; `faz6_tasarim.md` §4–5).

Boyayıcı ince tutulur: geometri `model/grafik_cizim.py`'de hesaplanır ve Qt'siz test edilir; burada yalnız ilkeller
çizilir. Aynı yol ekran önbelleği (`QPixmap`) ve yazdırma/PDF için kullanılır.
"""
import math
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QPolygonF

from ..model.grafik import Grafik
from ..model.grafik_cizim import (
    Cizgi, Cokgen, CizimListesi, Dikdortgen, Dilim, Dizi, Isaret, Metin, cizim_listesi,
)
from ..model.grafik_verisi import GrafikVerisi


def yazi_tipi(pt: float, kalin: bool = False, aile: Optional[str] = None) -> QFont:
    f = QFont(aile) if aile else QFont()
    f.setPointSizeF(max(1.0, pt))
    f.setBold(kalin)
    return f


def olcer_yap(aile: Optional[str] = None) -> Callable[[str, float], Tuple[float, float]]:
    """`QFontMetricsF` tabanlı ölçer (kalın başlıklar için ölçüm düz yazıdan biraz dar kalır; düzen payı bırakır)."""
    onbellek = {}

    def olcer(metin: str, pt: float) -> Tuple[float, float]:
        fm = onbellek.get(pt)
        if fm is None:
            fm = onbellek[pt] = QFontMetricsF(yazi_tipi(pt, False, aile))
        return fm.horizontalAdvance(metin), fm.height()
    return olcer


def _kalem(renk: Optional[str], kalinlik: float = 1.0) -> QPen:
    if renk is None:
        return QPen(Qt.NoPen)
    p = QPen(QColor(renk), kalinlik)
    p.setCapStyle(Qt.FlatCap)
    p.setJoinStyle(Qt.RoundJoin)
    return p


def _firca(renk: Optional[str]) -> QBrush:
    return QBrush(QColor(renk)) if renk else QBrush(Qt.NoBrush)


def ciz(p: QPainter, liste: CizimListesi, aile: Optional[str] = None) -> None:
    """`liste`yi `p`ye çizer (koordinatlar painter'ın mevcut dönüşümüne göredir)."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    for o in liste:
        if isinstance(o, Dikdortgen):
            p.setPen(_kalem(o.kenar))
            p.setBrush(_firca(o.dolgu))
            p.drawRect(QRectF(o.x, o.y, o.w, o.h))
        elif isinstance(o, Cizgi):
            p.setPen(_kalem(o.renk, o.kalinlik))
            p.drawLine(QPointF(o.x1, o.y1), QPointF(o.x2, o.y2))
        elif isinstance(o, Dizi):
            p.setPen(_kalem(o.renk, o.kalinlik))
            p.setBrush(Qt.NoBrush)
            parca = []
            for n in list(o.noktalar) + [None]:
                if n is None:
                    if len(parca) > 1:
                        p.drawPolyline(QPolygonF(parca))
                    elif len(parca) == 1:                    # tek nokta: görünür kalsın
                        p.drawPoint(parca[0])
                    parca = []
                else:
                    parca.append(QPointF(*n))
        elif isinstance(o, Cokgen):
            p.setPen(Qt.NoPen)
            p.setBrush(_firca(o.dolgu))
            p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in o.noktalar]))
        elif isinstance(o, Dilim):
            _dilim(p, o)
        elif isinstance(o, Isaret):
            p.setPen(Qt.NoPen)
            p.setBrush(_firca(o.dolgu))
            r = o.boyut / 2
            p.drawEllipse(QPointF(o.x, o.y), r, r)
        elif isinstance(o, Metin):
            _metin(p, o, aile)
    p.restore()


def _dilim(p: QPainter, o: Dilim) -> None:
    """Açılar 12 yönünden saat yönünde; Qt 3'ten saat yönünün tersine 1/16 derece."""
    p.setPen(_kalem("#FFFFFF", 1.0))
    p.setBrush(_firca(o.dolgu))
    dis = QRectF(o.cx - o.r_dis, o.cy - o.r_dis, 2 * o.r_dis, 2 * o.r_dis)
    bas = 90.0 - o.aci0                                      # Qt: 0° = 3 yönü, saat yönünün tersi pozitif
    sure = -(o.aci1 - o.aci0)
    yol = QPainterPath()
    yol.arcMoveTo(dis, bas)
    yol.arcTo(dis, bas, sure)
    if o.r_ic > 0:
        ic = QRectF(o.cx - o.r_ic, o.cy - o.r_ic, 2 * o.r_ic, 2 * o.r_ic)
        yol.arcTo(ic, bas + sure, -sure)
        yol.closeSubpath()
    else:
        yol.lineTo(QPointF(o.cx, o.cy))
        yol.closeSubpath()
    p.drawPath(yol)


def _metin(p: QPainter, o: Metin, aile: Optional[str]) -> None:
    f = yazi_tipi(o.pt, o.kalin, aile)
    p.setFont(f)
    p.setPen(QColor(o.renk))
    fm = QFontMetricsF(f)
    w, h = fm.horizontalAdvance(o.metin), fm.height()
    dx = {"sol": 0.0, "orta": -w / 2, "sag": -w}[o.hiza]
    dy = {"ust": 0.0, "orta": -h / 2, "alt": -h}[o.dikey]
    p.save()
    p.translate(o.x, o.y)
    if o.aci:
        p.rotate(o.aci)
    p.drawText(QPointF(dx, dy + fm.ascent()), o.metin)
    p.restore()


def grafik_ciz(p: QPainter, veri: GrafikVerisi, grafik: Grafik, boyut: Tuple[float, float],
               olcek: float = 1.0, aile: Optional[str] = None) -> CizimListesi:
    """Listeyi kurup çizer; listeyi döner (isabet denetimi/test için)."""
    liste = cizim_listesi(veri, grafik, boyut, olcer_yap(aile), olcek)
    ciz(p, liste, aile)
    return liste
