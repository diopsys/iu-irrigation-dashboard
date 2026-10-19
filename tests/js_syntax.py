"""JavaScript-Syntaxprüfung mit V8 (mini-racer), ohne Node.js.

Aufruf: tests/.venv/Scripts/python.exe tests/js_syntax.py <datei.js> [...]
Der Code wird nur kompiliert (new Function), nicht ausgeführt. Dateien mit
top-level await (Lader) werden in eine async-Funktion gepackt.
"""
import json
import sys

from py_mini_racer import MiniRacer

ctx = MiniRacer()
fehler = 0
for pfad in sys.argv[1:]:
    code = open(pfad, encoding="utf-8").read()
    if "await import(" in code.split("class ", 1)[0]:
        pruef = f"new (Object.getPrototypeOf(async function(){{}}).constructor)({json.dumps(code)})"
    else:
        pruef = f"new Function({json.dumps(code)})"
    try:
        ctx.eval(pruef)
        print(f"ok      {pfad}")
    except Exception as err:  # noqa: BLE001
        fehler += 1
        print(f"FEHLER  {pfad}: {err}")
sys.exit(1 if fehler else 0)
