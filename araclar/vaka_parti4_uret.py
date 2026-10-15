import json, os
V = []
def f(fm, h=None, **k):
    V.append(dict(id=f"P4_{len(V)+1:03d}", formul=fm, hucreler=h, **k))
M = {"A1": 2, "B1": 1, "A2": 5, "B2": 3, "C1": 1, "C2": 4, "A3": "x", "B3": 7}
S = {"A1": 2, "B1": 1, "C1": 0, "A2": 5, "B2": 3, "C2": 1, "A3": 1, "B3": 4, "C3": 2}
L = """=INDEX(MMULT(A1:B2,A1:B2),1,1) =INDEX(MMULT(A1:B2,A1:B2),2,2) =INDEX(MMULT(A1:B2,C1:C2),2,1) =INDEX(MMULT(A1:B2,C1:C2),1,1) =MMULT(A1:B2,A1:C3) =MMULT(A1:B3,A1:B2) =MMULT(A1:B2,A3:B3) =MDETERM(A1:B2) =MDETERM(S1:T2) =MDETERM(A1:A3) =MDETERM(A1:C2) =MINVERSE(A1:B2) =INDEX(MINVERSE(A1:B2),1,1) =INDEX(MINVERSE(A1:B2),2,1) =INDEX(MINVERSE(A1:B2),2,2) =INDEX(MUNIT(3),2,2) =INDEX(MUNIT(3),1,2) =MUNIT(0) =MUNIT(-1) =MUNIT("a") =MUNIT(2.9)""".split("\n")
for line in L:
    for fm in line.split(" ="):
        fm = fm.strip()
        if fm:
            f(fm if fm.startswith("=") else "=" + fm, M)
for fm in ["=MDETERM(A1:C3)", "=INDEX(MINVERSE(A1:C3),1,1)", "=INDEX(MINVERSE(A1:C3),3,2)", "=INDEX(MMULT(A1:C3,A1:C3),3,3)", "=MINVERSE(A1:B2)+0"]:
    f(fm, S)
F = {"A1": 79, "A2": 85, "A3": 78, "A4": 85, "A5": 50, "A6": 81, "A7": 95, "A8": 88, "A9": 97, "A10": "x", "B1": 70, "B2": 79, "B3": 89}
for fm in ["=INDEX(FREQUENCY(A1:A9,B1:B3),1)", "=INDEX(FREQUENCY(A1:A9,B1:B3),2)", "=INDEX(FREQUENCY(A1:A9,B1:B3),3)", "=INDEX(FREQUENCY(A1:A9,B1:B3),4)", "=INDEX(FREQUENCY(A1:A10,B1:B3),4)", "=INDEX(FREQUENCY(A1:A9,B5:B6),1)", "=INDEX(FREQUENCY(B5:B6,B1:B3),1)", "=SUM(FREQUENCY(A1:A9,B1:B3))", "=ROWS(FREQUENCY(A1:A9,B1:B3))"]:
    f(fm, F)
R = {"A1": 1, "A2": 2, "A3": 3, "A4": 4, "A5": 5, "B1": 2, "B2": 4.1, "B3": 5.9, "B4": 8.2, "B5": 9.8, "C1": 10, "C2": 20, "C3": 40, "C4": 80, "C5": 160, "D1": 1, "D2": "x", "D3": 3}
for fm in ["=TREND(B1:B5,A1:A5,6)", "=TREND(B1:B5,A1:A5,A1)", "=TREND(B1:B5,A1:A5,10,FALSE)", "=TREND(B1:B5)", "=INDEX(TREND(B1:B5,A1:A5,A1:A3),3)", "=TREND(B1:B5,A1:A4,6)", "=TREND(D1:D3,A1:A3)",
           "=GROWTH(C1:C5,A1:A5,6)", "=GROWTH(C1:C5,A1:A5,6,FALSE)", "=GROWTH(B1:B5,A1:A5,A1)", "=GROWTH(D1:D3,A1:A3)", "=GROWTH(B1:B2,A1:A3)",
           "=INDEX(LINEST(B1:B5,A1:A5),1,1)", "=INDEX(LINEST(B1:B5,A1:A5),1,2)", "=INDEX(LINEST(B1:B5,A1:A5,FALSE),1,1)", "=INDEX(LINEST(B1:B5,A1:A5,TRUE,TRUE),2,1)", "=INDEX(LINEST(B1:B5,A1:A5,TRUE,TRUE),2,2)",
           "=INDEX(LINEST(B1:B5,A1:A5,TRUE,TRUE),3,1)", "=INDEX(LINEST(B1:B5,A1:A5,TRUE,TRUE),3,2)", "=INDEX(LINEST(B1:B5,A1:A5,TRUE,TRUE),4,1)", "=INDEX(LINEST(B1:B5,A1:A5,TRUE,TRUE),4,2)", "=INDEX(LINEST(B1:B5,A1:A5,TRUE,TRUE),5,1)", "=INDEX(LINEST(B1:B5,A1:A5,TRUE,TRUE),5,2)",
           "=INDEX(LINEST(B1:B5),1,1)", "=LINEST(D1:D3,A1:A3)", "=INDEX(LINEST(B1:B5,A1:A5,FALSE,TRUE),3,1)"]:
    f(fm, R)
