# Excel'de olup Tabcel'de bulunmayan işlevler (2026-10-15 durum denetimi)

Kaynak: gerçek Excel 16, Türkçe arayüz (COM `FormulaLocal`, 2026-10-15) — Türkçe adlar **Excel'den ölçüldü**, kural 4 kapsamında doğrulanmış sayılır. Tabcel'de kayıtlı işlev sayısı: 327. Aşağıdaki liste Excel'in tüm işlevleri değil, sık kullanılan 324 işlev içinden Tabcel'de hâlâ olmayan 7 tanesidir (2026-10-15: 4 parti sonrası; önceki sayı 188). İşlev ekleme kural 11'e (≥ 4 test vakası) tabidir.

## Finans (1)

| İngilizce | Türkçe (Excel) |
|---|---|
| `VDB` | `DAB` |

## Arama/bilgi (2)

| İngilizce | Türkçe (Excel) |
|---|---|
| `CELL` | `HÜCRE` |
| `INFO` | `BİLGİ` |

## Dinamik dizi (4)

| İngilizce | Türkçe (Excel) |
|---|---|
| `MAKEARRAY` | `MAKEARRAY` |
| `MAP` | `MAP` |
| `REDUCE` | `REDUCE` |
| `SCAN` | `SCAN` |


## Bilinçli ertelenenler (2026-10-15 kararı)
- **MAP, REDUCE, SCAN, MAKEARRAY** `LAMBDA` ister; `LAMBDA` ve taşma başvurusu (`A1#`) ayrı bir faz.
- **VDB** (DAB), **CELL** (HÜCRE), **INFO** (BİLGİ) — kullanım sıklığı düşük.
- **EĞİLİM/BÜYÜME/DOT** yalnız tek bağımsız değişkenle.
