import sys, time, cProfile, pstats
sys.path.insert(0, '.')
from tabcel.io import xlsx_io, xlsx_hizli
print("yamali:", xlsx_hizli.yamali_mi())
pr = cProfile.Profile(); pr.enable()
k, r = xlsx_io.ac(sys.argv[1])
pr.disable()
pstats.Stats(pr).sort_stats("tottime").print_stats(14)
