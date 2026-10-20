"""Darstellungstest des Panels in V8 (mini-racer), ohne Browser und ohne HA.

Aufruf (im Repo-Stamm):  python tests/js_render.py [--text]

Lädt www/irrigation-app.js mit einem minimalen DOM-Ersatz, rendert jeden
Reiter mit der Beispielanlage (tests/beispiel.py) und erfundenen Zuständen –
auf Deutsch und Englisch, einmal im Ruhezustand und einmal während eines
Laufs – und meldet Laufzeitfehler sowie Texte ohne englische Übersetzung.
--text zeigt den sichtbaren Text der Reiter.
"""
import json
import sys
from datetime import datetime, timedelta

from beispiel import STAMM, beispiel
from py_mini_racer import MiniRacer

from custom_components.iu_irrigation_dashboard import iu_yaml

APP = STAMM / "custom_components/iu_irrigation_dashboard/www/irrigation-app.js"


def zustand(eid, state, **attr):
    return {"entity_id": eid, "state": str(state), "attributes": attr,
            "last_updated": "2026-07-01T06:00:00+00:00", "last_changed": "2026-07-01T06:00:00+00:00"}


def zustaende(daten, laeuft):
    jetzt = datetime.now().astimezone()
    zu = iu_yaml.zuordnung(daten)
    st = [zustand("sun.sun", "above_horizon"),
          zustand("sensor.garden_pump_power", 850 if laeuft else 3, unit_of_measurement="W", friendly_name="Pump power"),
          zustand("sensor.rain_total", 412.3, unit_of_measurement="mm", friendly_name="Rain total"),
          zustand("sensor.water_meter", 731.887, unit_of_measurement="m³", friendly_name="Water meter"),
          zustand("sensor.garden_pump_energy", 51.2, unit_of_measurement="kWh", friendly_name="Pump energy"),
          zustand("weather.home", "sunny", friendly_name="Home")]
    for c in daten["controller"]:
        if c["pumpe"].get("entity_id"):
            st.append(zustand(c["pumpe"]["entity_id"], "on" if laeuft or c["id"] == "c1" else "off", friendly_name=f"{c['name']} pump"))
        for i, z in enumerate(c["zonen"]):
            for v in z["ventile"]:
                offen = (laeuft and i == 0) or z["betrieb"] == "wasserhahn"
                st.append(zustand(v, "on" if offen else "off", friendly_name=z["name"]))
            st.append(zustand(zu["zonen"][z["id"]], "on" if laeuft and i == 0 else "off"))
            st.append(zustand(f"sensor.irrigation_run_time_{z['id']}", 123.4, zone_id=z["id"], unit_of_measurement="min"))
            if c["anschluss"] == "leitung":
                st.append(zustand(f"sensor.irrigation_water_{z['id']}", 840.5, wasser_zone=z["id"], unit_of_measurement="L"))
        aktiv = laeuft and c["id"] == "c1"
        st.append(zustand(zu["controller"][c["id"]], "on" if aktiv else "off", enabled=True,
                          current_start=jetzt.isoformat() if aktiv else None, current_duration="0:20:00",
                          current_name=c["zonen"][0]["name"]))
        for s in c["sequenzen"]:
            st.append(zustand(zu["sequenzen"][s["id"]], "on" if aktiv and s["id"] == "s1" else "off", status="off",
                              next_start=(jetzt + timedelta(hours=20)).isoformat(), next_duration="1:05:00",
                              next_name=s["plaene"][0]["name"] if s["plaene"] else None))
    st += [zustand("sensor.irrigation_automatic_runs", 12, laeufe="automatik"),
           zustand("sensor.irrigation_manual_runs", 3, laeufe="manuell")]
    return {s["entity_id"]: s for s in st}


def cfg(daten, laeuft):
    zonen = {z["id"]: {"bilanz": -3.2, "bedarf": 4.1, "referenz": 3.0, "faktor": 1.35}
             for c in daten["controller"] for z in c["zonen"]}
    return {
        "einstellungen": daten,
        "status": {"iu": "ok", "meldung": "", "datei": "packages/iu_irrigation_dashboard.yaml", "zuletzt": None, "app": "test"},
        "zustand": {
            "zuordnung": iu_yaml.zuordnung(daten),
            "wetter": {"et0_gestern": 3.2, "et0_prognose": 3.6, "regen_heute": 0.3, "regen_prognose": 2.1,
                       "regnet": False, "tage": [{"tag": "2026-07-1%d" % i, "et0": 3.1, "regen": i * 0.5} for i in range(8)],
                       "prognose_stunden": [["2026-07-20T%02d:00:00+02:00" % h, h % 3 * 0.4, 60] for h in range(24)],
                       "zonen": zonen},
            "sequenzen": {s["id"]: {"plan": s["plaene"][0]["name"] if s["plaene"] else None, "plan_prozent": 100,
                                    "zonen": {sz["zone"]: {"nr": k + 1, "prozent": 85, "aktiv": True, "minuten": 17}
                                              for k, sz in enumerate(s["zonen"])}}
                          for c in daten["controller"] for s in c["sequenzen"]},
            "laeufe": {"s1": {"start": "2026-07-15T05:15:00+02:00", "ende": "2026-07-15T06:00:00+02:00", "dauer_min": 45, "plan": "Summer"}},
            "manuell": {"c2": {"zone": "front"}} if laeuft else {}, "minuten": {}, "anzahl": {"automatik": 12, "manuell": 3},
        },
    }