W = {"A1": 1, "A2": 2, "A3": 3, "A4": 4, "A5": 5, "A6": 6, "A7": 7}
for fm in ["=INDEX(WRAPROWS(A1:A7,3),1,1)", "=INDEX(WRAPROWS(A1:A7,3),2,3)", "=INDEX(WRAPROWS(A1:A7,3),3,2)", "=INDEX(WRAPROWS(A1:A7,3),3,2)", "=INDEX(WRAPROWS(A1:A7,3,0),3,2)", "=ROWS(WRAPROWS(A1:A7,3))", "=COLUMNS(WRAPROWS(A1:A7,3))", "=WRAPROWS(A1:A7,0)", "=INDEX(WRAPCOLS(A1:A7,3),1,2)", "=INDEX(WRAPCOLS(A1:A7,3),3,3)", "=INDEX(WRAPCOLS(A1:A7,3,\"-\"),3,3)", "=COLUMNS(WRAPCOLS(A1:A7,3))", "=ROWS(WRAPCOLS(A1:A7,3))", "=INDEX(WRAPROWS(A1:A7,10),1,10)",
           "=INDEX(TEXTSPLIT(\"a,b;c,d\",\",\",\";\"),2,1)", "=INDEX(TEXTSPLIT(\"a,b;c,d\",\",\",\";\"),2,2)", "=INDEX(TEXTSPLIT(\"a,b,c\",\",\"),1,3)", "=INDEX(TEXTSPLIT(\"a,,c\",\",\"),1,2)", "=INDEX(TEXTSPLIT(\"a,,c\",\",\",,TRUE),1,2)", "=INDEX(TEXTSPLIT(\"a,b;c\",\",\",\";\"),2,2)", "=INDEX(TEXTSPLIT(\"a,b;c\",\",\",\";\",FALSE,0,\"-\"),2,2)", "=INDEX(TEXTSPLIT(\"aXb\",\"x\",,,1),1,2)", "=INDEX(TEXTSPLIT(\"aXb\",\"x\",,,0),1,1)", "=TEXTSPLIT(\"abc\",\"\")", "=INDEX(TEXTSPLIT(\"a-b+c\",{\"-\",\"+\"}),1,3)", "=COLUMNS(TEXTSPLIT(\"a b c\",\" \"))", "=ROWS(TEXTSPLIT(\"a b c\",,\" \"))", "=INDEX(TEXTSPLIT(\"\",\",\"),1,1)"]:
    f(fm, W)
DB = {"A1": "Ağaç", "B1": "Yükseklik", "C1": "Yaş", "D1": "Verim", "A2": "Elma", "B2": 18, "C2": 20, "D2": 14, "A3": "Armut", "B3": 12, "C3": 12, "D3": 10, "A4": "Kiraz", "B4": 13, "C4": 14, "D4": 9, "A5": "Elma", "B5": 14, "C5": 15, "D5": 10, "A6": "Armut", "B6": 9, "C6": 8, "D6": 8, "A7": "Elma", "B7": 8, "C7": 9, "D7": 6,
      "F1": "Ağaç", "G1": "Yükseklik", "F2": "Elma", "G2": ">10", "F3": "Armut", "H1": "Yaş", "H2": "<16", "F5": "Ağaç", "F6": "E*"}
