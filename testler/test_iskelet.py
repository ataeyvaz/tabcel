import tabcel


def test_ad_ve_surum():
    assert tabcel.APP_NAME
    assert tabcel.__version__
    assert tabcel.APP_NAME in tabcel.KUNYE


def test_resource_dir_var():
    assert tabcel.resource_dir().exists()


def test_model_ve_formul_qt_icermez():
    # Ayrı süreçte: diğer testler Qt'yi zaten yüklemiş olabilir.
    import subprocess, sys
    kod = ("import sys, pkgutil, importlib, tabcel.model, tabcel.formul\n"
           "for p in (tabcel.model, tabcel.formul):\n"
           "    for m in pkgutil.iter_modules(p.__path__):\n"
           "        importlib.import_module(p.__name__ + '.' + m.name)\n"
           "assert not any(k.startswith('PySide6') for k in sys.modules)")
    r = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True,
                       cwd=str(__import__("tabcel").resource_dir()))
    assert r.returncode == 0, r.stderr