STUBS = """
var window = globalThis;
window.addEventListener = () => {};
window.innerWidth = 1200; window.innerHeight = 900;
var navigator = { userAgent: 'js_render' };
var localStorage = { getItem() { return null; }, setItem() {} };
var document = { createElement() { return { style: {}, prepend() {} }; } };
function setInterval() { return 0; } function clearInterval() {} function setTimeout() { return 0; } function clearTimeout() {}
function confirm() { return true; }
var leer = { innerHTML: '', textContent: '', style: {}, classList: { add() {}, toggle() {} }, querySelector() { return null; }, querySelectorAll() { return []; }, prepend() {}, addEventListener() {} };
class HTMLElement {
  attachShadow() { this.shadowRoot = { ...leer, activeElement: null }; return this.shadowRoot; }
  dispatchEvent() {}
}
var customElements = { define(name, cls) { globalThis.__Panel = cls; } };
"""

STATISTIK = """
var schritte = [...Array(7)].map((_, i) => new Date(2026, 6, 10 + i));
var reihe = (f) => schritte.map((_, i) => i * f);
p._statDaten = { period: 'day', schritte, beregnung: reihe(10), regen: reihe(0.5),
  zonen: p._ctlListe().flatMap((c) => c.zonen.map((z) => ({ ...z, ctl: c, werte: reihe(3), liter: p._leitung(c) ? reihe(40) : null }))),
  energie: 1.2, kwh: reihe(0.2), liter: reihe(80), kosten: { wasser: reihe(0.13), abwasser: reihe(0.25), grund: reihe(0.08), strom: reihe(0.06) },
  mitWasser: true, mitStrom: true, mitPumpe: true, laeufeAuto: 3, laeufeMan: 1 };
"""
TEXT = r"p.{}().replace(/<style[\s\S]*?<\/style>|<datalist[\s\S]*?<\/datalist>|<[^>]+>/g, ' ').replace(/\s+/g, ' ')"
REITER = ["_uebersicht", "_automatik", "_manuell", "_wetter", "_statistik", "_einstellungen", "_kopfstatus"]


def main():
    daten = beispiel()
    ctx = MiniRacer()
    ctx.eval(STUBS)
    ctx.eval(APP.read_text(encoding="utf-8"))
    fehler = 0
    for sprache in ("de", "en"):
        for laeuft in (False, True):
            ctx.eval(f"""
var p = new __Panel();
p._spracheAus({{ language: '{sprache}' }});
p._hass = {{ states: {json.dumps(zustaende(daten, laeuft))}, user: {{ is_admin: true }}, config: {{ elevation: 30 }},
            callWS() {{ return Promise.resolve({{}}); }}, callService() {{ return Promise.resolve(); }},
            connection: {{ subscribeMessage() {{ return Promise.resolve(() => {{}}); }} }} }};
p._cfg = {json.dumps(cfg(daten, laeuft))};
{STATISTIK}""")
            print(f"── {sprache}, {'Lauf' if laeuft else 'Ruhe'}")
            for reiter in REITER:
                try:
                    laenge = ctx.eval(f"p.{reiter}().length")
                    print(f"ok      {reiter:16} {laenge} Zeichen")
                    if "--text" in sys.argv:
                        print("        " + ctx.eval(TEXT.format(reiter))[:1200])
                except Exception as err:  # noqa: BLE001
                    fehler += 1
                    print(f"FEHLER  {reiter:16} {err}")
            for i in range(len(daten["controller"])):
                for vertikal in ("false", "true"):
                    try:
                        ctx.eval(f"p._anlage(p._ctlListe()[{i}], {vertikal})")
                    except Exception as err:  # noqa: BLE001
                        fehler += 1
                        print(f"FEHLER  _anlage({i}, {vertikal}) {err}")
    fehlend = json.loads(ctx.eval("JSON.stringify([...FEHLEND])"))
    if fehlend:
        fehler += 1
        print("FEHLER  ohne englische Übersetzung:")
        for text in fehlend:
            print(f"          {text!r}")
    else:
        print("ok      alle Texte übersetzt")
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