for fm in ["=DSUM(A1:D7,\"Verim\",F1:G2)", "=DSUM(A1:D7,4,F1:G2)", "=DSUM(A1:D7,\"Verim\",F1:F3)", "=DSUM(A1:D7,\"Verim\",F1:G3)", "=DSUM(A1:D7,\"Verim\",F5:F6)", "=DSUM(A1:D7,\"verim\",F1:F2)", "=DSUM(A1:D7,\"Yok\",F1:F2)", "=DSUM(A1:D7,5,F1:F2)", "=DSUM(A1:D7,0,F1:F2)", "=DSUM(A1:D7,\"Verim\",H1:H2)",
           "=DCOUNT(A1:D7,\"Verim\",F1:G2)", "=DCOUNT(A1:D7,\"Ağaç\",F1:G2)", "=DCOUNTA(A1:D7,\"Ağaç\",F1:G2)", "=DAVERAGE(A1:D7,\"Verim\",F1:F2)", "=DAVERAGE(A1:D7,\"Verim\",H1:H2)", "=DMAX(A1:D7,\"Verim\",F1:F2)", "=DMIN(A1:D7,\"Verim\",F1:F2)", "=DMAX(A1:D7,\"Verim\",F1:F6)",
           "=DPRODUCT(A1:D7,\"Verim\",F1:F2)", "=DGET(A1:D7,\"Verim\",F1:G2)", "=DGET(A1:D7,\"Verim\",F1:F2)", "=DGET(A1:D7,\"Verim\",F1:F3)", "=DGET(A1:D7,\"Verim\",H1:H2)", "=DAVERAGE(A1:D7,\"Verim\",F5:F6)", "=DSUM(A1:D1,\"Verim\",F1:F2)", "=DSUM(A1:D7,\"Verim\",F1)"]:
    f(fm, DB)
AG = {"A1": 10, "A2": "=1/0", "A3": 30, "A4": 20, "A5": 5, "A6": "x", "B1": 1, "B2": 2, "B3": 3, "B4": 4, "B5": 5}
for fm in ["=AGGREGATE(9,6,A1:A5)", "=AGGREGATE(9,4,A1:A5)", "=AGGREGATE(4,6,A1:A5)", "=AGGREGATE(5,6,A1:A5)", "=AGGREGATE(1,6,A1:A5)", "=AGGREGATE(2,6,A1:A6)", "=AGGREGATE(3,6,A1:A6)", "=AGGREGATE(12,6,A1:A5)", "=AGGREGATE(14,6,A1:A5,2)", "=AGGREGATE(15,6,A1:A5,2)", "=AGGREGATE(14,6,A1:A5,9)", "=AGGREGATE(16,6,A1:A5,0.5)", "=AGGREGATE(17,6,A1:A5,1)", "=AGGREGATE(18,6,A1:A5,0.5)", "=AGGREGATE(19,6,A1:A5,3)",
           "=AGGREGATE(9,6,A1,A3,A4)", "=AGGREGATE(9,0,B1:B5)", "=AGGREGATE(6,6,B1:B5)", "=AGGREGATE(7,6,B1:B5)", "=AGGREGATE(8,6,B1:B5)", "=AGGREGATE(10,6,B1:B5)", "=AGGREGATE(11,6,B1:B5)", "=AGGREGATE(13,6,B1:B5)", "=AGGREGATE(20,6,B1:B5)", "=AGGREGATE(9,8,B1:B5)", "=AGGREGATE(0,6,B1:B5)", "=AGGREGATE(14,6,B1:B5)", "=AGGREGATE(9,2,A1:A5)", "=AGGREGATE(9,3,A1:A5)", "=AGGREGATE(9,7,A1:A5)", "=AGGREGATE(9,5,A1:A5)", "=AGGREGATE(9,1,A1:A5)"]:
    f(fm, AG)
G = {"A1": 5, "A2": "=A1*2", "A3": "abc"}
for fm in ["=HYPERLINK(\"http://x.com\")", "=HYPERLINK(\"http://x.com\",\"Tıkla\")", "=HYPERLINK(\"http://x.com\",5)", "=HYPERLINK(A1)", "=HYPERLINK(\"u\",A1)", "=HYPERLINK(\"u\",A3)",
           "=FORMULATEXT(A2)", "=FORMULATEXT(A1)", "=FORMULATEXT(A9)", "=IMAGINARY(\"3+4i\")", "=IMAGINARY(\"4i\")", "=IMAGINARY(\"i\")", "=IMAGINARY(\"-i\")", "=IMAGINARY(\"5\")", "=IMAGINARY(5)", "=IMAGINARY(\"3-4j\")", "=IMAGINARY(\"abc\")", "=IMAGINARY(\"1+i\")", "=IMAGINARY(\"\")", "=IMAGINARY(A1)", "=IMAGINARY(1/0)", "=IMAGINARY(\"1.5e2+2.5e1i\")"]:
    f(fm, G)
json.dump(V, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vaka_parti4.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(V))
