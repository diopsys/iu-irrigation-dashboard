/* Panel der Integration „IU Irrigation Dashboard“ (custom_components/iu_irrigation_dashboard).
 *
 * Geladen über irrigation-panel.js (Lader mit Zeitstempel, kein Cache-Problem).
 * Alle Controller, Pumpen, Zonen, Sequenzen und Pläne kommen aus den
 * Einstellungen der Integration (WebSocket iu_irrigation_dashboard/abonnieren: einstellungen,
 * status, zustand). Die Zuordnung zu den Irrigation-Unlimited-Entitäten
 * (c{n}_m/_z/_s) liefert zustand.zuordnung – hier ist nichts fest eingetragen.
 *
 * Sprache: Die Texte stehen deutsch im Code und laufen durch t(). Für andere
 * Sprachen als Deutsch gilt Englisch (TEXTE.en, Schlüssel = deutscher Text,
 * {name} = Platzhalter). Weitere Sprachen: TEXTE und KURZ ergänzen.
 */

const IST_AN = ['on', 'open', 'opening'];
const SCHALT_DOMAINS = ['switch', 'input_boolean', 'valve', 'cover', 'light'];
const MONATE_IU = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
const TAGE_IU = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
// Smarte Laufzeit (experimentell, wie smart.py): Voreinstellungen je Zonentyp
const ZONENTYPEN = {
  benutzerdefiniert: null,
  rasen: { kc: 0.8, speicher_mm: 20, giessweise: 'schwelle', schwelle_prozent: 50 },
  beet: { kc: 0.6, speicher_mm: 15, giessweise: 'schwelle', schwelle_prozent: 50 },
  hecke: { kc: 0.5, speicher_mm: 30, giessweise: 'schwelle', schwelle_prozent: 60 },
  gemuese: { kc: 1.0, speicher_mm: 10, giessweise: 'bedarf', schwelle_prozent: 30 },
};
const ZONENTYP_TEXT = { benutzerdefiniert: 'Benutzerdefiniert', rasen: 'Rasen', beet: 'Beet/Stauden', hecke: 'Hecke/Sträucher', gemuese: 'Gemüse/Kübel' };
const SMART_STANDARD = { typ: 'benutzerdefiniert', kc: 1, speicher_mm: null, giessweise: 'bedarf', schwelle_prozent: 50, flaeche_m2: null,
  leistung_quelle: 'hand', durchfluss_l_min: null, max_min: 120, aufteilen: false, durchgang_min: 30, sickerpause_min: 0 };
const GRUND_TEXT = { laeuft: 'nach Bedarf', begrenzt: 'auf Höchstlaufzeit begrenzt', kein_bedarf: 'kein Bedarf', regnet: 'es regnet' };
const QUELLE_TEXT = { zaehler: 'gemessen', durchfluss: 'Durchfluss ÷ Fläche', hand: 'von Hand', referenz: 'Referenzmenge' };
// Liter je Einheit eines Wasserzählers (wie wasser.py)
const LITER_JE = { L: 1, l: 1, 'm³': 1000, m3: 1000, gal: 3.785411784, 'ft³': 28.316846592, ft3: 28.316846592, CCF: 2831.6846592 };

// ── Sprache ───────────────────────────────────────────────────────────
const KURZ = {
  de: { monate: ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'], tage: ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'] },
  en: { monate: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], tage: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] },
};
const TEXTE = {
  en: {
    // Grundgerüst, Reiter, Kopf
    'Übersicht': 'Overview', 'Automatik': 'Automatic', 'Manuell': 'Manual', 'Wetter': 'Weather', 'Statistik': 'Statistics', 'Einstellungen': 'Settings',
    'Beregnung': 'Irrigation', 'Lade Beregnung …': 'Loading irrigation …', 'Fehler im Panel: {text}': 'Panel error: {text}',
    'Fehler: {text}': 'Error: {text}',
    'Das Panel wurde aktualisiert.': 'The panel has been updated.', 'Neu laden': 'Reload',
    'Die Integration „IU Irrigation Dashboard“ ist nicht eingerichtet ({fehler}).': 'The integration “IU Irrigation Dashboard” is not set up ({fehler}).',
    'Einstellungen → Geräte & Dienste → Integration hinzufügen → „IU Irrigation Dashboard“.': 'Settings → Devices & services → Add integration → “IU Irrigation Dashboard”.',
    'Lade Einstellungen …': 'Loading settings …', 'Noch kein Controller angelegt.': 'No controller set up yet.',
    ' Unter „Einstellungen“ einen Controller mit Pumpe und Zonen anlegen.': ' Add a controller with pump and zones under “Settings”.',
    'aus': 'off', 'bereit': 'ready', 'läuft': 'running', 'Pumpe': 'Pump', 'Pumpe {name}': 'Pump {name}', 'Beregnung läuft': 'Irrigation running',
    'Restzeit': 'remaining', 'Start {zeit}': 'start {zeit}',
    // Zeiten
    'heute {uhr}': 'today {uhr}', 'morgen {uhr}': 'tomorrow {uhr}', 'gestern {uhr}': 'yesterday {uhr}',
    'in {t}': 'in {t}', 'vor {t}': '{t} ago', '{n} Tagen': '{n} days', 'vor': 'before', 'nach': 'after',
    'Sonnenaufgang': 'sunrise', 'Sonnenuntergang': 'sunset', 'feste Uhrzeit': 'fixed time', 'um {zeit} Uhr': 'at {zeit}',
    // Wasserhahn
    'Wasserhahn': 'Tap', 'Ventil offen, solange die Pumpe läuft': 'Valve open while the pump is on', 'Läuft in der Automatik mit': 'Included in the automatic run',
    'Wasserhahn offen': 'tap open', 'Wasserhahn zu': 'tap closed', 'Ventil offen': 'valve open', 'Ventil zu': 'valve closed', 'nur manuell': 'manual only',
    // Anlagenbild
    'Anlagenbild {name}': 'System diagram {name}', 'Brunnen': 'Well', 'Standard {min} min': 'default {min} min',
    // Übersicht
    'Manueller Lauf': 'Manual run', 'Automatik · {name}': 'Automatic · {name}', 'Einzellauf': 'Single run', 'Manuell · {name}': 'Manual · {name}',
    'Automatik aus': 'Automatic off', 'nur manuelle Läufe': 'manual runs only', 'Bereit': 'Ready', 'nächster Lauf {wann}': 'next run {wann}',
    'kein Lauf geplant': 'no run scheduled', 'Keine Zonen.': 'No zones.', 'Pumpe Sonnenauf- bis -untergang': 'Pump on from sunrise to sunset',
    'Stoppen': 'Stop', 'Status': 'Status', 'Nächster Lauf': 'Next run', 'Letzter Lauf': 'Last run', 'noch keiner erfasst': 'none recorded yet',
    'Verdunstung': 'Evaporation', 'nächste 24 h · Regen heute {heute} mm, Prognose {prognose} mm': 'next 24 h · rain today {heute} mm, forecast {prognose} mm',
    // Automatik
    'gesperrt (Controller aus)': 'blocked (controller off)', 'ausgesetzt': 'suspended', 'pausiert': 'paused', 'Pause zwischen Zonen': 'pause between zones',
    'Wasserbilanz': 'Water balance', 'Laufzeit nach Wetter': 'Run time by weather', 'Wetter aus (100 %)': 'Weather off (100 %)',
    'Verdunstung gestern': 'Evaporation yesterday', 'Verdunstung 24 h': 'Evaporation 24 h', 'Prognose': 'forecast', 'Regen heute': 'Rain today',
    'es regnet': 'raining', 'Regen 24 h': 'Rain 24 h', 'Prognose × Wahrscheinlichkeit': 'forecast × probability', 'Grundfaktor für alle Sequenzen': 'Base factor for all sequences',
    'Automatik an': 'Automatic on', 'nicht in Irrigation Unlimited (Pumpe/Zonen fehlen)': 'not in Irrigation Unlimited (pump/zones missing)',
    'Keine Sequenz – in den Einstellungen anlegen.': 'No sequence – add one in the settings.',
    'LÄUFT': 'RUNNING', 'Im Wasserhahn-Betrieb (ausgeblendet): {zonen}.': 'In tap mode (hidden): {zonen}.',
    'Dauer': 'Duration', 'Dauer {name}': 'Duration {name}', 'Geplant': 'Planned', 'entfällt': 'skipped',
    'Nächster Lauf:': 'Next run:', 'Plan {name} {prozent} %': 'plan {name} {prozent} %', 'Letzter:': 'Last:',
    'Keine Zonen in dieser Sequenz.': 'No zones in this sequence.', 'Summe geplant {summe}': 'Total planned {summe}', ' · ohne Wetteranpassung': ' · without weather adjustment',
    ' · Dauer leer = Standardlaufzeit der Zone': ' · empty duration = default run time of the zone',
    'Ohne Plan (keine Automatik): {monate}.': 'Without plan (no automatic run): {monate}.',
    'Keine Pläne – die Sequenz läuft nur manuell. Pläne legst du in den Einstellungen an.': 'No plans – the sequence runs manually only. Add plans in the settings.',
    'AKTUELL': 'CURRENT', 'ohne Lauf': 'no run', 'Monate': 'Months', 'Tage': 'Days', 'Start': 'Start', 'Laufzeit': 'Run time',
    // Manuell
    '{name} – manueller Lauf': '{name} – manual run', 'Alle': 'All', 'Keine': 'None', 'Laufzeit für alle Zonen': 'Run time for all zones',
    '100 % = Standard': '100 % = default', 'Gesamtdauer': 'Total duration', 'Starten': 'Start',
    'Sequenz manuell starten (mit der Laufzeit oben, ohne Wetteranpassung):': 'Start a sequence manually (with the run time above, without weather adjustment):',
    // Wetter
    'ET₀ nach FAO-56': 'ET₀ per FAO-56', 'gemessen': 'measured', 'Menge × Wahrscheinlichkeit': 'amount × probability',
    'Verdunstung und Regen je Tag': 'Evaporation and rain per day', 'Regen': 'Rain', 'Noch keine Tage ausgewertet.': 'No days evaluated yet.',
    'Regenprognose je Stunde': 'Rain forecast per hour', 'Bodenspeicher je Zone': 'Soil storage per zone',
    'Referenz {referenz} mm = 100 % · Speicher {speicher} mm · Regen {wirksam} % wirksam': 'reference {referenz} mm = 100 % · storage {speicher} mm · rain {wirksam} % effective',
    'Zone': 'Zone', 'Bilanz': 'Balance', 'Bedarf': 'Demand', 'Referenz': 'Reference', 'Faktor': 'Factor', 'ohne Regen': 'no rain',
    'Bilanz < 0 = Defizit im Boden. Bedarf = Defizit + Verdunstung der nächsten 24 h − wirksamer Regen (heute und Prognose). Faktor = Bedarf ÷ Referenz, höchstens {max} %; dazu kommen Plan-%, Grundfaktor und Zonenfaktor. Jeder Lauf schreibt seine Wassermenge gut.':
      'Balance < 0 = soil deficit. Demand = deficit + evaporation of the next 24 h − effective rain (today and forecast). Factor = demand ÷ reference, at most {max} %; plan %, base factor and zone factor are applied on top. Every run credits its amount of water.',
    'Verdunstung {mm} mm': 'evaporation {mm} mm', 'Regen {mm} mm': 'rain {mm} mm', 'Keine Prognose verfügbar.': 'No forecast available.', '{h} h': '{h}:00',
    // Statistik
    '7 Tage': '7 days', '30 Tage': '30 days', '12 Monate': '12 months', 'Lade Statistik …': 'Loading statistics …',
    'Statistik nicht verfügbar: {fehler}': 'Statistics not available: {fehler}', 'Hahn': 'tap',
    'ohne Zonen im Wasserhahn-Betrieb': 'without zones in tap mode', 'Läufe': 'Runs', '{auto} Automatik · {man} manuell': '{auto} automatic · {man} manual',
    'Pumpen': 'Pumps', 'Energie': 'energy', 'Beregnung je Monat (min)': 'Irrigation per month (min)', 'Beregnung je Tag (min)': 'Irrigation per day (min)',
    'Regen je Monat (mm)': 'Rain per month (mm)', 'Regen je Tag (mm)': 'Rain per day (mm)', 'Beregnung {dauer}': 'irrigation {dauer}', 'Laufzeit je Zone': 'Run time per zone',
    // Einstellungen
    'nicht gefunden': 'not found', 'Nur für Administratoren.': 'Administrators only.',
    'Anzeige': 'Display', 'Tippen auf das Logo öffnet': 'Tapping the logo opens', 'Zur Startseite': 'To the start page',
    'Pfad einer HA-Seite (beginnt mit /) oder eine Adresse mit http(s)://, z. B. die Startseite eines Dashboards. Leer = das Logo hat keine Funktion.': 'Path of an HA page (starting with /) or an http(s):// address, e.g. the start page of a dashboard. Empty = the logo does nothing.',
    'Controller anlegen': 'Add controller', 'Controller': 'Controller', 'Wetter und Wasserbilanz': 'Weather and water balance',
    'Regenzähler (Summe, mm)': 'Rain counter (total, mm)', 'Regenrate (mm/h)': 'Rain rate (mm/h)', 'optional – > 0 = es regnet': 'optional – > 0 = raining',
    'Regensensor (an = Regen)': 'Rain sensor (on = rain)', 'optional': 'optional', 'Wetterprognose': 'Weather forecast', 'Temperatur': 'Temperature',
    'Luftfeuchte': 'Humidity', 'Wind': 'Wind', 'Einstrahlung (W/m²)': 'Solar radiation (W/m²)', 'Höhe des Windmessers': 'Anemometer height',
    'Höhe über NN': 'Elevation', 'Referenzbedarf (100 %)': 'Reference demand (100 %)', 'Bodenspeicher': 'Soil storage', 'Regen wirksam': 'Effective rain',
    'Höchstwert Laufzeit': 'Maximum run time', 'Einstrahlung aus Temperatur (kRs)': 'Radiation from temperature (kRs)',
    'Ohne Einstrahlungssensor wird die Einstrahlung aus der Temperaturspanne des Tages geschätzt (FAO-56): kRs 0,16 im Binnenland, 0,19 an der Küste.':
      'Without a radiation sensor, solar radiation is estimated from the daily temperature range (FAO-56): kRs 0.16 inland, 0.19 near the coast.',
    'Referenzbedarf = Wassermenge, die eine Zone bei 100 % Standardlaufzeit verteilt (3 mm sind ein guter Startwert). Zonen mit gemessener Beregnungsleistung (mm/h) rechnen mit Leistung × Standardlaufzeit. Ein Regentag über 100 mm gilt als Messfehler.':
      'Reference demand = amount of water a zone applies at 100 % of its default run time (3 mm is a good starting value). Zones with a measured application rate (mm/h) use rate × default run time. A day with more than 100 mm of rain is treated as a measurement error.',
    'IU-Historie (liest alle 2 min die Datenbank – nur bei Bedarf)': 'IU history (reads the database every 2 min – only if needed)',
    'Ungespeicherte Änderungen': 'Unsaved changes', 'Verwerfen': 'Discard', 'Speichern': 'Save',
    'Name der Zone': 'Zone name', 'nach oben': 'move up', 'nach unten': 'move down', 'Zone löschen': 'Delete zone',
    'Ventil(e) – mehrere werden gemeinsam geschaltet': 'Valve(s) – several are switched together', 'Ventil entfernen': 'Remove valve',
    'Ventil hinzufügen': 'Add valve', 'Ventil': 'Valve', 'Standardlaufzeit': 'Default run time', 'Zonenfaktor': 'Zone factor', 'Beregnungsleistung': 'Application rate',
    'Kann Wasserhahn sein (Ventil folgt der Pumpe)': 'Can be a tap (valve follows the pump)', 'Regen kürzt die Laufzeit (aus bei überdachten Zonen)': 'Rain shortens the run time (off for covered zones)',
    'Name des Controllers': 'Controller name', 'Controller löschen': 'Delete controller', 'Pumpe (Schalter)': 'Pump (switch)', 'Leistung (W)': 'Power (W)',
    'Energie (kWh)': 'Energy (kWh)', 'optional – Statistik': 'optional – statistics', '„Pumpt“ ab': '“Pumping” above', 'Vorlauf': 'Lead time', 'Nachlauf': 'Run-on',
    'Pumpe von Sonnenauf- bis -untergang an': 'Pump on from sunrise to sunset', 'Zonen': 'Zones', 'Zone anlegen': 'Add zone', 'Noch keine Zone.': 'No zone yet.',
    'Sequenzen': 'Sequences', 'Sequenz anlegen': 'Add sequence', 'Sequenz': 'Sequence', 'Noch keine Sequenz – ohne Sequenz gibt es keine Automatik.': 'No sequence yet – without a sequence there is no automatic run.',
    'Die Reihenfolge bestimmt die Nummern in Irrigation Unlimited (Controller {n}: …_c{n}_z1, …_c{n}_s1).': 'The order determines the numbers in Irrigation Unlimited (controller {n}: …_c{n}_z1, …_c{n}_s1).',
    'Standard': 'default', 'aktiv': 'active', 'entfernen': 'remove', 'Name des Plans': 'Plan name', 'Plan löschen': 'Delete plan', 'Name der Sequenz': 'Sequence name',
    'Sequenz löschen': 'Delete sequence', 'Laufzeit nach Wetter (Wasserbilanz)': 'Run time by weather (water balance)', 'Zonen in Reihenfolge': 'Zones in order',
    'Zone hinzufügen': 'Add zone', 'Keine Zone.': 'No zone.', 'Pläne': 'Plans', 'Plan anlegen': 'Add plan', 'Plan': 'Plan', 'Kein Plan – nur manuell.': 'No plan – manual only.',
    'Monate, Tage, Startzeit (vor/nach Sonnenauf- oder -untergang, feste Uhrzeit) und Laufzeit der Pläne stellst du im Reiter „Automatik“ ein.':
      'Months, days, start time (before/after sunrise or sunset, fixed time) and run time of the plans are set in the “Automatic” tab.',
    'Irrigation Unlimited ist auf dem Stand der Einstellungen.': 'Irrigation Unlimited is up to date with the settings.', 'Status unbekannt': 'Status unknown',
    'Datei {datei}': 'File {datei}', 'Datei neu erzeugen und Irrigation Unlimited neu laden': 'Regenerate the file and reload Irrigation Unlimited', 'Jetzt anwenden': 'Apply now',
    'Controller {n}': 'Controller {n}', 'Controller „{name}“ mit allen Zonen und Sequenzen löschen?': 'Delete controller “{name}” with all its zones and sequences?',
    'Zone {n}': 'Zone {n}', 'Zone „{name}“ löschen? Sie wird auch aus allen Sequenzen entfernt.': 'Delete zone “{name}”? It is also removed from all sequences.',
    'Sequenz {n}': 'Sequence {n}', 'Sequenz „{name}“ löschen?': 'Delete sequence “{name}”?', 'Plan {n}': 'Plan {n}', 'Plan „{name}“ löschen?': 'Delete plan “{name}”?',
    'Angewendet': 'Applied', 'Zone „{name}“ hat kein Ventil.': 'Zone “{name}” has no valve.', 'Gespeichert – Irrigation Unlimited wird aktualisiert': 'Saved – updating Irrigation Unlimited',
    // Bedienung
    'Wird gestoppt': 'Stopping', 'Manueller Lauf gestartet': 'Manual run started', 'Sequenz gestartet': 'Sequence started',
    // Meldungen der Integration (status.meldung)
    'Es ist noch kein Controller angelegt': 'No controller has been set up yet',
    'In configuration.yaml steht noch eine eigene irrigation_unlimited-Konfiguration. Unter Einstellungen → Reparaturen auskommentieren lassen.': 'configuration.yaml still contains its own irrigation_unlimited configuration. Comment it out under Settings → Repairs.',
    'configuration.yaml lädt den Ordner packages/ nicht. Ergänzen: homeassistant: packages: !include_dir_named packages': 'configuration.yaml does not load the packages/ folder. Add: homeassistant: packages: !include_dir_named packages',
    'Irrigation Unlimited ist noch nicht geladen – einmal Home Assistant neu starten.': 'Irrigation Unlimited is not loaded yet – restart Home Assistant once.',
    'Wird nach dem laufenden Lauf übernommen.': 'Will be applied after the current run.',
    'Kein Controller hat mindestens eine Zone und eine Pumpe oder einen Wasseranschluss': 'No controller has at least one zone and a pump or a water connection',
    // Wasseranschluss, Preise
    'Wasseranschluss': 'Water connection', 'Wasseranschluss {name}': 'Water connection {name}', 'Wasser': 'Water', 'fließt': 'flowing',
    'Hausanschluss': 'Mains', 'Wasserversorgung': 'Water supply', 'Wasserzähler': 'Water meter',
    'Zähler misst nur die Beregnung (eigener Gartenzähler)': 'Meter measures irrigation only (separate garden meter)',
    'Grundpreis': 'Base price', 'Wasserpreis': 'Water price', 'Erweitert': 'Advanced', 'Abwasser': 'Wastewater', 'Strompreis': 'Electricity price',
    'Die Ventile hängen direkt an der Wasserleitung, es gibt keine Pumpe. Mit dem Hauptzähler des Hauses zählt nur der Verbrauch, während eine Zone läuft; mit einem eigenen Gartenzähler der gesamte Verbrauch. Der Grundpreis wird in der Statistik anteilig auf den Zeitraum umgelegt.':
      'The valves are connected directly to the water mains, there is no pump. With the main meter of the house only the consumption while a zone is running counts; with a separate garden meter all of it. The base price is shared out over the period in the statistics.',
    'Noch kein Controller. Ein Controller ist eine Pumpe oder ein Wasseranschluss mit Zonen und Sequenzen.': 'No controller yet. A controller is a pump or a water connection with its zones and sequences.',
    // Statistik: Wasser, Strom, Kosten
    '{l} Liter': '{l} litres', 'Kosten': 'Costs', 'Wasser {eur}': 'water {eur}', 'Abwasser {eur}': 'wastewater {eur}', 'Grundpreis {eur}': 'base price {eur}', 'Strom {eur}': 'electricity {eur}', 'Strom': 'Electricity',
    'Wasser je Tag (L)': 'Water per day (L)', 'Wasser je Monat (L)': 'Water per month (L)', 'Strom je Tag (kWh)': 'Electricity per day (kWh)', 'Strom je Monat (kWh)': 'Electricity per month (kWh)',
    // Smarte Laufzeit (experimentell)
    'Smarte Laufzeit': 'Smart run time', 'experimentell': 'experimental', 'Smarte Laufzeit je Zone verwenden': 'Use smart run time per zone',
    'Jede Zone bekommt Zonentyp, Pflanzenfaktor (Kc), eigenen Bodenspeicher, Gießweise (täglich oder tief ab Schwelle) und Beregnungsleistung (von Hand, aus Durchfluss und Fläche oder gemessen mit dem Wasserzähler). Die Laufzeit wird in Minuten berechnet und kann in Durchgänge aufgeteilt werden. Noch nicht in einer ganzen Saison erprobt. Aus = Verhalten wie bisher.':
      'Every zone gets a zone type, crop coefficient (Kc), its own soil storage, a watering mode (daily or deep from a threshold) and an application rate (manual, from flow and area or measured with the water meter). The run time is calculated in minutes and can be split into cycles. Not yet tested over a whole season. Off = behaviour as before.',
    'smart': 'smart', 'nach Bedarf': 'as needed', 'auf Höchstlaufzeit begrenzt': 'limited to the maximum run time', 'Boden feucht genug (fehlt {fehlt} von {schwelle} mm)': 'soil moist enough ({fehlt} of {schwelle} mm missing)',
    'kein Bedarf': 'no demand', 'Rasen': 'Lawn', 'Beet/Stauden': 'Beds/perennials', 'Hecke/Sträucher': 'Hedge/shrubs', 'Gemüse/Kübel': 'Vegetables/pots', 'Benutzerdefiniert': 'Custom',
    'von {mm} mm': 'of {mm} mm', 'Referenzmenge': 'reference amount', 'Durchfluss ÷ Fläche': 'flow ÷ area', 'von Hand': 'manual', 'Schwelle': 'Threshold', 'Leistung': 'Rate',
    'Smarte Laufzeit: Bilanz je Zone mit Pflanzenfaktor (Kc × ET₀) und eigenem Bodenspeicher. Bedarf = Defizit + Kc × Verdunstung der nächsten 24 h − wirksamer Regen. „Tief gießen“ läuft erst, wenn das Defizit die Schwelle erreicht. Laufzeit = Bedarf ÷ Beregnungsleistung, höchstens die Höchstlaufzeit; dazu kommen Plan-% und Grundfaktor. Mit Wasserzähler und Fläche wird die gemessene Menge gutgeschrieben.':
      'Smart run time: balance per zone with crop coefficient (Kc × ET₀) and its own soil storage. Demand = deficit + Kc × evaporation of the next 24 h − effective rain. “Deep watering” only runs once the deficit reaches the threshold. Run time = demand ÷ application rate, at most the maximum run time; plan % and base factor are applied on top. With a water meter and an area the measured amount is credited.',
    'Zonentyp': 'Zone type', 'Pflanzenfaktor (Kc)': 'Crop coefficient (Kc)', 'Fläche': 'Area', 'Gießweise': 'Watering mode', 'täglich nach Bedarf': 'daily as needed',
    'tief gießen ab Schwelle': 'deep watering from a threshold', 'Schwelle (Defizit)': 'Threshold (deficit)', 'von Hand (mm/h)': 'manual (mm/h)',
    'aus Durchfluss und Fläche': 'from flow and area', 'gemessen mit dem Wasserzähler': 'measured with the water meter', 'Höchstlaufzeit': 'Maximum run time',
    'In Durchgänge aufteilen (Cycle & Soak)': 'Split into cycles (cycle & soak)', 'Höchstens je Durchgang': 'At most per cycle', 'Sickerpause nach Durchgang': 'Soak pause after a cycle',
    'Durchfluss': 'Flow', 'Durchfluss (Startwert)': 'Flow (initial value)', 'gemessen: {lmin} L/min aus {n} Läufen': 'measured: {lmin} L/min from {n} runs',
    '{n} von 3 Läufen gemessen': '{n} of 3 runs measured',
    'Kosten je Tag (€)': 'Costs per day (€)', 'Kosten je Monat (€)': 'Costs per month (€)', 'Laufzeit und Wasser je Zone': 'Run time and water per zone',
  },
};
let SPRACHE = 'de';
let LOCALE = 'de-DE';
const FEHLEND = new Set();   // Texte ohne Übersetzung (für tests/js_render.py)

function t(text, werte) {
  let s = text;
  if (SPRACHE !== 'de') {
    const tab = TEXTE[SPRACHE] || TEXTE.en;
    if (text in tab) s = tab[text]; else FEHLEND.add(text);
  }
  return werte ? s.replace(/\{(\w+)\}/g, (_, k) => (werte[k] ?? '')) : s;
}
const kurz = () => KURZ[SPRACHE] || KURZ.en;
const monatKurz = (i) => kurz().monate[i];
const tagKurz = (i) => kurz().tage[i];                   // 0 = Montag
const wochentag = (d) => kurz().tage[(d.getDay() + 6) % 7];
const BEZUG = ['sonnenaufgang', 'sonnenuntergang', 'uhrzeit'];
const BEZUG_TEXT = { sonnenaufgang: 'Sonnenaufgang', sonnenuntergang: 'Sonnenuntergang', uhrzeit: 'feste Uhrzeit' };

const TABS = [
  { id: 'uebersicht', label: 'Übersicht', icon: 'mdi:view-dashboard-outline' },
  { id: 'automatik', label: 'Automatik', icon: 'mdi:calendar-clock' },
  { id: 'manuell', label: 'Manuell', icon: 'mdi:gesture-tap-button' },
  { id: 'wetter', label: 'Wetter', icon: 'mdi:weather-partly-rainy' },
  { id: 'statistik', label: 'Statistik', icon: 'mdi:chart-bar' },
  { id: 'einstellungen', label: 'Einstellungen', icon: 'mdi:cog-outline', admin: true },
];

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const num = (v, d = null) => { const n = parseFloat(v); return Number.isFinite(n) ? n : d; };
const fmt = (v, nk = 0) => (v == null ? '–' : Number(v).toLocaleString(LOCALE, { minimumFractionDigits: nk, maximumFractionDigits: nk }));
const tiefKopie = (o) => JSON.parse(JSON.stringify(o));
const zufall = (praefix) => `${praefix}${Math.random().toString(16).slice(2, 10)}`;

function dauerSek(s) {
  if (s == null) return null;
  if (typeof s === 'number') return s;
  let tage = 0;
  const m = String(s).match(/(\d+)\s+day[s]?,\s*(.*)/);
  if (m) { tage = +m[1]; s = m[2]; }
  const z = String(s).split(':').map(Number);
  if (z.some((x) => !Number.isFinite(x))) return null;
  while (z.length < 3) z.unshift(0);
  return tage * 86400 + z[0] * 3600 + z[1] * 60 + z[2];
}
function fmtDauer(sek) {
  if (sek == null) return '–';
  sek = Math.max(0, Math.round(sek));
  const h = Math.floor(sek / 3600), m = Math.floor((sek % 3600) / 60), s = sek % 60;
  if (h) return `${h}:${String(m).padStart(2, '0')} h`;
  return `${m}:${String(s).padStart(2, '0')} min`;
}
function fmtMin(min) {
  if (min == null) return '–';
  min = Math.round(min);
  if (min >= 60) return `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')} min`;
  return `${min} min`;
}
function fmtZeit(d, mitTag = true) {
  if (!d) return '–';
  d = d instanceof Date ? d : new Date(d);
  if (isNaN(d)) return '–';
  const heute = new Date(); heute.setHours(0, 0, 0, 0);
  const tag = new Date(d); tag.setHours(0, 0, 0, 0);
  const diff = Math.round((tag - heute) / 86400000);
  const uhr = d.toLocaleTimeString(LOCALE, { hour: '2-digit', minute: '2-digit' });
  if (!mitTag) return uhr;
  if (diff === 0) return t('heute {uhr}', { uhr });
  if (diff === 1) return t('morgen {uhr}', { uhr });
  if (diff === -1) return t('gestern {uhr}', { uhr });
  return `${wochentag(d)} ${d.toLocaleDateString(LOCALE, { day: '2-digit', month: '2-digit' })} ${uhr}`;
}
function relativ(d) {
  if (!d) return '';
  const min = Math.round((new Date(d) - Date.now()) / 60000);
  const a = Math.abs(min);
  const z = a < 60 ? `${a} min` : a < 2880 ? `${Math.round(a / 60)} h` : t('{n} Tagen', { n: Math.round(a / 1440) });
  return min >= 0 ? t('in {t}', { t: z }) : t('vor {t}', { t: z });
}
function achse(max) {
  if (!(max > 0)) return { max: 1, schritt: 0.5 };
  const roh = max / 4;
  const p = Math.pow(10, Math.floor(Math.log10(roh)));
  const schritt = [1, 2, 2.5, 5, 10].map((f) => f * p).find((s) => s >= roh);
  return { max: Math.ceil(max / schritt) * schritt, schritt };
}
function versatzText(min) {
  const a = Math.abs(min);
  return `${Math.floor(a / 60)}:${String(a % 60).padStart(2, '0')} h ${t(min < 0 ? 'vor' : 'nach')}`;
}
function planZeitText(zeit) {
  if (!zeit) return '';
  if (zeit.bezug === 'uhrzeit') return t('um {zeit} Uhr', { zeit: zeit.uhrzeit });
  return `${versatzText(zeit.versatz_min)} ${t(BEZUG_TEXT[zeit.bezug])}`;
}

// Diagnose: Fehler sammeln, im Panel anzeigen und ins HA-Log schreiben
const DIAGNOSE = { fehler: [], panel: null };
const fehlerMelden = (text) => {
  DIAGNOSE.fehler.push(text);
  if (DIAGNOSE.panel) DIAGNOSE.panel._fehler(text);
};
window.addEventListener('error', (e) => {
  if (String(e.filename || '').includes('irrigation-app')) fehlerMelden(`${e.message} (${e.filename}:${e.lineno}:${e.colno})`);
});
window.addEventListener('unhandledrejection', (e) => {
  const r = e.reason;
  if (r && String(r.stack || '').includes('irrigation-app')) fehlerMelden(`Promise: ${r.message || r}`);
});

// Logo-Ziel: nur HA-Pfade (/…, nicht //…) oder http(s)-Adressen, sonst null (kein Link)
const logoZiel = (wert) => (typeof wert === 'string' && /^(\/(?!\/)|https?:\/\/)\S*$/i.test(wert.trim()) ? wert.trim() : null);

class BeregnungPanel extends HTMLElement {
  constructor() {
    super();
    this._tab = 'uebersicht';
    this._sig = '';
    this._busy = false;
    this._statZeitraum = 'woche';
    this._statDaten = null;
    this._statLaedt = false;
    this._man = {};            // je Controller: { zonen: Set, prozent }
    this.attachShadow({ mode: 'open' });
    try { this._tab = localStorage.getItem('beregnung-tab') || this._tab; } catch (e) { /* egal */ }
    if (!TABS.some((x) => x.id === this._tab)) this._tab = 'uebersicht';
    this._tabAusAdresse();
    this.shadowRoot.innerHTML = '<div style="min-height:100vh;background:#0a0e1a;color:#8b92a7;font-family:sans-serif;display:flex;align-items:center;justify-content:center">…</div>';
    // Beim Neuladen direkt auf die Panel-Adresse (z. B. Wischen in der iOS-App) setzt HA
    // hass/narrow, bevor dieses Modul geladen ist → hier übernehmen.
    for (const p of ['narrow', 'hass']) {
      if (Object.prototype.hasOwnProperty.call(this, p)) {
        const v = this[p];
        delete this[p];
        this[p] = v;
      }
    }
  }

  set hass(hass) {
    const erst = !this._hass;
    this._hass = hass;
    try {
      const neueSprache = this._spracheAus(hass);
      if (erst) {
        this._aufbau();
        DIAGNOSE.panel = this;
        DIAGNOSE.fehler.forEach((f) => this._fehler(f));
        this._abonnieren();
      } else if (neueSprache) {
        this._aufbau();
        this._sig = '';
        this._zeichnen();
        return;
      }
      if (this._tab === 'einstellungen' && this._cfg) return;
      const sig = this._signatur();
      if (sig !== this._sig && !this._busy && !this._fokus()) {
        this._sig = sig;
        this._zeichnen();
      }
    } catch (e) {
      this._fehler(`${e.message}\n${e.stack || ''}`);
    }
  }
  get hass() { return this._hass; }

  // Sprache aus HA übernehmen; true, wenn sie sich geändert hat
  _spracheAus(hass) {
    const tag = String(hass?.locale?.language || hass?.language || 'en');
    const sprache = tag.toLowerCase().startsWith('de') ? 'de' : 'en';
    const geaendert = sprache !== SPRACHE || tag !== LOCALE;
    SPRACHE = sprache;
    LOCALE = tag;
    return geaendert;
  }

  set narrow(v) {
    this._narrow = v;
  }

  connectedCallback() {
    this._ticker = setInterval(() => this._tick(), 1000);
    if (this._hass && !this._abo) this._abonnieren();
    // HA verwendet das Element beim erneuten Aufruf wieder → Reiter aus der Adresse auch hier
    if (this._tabAusAdresse() && this._hass) this._zeichnen();
  }

  // /irrigation?tab=<id> öffnet diesen Reiter (z. B. Tunet-Karte → „uebersicht“).
  // Der Parameter wird danach aus der Adresse entfernt; true = Reiter gewechselt.
  _tabAusAdresse() {
    try {
      const params = new URLSearchParams(location.search);
      const wunsch = params.get('tab');
      if (!wunsch) return false;
      params.delete('tab');
      const rest = params.toString();
      history.replaceState(history.state, '', `${location.pathname}${rest ? `?${rest}` : ''}${location.hash}`);
      if (!TABS.some((x) => x.id === wunsch) || wunsch === this._tab) return false;
      this._tab = wunsch;
      try { localStorage.setItem('beregnung-tab', wunsch); } catch (e) { /* egal */ }
      return true;
    } catch (e) {
      return false;
    }
  }
  disconnectedCallback() {
    clearInterval(this._ticker);
    if (this._abo) { this._abo.then((ab) => ab && ab()).catch(() => {}); this._abo = null; }
  }

  _log(level, message) {
    try {
      this._hass.callService('system_log', 'write', { message: `IU Irrigation Dashboard panel: ${message}`, level, logger: 'iu_irrigation_dashboard.panel' });
    } catch (e) { /* egal */ }
  }
  _fehler(text) {
    this._gemeldet = this._gemeldet || new Set();
    if (this._gemeldet.has(text)) return;
    this._gemeldet.add(text);
    if (this._hass) this._log('error', `${text} | ${navigator.userAgent}`);
    const ziel = this.shadowRoot.querySelector('#inhalt') || this.shadowRoot;
    const box = document.createElement('pre');
    box.className = 'fehlerbox';
    box.style.cssText = 'white-space:pre-wrap;background:#3b1111;color:#fca5a5;border:1px solid #ef4444;border-radius:8px;padding:12px;margin:12px;font-size:12px;';
    box.textContent = t('Fehler im Panel: {text}', { text });
    ziel.prepend(box);
  }

  // ── Daten der Integration ──────────────────────────────────────────
  _abonnieren() {
    if (this._abo || !this._hass?.connection) return;
    this._abo = this._hass.connection.subscribeMessage((msg) => {
      // Fingerabdruck der App: ändert er sich (Update mit Neustart), ist diese
      // offene Seite veraltet → Hinweis statt Absturz mit neuem Datenformat
      const app = msg.status?.app;
      if (app && this._app == null) this._app = app;
      else if (app && app !== this._app) { this._veraltet = true; this._zeichnen(); return; }
      this._cfg = msg;
      this._cfgFehler = null;
      if (!this._entwurfGeaendert) this._entwurf = null;
      this._sig = '';
      if (this._tab !== 'einstellungen' || !this._entwurfGeaendert) this._zeichnen();
      else this._statusLeiste();
    }, { type: 'iu_irrigation_dashboard/abonnieren' }).catch((e) => {
      this._abo = null;
      this._cfgFehler = e.message || String(e);
      this._zeichnen();
    });
  }
  _ws(type, daten = {}) {
    return this._hass.callWS({ type, ...daten }).catch((e) => {
      this._meldung(t('Fehler: {text}', { text: e.message || e }), true);
      throw e;
    });
  }
  _aendern(aenderungen) { return this._ws('iu_irrigation_dashboard/aendern', { aenderungen }).catch(() => {}); }

  _e() { return this._cfg?.einstellungen || { controller: [], wetter: {}, iu: {} }; }
  _z() { return this._cfg?.zustand || {}; }
  _zu() { return this._z().zuordnung || { controller: {}, zonen: {}, sequenzen: {}, zone_nr: {} }; }
  _ctlListe() { return this._e().controller || []; }
  _ctl(id) { return this._ctlListe().find((c) => c.id === id); }

  _s(id) { return id ? this._hass?.states[id] : undefined; }
  _st(id) { return this._s(id)?.state; }
  _a(id, k) { return this._s(id)?.attributes?.[k]; }
  _an(id) { return this._st(id) === 'on'; }
  _offen(id) { return IST_AN.includes(this._st(id)); }

  _hahnAktiv(z) { return z.wasserhahn && z.betrieb === 'wasserhahn'; }
  _leitung(ctl) { return ctl?.anschluss === 'leitung'; }
  _smart() { return !!this._e().smart?.aktiv; }
  // gemessener Durchfluss einer Zone (Median der letzten 5 Läufe, ab 3)
  _messungText(z) {
    const m = ((this._z().durchfluss || {})[z.id] || []).slice(-5).filter((x) => x > 0);
    if (!m.length) return '';
    if (m.length < 3) return esc(t('{n} von 3 Läufen gemessen', { n: m.length }));
    const s = [...m].sort((a, b) => a - b);
    const lmin = s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
    const fl = z.smart?.flaeche_m2;
    return esc(t('gemessen: {lmin} L/min aus {n} Läufen', { lmin: fmt(lmin, 1), n: m.length })) + (fl ? ` = ${fmt((lmin * 60) / fl, 1)} mm/h` : '');
  }
  // Grund der smarten Laufzeit; unter der Schwelle mit den Zahlen
  _grundText(d) {
    if (!d?.grund) return '';
    if (d.grund === 'unter_schwelle') return t('Boden feucht genug (fehlt {fehlt} von {schwelle} mm)', { fehlt: fmt(d.defizit, 1), schwelle: fmt(d.schwelle, 1) });
    return t(GRUND_TEXT[d.grund] || '');
  }
  _wasserKosten(ctl, liter) {
    const w = ctl.wasser || {};
    const preis = (w.preis_m3 || 0) + (w.abwasser_m3 || 0);
    return this._leitung(ctl) && liter != null && preis ? (liter / 1000) * preis : null;
  }
  _ventilOffen(z) { return z.ventile.some((v) => this._offen(v)) || this._an(this._zu().zonen[z.id]); }
  _inAutomatik(ctl, z) {
    return !this._hahnAktiv(z) && (ctl.sequenzen || []).some((s) => s.zonen.some((sz) => sz.zone === z.id && sz.aktiv));
  }
  // aus | standby (an, kein Wasserbezug) | laeuft (Leistung > Schwelle)
  _pumpe(ctl) {
    // Wasseranschluss: Leitung steht immer unter Druck, „läuft“ = ein Ventil ist offen
    if (this._leitung(ctl)) return (ctl.zonen || []).some((z) => this._ventilOffen(z)) ? 'laeuft' : 'standby';
    const p = ctl.pumpe || {};
    if (!this._offen(p.entity_id)) return 'aus';
    if (!p.leistung) return 'laeuft';
    return num(this._st(p.leistung), 0) > num(p.schwelle_w, 50) ? 'laeuft' : 'standby';
  }
  _ctlLaeuft(ctl) { return this._an(this._zu().controller[ctl.id]) || !!(this._z().manuell || {})[ctl.id]; }
  _laeuft() { return this._ctlListe().some((c) => this._ctlLaeuft(c)); }

  _aktuellerLauf(ctl) {
    const zu = this._zu();
    const ce = zu.controller[ctl.id];
    const a = this._s(ce)?.attributes;
    if (!a || this._st(ce) !== 'on' || !a.current_start) return null;
    const start = new Date(a.current_start);
    const dauer = dauerSek(a.current_duration);
    const zone = (ctl.zonen || []).find((z) => z.name === a.current_name);
    const manuell = (this._z().manuell || {})[ctl.id];
    const seq = (ctl.sequenzen || []).find((s) => this._an(zu.sequenzen[s.id]));
    const plan = manuell ? t('Manueller Lauf') : seq ? t('Automatik · {name}', { name: seq.name }) : t('Einzellauf');
    return { name: zone ? zone.name : a.current_name, zoneId: zone?.id, start, ende: dauer != null ? new Date(start.getTime() + dauer * 1000) : null, plan };
  }

  _signatur() {
    const ids = ['sun.sun'];
    const zu = this._zu();
    ids.push(...Object.values(zu.controller), ...Object.values(zu.zonen), ...Object.values(zu.sequenzen));
    for (const c of this._ctlListe()) {
      ids.push(c.pumpe.entity_id, c.pumpe.leistung, c.wasser?.zaehler, ...c.zonen.flatMap((z) => z.ventile));
    }
    return ids.filter(Boolean).map((id) => { const s = this._s(id); return s ? s.last_updated : '-'; }).join('|');
  }
  _fokus() {
    const a = this.shadowRoot.activeElement;
    return a && (a.tagName === 'INPUT' || a.tagName === 'SELECT') && a.type !== 'checkbox' && a.type !== 'range';
  }
  _dienst(domain, service, data) {
    return this._hass.callService(domain, service, data).catch((e) => this._meldung(t('Fehler: {text}', { text: e.message || e }), true));
  }
  _meldung(text, fehler = false) {
    const m = this.shadowRoot.querySelector('#meldung');
    if (!m) return;
    m.textContent = text;
    m.className = `meldung sichtbar${fehler ? ' fehler' : ''}`;
    clearTimeout(this._meldungTimer);
    this._meldungTimer = setTimeout(() => { m.className = 'meldung'; }, 4000);
  }

  // ── Grundgerüst ─────────────────────────────────────────────────────
  _aufbau() {
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="app">
        <header>
          <button id="logo" class="logo"><ha-icon icon="mdi:sprinkler-variant"></ha-icon><span class="logo-text">${t('Beregnung')}</span></button>
          <nav>${TABS.filter((x) => !x.admin || this._hass?.user?.is_admin).map((x) => `<button class="nav" data-tab="${x.id}"><ha-icon icon="${x.icon}"></ha-icon><span>${t(x.label)}</span></button>`).join('')}</nav>
          <div id="kopfstatus" class="kopfstatus"></div>
        </header>
        <main id="inhalt"></main>
        <div id="tip" class="tip"></div>
        <div id="meldung" class="meldung"></div>
      </div>`;
    const root = this.shadowRoot;
    root.querySelector('#logo').addEventListener('click', () => {
      const ziel = logoZiel(this._cfg?.einstellungen?.anzeige?.logo_link);
      if (!ziel) return;
      if (/^https?:\/\//i.test(ziel)) { window.location.href = ziel; return; }
      history.pushState(null, '', ziel);
      window.dispatchEvent(new CustomEvent('location-changed', { detail: { replace: false } }));
    });
    root.querySelectorAll('.nav').forEach((b) => b.addEventListener('click', () => {
      this._tab = b.dataset.tab;
      try { localStorage.setItem('beregnung-tab', this._tab); } catch (e) { /* egal */ }
      this._zeichnen();
    }));
    const inhalt = root.querySelector('#inhalt');
    inhalt.addEventListener('click', (ev) => this._klick(ev));
    inhalt.addEventListener('change', (ev) => this._aenderung(ev));
    inhalt.addEventListener('input', (ev) => this._eingabe(ev));
    inhalt.addEventListener('pointerdown', (ev) => { if (ev.target.type === 'range') this._busy = true; });
    const tip = root.querySelector('#tip');
    inhalt.addEventListener('pointermove', (ev) => {
      const el = ev.composedPath().find((n) => n.dataset && n.dataset.tip);
      if (!el) { tip.style.opacity = 0; return; }
      tip.innerHTML = el.dataset.tip;
      tip.style.opacity = 1;
      const w = tip.offsetWidth, h = tip.offsetHeight;
      let x = ev.clientX + 14, y = ev.clientY - h - 10;
      if (x + w > window.innerWidth - 8) x = ev.clientX - w - 14;
      if (y < 8) y = ev.clientY + 16;
      tip.style.transform = `translate(${x}px, ${y}px)`;
    });
    inhalt.addEventListener('pointerleave', () => { tip.style.opacity = 0; });
  }

  _zeichnen() {
    const root = this.shadowRoot;
    root.querySelectorAll('.nav').forEach((b) => b.classList.toggle('aktiv', b.dataset.tab === this._tab));
    const logo = root.querySelector('#logo');
    if (logo) {
      const ziel = logoZiel(this._cfg?.einstellungen?.anzeige?.logo_link);
      logo.classList.toggle('link', !!ziel);
      logo.title = ziel ? t('Zur Startseite') : '';
    }
    const kopf = root.querySelector('#kopfstatus');
    if (kopf) kopf.innerHTML = this._cfg ? this._kopfstatus() : '';
    const inhalt = root.querySelector('#inhalt');
    if (!inhalt) return;
    const fn = {
      uebersicht: () => this._uebersicht(),
      automatik: () => this._automatik(),
      manuell: () => this._manuell(),
      wetter: () => this._wetter(),
      statistik: () => this._statistik(),
      einstellungen: () => this._einstellungen(),
    }[this._tab] || (() => this._uebersicht());
    try {
      if (this._veraltet) {
        inhalt.innerHTML = `<section class="karte"><p class="leer">${t('Das Panel wurde aktualisiert.')}<br><br><button class="knopf blau" data-aktion="neu-laden"><ha-icon icon="mdi:refresh"></ha-icon>${t('Neu laden')}</button></p></section>`;
        return;
      }
      if (this._cfgFehler) {
        inhalt.innerHTML = `<section class="karte"><p class="leer">${esc(t('Die Integration „IU Irrigation Dashboard“ ist nicht eingerichtet ({fehler}).', { fehler: this._cfgFehler }))}<br>${esc(t('Einstellungen → Geräte & Dienste → Integration hinzufügen → „IU Irrigation Dashboard“.'))}</p></section>`;
        return;
      }
      if (!this._cfg) {
        inhalt.innerHTML = `<section class="karte"><p class="leer pulsiert">${t('Lade Einstellungen …')}</p></section>`;
        return;
      }
      if (!this._ctlListe().length && this._tab !== 'einstellungen') {
        inhalt.innerHTML = `<section class="karte"><p class="leer">${t('Noch kein Controller angelegt.')}${this._hass?.user?.is_admin ? t(' Unter „Einstellungen“ einen Controller mit Pumpe und Zonen anlegen.') : ''}</p></section>`;
        return;
      }
      inhalt.innerHTML = fn();
    } catch (e) {
      inhalt.innerHTML = '';
      this._fehler(`${this._tab}: ${e.message}\n${e.stack || ''}`);
      return;
    }
    if (this._tab === 'statistik' && !this._statDaten && !this._statLaedt) this._statLaden();
    this._tick();
  }

  // Stand des Wasserzählers am Wasseranschluss: { wert, einheit } oder null
  _zaehlerStand(c) {
    const z = this._leitung(c) ? c.wasser?.zaehler : null;
    const wert = z ? num(this._st(z)) : null;
    if (wert == null) return null;
    const einheit = this._a(z, 'unit_of_measurement') || '';
    return { wert: fmt(wert, einheit === 'm³' || einheit === 'm3' ? 3 : 0), einheit };
  }
  _pumpeText(c, pz, mitStand = true) {
    if (this._leitung(c)) {
      const stand = mitStand ? this._zaehlerStand(c) : null;
      return `${t(pz === 'laeuft' ? 'fließt' : 'bereit')}${stand ? ` · ${stand.wert} ${stand.einheit}` : ''}`;
    }
    const w = num(this._st(c.pumpe.leistung));
    return pz === 'aus' ? t('aus') : `${t(pz === 'laeuft' ? 'läuft' : 'bereit')}${w != null ? ` · ${fmt(w)} W` : ''}`;
  }

  _kopfstatus() {
    const pills = this._ctlListe().map((c) => {
      const pz = this._pumpe(c);
      const leitung = this._leitung(c);
      const name = this._ctlListe().length > 1 ? `${c.name}: ` : `${t(leitung ? 'Wasser' : 'Pumpe')} `;
      const titel = t(leitung ? 'Wasseranschluss {name}' : 'Pumpe {name}', { name: c.name });
      const klasse = leitung ? (pz === 'laeuft' ? 'blau live' : '') : `${pz !== 'aus' ? 'gruen' : ''} ${pz === 'laeuft' ? 'live' : ''}`;
      return `<span class="pill ${klasse}" title="${esc(titel)}"><ha-icon icon="${leitung ? 'mdi:water-pump-off' : 'mdi:pump'}"></ha-icon>${esc(name)}${this._pumpeText(c, pz)}</span>`;
    }).join('');
    return `${pills}${this._laeuft() ? `<span class="pill blau live"><ha-icon icon="mdi:water"></ha-icon>${t('Beregnung läuft')}</span>` : ''}`;
  }

  _tick() {
    const root = this.shadowRoot;
    const jetzt = Date.now();
    root.querySelectorAll('[data-ende]').forEach((el) => { el.textContent = fmtDauer((+el.dataset.ende - jetzt) / 1000); });
    root.querySelectorAll('[data-fortschritt]').forEach((el) => {
      const [s, e] = el.dataset.fortschritt.split(',').map(Number);
      el.style.width = `${Math.min(100, Math.max(0, ((jetzt - s) / (e - s)) * 100))}%`;
    });
  }

  _kachel(label, wert, einheit, sub, farbe, icon) {
    return `
      <div class="kachel ${farbe}">
        <div class="kachel-kopf"><ha-icon icon="${icon}"></ha-icon><span>${esc(label)}</span></div>
        <div class="kachel-wert">${esc(wert)}${einheit ? `<span class="einheit">${esc(einheit)}</span>` : ''}</div>
        <div class="sub">${sub}</div>
      </div>`;
  }
  _laufBox(lauf) {
    return `
      <div class="laufbox">
        <div class="laufkopf">
          <div><div class="lauf-name">${esc(lauf.name)}</div><div class="sub">${esc(lauf.plan)} · ${t('Start {zeit}', { zeit: fmtZeit(lauf.start, false) })}</div></div>
          <div class="lauf-rest">${lauf.ende ? `<span data-ende="${lauf.ende.getTime()}"></span><div class="sub">${t('Restzeit')}</div>` : ''}</div>
        </div>
        ${lauf.ende ? `<div class="balken"><div data-fortschritt="${lauf.start.getTime()},${lauf.ende.getTime()}"></div></div>` : ''}
      </div>`;
  }
  _hahnModus(z) {
    const hahn = this._hahnAktiv(z);
    return `
      <div class="modus" role="group" aria-label="${esc(z.name)}">
        <span class="modus-titel">${esc(z.name)}</span>
        <button class="modus-knopf ${hahn ? 'an' : ''}" data-aktion="betrieb" data-zone="${esc(z.id)}" data-betrieb="wasserhahn" aria-pressed="${hahn}" title="${t('Ventil offen, solange die Pumpe läuft')}"><ha-icon icon="mdi:water-pump"></ha-icon>${t('Wasserhahn')}</button>
        <button class="modus-knopf ${hahn ? '' : 'an'}" data-aktion="betrieb" data-zone="${esc(z.id)}" data-betrieb="beregnung" aria-pressed="${!hahn}" title="${t('Läuft in der Automatik mit')}"><ha-icon icon="mdi:sprinkler-variant"></ha-icon>${t('Beregnung')}</button>
      </div>`;
  }

  // ── Anlagenbild je Controller ───────────────────────────────────────
  _anlage(ctl, vertikal) {
    const zonen = ctl.zonen;
    const pz = this._pumpe(ctl);
    const pumpe = pz !== 'aus';
    const pumpt = pz === 'laeuft';
    const offen = zonen.map((z) => this._ventilOffen(z));
    const fliesst = pumpt && offen.some(Boolean);
    // im Anlagenbild steht der Zählerstand im Kreis, darunter nur der Zustand
    const pumpeText = this._pumpeText(ctl, pz, false);
    const lauf = this._aktuellerLauf(ctl);
    const zoneInfo = (z, i) => {
      if (lauf && lauf.zoneId === z.id && lauf.ende) return `<tspan class="rest" data-ende="${lauf.ende.getTime()}"></tspan>`;
      if (this._hahnAktiv(z)) return t(offen[i] ? 'Wasserhahn offen' : 'Wasserhahn zu');
      if (offen[i]) return t(pumpt ? 'läuft' : 'Ventil offen');
      return this._inAutomatik(ctl, z) ? `${z.standard_min} min` : t('nur manuell');
    };
    const ventil = (x, y, auf, rot) => `
      <g transform="translate(${x} ${y}) rotate(${rot})" class="ventil ${auf ? 'auf' : ''}">
        <path d="M-11 -9 L11 9 L11 -9 L-11 9 Z"/><line x1="0" y1="0" x2="0" y2="-15"/><rect x="-7" y="-21" width="14" height="6" rx="2"/>
      </g>`;
    // Sprühfächer: Tropfen fliegen in fünf Strahlen aus der Düse, dahinter ein Nebelkegel
    const regner = (x, y, aktiv, richtung, druck) => {
      const rechts = richtung === 'rechts';
      const basis = richtung === 'oben' ? -90 : richtung === 'unten' ? 90 : 0;
      const winkel = rechts ? [-44, -22, 0, 22, 44] : [-60, -30, 0, 30, 60];
      const weite = rechts ? 26 : 30;
      const rad = (g) => (g * Math.PI) / 180;
      const a1 = rad(basis + winkel[0] - 8), a2 = rad(basis + winkel[winkel.length - 1] + 8);
      const nebel = `<path class="nebel" d="M${x} ${y} L${x + weite * Math.cos(a1)} ${y + weite * Math.sin(a1)} A${weite} ${weite} 0 0 1 ${x + weite * Math.cos(a2)} ${y + weite * Math.sin(a2)} Z"/>`;
      const strahlen = winkel.map((w, j) => `<g transform="translate(${x} ${y}) rotate(${basis + w})">${[0, 1, 2].map((k) =>
        `<circle class="tropfen ${rechts ? 'kurz' : ''}" r="${k === 1 ? 2.4 : 1.9}" style="animation-delay:${(j * 0.17 + k * 0.4).toFixed(2)}s"/>`).join('')}</g>`).join('');
      return `<g class="regner ${aktiv || druck ? 'aktiv' : ''}">${aktiv ? nebel + strahlen : ''}<circle class="duese" cx="${x}" cy="${y}" r="8"/></g>`;
    };
    // Wasserhahn (Zone im Wasserhahn-Betrieb): Gehäuse am Rohrende, Hebel,
    // Auslauf nach rechts unten; bei Wasserfluss fallen Tropfen aus dem Auslauf
    const hahn = (x, y, aktiv, richtung, druck) => {
      const hebel = richtung === 'rechts'
        ? '<rect class="hebel" x="-8" y="-15" width="16" height="5" rx="2"/><line x1="0" y1="-10" x2="0" y2="-8"/>'
        : '<rect class="hebel" x="-19" y="-2.5" width="10" height="5" rx="2"/><line x1="-9" y1="0" x2="-7" y2="0"/>';
      const tropfen = aktiv ? [0, 1, 2].map((k) => `<circle class="hahn-tropfen" cx="21" cy="8" r="${k === 1 ? 2.4 : 2}" style="animation-delay:${(k * 0.33).toFixed(2)}s"/>`).join('') : '';
      return `<g class="hahn ${aktiv || druck ? 'aktiv' : ''}" transform="translate(${x} ${y}) scale(${richtung === 'rechts' ? 1.2 : 1.5})">
        <rect class="koerper" x="-8" y="-8" width="16" height="16" rx="4"/>${hebel}
        <path class="auslauf" d="M8 -3 H17 Q21 -3 21 1 V5"/>${tropfen}</g>`;
    };
    const pumpenSymbol = (x, y) => `
      <g class="pumpe ${pumpe ? 'an' : ''} ${pumpt ? 'dreht' : ''}" transform="translate(${x} ${y})">
        <title>${t('Pumpe')} ${pumpeText}</title><circle r="30"/>
        <g class="rad"><path d="M0 -20 L5 -4 L20 0 L4 5 L0 20 L-5 4 L-20 0 L-4 -5 Z"/></g><circle r="4" class="nabe"/>
      </g>`;
    // Wasseranschluss: Zähler statt Pumpe, Hausanschluss statt Brunnen
    const leitung = this._leitung(ctl);
    const quelleName = t(leitung ? 'Wasseranschluss' : 'Pumpe');
    const stand = this._zaehlerStand(ctl);
    const zaehlerSymbol = (x, y) => `
      <g class="zaehler-symbol ${pumpt ? 'an' : ''}" transform="translate(${x} ${y})">
        <title>${quelleName} ${this._pumpeText(ctl, pz)}</title><circle r="30"/>
        ${stand ? `<text y="0" class="wert">${esc(stand.wert)}</text><text y="14" class="einheit">${esc(stand.einheit)}</text>` : '<text y="5" class="wert">H₂O</text>'}
      </g>`;
    const quelle = leitung ? zaehlerSymbol : pumpenSymbol;
    const gesperrt = (z) => (!this._inAutomatik(ctl, z) && !this._hahnAktiv(z) ? 'gesperrt' : '');
    const letzte = Math.max(-1, ...offen.map((o, i) => (o ? i : -1)));
    const titel = esc(t('Anlagenbild {name}', { name: ctl.name }));

    if (!vertikal) {
      const DX = Math.min(88, 750 / Math.max(1, zonen.length));
      const X0 = 250, YM = 200;
      const xs = zonen.map((_, i) => X0 + i * DX);
      const xEnde = xs.length ? xs[xs.length - 1] : X0;
      const breite = Math.max(1000, xEnde + 60);
      let s = `<svg viewBox="0 0 ${breite} 400" class="anlage" role="img" aria-label="${titel}">`;
      if (leitung) {
        s += `<g class="brunnen" transform="translate(20 250)"><path d="M0 80 L0 30 L40 0 L80 30 L80 80 Z" class="wand"/></g>`;
        s += `<text x="60" y="352" class="lbl mitte">${t('Hausanschluss')}</text>`;
      } else {
        s += `<g class="brunnen" transform="translate(20 250)"><path d="M0 0 L0 70 Q0 80 10 80 L70 80 Q80 80 80 70 L80 0" class="wand"/><path d="M2 30 Q12 24 22 30 T42 30 T62 30 T78 30 L78 70 Q78 78 70 78 L10 78 Q2 78 2 70 Z" class="wasser"/></g>`;
        s += `<text x="60" y="352" class="lbl mitte">${t('Brunnen')}</text>`;
      }
      s += `<path d="M60 280 L60 ${YM} L120 ${YM}" class="rohr ${pumpe ? 'wasser' : ''}"/>`;
      if (fliesst) s += `<path d="M60 280 L60 ${YM} L120 ${YM}" class="fluss"/>`;
      s += `<path d="M180 ${YM} L${xEnde} ${YM}" class="rohr ${pumpe ? 'wasser' : ''}"/>`;
      if (fliesst && letzte >= 0) s += `<path d="M180 ${YM} L${xs[letzte]} ${YM}" class="fluss"/>`;
      // nach den Rohren zeichnen – der Kreis verdeckt die runden Rohrenden
      s += quelle(150, YM);
      s += `<text x="150" y="${YM + 52}" class="lbl mitte">${quelleName}</text><text x="150" y="${YM + 70}" class="sub mitte">${pumpeText}</text>`;
      zonen.forEach((z, i) => {
        const x = xs[i], oben = i % 2 === 0;
        // Regner mit Abstand zu Name/Laufzeit, damit der Sprühfächer sie nicht überdeckt
        const yE = oben ? 90 : 310, yV = oben ? 140 : 260;
        const nass = offen[i] && pumpe, stroemt = offen[i] && pumpt;
        s += `<g class="zone ${nass ? 'nass' : ''} ${gesperrt(z)}" data-tip="${esc(`<b>${esc(z.name)}</b><br>${t(offen[i] ? 'Ventil offen' : 'Ventil zu')}<br>${t('Standard {min} min', { min: z.standard_min })}`)}">`;
        s += `<rect x="${x - DX / 2}" y="${oben ? 0 : YM}" width="${DX}" height="${oben ? YM : 400 - YM}" class="treffer"/>`;
        s += `<path d="M${x} ${YM} L${x} ${yE}" class="rohr duenn ${nass ? 'wasser' : ''}"/>`;
        if (stroemt) s += `<path d="M${x} ${YM} L${x} ${yE}" class="fluss duenn"/>`;
        s += ventil(x, yV, offen[i], 90) + (this._hahnAktiv(z) ? hahn : regner)(x, yE, stroemt, oben ? 'oben' : 'unten', nass);
        const yT = oben ? 22 : 378;
        s += `<text x="${x}" y="${yT}" class="lbl mitte">${esc(z.name)}</text><text x="${x}" y="${oben ? yT + 17 : yT - 20}" class="sub mitte">${zoneInfo(z, i)}</text></g>`;
      });
      return s + '</svg>';
    }
    const Y0 = 150, DY = 62, XM = 60;
    const ys = zonen.map((_, i) => Y0 + i * DY);
    const yEnde = ys.length ? ys[ys.length - 1] : Y0;
    let s = `<svg viewBox="0 0 360 ${yEnde + 40}" class="anlage" role="img" aria-label="${titel}">`;
    s += `<path d="M${XM} 80 L${XM} ${yEnde}" class="rohr ${pumpe ? 'wasser' : ''}"/>`;
    if (fliesst && letzte >= 0) s += `<path d="M${XM} 80 L${XM} ${ys[letzte]}" class="fluss"/>`;
    s += quelle(XM, 50);
    s += `<text x="${XM + 45}" y="45" class="lbl">${quelleName}</text><text x="${XM + 45}" y="64" class="sub">${pumpeText}</text>`;
    zonen.forEach((z, i) => {
      const y = ys[i], nass = offen[i] && pumpe, stroemt = offen[i] && pumpt;
      s += `<g class="zone ${nass ? 'nass' : ''} ${gesperrt(z)}">`;
      s += `<path d="M${XM} ${y} L150 ${y}" class="rohr duenn ${nass ? 'wasser' : ''}"/>`;
      if (stroemt) s += `<path d="M${XM} ${y} L150 ${y}" class="fluss duenn"/>`;
      s += ventil(105, y, offen[i], 0) + (this._hahnAktiv(z) ? hahn : regner)(158, y, stroemt, 'rechts', nass);
      s += `<text x="200" y="${y - 3}" class="lbl">${esc(z.name)}</text><text x="200" y="${y + 15}" class="sub">${zoneInfo(z, i)}</text></g>`;
    });
    return s + '</svg>';
  }

  // ── Übersicht ──────────────────────────────────────────────────────
  _naechsteLaeufe() {
    const zu = this._zu();
    const liste = [];
    for (const c of this._ctlListe()) {
      if (!this._a(zu.controller[c.id], 'enabled')) continue;
      for (const s of c.sequenzen) {
        const e = zu.sequenzen[s.id];
        const ns = this._a(e, 'next_start');
        if (ns) liste.push({ ctl: c, seq: s, start: new Date(ns), dauer: dauerSek(this._a(e, 'next_duration')), plan: this._a(e, 'next_name') });
      }
    }
    return liste.sort((a, b) => a.start - b.start);
  }
  _letzteLaeufe() {
    const laeufe = this._z().laeufe || {};
    return Object.entries(laeufe).map(([id, l]) => ({ id, ...l })).sort((a, b) => new Date(b.start) - new Date(a.start));
  }
  _seqName(id) {
    if (id.startsWith('manuell_')) {
      const c = this._ctl(id.slice(8));
      return c && this._ctlListe().length > 1 ? t('Manuell · {name}', { name: c.name }) : t('Manuell');
    }
    for (const c of this._ctlListe()) { const s = c.sequenzen.find((x) => x.id === id); if (s) return s.name; }
    return id;
  }

  _uebersicht() {
    const naechste = this._naechsteLaeufe();
    const n = naechste[0];
    const letzter = this._letzteLaeufe()[0];
    const w = this._z().wetter || {};
    const laeufe = this._ctlListe().map((c) => this._aktuellerLauf(c)).filter(Boolean);
    const autoAn = this._ctlListe().some((c) => this._a(this._zu().controller[c.id], 'enabled'));
    let status, statusSub, klasse;
    if (laeufe.length) { status = laeufe.map((l) => l.name).join(', '); statusSub = laeufe.map((l) => l.plan).join(', '); klasse = 'blau'; }
    else if (!autoAn) { status = t('Automatik aus'); statusSub = t('nur manuelle Läufe'); klasse = 'gelb'; }
    else { status = t('Bereit'); statusSub = n ? t('nächster Lauf {wann}', { wann: relativ(n.start) }) : t('kein Lauf geplant'); klasse = 'gruen'; }

    const karten = this._ctlListe().map((c) => {
      const lauf = this._aktuellerLauf(c);
      const haehne = c.zonen.filter((z) => z.wasserhahn);
      return `
        <section class="karte">
          <div class="kopf"><div><ha-icon icon="mdi:pipe-valve"></ha-icon><span>${esc(c.name)}</span></div>${lauf ? '<span class="live-badge">LIVE</span>' : ''}</div>
          ${c.zonen.length ? `<div class="anlage-breit">${this._anlage(c, false)}</div><div class="anlage-schmal">${this._anlage(c, true)}</div>` : `<p class="leer">${t('Keine Zonen.')}</p>`}
          ${lauf ? this._laufBox(lauf) : ''}
          <div class="zeile-knoepfe">
            <div class="knopfgruppe senkrecht">
              ${this._leitung(c) ? '' : `<label class="schalter"><input type="checkbox" data-tagbetrieb="${esc(c.id)}" ${c.pumpe.tagbetrieb ? 'checked' : ''}><span></span>${t('Pumpe Sonnenauf- bis -untergang')}</label>`}
              ${haehne.map((z) => this._hahnModus(z)).join('')}
            </div>
            ${this._ctlLaeuft(c) ? `<button class="knopf rot" data-aktion="stopp" data-ctl="${esc(c.id)}"><ha-icon icon="mdi:stop"></ha-icon>${t('Stoppen')}</button>` : ''}
          </div>
        </section>`;
    }).join('');

    return `
      <section class="kacheln">
        ${this._kachel(t('Status'), status, '', statusSub, klasse, 'mdi:information-outline')}
        ${this._kachel(t('Nächster Lauf'), n ? fmtZeit(n.start) : '–', '', n ? `${esc(n.seq.name)}${n.plan ? ` · ${esc(n.plan)}` : ''}${n.dauer ? ` · ${fmtDauer(n.dauer)}` : ''}` : t(autoAn ? 'kein Lauf geplant' : 'Automatik aus'), 'blau', 'mdi:calendar-arrow-right')}
        ${this._kachel(t('Letzter Lauf'), letzter ? fmtZeit(letzter.start) : '–', '', letzter ? `${esc(this._seqName(letzter.id))} · ${fmtMin(letzter.dauer_min)} · ${relativ(letzter.start)}` : t('noch keiner erfasst'), 'lila', 'mdi:calendar-check')}
        ${this._kachel(t('Verdunstung'), w.et0_prognose != null ? fmt(w.et0_prognose, 1) : '–', 'mm', t('nächste 24 h · Regen heute {heute} mm, Prognose {prognose} mm', { heute: fmt(w.regen_heute, 1), prognose: fmt(w.regen_prognose, 1) }), 'tuerkis', 'mdi:weather-sunny-alert')}
      </section>
      ${karten}`;
  }

  // ── Automatik ──────────────────────────────────────────────────────
  _statusText(s) {
    const text = { off: 'bereit', on: 'läuft', disabled: 'aus', blocked: 'gesperrt (Controller aus)', suspended: 'ausgesetzt', paused: 'pausiert', delay: 'Pause zwischen Zonen' }[s];
    return text ? t(text) : s || '–';
  }

  _automatik() {
    const wt = this._e().wetter;
    const w = this._z().wetter || {};
    const kopf = `
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="mdi:weather-partly-rainy"></ha-icon><span>${t('Wasserbilanz')}</span></div>
          <label class="schalter gross"><input type="checkbox" data-wetter-aktiv ${wt.aktiv ? 'checked' : ''}><span></span>${t(wt.aktiv ? 'Laufzeit nach Wetter' : 'Wetter aus (100 %)')}</label></div>
        <div class="info-raster">
          <div><div class="sub">${t('Verdunstung gestern')}</div><div class="gross-wert">${fmt(w.et0_gestern, 1)} mm</div></div>
          <div><div class="sub">${t('Verdunstung 24 h')}</div><div class="gross-wert">${fmt(w.et0_prognose, 1)} mm</div><div class="sub">${t('Prognose')}</div></div>
          <div><div class="sub">${t('Regen heute')}</div><div class="gross-wert">${fmt(w.regen_heute, 1)} mm</div><div class="sub">${w.regnet ? t('es regnet') : ''}</div></div>
          <div><div class="sub">${t('Regen 24 h')}</div><div class="gross-wert">${fmt(w.regen_prognose, 1)} mm</div><div class="sub">${t('Prognose × Wahrscheinlichkeit')}</div></div>
        </div>
        <div class="regler">
          <div class="regler-kopf"><span>${t('Grundfaktor für alle Sequenzen')}</span><b data-anzeige="grundfaktor">${fmt(wt.grundfaktor)} %</b></div>
          <input type="range" min="0" max="200" step="5" value="${wt.grundfaktor}" data-grundfaktor>
          <div class="skala"><span>0 %</span><span>100 %</span><span>200 %</span></div>
        </div>
      </section>`;
    return kopf + this._ctlListe().map((c) => this._automatikCtl(c)).join('');
  }

  _automatikCtl(c) {
    const zu = this._zu();
    const ce = zu.controller[c.id];
    const autoAn = !!this._a(ce, 'enabled');
    const seqs = c.sequenzen.map((s) => this._automatikSeq(c, s)).join('');
    const haehne = c.zonen.filter((z) => z.wasserhahn);
    return `
      <section class="karte ctl-karte">
        <div class="kopf"><div><ha-icon icon="mdi:pump"></ha-icon><span>${esc(c.name)}</span></div>
          ${ce ? `<label class="schalter gross"><input type="checkbox" data-iu-ctl="${esc(ce)}" ${autoAn ? 'checked' : ''}><span></span>${t(autoAn ? 'Automatik an' : 'Automatik aus')}</label>` : `<span class="sub">${t('nicht in Irrigation Unlimited (Pumpe/Zonen fehlen)')}</span>`}</div>
        ${haehne.length ? `<div class="hahn-liste">${haehne.map((z) => `<div class="hahn-zeile">${this._hahnModus(z)}<span class="sub">${t(this._ventilOffen(z) ? 'Ventil offen' : 'Ventil zu')}</span></div>`).join('')}</div>` : ''}
        ${seqs || `<p class="leer">${t('Keine Sequenz – in den Einstellungen anlegen.')}</p>`}
      </section>`;
  }

  _automatikSeq(c, s) {
    const zu = this._zu();
    const e = zu.sequenzen[s.id];
    const soll = (this._z().sequenzen || {})[s.id] || { zonen: {} };
    const lauf = this._aktuellerLauf(c);
    const letzter = (this._z().laeufe || {})[s.id];
    const ns = this._a(e, 'next_start');
    let summe = 0;
    const zeilen = s.zonen.map((sz) => {
      const z = c.zonen.find((x) => x.id === sz.zone);
      if (!z || this._hahnAktiv(z)) return '';     // Wasserhahn-Betrieb: nicht in der Automatik
      const sl = soll.zonen[sz.zone] || {};
      const dauer = sz.dauer_min || z.standard_min;
      const an = sz.aktiv;
      const geplant = an && sl.aktiv ? (sl.smart ? sl.minuten : (dauer * (sl.prozent ?? 100)) / 100) : 0;
      const smartInfo = sl.smart ? (sl.durchgaenge > 1 ? `${sl.durchgaenge} × ${fmtMin(geplant / sl.durchgaenge)}` : t('smart')) : `${sl.prozent} %`;
      summe += geplant;
      const aktiv = lauf && lauf.zoneId === z.id && this._an(e);
      return `
        <div class="zone-zeile ${an ? '' : 'aus'} ${aktiv ? 'aktiv' : ''}">
          <label class="schalter"><input type="checkbox" data-seqzone="${esc(s.id)}|${esc(z.id)}" ${sz.aktiv ? 'checked' : ''}><span></span></label>
          <div class="zone-name">${esc(z.name)}${aktiv ? ` <span class="live-badge">${t('LÄUFT')}</span>` : ''}</div>
          <label class="zone-wert"><span class="sub">${t('Dauer')}</span><span class="min-feld"><input type="number" min="1" max="240" step="1" value="${sz.dauer_min ?? ''}" placeholder="${z.standard_min}" data-seqdauer="${esc(s.id)}|${esc(z.id)}" aria-label="${esc(t('Dauer {name}', { name: z.name }))}">min</span></label>
          <div class="zone-wert geplant"><span class="sub">${t('Geplant')}</span>${an ? (sl.aktiv ? `${fmtMin(geplant)} <span class="sub">${smartInfo}</span>` : `<span class="sub">${esc((sl.smart && this._grundText({ ...((this._z().wetter || {}).zonen || {})[z.id], grund: sl.grund })) || t('entfällt'))}</span>`) : '–'}</div>
        </div>`;
    }).join('');
    const haehne = s.zonen.map((sz) => c.zonen.find((x) => x.id === sz.zone)).filter((z) => z && this._hahnAktiv(z));
    const plaene = s.plaene.map((p) => this._planKarte(s, p, soll.plan === p.name)).join('');
    const ohne = MONATE_IU.map((m, i) => [m, i]).filter(([m]) => !s.plaene.some((p) => p.monate.includes(m)));
    return `
      <div class="seq">
        <div class="seq-kopf">
          <div><b>${esc(s.name)}</b> <span class="sub">${esc(this._statusText(this._st(e) === 'on' ? 'on' : this._a(e, 'status')))}</span></div>
          <div class="sub">${t('Nächster Lauf:')} <b>${ns ? fmtZeit(ns) : '–'}</b>${ns && this._a(e, 'next_duration') ? ` · ${fmtDauer(dauerSek(this._a(e, 'next_duration')))}` : ''}${soll.plan ? ` · ${esc(t('Plan {name} {prozent} %', { name: soll.plan, prozent: soll.plan_prozent }))}` : ''}
            · ${t('Letzter:')} ${letzter ? `${fmtZeit(letzter.start)} (${fmtMin(letzter.dauer_min)})` : '–'}</div>
        </div>
        <div class="zonen-liste">${zeilen || `<p class="leer">${t('Keine Zonen in dieser Sequenz.')}</p>`}</div>
        ${haehne.length ? `<div class="sub">${esc(t('Im Wasserhahn-Betrieb (ausgeblendet): {zonen}.', { zonen: haehne.map((z) => z.name).join(', ') }))}</div>` : ''}
        <div class="sub summe">${t('Summe geplant {summe}', { summe: fmtMin(summe) })}${s.wetter ? '' : t(' · ohne Wetteranpassung')}${t(' · Dauer leer = Standardlaufzeit der Zone')}</div>
        <div class="saisons">${plaene}</div>
        ${ohne.length && s.plaene.length ? `<p class="hinweis">${t('Ohne Plan (keine Automatik): {monate}.', { monate: ohne.map(([, i]) => monatKurz(i)).join(', ') })}</p>` : ''}
        ${s.plaene.length ? '' : `<p class="hinweis">${t('Keine Pläne – die Sequenz läuft nur manuell. Pläne legst du in den Einstellungen an.')}</p>`}
      </div>`;
  }

  _planKarte(s, p, aktuell) {
    const id = `${esc(s.id)}|${esc(p.key)}`;
    let versatzOpt = '';
    for (let m = -720; m <= 720; m += 15) versatzOpt += `<option value="${m}" ${m === p.zeit.versatz_min ? 'selected' : ''}>${versatzText(m)}</option>`;
    return `
      <div class="saison ${aktuell ? 'aktuell' : ''}">
        <div class="saison-kopf"><b>${esc(p.name)}</b>${aktuell ? `<span class="live-badge">${t('AKTUELL')}</span>` : ''}${!p.monate.length || !p.tage.length ? `<span class="sub">${t('ohne Lauf')}</span>` : ''}</div>
        <div class="sub">${t('Monate')}</div>
        <div class="chips monate">${MONATE_IU.map((m, i) => `<button class="chip ${p.monate.includes(m) ? 'an' : ''}" data-plan-monat="${id}|${m}" aria-pressed="${p.monate.includes(m)}">${monatKurz(i)}</button>`).join('')}</div>
        <div class="sub">${t('Tage')}</div>
        <div class="chips">${TAGE_IU.map((x, i) => `<button class="chip ${p.tage.includes(x) ? 'an' : ''}" data-plan-tag="${id}|${x}" aria-pressed="${p.tage.includes(x)}">${tagKurz(i)}</button>`).join('')}</div>
        <div class="saison-start"><span class="sub">${t('Start')}</span>
          <span class="zeit-felder">
            <select data-plan-bezug="${id}">${BEZUG.map((k) => `<option value="${k}" ${k === p.zeit.bezug ? 'selected' : ''}>${t(BEZUG_TEXT[k])}</option>`).join('')}</select>
            ${p.zeit.bezug === 'uhrzeit'
    ? `<input type="time" value="${esc(p.zeit.uhrzeit)}" data-plan-uhrzeit="${id}">`
    : `<select data-plan-versatz="${id}">${versatzOpt}</select>`}
          </span></div>
        <div class="regler">
          <div class="regler-kopf"><span>${t('Laufzeit')}</span><b data-anzeige="plan:${id}">${fmt(p.laufzeit)} %</b></div>
          <input type="range" min="0" max="200" step="5" value="${p.laufzeit}" data-plan-laufzeit="${id}">
        </div>
      </div>`;
  }

  // ── Manuell ────────────────────────────────────────────────────────
  _manZustand(cid) {
    if (!this._man[cid]) this._man[cid] = { zonen: new Set(), prozent: 100 };
    return this._man[cid];
  }
  _manuell() {
    return this._ctlListe().map((c) => {
      const m = this._manZustand(c.id);
      const info = (this._z().manuell || {})[c.id];
      const lauf = this._aktuellerLauf(c);
      let summe = 0;
      const karten = c.zonen.map((z) => {
        const an = m.zonen.has(z.id);
        const min = (z.standard_min * m.prozent) / 100;
        if (an) summe += min;
        const aktiv = (info && info.zone === z.id) || (lauf && lauf.zoneId === z.id);
        return `
          <button class="zonenkarte ${an ? 'an' : ''} ${aktiv ? 'aktiv' : ''}" data-man-zone="${esc(c.id)}|${esc(z.id)}" aria-pressed="${an}">
            <div class="zk-kopf"><div class="zk-name" title="${esc(z.name)}">${esc(z.name)}</div><span class="haken"><ha-icon icon="mdi:check"></ha-icon></span></div>
            <div class="zk-info">${this._hahnAktiv(z) ? `<span class="hahn-info">${t('Wasserhahn')}</span>` : ''}</div>
            <div class="zk-min" data-min="${z.standard_min}">${fmtMin(min)}</div>
            <div class="sub">${t('Standard {min} min', { min: z.standard_min })}</div>
          </button>`;
      }).join('');
      const seqKnoepfe = c.sequenzen.filter((s) => s.zonen.some((sz) => sz.aktiv)).map((s) => `<button class="knopf klein" data-aktion="man-seq" data-ctl="${esc(c.id)}" data-seq="${esc(s.id)}" ${info ? 'disabled' : ''}><ha-icon icon="mdi:play"></ha-icon>${esc(s.name)}</button>`).join('');
      return `
        <section class="karte">
          <div class="kopf"><div><ha-icon icon="mdi:gesture-tap-button"></ha-icon><span>${esc(t('{name} – manueller Lauf', { name: c.name }))}</span></div>
            <div class="knopfgruppe">
              <button class="knopf klein" data-aktion="man-alle" data-ctl="${esc(c.id)}">${t('Alle')}</button>
              <button class="knopf klein" data-aktion="man-keine" data-ctl="${esc(c.id)}">${t('Keine')}</button>
            </div></div>
          <div class="zonen-raster">${karten}</div>
          <div class="regler">
            <div class="regler-kopf"><span>${t('Laufzeit für alle Zonen')}</span><b data-anzeige="man:${esc(c.id)}">${fmt(m.prozent)} %</b></div>
            <input type="range" min="5" max="200" step="5" value="${m.prozent}" data-man-prozent="${esc(c.id)}">
            <div class="skala"><span>5 %</span><span>${t('100 % = Standard')}</span><span>200 %</span></div>
          </div>
          <div class="start-zeile">
            <div><div class="sub">${t('Gesamtdauer')}</div><div class="gross-wert" data-man-summe="${esc(c.id)}">${fmtMin(summe)}</div></div>
            ${info || this._ctlLaeuft(c)
    ? `<button class="knopf rot gross" data-aktion="stopp" data-ctl="${esc(c.id)}"><ha-icon icon="mdi:stop"></ha-icon>${t('Stoppen')}</button>`
    : `<button class="knopf blau gross" data-aktion="man-start" data-ctl="${esc(c.id)}" ${summe > 0 ? '' : 'disabled'}><ha-icon icon="mdi:play"></ha-icon>${t('Starten')}</button>`}
          </div>
          ${seqKnoepfe ? `<div class="seq-start"><span class="sub">${t('Sequenz manuell starten (mit der Laufzeit oben, ohne Wetteranpassung):')}</span><div class="knopfgruppe">${seqKnoepfe}</div></div>` : ''}
          ${lauf ? this._laufBox(lauf) : ''}
        </section>`;
    }).join('');
  }

  // ── Wetter ─────────────────────────────────────────────────────────
  _wetter() {
    const w = this._z().wetter || {};
    const wt = this._e().wetter;
    const tage = w.tage || [];
    const zonen = this._ctlListe().flatMap((c) => c.zonen.map((z) => ({ ...z, ctl: c })));
    const smartAn = this._smart();
    const zeilen = zonen.map((z) => {
      const d = (w.zonen || {})[z.id] || {};
      if (smartAn && d.smart) {
        const kosten = this._wasserKosten(z.ctl, d.liter);
        return `<tr><td>${esc(z.name)}<div class="sub">${esc(t(ZONENTYP_TEXT[z.smart?.typ] || ''))} · Kc ${fmt(d.kc, 2)}</div></td>
          <td class="r">${fmt(d.bilanz, 1)} mm<div class="sub">${t('von {mm} mm', { mm: fmt(d.speicher) })}</div></td>
          <td class="r">${d.schwelle ? `${fmt(d.schwelle, 1)} mm` : '–'}</td><td class="r">${fmt(d.bedarf, 1)} mm</td>
          <td class="r">${fmt(d.leistung, 1)} mm/h<div class="sub">${esc(t(QUELLE_TEXT[d.quelle] || ''))}</div></td>
          <td class="r"><b>${d.minuten ? fmtMin(d.minuten) : '–'}</b>${d.durchgaenge > 1 ? `<div class="sub">${d.durchgaenge} × ${fmtMin(d.minuten / d.durchgaenge)}</div>` : ''}</td>
          <td class="r">${d.minuten ? (d.liter != null ? `${fmt(d.liter)} L${kosten != null ? `<div class="sub">${fmt(kosten, 2)} €</div>` : ''}` : `${fmt(d.mm, 1)} mm`) : '–'}</td>
          <td><span class="sub">${esc(this._grundText(d))}</span></td></tr>`;
      }
      return `<tr><td>${esc(z.name)}${this._ctlListe().length > 1 ? ` <span class="sub">${esc(z.ctl.name)}</span>` : ''}</td>
        <td class="r">${fmt(d.bilanz, 1)} mm</td><td class="r">${fmt(d.bedarf, 1)} mm</td><td class="r">${fmt(d.referenz, 1)} mm</td>
        <td class="r"><b>${d.faktor != null ? fmt(d.faktor * 100) : '–'} %</b></td><td>${z.regen ? '' : `<span class="sub">${t('ohne Regen')}</span>`}</td></tr>`;
    }).join('');
    return `
      <section class="kacheln">
        ${this._kachel(t('Verdunstung gestern'), fmt(w.et0_gestern, 1), 'mm', t('ET₀ nach FAO-56'), 'gelb', 'mdi:weather-sunny-alert')}
        ${this._kachel(t('Verdunstung 24 h'), fmt(w.et0_prognose, 1), 'mm', t('Prognose'), 'gelb', 'mdi:weather-sunny')}
        ${this._kachel(t('Regen heute'), fmt(w.regen_heute, 1), 'mm', t(w.regnet ? 'es regnet' : 'gemessen'), w.regnet ? 'blau' : 'tuerkis', 'mdi:weather-rainy')}
        ${this._kachel(t('Regen 24 h'), fmt(w.regen_prognose, 1), 'mm', t('Menge × Wahrscheinlichkeit'), 'lila', 'mdi:weather-cloudy-clock')}
      </section>
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="mdi:chart-bar"></ha-icon><span>${t('Verdunstung und Regen je Tag')}</span></div>
          <div class="legende"><span><i class="sw et0"></i>${t('Verdunstung')}</span><span><i class="sw gemessen"></i>${t('Regen')}</span></div></div>
        ${tage.length ? this._tageDiagramm(tage) : `<p class="leer">${t('Noch keine Tage ausgewertet.')}</p>`}
      </section>
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="mdi:weather-pouring"></ha-icon><span>${t('Regenprognose je Stunde')}</span></div></div>
        ${this._prognoseDiagramm(w.prognose_stunden || [])}
      </section>
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="mdi:water-percent"></ha-icon><span>${t('Bodenspeicher je Zone')}</span></div><span class="sub">${t('Referenz {referenz} mm = 100 % · Speicher {speicher} mm · Regen {wirksam} % wirksam', { referenz: fmt(wt.referenz_mm, 1), speicher: fmt(wt.speicher_mm), wirksam: wt.regen_wirksam })}</span></div>
        ${smartAn ? `<div class="tabelle-scroll"><table class="tabelle"><tr><th>${t('Zone')}</th><th class="r">${t('Bilanz')}</th><th class="r">${t('Schwelle')}</th><th class="r">${t('Bedarf')}</th><th class="r">${t('Leistung')}</th><th class="r">${t('Geplant')}</th><th class="r">${t('Wasser')}</th><th></th></tr>${zeilen}</table></div>
        <p class="hinweis"><span class="badge-exp">${t('experimentell')}</span> ${esc(t('Smarte Laufzeit: Bilanz je Zone mit Pflanzenfaktor (Kc × ET₀) und eigenem Bodenspeicher. Bedarf = Defizit + Kc × Verdunstung der nächsten 24 h − wirksamer Regen. „Tief gießen“ läuft erst, wenn das Defizit die Schwelle erreicht. Laufzeit = Bedarf ÷ Beregnungsleistung, höchstens die Höchstlaufzeit; dazu kommen Plan-% und Grundfaktor. Mit Wasserzähler und Fläche wird die gemessene Menge gutgeschrieben.'))}</p>`
          : `<table class="tabelle"><tr><th>${t('Zone')}</th><th class="r">${t('Bilanz')}</th><th class="r">${t('Bedarf')}</th><th class="r">${t('Referenz')}</th><th class="r">${t('Faktor')}</th><th></th></tr>${zeilen}</table>
        <p class="hinweis">${esc(t('Bilanz < 0 = Defizit im Boden. Bedarf = Defizit + Verdunstung der nächsten 24 h − wirksamer Regen (heute und Prognose). Faktor = Bedarf ÷ Referenz, höchstens {max} %; dazu kommen Plan-%, Grundfaktor und Zonenfaktor. Jeder Lauf schreibt seine Wassermenge gut.', { max: wt.max_faktor }))}</p>`}
      </section>`;
  }

  _tageDiagramm(tage) {
    const W = 960, H = 220, L = 44, R = 10, T = 12, B = 30;
    const { max, schritt } = achse(Math.max(1, ...tage.map((x) => Math.max(x.et0 || 0, x.regen || 0))));
    const bw = (W - L - R) / tage.length;
    const y = (v) => T + (H - T - B) * (1 - Math.min(v, max) / max);
    let s = `<svg viewBox="0 0 ${W} ${H}" class="diagramm" role="img" aria-label="${t('Verdunstung und Regen je Tag')}">`;
    for (let v = 0; v <= max + 1e-9; v += schritt) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="${v === 0 ? 'achse' : 'gitter'}"/><text x="${L - 6}" y="${y(v) + 4}" class="ax r">${fmt(v, schritt < 1 ? 1 : 0)}</text>`;
    tage.forEach((tg, i) => {
      const x = L + i * bw;
      const d = new Date(tg.tag);
      s += `<g data-tip="${esc(`<b>${d.toLocaleDateString(LOCALE, { weekday: 'short', day: '2-digit', month: '2-digit' })}</b><br>${t('Verdunstung {mm} mm', { mm: fmt(tg.et0, 1) })}<br>${t('Regen {mm} mm', { mm: fmt(tg.regen, 1) })}`)}"><rect x="${x}" y="${T}" width="${bw}" height="${H - T - B}" class="treffer"/>`;
      const bb = bw * 0.36;
      if (tg.et0 > 0) s += `<rect x="${x + bw * 0.12}" y="${y(tg.et0)}" width="${bb}" height="${Math.max(1, y(0) - y(tg.et0))}" rx="2" class="bar et0"/>`;
      if (tg.regen > 0) s += `<rect x="${x + bw * 0.52}" y="${y(tg.regen)}" width="${bb}" height="${Math.max(1, y(0) - y(tg.regen))}" rx="2" class="bar gemessen"/>`;
      s += `</g><text x="${x + bw / 2}" y="${H - 10}" class="ax mitte">${d.getDate()}.</text>`;
    });
    return s + '</svg>';
  }

  _prognoseDiagramm(stunden) {
    if (!stunden.length) return `<p class="leer">${t('Keine Prognose verfügbar.')}</p>`;
    const W = 960, H = 200, L = 44, R = 10, T = 12, B = 30;
    const { max, schritt } = achse(Math.max(1, ...stunden.map((s) => s[1] || 0)));
    const bw = (W - L - R) / stunden.length;
    const y = (v) => T + (H - T - B) * (1 - v / max);
    let s = `<svg viewBox="0 0 ${W} ${H}" class="diagramm" role="img" aria-label="${t('Regenprognose je Stunde')}">`;
    for (let v = 0; v <= max + 1e-9; v += schritt) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="${v === 0 ? 'achse' : 'gitter'}"/><text x="${L - 6}" y="${y(v) + 4}" class="ax r">${fmt(v, schritt < 1 ? 1 : 0)}</text>`;
    stunden.forEach(([ts, mm, p], i) => {
      const x = L + i * bw;
      const zt = new Date(ts);
      s += `<g data-tip="${esc(`<b>${fmtZeit(zt)}</b><br>${fmt(mm, 1)} mm · ${p} %`)}"><rect x="${x}" y="${T}" width="${bw}" height="${H - T - B}" class="treffer"/>`;
      if (mm > 0) s += `<rect x="${x + 1}" y="${y(mm)}" width="${Math.max(1, bw - 2)}" height="${Math.max(1, y(0) - y(mm))}" rx="2" class="bar prognose" style="opacity:${0.35 + 0.65 * (p / 100)}"/>`;
      s += '</g>';
      if (zt.getHours() % 6 === 0) s += `<text x="${x + bw / 2}" y="${H - 10}" class="ax mitte">${zt.getHours() === 0 ? wochentag(zt) : t('{h} h', { h: zt.getHours() })}</text>`;
    });
    return s + '</svg>';
  }

  // ── Statistik ──────────────────────────────────────────────────────
  _statBereich() {
    const ende = new Date();
    const start = new Date(); start.setHours(0, 0, 0, 0);
    if (this._statZeitraum === 'woche') start.setDate(start.getDate() - 6);
    else if (this._statZeitraum === 'monat') start.setDate(start.getDate() - 29);
    else { start.setDate(1); start.setMonth(start.getMonth() - 11); }
    return { start, ende, period: this._statZeitraum === 'jahr' ? 'month' : 'day' };
  }
  _laeufeId(art) {
    return Object.keys(this._hass.states).find((k) => k.startsWith('sensor.') && this._hass.states[k].attributes.laeufe === art);
  }
  _zaehlerId(zoneId) {
    return Object.keys(this._hass.states).find((k) => k.startsWith('sensor.') && this._hass.states[k].attributes.zone_id === zoneId);
  }
  _wasserId(zoneId) {
    return Object.keys(this._hass.states).find((k) => k.startsWith('sensor.') && this._hass.states[k].attributes.wasser_zone === zoneId);
  }
  async _statLaden() {
    this._statLaedt = true;
    const { start, ende, period } = this._statBereich();
    const ctls = this._ctlListe();
    const zonen = ctls.flatMap((c) => c.zonen.map((z) => ({ ...z, ctl: c, zaehler: this._zaehlerId(z.id), wasserId: this._leitung(c) ? this._wasserId(z.id) : null })));
    const energie = ctls.filter((c) => !this._leitung(c) && c.pumpe.energie);
    // eigener Gartenzähler: der ganze Verbrauch ist Beregnung (Statistik des Zählers)
    const gartenzaehler = ctls.filter((c) => this._leitung(c) && c.wasser?.zaehler && c.wasser.nur_beregnung);
    const regenId = this._e().wetter.regen;
    const ids = [...new Set([...zonen.flatMap((z) => [z.zaehler, z.wasserId]), regenId, ...energie.map((c) => c.pumpe.energie),
      ...gartenzaehler.map((c) => c.wasser.zaehler), this._laeufeId('automatik'), this._laeufeId('manuell')].filter(Boolean))];
    const statistik = (von, periode) => this._hass.callWS({ type: 'recorder/statistics_during_period', start_time: von.toISOString(), end_time: ende.toISOString(), statistic_ids: ids, period: periode, types: ['change'] });
    try {
      // Die Langzeitstatistik entsteht erst stündlich. Die Zeit seit der letzten
      // fertigen Stunde je Sensor aus der 5-Minuten-Statistik ergänzen.
      const seit = new Date(Math.max(start.getTime(), ende.getTime() - 3 * 3600e3));
      const [r, stunden, fuenf] = await Promise.all([statistik(start, period), statistik(seit, 'hour'), statistik(seit, '5minute')]);
      const ms = (x) => (typeof x === 'number' ? x : Date.parse(x));
      for (const id of ids) {
        const fertig = Math.max(seit.getTime(), ...(stunden[id] || []).map((p) => ms(p.end)));
        const neu = (fuenf[id] || []).filter((p) => ms(p.start) >= fertig);
        if (neu.length) r[id] = [...(r[id] || []), ...neu];
      }
      const schritte = [];
      const zt = new Date(start);
      while (zt <= ende) { schritte.push(new Date(zt)); if (period === 'month') zt.setMonth(zt.getMonth() + 1); else zt.setDate(zt.getDate() + 1); }
      const key = (d) => (period === 'month' ? `${d.getFullYear()}-${d.getMonth()}` : `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`);
      const reihe = (id) => {
        const m = {};
        for (const p of r[id] || []) { const d = new Date(typeof p.start === 'number' ? p.start : Date.parse(p.start)); m[key(d)] = (m[key(d)] || 0) + Math.max(0, p.change || 0); }
        return schritte.map((d) => m[key(d)] || 0);
      };
      const summe = (a) => a.reduce((x, y) => x + y, 0);
      const null_ = () => schritte.map(() => 0);
      const zonenReihen = zonen.map((z) => ({ ...z, werte: z.zaehler ? reihe(z.zaehler) : null_(), liter: z.wasserId ? reihe(z.wasserId) : null }));
      const beregnung = schritte.map((_, i) => zonenReihen.filter((z) => !this._hahnAktiv(z)).reduce((s, z) => s + z.werte[i], 0));
      // Wasser (Liter), Strom (kWh) und Kosten je Schritt; Grundpreis anteilig (Monate je Schritt)
      const monateJeSchritt = period === 'month' ? 1 : 12 / 365;
      const liter = null_(), kwh = null_();
      const kosten = { wasser: null_(), abwasser: null_(), grund: null_(), strom: null_() };
      let mitWasser = false, mitStrom = false;
      for (const c of ctls) {
        if (this._leitung(c)) {
          const w = c.wasser || {};
          if (!w.zaehler) continue;
          mitWasser = true;
          const l = w.nur_beregnung
            ? reihe(w.zaehler).map((v) => v * (LITER_JE[this._a(w.zaehler, 'unit_of_measurement')] ?? 1))
            : schritte.map((_, i) => zonenReihen.filter((z) => z.ctl.id === c.id && z.liter).reduce((s, z) => s + z.liter[i], 0));
          l.forEach((v, i) => {
            liter[i] += v;
            kosten.wasser[i] += (v / 1000) * (w.preis_m3 || 0);
            kosten.abwasser[i] += (v / 1000) * (w.abwasser_m3 || 0);
            kosten.grund[i] += (w.grundpreis_monat || 0) * monateJeSchritt;
          });
        } else if (c.pumpe.energie) {
          mitStrom = true;
          const faktor = this._a(c.pumpe.energie, 'unit_of_measurement') === 'Wh' ? 0.001 : 1;
          reihe(c.pumpe.energie).forEach((v, i) => { kwh[i] += v * faktor; kosten.strom[i] += v * faktor * (c.pumpe.strompreis_kwh || 0); });
        }
      }
      this._statDaten = { period, schritte, zonen: zonenReihen, beregnung, regen: regenId ? reihe(regenId) : null_(),
        energie: summe(kwh), kwh, liter, kosten, mitWasser, mitStrom, mitPumpe: ctls.some((c) => !this._leitung(c)),
        laeufeAuto: summe(reihe(this._laeufeId('automatik'))), laeufeMan: summe(reihe(this._laeufeId('manuell'))) };
    } catch (e) {
      this._statDaten = { fehler: e.message || String(e) };
    }
    this._statLaedt = false;
    if (this._tab === 'statistik') { this._sig = ''; this._zeichnen(); }
  }
  _statistik() {
    const knoepfe = [['woche', '7 Tage'], ['monat', '30 Tage'], ['jahr', '12 Monate']].map(([id, x]) => `<button class="zeit ${this._statZeitraum === id ? 'aktiv' : ''}" data-zeitraum="${id}">${t(x)}</button>`).join('');
    const d = this._statDaten;
    if (!d) return `<div class="zeitwahl">${knoepfe}</div><section class="karte"><p class="leer pulsiert">${t('Lade Statistik …')}</p></section>`;
    if (d.fehler) return `<div class="zeitwahl">${knoepfe}</div><section class="karte"><p class="leer">${esc(t('Statistik nicht verfügbar: {fehler}', { fehler: d.fehler }))}</p></section>`;
    const summe = (a) => (a || []).reduce((x, y) => x + y, 0);
    const eur = (v) => `${fmt(v, 2)} €`;
    const gesamt = summe(d.beregnung);
    const monat = d.period === 'month';
    const labelFn = (x) => (monat ? x.toLocaleDateString(LOCALE, { month: 'short' }) : (d.schritte.length > 10 ? `${x.getDate()}.` : `${wochentag(x)} ${x.getDate()}.`));
    const tipFn = (x) => (monat ? x.toLocaleDateString(LOCALE, { month: 'long', year: 'numeric' }) : x.toLocaleDateString(LOCALE, { weekday: 'short', day: '2-digit', month: '2-digit' }));
    const k = { wasser: [], abwasser: [], grund: [], strom: [], ...(d.kosten || {}) };
    const kWasser = summe(k.wasser), kAbwasser = summe(k.abwasser), kGrund = summe(k.grund), kStrom = summe(k.strom);
    const kGesamt = kWasser + kAbwasser + kGrund + kStrom;
    // Kostenarten: [Werte je Schritt, Summe, Klasse, Text]; nur die mit Betrag
    const arten = [[k.wasser, kWasser, 'wasser', 'Wasser'], [k.abwasser, kAbwasser, 'abwasser', 'Abwasser'],
      [k.grund, kGrund, 'grund', 'Grundpreis'], [k.strom, kStrom, 'strom', 'Strom']].filter(([, s]) => s > 0);
    const liter = summe(d.liter);
    const summen = d.zonen.map((z) => ({ z, s: summe(z.werte), l: z.liter ? summe(z.liter) : null }));
    const zmax = Math.max(1, ...summen.map((x) => x.s));
    const balken = summen.map(({ z, s, l }) => `<div class="hbar"><span class="hbar-name">${esc(z.name)}${this._hahnAktiv(z) ? ` <span class="sub">${t('Hahn')}</span>` : ''}</span><span class="hbar-spur"><i style="width:${(s / zmax) * 100}%"></i></span><span class="hbar-wert">${fmtMin(s)}${l != null ? `<span class="sub"> · ${fmt(l)} L</span>` : ''}</span></div>`).join('');
    const kostenTeile = arten.map(([, s, , x]) => t(`${x} {eur}`, { eur: eur(s) })).join(' · ');
    const kacheln = [
      this._kachel(t('Beregnung'), fmtMin(gesamt), '', t('ohne Zonen im Wasserhahn-Betrieb'), 'blau', 'mdi:sprinkler-variant'),
      this._kachel(t('Läufe'), fmt(d.laeufeAuto + d.laeufeMan), '', t('{auto} Automatik · {man} manuell', { auto: fmt(d.laeufeAuto), man: fmt(d.laeufeMan) }), 'lila', 'mdi:counter'),
      this._kachel(t('Regen'), fmt(summe(d.regen), 1), 'mm', t('gemessen'), 'tuerkis', 'mdi:weather-rainy'),
      d.mitWasser ? this._kachel(t('Wasser'), fmt(liter / 1000, 2), 'm³', t('{l} Liter', { l: fmt(liter) }), 'tuerkis', 'mdi:water') : '',
      d.mitPumpe !== false ? this._kachel(t('Pumpen'), fmt(d.energie, 1), 'kWh', `${t('Energie')}${kStrom > 0 ? ` · ${eur(kStrom)}` : ''}`, 'gruen', 'mdi:pump') : '',
      kGesamt > 0 ? this._kachel(t('Kosten'), fmt(kGesamt, 2), '€', kostenTeile, 'gelb', 'mdi:cash') : '',
    ].join('');
    const karte = (icon, titel, inhalt) => `<div class="karte"><div class="kopf"><div><ha-icon icon="${icon}"></ha-icon><span>${titel}</span></div></div>${inhalt}</div>`;
    const kostenTip = (i) => arten.filter(([w]) => w[i] > 0).map(([w, , , x]) => t(`${x} {eur}`, { eur: eur(w[i]) })).join('<br>');
    const verbrauch = [
      d.mitWasser ? karte('mdi:water', t(monat ? 'Wasser je Monat (L)' : 'Wasser je Tag (L)'),
        this._balken(d.schritte, d.liter, 'wasser', labelFn, (x, v) => `<b>${tipFn(x)}</b><br>${t('{l} Liter', { l: fmt(v) })}`)) : '',
      d.mitStrom ? karte('mdi:lightning-bolt', t(monat ? 'Strom je Monat (kWh)' : 'Strom je Tag (kWh)'),
        this._balken(d.schritte, d.kwh, 'strom', labelFn, (x, v) => `<b>${tipFn(x)}</b><br>${fmt(v, 2)} kWh`)) : '',
      kGesamt > 0 ? karte('mdi:cash', t(monat ? 'Kosten je Monat (€)' : 'Kosten je Tag (€)'),
        this._stapel(d.schritte, arten.map(([w, , c]) => [w, c]), labelFn,
          (x, i) => `<b>${tipFn(x)}</b><br>${kostenTip(i)}<br><b>${eur(arten.reduce((s, [w]) => s + w[i], 0))}</b>`)
        + `<div class="legende">${arten.map(([, , c, x]) => `<span><i class="sw ${c}"></i>${t(x)}</span>`).join('')}</div>`) : '',
    ].filter(Boolean).join('');
    return `
      <div class="zeitwahl">${knoepfe}</div>
      <section class="kacheln">${kacheln}</section>
      <section class="spalten">
        ${karte('mdi:sprinkler-variant', t(monat ? 'Beregnung je Monat (min)' : 'Beregnung je Tag (min)'),
          this._balken(d.schritte, d.beregnung, 'garten', labelFn, (x, v) => `<b>${tipFn(x)}</b><br>${t('Beregnung {dauer}', { dauer: fmtMin(v) })}`))}
        ${karte('mdi:weather-rainy', t(monat ? 'Regen je Monat (mm)' : 'Regen je Tag (mm)'),
          this._balken(d.schritte, d.regen, 'gemessen', labelFn, (x, v) => `<b>${tipFn(x)}</b><br>${t('Regen {mm} mm', { mm: fmt(v, 1) })}`))}
      </section>
      ${verbrauch ? `<section class="spalten">${verbrauch}</section>` : ''}
      <section class="karte"><div class="kopf"><div><ha-icon icon="mdi:format-list-bulleted"></ha-icon><span>${t(d.mitWasser ? 'Laufzeit und Wasser je Zone' : 'Laufzeit je Zone')}</span></div></div><div class="hbars">${balken}</div></section>`;
  }
  // gestapelte Balken: teile = [[werte, klasse], …], tipFn(schritt, index)
  _stapel(schritte, teile, labelFn, tipFn) {
    const W = 520, H = 220, L = 44, R = 8, T = 12, B = 28;
    const summen = schritte.map((_, i) => teile.reduce((s, [w]) => s + w[i], 0));
    const { max, schritt } = achse(Math.max(...summen, 0) || 1);
    const bw = (W - L - R) / schritte.length;
    const y = (v) => T + (H - T - B) * (1 - v / max);
    const jede = Math.ceil(schritte.length / 10);
    let s = `<svg viewBox="0 0 ${W} ${H}" class="diagramm" role="img">`;
    for (let v = 0; v <= max + 1e-9; v += schritt) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="${v === 0 ? 'achse' : 'gitter'}"/><text x="${L - 6}" y="${y(v) + 4}" class="ax r">${fmt(v, schritt < 1 ? 2 : 0)}</text>`;
    schritte.forEach((x0, i) => {
      const x = L + i * bw;
      s += `<g data-tip="${esc(tipFn(x0, i))}"><rect x="${x}" y="${T}" width="${bw}" height="${H - T - B}" class="treffer"/>`;
      let unten = 0;
      for (const [w, klasse] of teile) {
        if (w[i] > 0) s += `<rect x="${x + bw * 0.15}" y="${y(unten + w[i])}" width="${bw * 0.7}" height="${Math.max(1, y(unten) - y(unten + w[i]))}" class="bar ${klasse}"/>`;
        unten += w[i];
      }
      s += '</g>';
      if (i % jede === 0) s += `<text x="${x + bw / 2}" y="${H - 9}" class="ax mitte">${esc(labelFn(x0))}</text>`;
    });
    return s + '</svg>';
  }
  _balken(schritte, werte, klasse, labelFn, tipFn) {
    const W = 520, H = 220, L = 44, R = 8, T = 12, B = 28;
    const { max, schritt } = achse(Math.max(...werte, 0) || 1);
    const bw = (W - L - R) / werte.length;
    const y = (v) => T + (H - T - B) * (1 - v / max);
    const jede = Math.ceil(werte.length / 10);
    let s = `<svg viewBox="0 0 ${W} ${H}" class="diagramm" role="img">`;
    for (let v = 0; v <= max + 1e-9; v += schritt) s += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="${v === 0 ? 'achse' : 'gitter'}"/><text x="${L - 6}" y="${y(v) + 4}" class="ax r">${fmt(v, schritt < 1 ? 1 : 0)}</text>`;
    werte.forEach((v, i) => {
      const x = L + i * bw;
      s += `<g data-tip="${esc(tipFn(schritte[i], v))}"><rect x="${x}" y="${T}" width="${bw}" height="${H - T - B}" class="treffer"/>`;
      if (v > 0) s += `<rect x="${x + bw * 0.15}" y="${y(v)}" width="${bw * 0.7}" height="${Math.max(1, y(0) - y(v))}" rx="3" class="bar ${klasse}"/>`;
      s += '</g>';
      if (i % jede === 0) s += `<text x="${x + bw / 2}" y="${H - 9}" class="ax mitte">${esc(labelFn(schritte[i]))}</text>`;
    });
    return s + '</svg>';
  }

  // ── Einstellungen (nur Admin) ──────────────────────────────────────
  _entwurfHolen() {
    if (!this._entwurf) { this._entwurf = tiefKopie(this._cfg.einstellungen); this._entwurfGeaendert = false; }
    return this._entwurf;
  }
  _datalisten() {
    const opt = (pred) => Object.values(this._hass.states).filter(pred).sort((a, b) => a.entity_id.localeCompare(b.entity_id))
      .map((st) => `<option value="${esc(st.entity_id)}">${esc(st.attributes.friendly_name || '')}</option>`).join('');
    const dom = (st) => st.entity_id.split('.')[0];
    const einheit = (st) => st.attributes.unit_of_measurement || '';
    const sensor = (einheiten) => (st) => dom(st) === 'sensor' && einheiten.includes(einheit(st));
    return `
      <datalist id="dl-schalter">${opt((st) => SCHALT_DOMAINS.includes(dom(st)))}</datalist>
      <datalist id="dl-leistung">${opt(sensor(['W', 'kW']))}</datalist>
      <datalist id="dl-energie">${opt(sensor(['Wh', 'kWh']))}</datalist>
      <datalist id="dl-wasser">${opt(sensor(Object.keys(LITER_JE)))}</datalist>
      <datalist id="dl-regen">${opt(sensor(['mm', 'in']))}</datalist>
      <datalist id="dl-regenrate">${opt(sensor(['mm/h', 'in/h']))}</datalist>
      <datalist id="dl-binaer">${opt((st) => dom(st) === 'binary_sensor')}</datalist>
      <datalist id="dl-wetter">${opt((st) => dom(st) === 'weather')}</datalist>
      <datalist id="dl-temperatur">${opt(sensor(['°C', '°F']))}</datalist>
      <datalist id="dl-feuchte">${opt((st) => dom(st) === 'sensor' && (st.attributes.device_class === 'humidity' || einheit(st) === '%'))}</datalist>
      <datalist id="dl-wind">${opt(sensor(['km/h', 'm/s', 'mph', 'kn']))}</datalist>
      <datalist id="dl-strahlung">${opt(sensor(['W/m²', 'W/m2']))}</datalist>`;
  }
  _entInfo(wert) {
    const st = wert ? this._s(wert) : null;
    return !wert ? '' : st ? `${esc(st.attributes.friendly_name || '')} · ${esc(st.state)}${st.attributes.unit_of_measurement ? ` ${esc(st.attributes.unit_of_measurement)}` : ''}` : `<span class="warn">${t('nicht gefunden')}</span>`;
  }
  _entFeld(pfad, wert, liste, platzhalter = '') {
    return `<span class="ent-feld"><input type="text" list="${liste}" data-e="${pfad}" value="${esc(wert || '')}" placeholder="${esc(platzhalter)}" spellcheck="false" autocomplete="off"><span class="ent-info">${this._entInfo(wert)}</span></span>`;
  }
  _zahlFeld(pfad, wert, min, max, schritt = 1, einheit = '', leerErlaubt = false, platzhalter = '') {
    return `<span class="feld"><input type="number" data-e="${pfad}" data-typ="${leerErlaubt ? 'zahl-leer' : 'zahl'}" value="${wert ?? ''}" min="${min}" max="${max}" step="${schritt}" placeholder="${esc(platzhalter)}">${einheit}</span>`;
  }
  _haken(pfad, wert, text) {
    return `<label class="schalter"><input type="checkbox" data-e="${pfad}" ${wert ? 'checked' : ''}><span></span>${esc(text)}</label>`;
  }
  _knopf(aktion, icon, titel, daten, text = '', klasse = '') {
    const attr = Object.entries(daten).map(([k, v]) => `data-${k}="${v}"`).join(' ');
    return `<button class="knopf klein ${klasse}" data-aktion="${aktion}" ${attr} title="${esc(titel)}"><ha-icon icon="${icon}"></ha-icon>${esc(text)}</button>`;
  }

  _einstellungen() {
    if (!this._hass?.user?.is_admin) return `<section class="karte"><p class="leer">${t('Nur für Administratoren.')}</p></section>`;
    const e = this._entwurfHolen();
    if (!e.anzeige) e.anzeige = { logo_link: null };
    const wt = e.wetter;
    const ctlKarten = e.controller.map((c, ci) => this._einstCtl(c, ci, e)).join('');
    return `
      ${this._datalisten()}
      <div id="status-leiste">${this._statusLeisteHtml()}</div>
      ${ctlKarten || `<section class="karte"><p class="leer">${t('Noch kein Controller. Ein Controller ist eine Pumpe oder ein Wasseranschluss mit Zonen und Sequenzen.')}</p></section>`}
      <div class="zeile-knoepfe">${this._knopf('e-ctl-neu', 'mdi:plus', t('Controller anlegen'), {}, t('Controller'))}</div>
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="mdi:weather-partly-rainy"></ha-icon><span>${t('Wetter und Wasserbilanz')}</span></div></div>
        <div class="formular breit">
          <label>${t('Regenzähler (Summe, mm)')}${this._entFeld('wetter.regen', wt.regen, 'dl-regen')}</label>
          <label>${t('Regenrate (mm/h)')}${this._entFeld('wetter.regenrate', wt.regenrate, 'dl-regenrate', t('optional – > 0 = es regnet'))}</label>
          <label>${t('Regensensor (an = Regen)')}${this._entFeld('wetter.regensensor', wt.regensensor, 'dl-binaer', t('optional'))}</label>
          <label>${t('Wetterprognose')}${this._entFeld('wetter.prognose', wt.prognose, 'dl-wetter', 'weather.…')}</label>
          <label>${t('Temperatur')}${this._entFeld('wetter.temperatur', wt.temperatur, 'dl-temperatur')}</label>
          <label>${t('Luftfeuchte')}${this._entFeld('wetter.feuchte', wt.feuchte, 'dl-feuchte')}</label>
          <label>${t('Wind')}${this._entFeld('wetter.wind', wt.wind, 'dl-wind')}</label>
          <label>${t('Einstrahlung (W/m²)')}${this._entFeld('wetter.strahlung', wt.strahlung, 'dl-strahlung')}</label>
          <label>${t('Höhe des Windmessers')}${this._zahlFeld('wetter.wind_hoehe_m', wt.wind_hoehe_m, 0.5, 30, 0.5, 'm')}</label>
          <label>${t('Höhe über NN')}${this._zahlFeld('wetter.hoehe_m', wt.hoehe_m, -100, 5000, 1, 'm', true, `HA: ${this._hass.config?.elevation ?? 0}`)}</label>
          <label>${t('Referenzbedarf (100 %)')}${this._zahlFeld('wetter.referenz_mm', wt.referenz_mm, 0.5, 50, 0.5, 'mm')}</label>
          <label>${t('Bodenspeicher')}${this._zahlFeld('wetter.speicher_mm', wt.speicher_mm, 0, 100, 1, 'mm')}</label>
          <label>${t('Regen wirksam')}${this._zahlFeld('wetter.regen_wirksam', wt.regen_wirksam, 0, 100, 5, '%')}</label>
          <label>${t('Höchstwert Laufzeit')}${this._zahlFeld('wetter.max_faktor', wt.max_faktor, 100, 400, 10, '%')}</label>
          ${wt.strahlung ? '' : `<label>${t('Einstrahlung aus Temperatur (kRs)')}${this._zahlFeld('wetter.krs', wt.krs, 0.05, 0.3, 0.01)}</label>`}
        </div>
        <p class="hinweis">${t('Referenzbedarf = Wassermenge, die eine Zone bei 100 % Standardlaufzeit verteilt (3 mm sind ein guter Startwert). Zonen mit gemessener Beregnungsleistung (mm/h) rechnen mit Leistung × Standardlaufzeit. Ein Regentag über 100 mm gilt als Messfehler.')}${wt.strahlung ? '' : ` ${t('Ohne Einstrahlungssensor wird die Einstrahlung aus der Temperaturspanne des Tages geschätzt (FAO-56): kRs 0,16 im Binnenland, 0,19 an der Küste.')}`}</p>
      </section>
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="mdi:brain"></ha-icon><span>${t('Smarte Laufzeit')}</span><span class="badge-exp">${t('experimentell')}</span></div></div>
        <label class="schalter"><input type="checkbox" data-e="smart.aktiv" data-zeichnen="1" ${e.smart?.aktiv ? 'checked' : ''}><span></span>${t('Smarte Laufzeit je Zone verwenden')}</label>
        <p class="hinweis">${t('Jede Zone bekommt Zonentyp, Pflanzenfaktor (Kc), eigenen Bodenspeicher, Gießweise (täglich oder tief ab Schwelle) und Beregnungsleistung (von Hand, aus Durchfluss und Fläche oder gemessen mit dem Wasserzähler). Die Laufzeit wird in Minuten berechnet und kann in Durchgänge aufgeteilt werden. Noch nicht in einer ganzen Saison erprobt. Aus = Verhalten wie bisher.')}</p>
      </section>
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="mdi:monitor-dashboard"></ha-icon><span>${t('Anzeige')}</span></div></div>
        <div class="formular breit">
          <label>${t('Tippen auf das Logo öffnet')}<span class="feld"><input type="text" data-e="anzeige.logo_link" value="${esc(e.anzeige.logo_link || '')}" placeholder="/lovelace/0" spellcheck="false" autocomplete="off"></span></label>
        </div>
        <p class="hinweis">${t('Pfad einer HA-Seite (beginnt mit /) oder eine Adresse mit http(s)://, z. B. die Startseite eines Dashboards. Leer = das Logo hat keine Funktion.')}</p>
      </section>
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="mdi:cog-outline"></ha-icon><span>Irrigation Unlimited</span></div></div>
        ${this._haken('iu.historie', e.iu.historie, t('IU-Historie (liest alle 2 min die Datenbank – nur bei Bedarf)'))}
      </section>
      <div class="speicher-leiste ${this._entwurfGeaendert ? 'sichtbar' : ''}">
        <span>${t('Ungespeicherte Änderungen')}</span><span id="e-fehler" class="warn"></span>
        <button class="knopf" data-aktion="e-verwerfen">${t('Verwerfen')}</button>
        <button class="knopf blau" data-aktion="e-speichern"><ha-icon icon="mdi:content-save"></ha-icon>${t('Speichern')}</button>
      </div>`;
  }

  _einstPumpe(c, p) {
    return `
          <label>${t('Pumpe (Schalter)')}${this._entFeld(`${p}.pumpe.entity_id`, c.pumpe.entity_id, 'dl-schalter', 'switch.…')}</label>
          <label>${t('Leistung (W)')}${this._entFeld(`${p}.pumpe.leistung`, c.pumpe.leistung, 'dl-leistung', t('optional'))}</label>
          <label>${t('Energie (kWh)')}${this._entFeld(`${p}.pumpe.energie`, c.pumpe.energie, 'dl-energie', t('optional – Statistik'))}</label>
          <label>${t('Strompreis')}${this._zahlFeld(`${p}.pumpe.strompreis_kwh`, c.pumpe.strompreis_kwh, 0, 10, 0.01, '€/kWh', true, t('optional'))}</label>
          <label>${t('„Pumpt“ ab')}${this._zahlFeld(`${p}.pumpe.schwelle_w`, c.pumpe.schwelle_w, 0, 5000, 1, 'W')}</label>
          <label>${t('Vorlauf')}${this._zahlFeld(`${p}.pumpe.vorlauf_s`, c.pumpe.vorlauf_s, 0, 600, 1, 's')}</label>
          <label>${t('Nachlauf')}${this._zahlFeld(`${p}.pumpe.nachlauf_s`, c.pumpe.nachlauf_s, 0, 600, 1, 's')}</label>
          ${this._haken(`${p}.pumpe.tagbetrieb`, c.pumpe.tagbetrieb, t('Pumpe von Sonnenauf- bis -untergang an'))}`;
  }
  _einstWasser(c, p) {
    const w = c.wasser || {};
    return `
          <label>${t('Wasserzähler')}${this._entFeld(`${p}.wasser.zaehler`, w.zaehler, 'dl-wasser', t('optional – Statistik'))}</label>
          ${this._haken(`${p}.wasser.nur_beregnung`, w.nur_beregnung, t('Zähler misst nur die Beregnung (eigener Gartenzähler)'))}
          <label>${t('Grundpreis')}${this._zahlFeld(`${p}.wasser.grundpreis_monat`, w.grundpreis_monat, 0, 1000, 0.01, '€/Monat', true, t('optional'))}</label>
          <label>${t('Wasserpreis')}${this._zahlFeld(`${p}.wasser.preis_m3`, w.preis_m3, 0, 1000, 0.01, '€/m³', true, t('optional'))}</label>
          <details class="erweitert"><summary>${t('Erweitert')}</summary>
            <label>${t('Abwasser')}${this._zahlFeld(`${p}.wasser.abwasser_m3`, w.abwasser_m3, 0, 1000, 0.01, '€/m³', true, t('optional'))}</label>
          </details>
          <p class="hinweis">${t('Die Ventile hängen direkt an der Wasserleitung, es gibt keine Pumpe. Mit dem Hauptzähler des Hauses zählt nur der Verbrauch, während eine Zone läuft; mit einem eigenen Gartenzähler der gesamte Verbrauch. Der Grundpreis wird in der Statistik anteilig auf den Zeitraum umgelegt.')}</p>`;
  }

  _einstSmart(c, z, pz) {
    const s = { ...SMART_STANDARD, ...(z.smart || {}) };
    const opt = (werte, wahl) => Object.entries(werte).map(([k, x]) => `<option value="${k}" ${k === wahl ? 'selected' : ''}>${esc(t(x))}</option>`).join('');
    const quellen = { hand: 'von Hand (mm/h)', durchfluss: 'aus Durchfluss und Fläche',
      ...(this._leitung(c) && c.wasser?.zaehler ? { zaehler: 'gemessen mit dem Wasserzähler' } : {}) };
    const messung = this._messungText(z);
    return `
        <div class="smart-zone">
          <div class="unterkopf klein"><span>${t('Smarte Laufzeit')}<span class="badge-exp">${t('experimentell')}</span></span></div>
          <div class="formular">
            <label>${t('Zonentyp')}<select class="auto" data-e="${pz}.smart.typ" data-zonentyp="${pz}" data-zeichnen="1">${opt(ZONENTYP_TEXT, s.typ)}</select></label>
            <label>${t('Pflanzenfaktor (Kc)')}${this._zahlFeld(`${pz}.smart.kc`, s.kc, 0.1, 1.5, 0.05)}</label>
            <label>${t('Fläche')}${this._zahlFeld(`${pz}.smart.flaeche_m2`, s.flaeche_m2, 0.1, 100000, 0.1, 'm²', true, t('optional'))}</label>
            <label>${t('Bodenspeicher')}${this._zahlFeld(`${pz}.smart.speicher_mm`, s.speicher_mm, 1, 100, 1, 'mm', true, fmt(this._entwurfHolen().wetter.speicher_mm))}</label>
            <label>${t('Gießweise')}<select class="auto" data-e="${pz}.smart.giessweise" data-zeichnen="1">${opt({ bedarf: 'täglich nach Bedarf', schwelle: 'tief gießen ab Schwelle' }, s.giessweise)}</select></label>
            ${s.giessweise === 'schwelle' ? `<label>${t('Schwelle (Defizit)')}${this._zahlFeld(`${pz}.smart.schwelle_prozent`, s.schwelle_prozent, 10, 90, 5, '%')}</label>` : ''}
            <label>${t('Beregnungsleistung')}<select class="auto" data-e="${pz}.smart.leistung_quelle" data-zeichnen="1">${opt(quellen, s.leistung_quelle)}</select></label>
            ${s.leistung_quelle === 'hand'
              ? `<label>${t('Leistung')}${this._zahlFeld(`${pz}.leistung_mm_h`, z.leistung_mm_h, 0.1, 200, 0.1, 'mm/h', true, t('optional'))}</label>`
              : `<label>${t(s.leistung_quelle === 'zaehler' ? 'Durchfluss (Startwert)' : 'Durchfluss')}${this._zahlFeld(`${pz}.smart.durchfluss_l_min`, s.durchfluss_l_min, 0.1, 1000, 0.1, 'L/min', true, t('optional'))}</label>`}
            ${messung ? `<p class="hinweis">${messung}</p>` : ''}
            <label>${t('Höchstlaufzeit')}${this._zahlFeld(`${pz}.smart.max_min`, s.max_min, 1, 240, 1, 'min')}</label>
            <label class="schalter"><input type="checkbox" data-e="${pz}.smart.aufteilen" data-zeichnen="1" ${s.aufteilen ? 'checked' : ''}><span></span>${t('In Durchgänge aufteilen (Cycle & Soak)')}</label>
            ${s.aufteilen ? `<label>${t('Höchstens je Durchgang')}${this._zahlFeld(`${pz}.smart.durchgang_min`, s.durchgang_min, 1, 240, 1, 'min')}</label>
            <label>${t('Sickerpause nach Durchgang')}${this._zahlFeld(`${pz}.smart.sickerpause_min`, s.sickerpause_min, 0, 120, 1, 'min')}</label>` : ''}
          </div>
        </div>`;
  }

  _einstCtl(c, ci, e) {
    const p = `controller.${ci}`;
    const leitung = this._leitung(c);
    const smartAn = !!e.smart?.aktiv;
    const zonen = c.zonen.map((z, zi) => `
      <div class="ez">
        <div class="ez-kopf">
          <input type="text" class="ez-name" data-e="${p}.zonen.${zi}.name" value="${esc(z.name)}" maxlength="40" aria-label="${t('Name der Zone')}">
          <span class="knopfgruppe">
            ${this._knopf('e-zone-hoch', 'mdi:arrow-up', t('nach oben'), { ci, i: zi })}${this._knopf('e-zone-runter', 'mdi:arrow-down', t('nach unten'), { ci, i: zi })}
            ${this._knopf('e-zone-weg', 'mdi:delete-outline', t('Zone löschen'), { ci, i: zi }, '', 'rot-text')}
          </span>
        </div>
        <div class="ez-raster">
          <div class="ez-ventile"><span class="sub">${t('Ventil(e) – mehrere werden gemeinsam geschaltet')}</span>
            ${z.ventile.map((v, j) => `<div class="ez-ventil">${this._entFeld(`${p}.zonen.${zi}.ventile.${j}`, v, 'dl-schalter', 'switch.…')}${z.ventile.length > 1 ? this._knopf('e-ventil-weg', 'mdi:close', t('Ventil entfernen'), { ci, i: zi, j }) : ''}</div>`).join('')}
            ${this._knopf('e-ventil-neu', 'mdi:plus', t('Ventil hinzufügen'), { ci, i: zi }, t('Ventil'))}
          </div>
          <div class="formular">
            <label>${t('Standardlaufzeit')}${this._zahlFeld(`${p}.zonen.${zi}.standard_min`, z.standard_min, 1, 240, 1, 'min')}</label>
            ${smartAn ? '' : `<label>${t('Zonenfaktor')}${this._zahlFeld(`${p}.zonen.${zi}.faktor`, z.faktor, 0, 300, 5, '%')}</label>
            <label>${t('Beregnungsleistung')}${this._zahlFeld(`${p}.zonen.${zi}.leistung_mm_h`, z.leistung_mm_h, 0.1, 200, 0.1, 'mm/h', true, t('optional'))}</label>`}
            ${this._leitung(c) ? '' : this._haken(`${p}.zonen.${zi}.wasserhahn`, z.wasserhahn, t('Kann Wasserhahn sein (Ventil folgt der Pumpe)'))}
            ${this._haken(`${p}.zonen.${zi}.regen`, z.regen, t('Regen kürzt die Laufzeit (aus bei überdachten Zonen)'))}
          </div>
        </div>
        ${smartAn ? this._einstSmart(c, z, `${p}.zonen.${zi}`) : ''}
      </div>`).join('');
    const seqs = c.sequenzen.map((s, si) => this._einstSeq(c, ci, s, si)).join('');
    return `
      <section class="karte">
        <div class="kopf"><div><ha-icon icon="${leitung ? 'mdi:water-pump-off' : 'mdi:pump'}"></ha-icon><input type="text" class="titel-feld" data-e="${p}.name" value="${esc(c.name)}" maxlength="40" aria-label="${t('Name des Controllers')}"></div>
          ${this._knopf('e-ctl-weg', 'mdi:delete-outline', t('Controller löschen'), { ci }, t('Controller löschen'), 'rot-text')}</div>
        <div class="formular breit">
          <label>${t('Wasserversorgung')}<select class="auto" data-e="${p}.anschluss" data-zeichnen="1">
            <option value="pumpe" ${leitung ? '' : 'selected'}>${t('Pumpe')}</option>
            <option value="leitung" ${leitung ? 'selected' : ''}>${t('Wasseranschluss')}</option>
          </select></label>
          ${leitung ? this._einstWasser(c, p) : this._einstPumpe(c, p)}
        </div>
        <div class="unterkopf"><span>${t('Zonen')}</span>${this._knopf('e-zone-neu', 'mdi:plus', t('Zone anlegen'), { ci }, t('Zone'))}</div>
        <div class="ez-liste">${zonen || `<p class="leer">${t('Noch keine Zone.')}</p>`}</div>
        <div class="unterkopf"><span>${t('Sequenzen')}</span>${this._knopf('e-seq-neu', 'mdi:plus', t('Sequenz anlegen'), { ci }, t('Sequenz'))}</div>
        <div class="ez-liste">${seqs || `<p class="leer">${t('Noch keine Sequenz – ohne Sequenz gibt es keine Automatik.')}</p>`}</div>
        <p class="hinweis">${t('Die Reihenfolge bestimmt die Nummern in Irrigation Unlimited (Controller {n}: …_c{n}_z1, …_c{n}_s1).', { n: ci + 1 })}</p>
      </section>`;
  }

  _einstSeq(c, ci, s, si) {
    const p = `controller.${ci}.sequenzen.${si}`;
    const optZonen = (wahl) => c.zonen.map((z) => `<option value="${esc(z.id)}" ${z.id === wahl ? 'selected' : ''}>${esc(z.name)}</option>`).join('');
    const eintraege = s.zonen.map((sz, k) => `
      <div class="sz-zeile">
        <select data-e="${p}.zonen.${k}.zone">${optZonen(sz.zone)}</select>
        <span class="feld">${t('Dauer')}${this._zahlFeld(`${p}.zonen.${k}.dauer_min`, sz.dauer_min, 1, 240, 1, 'min', true, t('Standard'))}</span>
        ${this._haken(`${p}.zonen.${k}.aktiv`, sz.aktiv, t('aktiv'))}
        <span class="knopfgruppe">${this._knopf('e-sz-hoch', 'mdi:arrow-up', t('nach oben'), { ci, si, k })}${this._knopf('e-sz-runter', 'mdi:arrow-down', t('nach unten'), { ci, si, k })}${this._knopf('e-sz-weg', 'mdi:close', t('entfernen'), { ci, si, k })}</span>
      </div>`).join('');
    const plaene = s.plaene.map((pl, pi) => `
      <div class="es"><input type="text" data-e="${p}.plaene.${pi}.name" value="${esc(pl.name)}" maxlength="30" aria-label="${t('Name des Plans')}">
        <span class="sub">${planZeitText(pl.zeit)} · ${pl.laufzeit} %</span>${this._knopf('e-plan-weg', 'mdi:delete-outline', t('Plan löschen'), { ci, si, pi }, '', 'rot-text')}</div>`).join('');
    return `
      <div class="ez">
        <div class="ez-kopf">
          <input type="text" class="ez-name" data-e="${p}.name" value="${esc(s.name)}" maxlength="40" aria-label="${t('Name der Sequenz')}">
          ${this._knopf('e-seq-weg', 'mdi:delete-outline', t('Sequenz löschen'), { ci, si }, '', 'rot-text')}
        </div>
        <div class="formular">
          <label>${t('Pause zwischen Zonen')}${this._zahlFeld(`${p}.pause_s`, s.pause_s, 0, 600, 1, 's')}</label>
          ${this._haken(`${p}.wetter`, s.wetter, t('Laufzeit nach Wetter (Wasserbilanz)'))}
        </div>
        <div class="unterkopf klein"><span>${t('Zonen in Reihenfolge')}</span>${this._knopf('e-sz-neu', 'mdi:plus', t('Zone hinzufügen'), { ci, si }, t('Zone'))}</div>
        ${eintraege || `<p class="leer">${t('Keine Zone.')}</p>`}
        <div class="unterkopf klein"><span>${t('Pläne')}</span>${this._knopf('e-plan-neu', 'mdi:plus', t('Plan anlegen'), { ci, si }, t('Plan'))}</div>
        <div class="es-liste">${plaene || `<p class="leer">${t('Kein Plan – nur manuell.')}</p>`}</div>
        <p class="hinweis">${t('Monate, Tage, Startzeit (vor/nach Sonnenauf- oder -untergang, feste Uhrzeit) und Laufzeit der Pläne stellst du im Reiter „Automatik“ ein.')}</p>
      </div>`;
  }

  _statusLeisteHtml() {
    const st = this._cfg?.status || {};
    const meldung = st.meldung ? t(st.meldung) : '';
    const text = {
      ok: ['gruen', 'mdi:check-circle-outline', t('Irrigation Unlimited ist auf dem Stand der Einstellungen.')],
      ausstehend: ['gelb', 'mdi:timer-sand', meldung], unvollstaendig: ['gelb', 'mdi:alert-outline', meldung],
      neustart: ['gelb', 'mdi:restart-alert', meldung], include: ['rot', 'mdi:alert-circle-outline', meldung],
      konflikt: ['rot', 'mdi:alert-circle-outline', meldung], fehler: ['rot', 'mdi:alert-circle-outline', meldung],
    }[st.iu] || ['', 'mdi:help-circle-outline', meldung || t('Status unbekannt')];
    return `<section class="statusbox ${text[0]}"><ha-icon icon="${text[1]}"></ha-icon>
      <div><b>${esc(text[2] || '')}</b><div class="sub">${esc(t('Datei {datei}', { datei: st.datei || '' }))}${st.zuletzt ? ` · ${fmtZeit(st.zuletzt)}` : ''}</div></div>
      <button class="knopf klein" data-aktion="e-anwenden" title="${t('Datei neu erzeugen und Irrigation Unlimited neu laden')}">${t('Jetzt anwenden')}</button></section>`;
  }
  _statusLeiste() {
    const el = this.shadowRoot.querySelector('#status-leiste');
    if (el) el.innerHTML = this._statusLeisteHtml();
  }

  _entwurfSetzen(pfad, el) {
    const e = this._entwurfHolen();
    const teile = pfad.split('.');
    let ziel = e;
    for (const x of teile.slice(0, -1)) { const k = /^\d+$/.test(x) ? Number(x) : x; ziel = ziel[k] ?? (ziel[k] = {}); }
    const letzter = teile[teile.length - 1];
    let wert;
    if (el.type === 'checkbox') wert = el.checked;
    else if (el.dataset.typ === 'zahl') wert = num(el.value, 0);
    else if (el.dataset.typ === 'zahl-leer') wert = el.value === '' ? null : num(el.value, null);
    else wert = el.value.trim() || null;
    ziel[/^\d+$/.test(letzter) ? Number(letzter) : letzter] = wert;
    if (!this._entwurfGeaendert) {
      this._entwurfGeaendert = true;
      this.shadowRoot.querySelector('.speicher-leiste')?.classList.add('sichtbar');
    }
    if (el.getAttribute('list')) {
      const info = el.parentElement.querySelector('.ent-info');
      if (info) info.innerHTML = this._entInfo(wert);
    }
  }

  async _einstellungKlick(a, el) {
    const e = this._entwurfHolen();
    const d = el.dataset;
    const ci = Number(d.ci), i = Number(d.i), si = Number(d.si), k = Number(d.k);
    const c = e.controller[ci];
    const neu = () => { this._entwurfGeaendert = true; this._zeichnen(); };
    const tauschen = (liste, a1, a2) => { if (a2 >= 0 && a2 < liste.length) [liste[a1], liste[a2]] = [liste[a2], liste[a1]]; };
    if (a === 'e-ctl-neu') {
      e.controller.push({ id: zufall('c'), name: t('Controller {n}', { n: e.controller.length + 1 }), anschluss: 'pumpe',
        pumpe: { entity_id: null, leistung: null, energie: null, schwelle_w: 50, vorlauf_s: 2, nachlauf_s: 2, tagbetrieb: false, strompreis_kwh: null },
        wasser: { zaehler: null, nur_beregnung: false, grundpreis_monat: null, preis_m3: null, abwasser_m3: null }, zonen: [], sequenzen: [] });
      neu();
    } else if (a === 'e-ctl-weg') {
      if (confirm(t('Controller „{name}“ mit allen Zonen und Sequenzen löschen?', { name: c.name }))) { e.controller.splice(ci, 1); neu(); }
    } else if (a === 'e-zone-neu') {
      c.zonen.push({ id: zufall('z'), name: t('Zone {n}', { n: c.zonen.length + 1 }), ventile: [''], standard_min: 20, wasserhahn: false, betrieb: 'beregnung', regen: true, faktor: 100, leistung_mm_h: null, smart: { ...SMART_STANDARD } });
      neu();
    } else if (a === 'e-zone-weg') {
      const z = c.zonen[i];
      if (confirm(t('Zone „{name}“ löschen? Sie wird auch aus allen Sequenzen entfernt.', { name: z.name }))) {
        c.zonen.splice(i, 1);
        c.sequenzen.forEach((s) => { s.zonen = s.zonen.filter((sz) => sz.zone !== z.id); });
        neu();
      }
    } else if (a === 'e-zone-hoch' || a === 'e-zone-runter') {
      tauschen(c.zonen, i, a === 'e-zone-hoch' ? i - 1 : i + 1); neu();
    } else if (a === 'e-ventil-neu') {
      c.zonen[i].ventile.push(''); neu();
    } else if (a === 'e-ventil-weg') {
      c.zonen[i].ventile.splice(Number(d.j), 1); neu();
    } else if (a === 'e-seq-neu') {
      c.sequenzen.push({ id: zufall('s'), name: t('Sequenz {n}', { n: c.sequenzen.length + 1 }), pause_s: 1, wetter: true,
        zonen: c.zonen.map((z) => ({ zone: z.id, dauer_min: null, aktiv: !z.wasserhahn })), plaene: [] });
      neu();
    } else if (a === 'e-seq-weg') {
      if (confirm(t('Sequenz „{name}“ löschen?', { name: c.sequenzen[si].name }))) { c.sequenzen.splice(si, 1); neu(); }
    } else if (a === 'e-sz-neu') {
      const s = c.sequenzen[si];
      const frei = c.zonen.find((z) => !s.zonen.some((sz) => sz.zone === z.id)) || c.zonen[0];
      if (frei) { s.zonen.push({ zone: frei.id, dauer_min: null, aktiv: true }); neu(); }
    } else if (a === 'e-sz-weg') {
      c.sequenzen[si].zonen.splice(k, 1); neu();
    } else if (a === 'e-sz-hoch' || a === 'e-sz-runter') {
      tauschen(c.sequenzen[si].zonen, k, a === 'e-sz-hoch' ? k - 1 : k + 1); neu();
    } else if (a === 'e-plan-neu') {
      const s = c.sequenzen[si];
      let n = s.plaene.length + 1;
      while (s.plaene.some((x) => x.key === `plan${n}`)) n += 1;
      s.plaene.push({ key: `plan${n}`, name: t('Plan {n}', { n }), monate: [], tage: [], zeit: { bezug: 'sonnenaufgang', versatz_min: 120, uhrzeit: '06:00' }, laufzeit: 100 });
      neu();
    } else if (a === 'e-plan-weg') {
      const s = c.sequenzen[si];
      if (confirm(t('Plan „{name}“ löschen?', { name: s.plaene[Number(d.pi)].name }))) { s.plaene.splice(Number(d.pi), 1); neu(); }
    } else if (a === 'e-verwerfen') {
      this._entwurf = null; this._entwurfGeaendert = false; this._zeichnen();
    } else if (a === 'e-anwenden') {
      try { await this._ws('iu_irrigation_dashboard/anwenden'); this._meldung(t('Angewendet')); } catch (err) { /* gemeldet */ }
    } else if (a === 'e-speichern') {
      const daten = tiefKopie(e);
      daten.controller.forEach((cc) => cc.zonen.forEach((z) => { z.ventile = z.ventile.filter(Boolean); }));
      const feld = this.shadowRoot.querySelector('#e-fehler');
      const leer = daten.controller.flatMap((cc) => cc.zonen).find((z) => !z.ventile.length);
      if (leer) { if (feld) feld.textContent = t('Zone „{name}“ hat kein Ventil.', { name: leer.name }); return; }
      try {
        await this._hass.callWS({ type: 'iu_irrigation_dashboard/speichern', einstellungen: daten });
        this._entwurf = null; this._entwurfGeaendert = false;
        this._meldung(t('Gespeichert – Irrigation Unlimited wird aktualisiert'));
        this._zeichnen();
      } catch (err) {
        if (feld) feld.textContent = err.message || String(err);
      }
    }
  }

  // ── Bedienung ──────────────────────────────────────────────────────
  _plan(sid, key) {
    for (const c of this._ctlListe()) {
      const s = c.sequenzen.find((x) => x.id === sid);
      if (s) return { s, p: s.plaene.find((x) => x.key === key) };
    }
    return {};
  }

  _planChip(art, sid, key, wert) {
    const { s, p } = this._plan(sid, key);
    if (!p) return;
    const ordnung = art === 'monate' ? MONATE_IU : TAGE_IU;
    const aend = [];
    const setze = (plan, liste) => aend.push({ art: 'plan', id: sid, key: plan.key, felder: { [art]: ordnung.filter((x) => liste.includes(x)) } });
    if (p[art].includes(wert)) setze(p, p[art].filter((x) => x !== wert));
    else {
      // ein Monat gehört in einer Sequenz nur zu einem Plan: erst bei den anderen entfernen
      if (art === 'monate') s.plaene.forEach((o) => { if (o.key !== key && o.monate.includes(wert)) setze(o, o.monate.filter((x) => x !== wert)); });
      setze(p, [...p[art], wert]);
    }
    this._aendern(aend);
  }

  _manSumme(cid) {
    const c = this._ctl(cid);
    const m = this._manZustand(cid);
    let summe = 0;
    this.shadowRoot.querySelectorAll(`[data-man-zone^="${cid}|"]`).forEach((k) => {
      const mEl = k.querySelector('.zk-min');
      const min = (num(mEl.dataset.min, 0) * m.prozent) / 100;
      mEl.textContent = fmtMin(min);
      if (m.zonen.has(k.dataset.manZone.split('|')[1])) summe += min;
    });
    const s = this.shadowRoot.querySelector(`[data-man-summe="${cid}"]`);
    if (s) s.textContent = fmtMin(summe);
    return c;
  }

  _klick(ev) {
    const el = ev.target.closest('[data-aktion],[data-zeitraum],[data-plan-monat],[data-plan-tag],[data-man-zone]');
    if (!el) return;
    const d = el.dataset;
    if (d.planMonat || d.planTag) {
      const [sid, key, wert] = (d.planMonat || d.planTag).split('|');
      this._planChip(d.planMonat ? 'monate' : 'tage', sid, key, wert);
      return;
    }
    if (d.manZone) {
      const [cid, zid] = d.manZone.split('|');
      const m = this._manZustand(cid);
      if (m.zonen.has(zid)) m.zonen.delete(zid); else m.zonen.add(zid);
      this._zeichnen();
      return;
    }
    if (d.zeitraum) { this._statZeitraum = d.zeitraum; this._statDaten = null; this._zeichnen(); return; }
    const a = d.aktion;
    if (a === 'neu-laden') { window.location.reload(); return; }
    if (a.startsWith('e-')) { this._einstellungKlick(a, el); return; }
    if (a === 'betrieb') {
      this._aendern([{ art: 'zone', id: d.zone, felder: { betrieb: d.betrieb } }]);
    } else if (a === 'stopp') {
      this._ws('iu_irrigation_dashboard/stopp', { controller: d.ctl }).then(() => this._meldung(t('Wird gestoppt'))).catch(() => {});
    } else if (a === 'man-alle' || a === 'man-keine') {
      const m = this._manZustand(d.ctl);
      m.zonen = new Set(a === 'man-alle' ? this._ctl(d.ctl).zonen.map((z) => z.id) : []);
      this._zeichnen();
    } else if (a === 'man-start') {
      const m = this._manZustand(d.ctl);
      const reihenfolge = this._ctl(d.ctl).zonen.map((z) => z.id).filter((id) => m.zonen.has(id));
      this._ws('iu_irrigation_dashboard/manuell', { controller: d.ctl, zonen: reihenfolge, prozent: m.prozent }).then(() => this._meldung(t('Manueller Lauf gestartet'))).catch(() => {});
    } else if (a === 'man-seq') {
      const m = this._manZustand(d.ctl);
      this._ws('iu_irrigation_dashboard/manuell', { controller: d.ctl, sequenz: d.seq, prozent: m.prozent }).then(() => this._meldung(t('Sequenz gestartet'))).catch(() => {});
    }
  }

  _aenderung(ev) {
    const el = ev.target;
    const d = el.dataset;
    const paar = (wert) => wert.split('|');
    if (d.e) {
      this._entwurfSetzen(d.e, el);
      if (d.zonentyp && ZONENTYPEN[el.value]) {
        // Zonentyp setzt Kc, Bodenspeicher und Gießweise vor
        const zone = d.zonentyp.split('.').reduce((o, x) => o[/^\d+$/.test(x) ? Number(x) : x], this._entwurfHolen());
        Object.assign(zone.smart, ZONENTYPEN[el.value]);
      }
      if (d.zeichnen) this._zeichnen();
      return;
    }
    if (d.tagbetrieb) this._aendern([{ art: 'pumpe', id: d.tagbetrieb, felder: { tagbetrieb: el.checked } }]);
    else if (d.iuCtl) this._dienst('irrigation_unlimited', el.checked ? 'enable' : 'disable', { entity_id: d.iuCtl });
    else if ('wetterAktiv' in d) this._aendern([{ art: 'wetter', felder: { aktiv: el.checked } }]);
    else if ('grundfaktor' in d) { this._aendern([{ art: 'wetter', felder: { grundfaktor: Number(el.value) } }]); this._busy = false; }
    else if (d.seqzone) { const [sid, zid] = paar(d.seqzone); this._aendern([{ art: 'seqzone', id: sid, zone: zid, felder: { aktiv: el.checked } }]); }
    else if (d.seqdauer) {
      const [sid, zid] = paar(d.seqdauer);
      const v = el.value === '' ? null : Math.round(num(el.value, 0));
      if (v === null || v >= 1) this._aendern([{ art: 'seqzone', id: sid, zone: zid, felder: { dauer_min: v } }]);
      el.blur();
    } else if (d.planBezug || d.planVersatz || d.planUhrzeit) {
      const [sid, key] = paar(d.planBezug || d.planVersatz || d.planUhrzeit);
      const { p } = this._plan(sid, key);
      if (!p) return;
      const zeit = { ...p.zeit };
      if (d.planBezug) zeit.bezug = el.value;
      if (d.planVersatz) zeit.versatz_min = Number(el.value);
      if (d.planUhrzeit) zeit.uhrzeit = el.value.slice(0, 5);
      this._aendern([{ art: 'plan', id: sid, key, felder: { zeit } }]);
      el.blur();
    } else if (d.planLaufzeit) {
      const [sid, key] = paar(d.planLaufzeit);
      this._aendern([{ art: 'plan', id: sid, key, felder: { laufzeit: Number(el.value) } }]);
      this._busy = false;
    } else if (d.manProzent) { this._busy = false; this._zeichnen(); }
  }

  _eingabe(ev) {
    const el = ev.target;
    const d = el.dataset;
    if (d.e && el.type !== 'checkbox' && el.tagName !== 'SELECT') { this._entwurfSetzen(d.e, el); return; }
    const anzeige = (schluessel) => { const a = this.shadowRoot.querySelector(`[data-anzeige="${schluessel}"]`); if (a) a.textContent = `${fmt(num(el.value, 0))} %`; };
    if ('grundfaktor' in d) anzeige('grundfaktor');
    else if (d.planLaufzeit) anzeige(`plan:${d.planLaufzeit}`);
    else if (d.manProzent) {
      this._manZustand(d.manProzent).prozent = num(el.value, 100);
      anzeige(`man:${d.manProzent}`);
      this._manSumme(d.manProzent);
    }
  }
}

const STYLE = `
:host {
  --bg: #0a0e1a; --bg2: #0f1419; --karte: #1a1f2e; --rand: #2a3342; --rand2: #3b4455;
  --text: #ffffff; --text2: #8b92a7;
  --blau: #4a9eff; --rot: #ef4444; --gruen: #10b981; --lila: #8b5cf6; --gelb: #fbbf24; --tuerkis: #22c3ee;
  --verlauf: linear-gradient(135deg, #1a1f2e 0%, #151922 100%);
  display: block; min-height: 100vh; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5;
}
* { box-sizing: border-box; }
ha-icon { --mdc-icon-size: 18px; display: inline-flex; }
.app { min-height: 100vh; display: flex; flex-direction: column; }
header {
  background: var(--bg2); border-bottom: 1px solid var(--rand); padding: .75rem 2rem;
  display: flex; align-items: center; gap: 1.5rem; position: sticky; top: 0; z-index: 10;
}
.logo { display: flex; align-items: center; gap: .6rem; font-size: 1.25rem; font-weight: 700; color: var(--blau); background: none; border: 0; padding: 0; font-family: inherit; cursor: default; }
.logo.link { cursor: pointer; }
.logo ha-icon { --mdc-icon-size: 26px; }
nav { display: flex; gap: .25rem; flex: 1; justify-content: center; overflow-x: auto; scrollbar-width: none; }
nav::-webkit-scrollbar { display: none; }
.nav {
  display: flex; align-items: center; gap: .5rem; padding: .5rem 1rem; background: transparent; border: none;
  color: var(--text2); cursor: pointer; border-radius: 8px; font-size: .8rem; font-weight: 500; white-space: nowrap;
  transition: background .2s, color .2s; font-family: inherit;
}
.nav:hover { background: var(--karte); color: var(--text); }
.nav.aktiv { background: var(--karte); color: var(--blau); }
.kopfstatus { display: flex; gap: .5rem; flex-wrap: wrap; justify-content: flex-end; }
.pill { display: inline-flex; align-items: center; gap: .35rem; font-size: .75rem; padding: .3rem .65rem; border-radius: 999px; background: var(--karte); border: 1px solid var(--rand); color: var(--text2); white-space: nowrap; }
.pill ha-icon { --mdc-icon-size: 15px; }
.pill.gruen { color: var(--gruen); border-color: rgba(16,185,129,.4); }
.pill.blau { color: var(--blau); border-color: rgba(74,158,255,.4); }
.live { animation: puls 2s ease-in-out infinite; }
main { padding: 1.25rem 2rem 2rem; display: flex; flex-direction: column; gap: 1.25rem; max-width: 1400px; width: 100%; margin: 0 auto; }

.kacheln { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.kachel { background: var(--verlauf); border: 1px solid var(--rand); border-radius: 12px; padding: 1.1rem 1.25rem; position: relative; overflow: hidden; transition: transform .2s, border-color .2s; min-width: 0; }
.kachel::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--rand2); }
.kachel.blau::before { background: var(--blau); } .kachel.gruen::before { background: var(--gruen); }
.kachel.lila::before { background: var(--lila); } .kachel.gelb::before { background: var(--gelb); }
.kachel.tuerkis::before { background: var(--tuerkis); } .kachel.rot::before { background: var(--rot); }
.kachel:hover { transform: translateY(-2px); border-color: var(--rand2); }
.kachel-kopf { display: flex; align-items: center; gap: .45rem; margin-bottom: .4rem; color: var(--text2); }
.kachel-kopf span { font-size: .7rem; text-transform: uppercase; letter-spacing: .5px; font-weight: 600; }
.kachel-wert { font-size: 1.6rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.einheit { font-size: .9rem; color: var(--text2); font-weight: 400; margin-left: .25rem; }
.sub { font-size: .75rem; color: var(--text2); }

.karte { background: var(--verlauf); border: 1px solid var(--rand); border-radius: 12px; padding: 1.25rem; min-width: 0; }
.kopf { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
.kopf > div:first-child { display: flex; align-items: center; gap: .5rem; }
.kopf > div:first-child span { font-size: .95rem; font-weight: 600; }
.kopf > div:first-child ha-icon { color: var(--blau); }
.spalten { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.live-badge { font-size: .6rem; font-weight: 700; color: var(--gruen); background: rgba(16,185,129,.15); padding: .2rem .5rem; border-radius: 4px; letter-spacing: 1px; animation: puls 2s ease-in-out infinite; }
@keyframes puls { 0%,100% { opacity: 1; } 50% { opacity: .5; } }
.hinweis { font-size: .78rem; color: var(--text2); margin: 1rem 0 0; }
.hinweis.oben { margin: 0; }
.leer { color: var(--text2); text-align: center; padding: 2rem 0; margin: 0; }
.pulsiert { animation: puls 1s ease-in-out infinite; }

/* Anlage */
.anlage { width: 100%; height: auto; display: block; background: var(--bg2); border-radius: 8px; }
.anlage-schmal { display: none; }
.anlage .lbl { fill: var(--text); font-size: 13px; font-weight: 600; }
.anlage .sub { fill: var(--text2); font-size: 12px; }
.anlage .rest { fill: var(--blau); font-weight: 700; }
.anlage .mitte { text-anchor: middle; }
.rohr { fill: none; stroke: var(--rand); stroke-width: 10; stroke-linecap: round; stroke-linejoin: round; transition: stroke .4s; }
.rohr.duenn { stroke-width: 6; }
.rohr.wasser { stroke: #1d4f8f; }
.fluss { fill: none; stroke: var(--blau); stroke-width: 4; stroke-linecap: round; stroke-dasharray: 2 14; animation: fluss .7s linear infinite; }
.fluss.duenn { stroke-width: 3; }
.fluss.steht { animation: none; stroke-dasharray: none; stroke-opacity: .35; }
@keyframes fluss { to { stroke-dashoffset: -16; } }
.ventil path { fill: var(--karte); stroke: var(--rand2); stroke-width: 2; stroke-linejoin: round; }
.ventil line, .ventil rect { stroke: var(--rand2); stroke-width: 2; fill: var(--karte); }
.ventil.auf path { fill: var(--gruen); stroke: var(--gruen); }
.ventil.auf rect { fill: var(--gruen); stroke: var(--gruen); }
.regner .duese { fill: var(--karte); stroke: var(--rand2); stroke-width: 2; }
.regner.aktiv .duese { fill: var(--blau); stroke: var(--blau); }
.regner .nebel { fill: var(--blau); opacity: .1; animation: nebel 1.6s ease-in-out infinite; }
@keyframes nebel { 0%, 100% { opacity: .06; } 50% { opacity: .16; } }
.regner .tropfen { fill: #7cc4ff; opacity: 0; animation: tropfen 1.2s linear infinite; }
.regner .tropfen.kurz { animation-name: tropfen-kurz; }
.hahn .koerper, .hahn .hebel { fill: var(--karte); stroke: var(--rand2); stroke-width: 2; }
.hahn line { stroke: var(--rand2); stroke-width: 2; }
.hahn .auslauf { fill: none; stroke: var(--rand2); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
.hahn.aktiv .koerper, .hahn.aktiv .hebel { fill: var(--blau); stroke: var(--blau); }
.hahn.aktiv line, .hahn.aktiv .auslauf { stroke: var(--blau); }
.hahn .hahn-tropfen { fill: #7cc4ff; opacity: 0; animation: hahn-tropfen 1s ease-in infinite; }
@keyframes hahn-tropfen { 0% { transform: translateY(0) scale(.6); opacity: 0; } 15% { opacity: 1; } 80% { opacity: .9; } 100% { transform: translateY(16px) scale(1); opacity: 0; } }
@keyframes tropfen { 0% { transform: translateX(9px) scale(.5); opacity: 0; } 15% { opacity: 1; } 75% { opacity: .8; } 100% { transform: translateX(30px) scale(1.1); opacity: 0; } }
@keyframes tropfen-kurz { 0% { transform: translateX(9px) scale(.5); opacity: 0; } 15% { opacity: 1; } 75% { opacity: .8; } 100% { transform: translateX(26px) scale(1.1); opacity: 0; } }
.zone.gesperrt .lbl { fill: var(--text2); }
.zone.nass .lbl { fill: var(--blau); }
.treffer { fill: transparent; }
.pumpe > circle:first-of-type { fill: var(--karte); stroke: var(--rand2); stroke-width: 3; }
.pumpe.an > circle:first-of-type { stroke: var(--gruen); }
.pumpe .rad path { fill: var(--rand2); }
.pumpe.an .rad path { fill: var(--gruen); }
.pumpe.dreht .rad { animation: drehen 1s linear infinite; }
.pumpe .nabe { fill: var(--bg2); }
@keyframes drehen { to { transform: rotate(360deg); } }
.brunnen .wand { fill: none; stroke: var(--rand2); stroke-width: 3; }
.brunnen .wasser { fill: #1d4f8f; opacity: .7; }

.laufbox { margin-top: 1rem; background: var(--bg2); border: 1px solid rgba(74,158,255,.35); border-radius: 10px; padding: 1rem 1.25rem; }
.laufkopf { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
.lauf-name { font-size: 1.15rem; font-weight: 700; color: var(--blau); }
.lauf-rest { text-align: right; font-size: 1.4rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.balken { height: 6px; background: var(--rand); border-radius: 3px; overflow: hidden; margin-top: .75rem; }
.balken > div { height: 100%; background: var(--blau); border-radius: 3px; transition: width 1s linear; }

/* Bedienelemente */
.zeile-knoepfe { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-top: 1rem; flex-wrap: wrap; }
.knopf { display: inline-flex; align-items: center; gap: .4rem; padding: .55rem 1rem; border-radius: 8px; border: 1px solid var(--rand); background: var(--karte); color: var(--text); cursor: pointer; font: inherit; font-size: .85rem; font-weight: 600; transition: opacity .2s, border-color .2s; }
.knopf:hover { border-color: var(--blau); }
.knopf:disabled { opacity: .4; cursor: not-allowed; }
.knopf.blau { background: var(--blau); border-color: var(--blau); color: #fff; }
.knopf.rot { background: var(--rot); border-color: var(--rot); color: #fff; }
.knopf.gross { padding: .8rem 1.6rem; font-size: 1rem; }
.knopf.klein { padding: .35rem .75rem; font-size: .75rem; font-weight: 500; color: var(--text2); }
.knopf.klein:hover { color: var(--text); }
.knopfgruppe { display: flex; gap: .4rem; flex-wrap: wrap; }
.knopfgruppe.senkrecht { flex-direction: column; gap: .6rem; }
.modus { display: inline-flex; align-items: center; gap: .3rem; background: var(--bg2); border: 1px solid var(--rand); border-radius: 8px; padding: .2rem .25rem .2rem .7rem; flex-wrap: wrap; }
.modus-titel { font-size: .85rem; color: var(--text2); margin-right: .35rem; }
.modus-knopf { display: inline-flex; align-items: center; gap: .35rem; padding: .35rem .75rem; border-radius: 6px; border: 1px solid transparent; background: transparent; color: var(--text2); font: inherit; font-size: .82rem; cursor: pointer; transition: background .15s, color .15s; }
.modus-knopf ha-icon { --mdc-icon-size: 16px; }
.modus-knopf:hover { color: var(--text); }
.modus-knopf.an { background: rgba(74,158,255,.2); border-color: var(--blau); color: var(--text); font-weight: 600; }
.schalter { display: inline-flex; align-items: center; gap: .6rem; cursor: pointer; font-size: .85rem; color: var(--text2); user-select: none; }
.schalter input { position: absolute; opacity: 0; width: 0; height: 0; }
.schalter span { width: 38px; height: 22px; border-radius: 11px; background: var(--rand); position: relative; transition: background .2s; flex-shrink: 0; }
.schalter span::after { content: ''; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: var(--text2); transition: transform .2s, background .2s; }
.schalter input:checked + span { background: rgba(74,158,255,.35); }
.schalter input:checked + span::after { transform: translateX(16px); background: var(--blau); }
.schalter input:disabled + span { opacity: .4; }
.schalter input:focus-visible + span { outline: 2px solid var(--blau); outline-offset: 2px; }
.schalter.gross { font-size: .95rem; font-weight: 600; color: var(--text); }

.info-raster { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; padding: 1rem; background: var(--bg2); border-radius: 10px; }
.info-raster.zwei { grid-template-columns: 1fr 1fr; }
.gross-wert { font-size: 1.15rem; font-weight: 700; margin: .1rem 0; }

.regler { margin-top: 1.25rem; }
.regler-kopf { display: flex; justify-content: space-between; font-size: .85rem; color: var(--text2); margin-bottom: .4rem; }
.regler-kopf b { color: var(--text); font-size: 1.1rem; font-variant-numeric: tabular-nums; }
input[type=range] { width: 100%; accent-color: var(--blau); height: 28px; cursor: pointer; }
.skala { display: flex; justify-content: space-between; font-size: .7rem; color: var(--text2); }

.zonen-liste { display: flex; flex-direction: column; }
.zone-zeile { display: grid; grid-template-columns: auto 1fr 110px 110px; gap: 1rem; align-items: center; padding: .7rem .25rem; border-bottom: 1px solid var(--rand); }
.zone-zeile:last-child { border-bottom: none; }
.zone-zeile.aus .zone-name, .zone-zeile.aus .zone-wert { color: var(--text2); }
.zone-zeile.aktiv { background: rgba(74,158,255,.08); border-radius: 8px; }
.zone-name { font-weight: 600; display: flex; align-items: center; gap: .6rem; }
.nr { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 6px; background: var(--bg2); border: 1px solid var(--rand); font-size: .75rem; color: var(--text2); flex-shrink: 0; }
.zone-wert { text-align: right; font-variant-numeric: tabular-nums; display: flex; flex-direction: column; }
.min-feld { display: inline-flex; align-items: center; justify-content: flex-end; gap: .35rem; }
.min-feld input { width: 64px; background: var(--bg2); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .3rem .4rem; font: inherit; font-size: .95rem; text-align: right; color-scheme: dark; }
.min-feld input:hover { border-color: var(--rand2); }
.min-feld input:focus { outline: none; border-color: var(--blau); }

.saisons { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.saison { background: var(--bg2); border: 1px solid var(--rand); border-radius: 10px; padding: 1rem; display: flex; flex-direction: column; gap: .5rem; min-width: 0; }
.saison.aktuell { border-color: rgba(74,158,255,.5); }
.saison-kopf { display: flex; align-items: center; gap: .6rem; margin-bottom: .25rem; }
.saison-kopf b { font-size: 1rem; }
.saison .regler { margin-top: .25rem; }
.chips { display: flex; flex-wrap: wrap; gap: .3rem; }
.chips.monate { display: grid; grid-template-columns: repeat(6, 1fr); }
.chip { padding: .3rem .2rem; min-width: 2.4rem; border-radius: 6px; border: 1px solid var(--rand); background: var(--karte); color: var(--text2); font: inherit; font-size: .75rem; cursor: pointer; transition: background .15s, border-color .15s, color .15s; }
.chip:hover { border-color: var(--blau); color: var(--text); }
.chip.an { background: rgba(74,158,255,.2); border-color: var(--blau); color: var(--text); font-weight: 600; }
.saison-start { display: flex; justify-content: space-between; align-items: center; gap: .5rem; font-size: .85rem; margin-top: .25rem; }
.saison-start select { background: var(--karte); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .3rem .4rem; font: inherit; font-size: .8rem; color-scheme: dark; margin-left: .3rem; }
.tabelle { width: 100%; border-collapse: collapse; font-size: .85rem; }
.tabelle th { text-align: left; color: var(--text2); font-weight: 500; font-size: .75rem; padding: .4rem .5rem; border-bottom: 1px solid var(--rand); }
.tabelle td { padding: .55rem .5rem; border-bottom: 1px solid var(--rand); }
.tabelle tr:last-child td { border-bottom: none; }
.tabelle .r { text-align: right; }
.tabelle tr.markiert td { color: var(--blau); font-weight: 600; }

.zonen-raster { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); grid-auto-rows: 1fr; gap: .75rem; }
.zonenkarte { position: relative; display: block; background: var(--bg2); border: 1px solid var(--rand); border-radius: 10px; padding: .8rem .9rem; cursor: pointer; transition: border-color .2s, background .2s; user-select: none; }
.zonenkarte input { position: absolute; opacity: 0; }
.zonenkarte:hover { border-color: var(--rand2); }
.zonenkarte.an { border-color: var(--blau); background: rgba(74,158,255,.08); }
.zonenkarte.aktiv { box-shadow: 0 0 0 2px var(--gruen); }
.zonenkarte:focus-within { outline: 2px solid var(--blau); outline-offset: 2px; }
.zk-kopf { display: flex; justify-content: space-between; align-items: center; gap: .5rem; height: 24px; }
.haken { flex-shrink: 0; width: 22px; height: 22px; border-radius: 6px; border: 1px solid var(--rand2); display: inline-flex; align-items: center; justify-content: center; color: transparent; }
.haken ha-icon { --mdc-icon-size: 16px; }
.zonenkarte.an .haken { background: var(--blau); border-color: var(--blau); color: #fff; }
.zk-name { font-weight: 600; font-size: .9rem; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.zk-info { height: 22px; margin: .3rem 0 .2rem; display: flex; align-items: center; }
.hahn-info { font-size: .65rem; font-weight: 600; color: var(--tuerkis); border: 1px solid rgba(34,195,238,.45); border-radius: 4px; padding: .05rem .35rem; white-space: nowrap; line-height: 1.4; }
.zk-min { font-size: 1.15rem; font-weight: 700; color: var(--blau); font-variant-numeric: tabular-nums; }
.zonenkarte:not(.an) .zk-min { color: var(--text2); }
.start-zeile { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-top: 1.25rem; padding-top: 1.25rem; border-top: 1px solid var(--rand); flex-wrap: wrap; }

.formular { display: flex; flex-direction: column; gap: .75rem; }
.formular label { display: flex; justify-content: space-between; align-items: center; gap: 1rem; font-size: .85rem; color: var(--text2); }
.feld { display: inline-flex; align-items: center; gap: .4rem; }
.formular input[type=number], .formular select { background: var(--bg2); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .4rem .6rem; font: inherit; font-size: .85rem; width: 90px; color-scheme: dark; }
.formular select { width: 110px; }
.formular input:focus, .formular select:focus { outline: none; border-color: var(--blau); }

/* Diagramme */
.diagramm, .kennlinie { width: 100%; height: auto; display: block; }
.gitter { stroke: var(--rand); stroke-width: 1; stroke-dasharray: 2 4; }
.achse { stroke: var(--rand2); stroke-width: 1; }
.ax { fill: var(--text2); font-size: 11px; }
.ax.r { text-anchor: end; } .ax.mitte { text-anchor: middle; }
.bar.gemessen { fill: var(--tuerkis); }
.bar.prognose { fill: var(--lila); }
.bar.garten { fill: var(--blau); }
.bar.wasser, .sw.wasser { fill: #38bdf8; background: #38bdf8; }
.bar.abwasser, .sw.abwasser { fill: #6366f1; background: #6366f1; }
.bar.grund, .sw.grund { fill: var(--lila); background: var(--lila); }
.bar.strom, .sw.strom { fill: var(--gelb); background: var(--gelb); }
.zaehler-symbol > circle { fill: var(--karte); stroke: var(--rand2); stroke-width: 3; }
.zaehler-symbol.an > circle { stroke: #38bdf8; }
.zaehler-symbol text { fill: var(--text2); text-anchor: middle; }
.zaehler-symbol .wert { font-size: 12px; font-weight: 600; }
.zaehler-symbol .einheit { font-size: 10px; }
.zaehler-symbol.an text { fill: #38bdf8; }
.formular select.auto { width: auto; }
.badge-exp { display: inline-block; margin-left: .5rem; padding: .1rem .45rem; border-radius: 999px; font-size: .62rem; font-weight: 600;
  letter-spacing: .05em; text-transform: uppercase; vertical-align: middle; color: var(--gelb); background: rgba(251, 191, 36, .12); border: 1px solid rgba(251, 191, 36, .4); }
.smart-zone { margin-top: .9rem; padding-top: .6rem; border-top: 1px dashed var(--rand); }
.tabelle-scroll { overflow-x: auto; }
.erweitert summary { cursor: pointer; font-size: .85rem; color: var(--text2); }
.erweitert[open] summary { margin-bottom: .75rem; }
.jetzt { stroke: var(--text2); stroke-width: 1; stroke-dasharray: 4 3; }
.kennlinie .linie { fill: none; stroke: var(--blau); stroke-width: 2; stroke-linejoin: round; }
.kennlinie .punkt { fill: var(--gelb); stroke: var(--bg2); stroke-width: 2; }
.legende { display: flex; gap: 1rem; font-size: .75rem; color: var(--text2); }
.legende span { display: inline-flex; align-items: center; gap: .35rem; }
.sw { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
.sw.gemessen { background: var(--tuerkis); } .sw.prognose { background: var(--lila); }
.tip { position: fixed; left: 0; top: 0; pointer-events: none; opacity: 0; transition: opacity .12s; background: var(--karte); border: 1px solid var(--rand2); border-radius: 8px; padding: .45rem .65rem; font-size: .75rem; color: var(--text); box-shadow: 0 8px 24px rgba(0,0,0,.4); z-index: 50; white-space: nowrap; }
.tip b { font-weight: 600; }

.hbars { display: flex; flex-direction: column; gap: .55rem; }
.hbar { display: grid; grid-template-columns: 180px 1fr 100px; gap: 1rem; align-items: center; font-size: .85rem; }
.hbar-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hbar-spur { height: 10px; background: var(--bg2); border-radius: 5px; overflow: hidden; }
.hbar-spur i { display: block; height: 100%; background: var(--blau); border-radius: 5px; }
.hbar-wert { text-align: right; color: var(--text2); font-variant-numeric: tabular-nums; }

.zeitwahl { display: flex; gap: .5rem; flex-wrap: wrap; }
.zeit { padding: .4rem .875rem; background: var(--karte); border: 1px solid var(--rand); color: var(--text2); border-radius: 6px; cursor: pointer; font: inherit; font-size: .8rem; font-weight: 500; }
.zeit:hover { border-color: var(--blau); color: var(--text); }
.zeit.aktiv { background: var(--blau); border-color: var(--blau); color: #fff; }

.meldung { position: fixed; bottom: 1.5rem; left: 50%; transform: translate(-50%, 20px); opacity: 0; transition: opacity .2s, transform .2s; background: var(--karte); border: 1px solid var(--rand2); color: var(--text); padding: .6rem 1rem; border-radius: 8px; font-size: .85rem; z-index: 60; pointer-events: none; }
.meldung.sichtbar { opacity: 1; transform: translate(-50%, 0); }
.meldung.fehler { border-color: var(--rot); color: var(--rot); }

/* Einstellungen */
.statusbox { display: flex; align-items: center; gap: .9rem; padding: .9rem 1.1rem; border-radius: 10px; border: 1px solid var(--rand); background: var(--karte); }
.statusbox > div { flex: 1; }
.statusbox ha-icon { --mdc-icon-size: 24px; }
.statusbox.gruen { border-color: rgba(16,185,129,.45); } .statusbox.gruen ha-icon { color: var(--gruen); }
.statusbox.gelb { border-color: rgba(251,191,36,.45); } .statusbox.gelb ha-icon { color: var(--gelb); }
.statusbox.rot { border-color: rgba(239,68,68,.5); } .statusbox.rot ha-icon { color: var(--rot); }
.formular.breit label { gap: 1.5rem; }
.formular input[type=text] { background: var(--bg2); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .4rem .6rem; font: inherit; font-size: .85rem; width: 280px; max-width: 100%; color-scheme: dark; }
.ent-feld { display: inline-flex; flex-direction: column; align-items: flex-end; gap: .15rem; min-width: 0; }
.ent-feld input { background: var(--bg2); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .4rem .6rem; font: inherit; font-size: .85rem; width: 300px; max-width: 100%; color-scheme: dark; }
.ent-feld input:focus, .ez-name:focus, .es input:focus { outline: none; border-color: var(--blau); }
.ent-info { font-size: .72rem; color: var(--text2); max-width: 300px; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.warn { color: var(--gelb); }
.ez-liste { display: flex; flex-direction: column; gap: .9rem; }
.ez { background: var(--bg2); border: 1px solid var(--rand); border-radius: 10px; padding: .9rem 1rem; }
.ez-kopf { display: flex; align-items: center; gap: .6rem; margin-bottom: .75rem; }
.ez-name { flex: 1; min-width: 0; background: var(--karte); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .4rem .6rem; font: inherit; font-weight: 600; }
.ez-raster { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.ez-ventile { display: flex; flex-direction: column; gap: .45rem; align-items: flex-start; }
.ez-ventil { display: flex; align-items: flex-start; gap: .4rem; }
.ez-ventil .ent-feld { align-items: flex-start; }
.ez-ventil .ent-info { text-align: left; }
.knopf.rot-text { color: var(--rot); }
.knopf.klein ha-icon { --mdc-icon-size: 16px; }
.es-liste { display: flex; flex-direction: column; gap: .5rem; }
.es { display: flex; align-items: center; gap: .6rem; }
.es input { flex: 1; background: var(--bg2); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .4rem .6rem; font: inherit; }
.speicher-leiste { position: sticky; bottom: 1rem; display: none; align-items: center; gap: .75rem; justify-content: flex-end; padding: .75rem 1rem; border-radius: 10px; background: var(--karte); border: 1px solid var(--blau); box-shadow: 0 8px 24px rgba(0,0,0,.45); z-index: 5; flex-wrap: wrap; }
.speicher-leiste.sichtbar { display: flex; }
.speicher-leiste > span:first-child { margin-right: auto; font-weight: 600; }
.hahn-liste { display: flex; flex-direction: column; gap: .6rem; }
.hahn-zeile { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }

@media (max-width: 1100px) {
  .kacheln { grid-template-columns: repeat(2, 1fr); }
  .saisons { grid-template-columns: 1fr 1fr; }
  .info-raster { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 870px) {
  header { padding: .6rem 1rem; gap: .75rem; flex-wrap: wrap; }
  nav { order: 3; flex-basis: 100%; justify-content: flex-start; }
  .nav span { display: none; }
  .nav { padding: .5rem .8rem; }
  .nav.aktiv span { display: inline; }
  main { padding: 1rem; gap: 1rem; }
  .spalten { grid-template-columns: 1fr; }
  .saisons { grid-template-columns: 1fr; }
  .ez-raster { grid-template-columns: 1fr; }
  .formular label { flex-wrap: wrap; }
  .anlage-breit { display: none; }
  .anlage-schmal { display: block; }
  /* Handy: Logo und Status in einer Zeile, Status bei Platzmangel seitlich wischbar */
  .logo { flex-shrink: 0; }
  .kopfstatus { flex: 1; min-width: 0; flex-wrap: nowrap; justify-content: flex-start; overflow-x: auto; scrollbar-width: none; }
  .kopfstatus::-webkit-scrollbar { display: none; }
  .kopfstatus > :first-child { margin-left: auto; }
}
@media (max-width: 560px) {
  .logo-text { display: none; }
  .kachel-wert { font-size: 1.3rem; }
  .zone-zeile { grid-template-columns: auto 1fr 110px; }
  .zone-zeile .geplant { display: none; }
  .hbar { grid-template-columns: 110px 1fr 70px; gap: .5rem; }
  .info-raster { gap: .75rem; padding: .75rem; }
  .zonen-raster { grid-template-columns: repeat(2, 1fr); }
}

/* Etappe 2: Controller, Sequenzen, Pläne, Wetter */
.ctl-karte { display: flex; flex-direction: column; gap: 1rem; }
.seq { background: var(--bg2); border: 1px solid var(--rand); border-radius: 10px; padding: 1rem; display: flex; flex-direction: column; gap: .6rem; }
.seq-kopf { display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; align-items: baseline; }
.seq-kopf b { font-size: 1rem; }
.summe { text-align: right; }
.seq-start { display: flex; flex-direction: column; gap: .4rem; margin-top: 1rem; }
.zeit-felder { display: inline-flex; gap: .35rem; flex-wrap: wrap; justify-content: flex-end; }
.zeit-felder select, .zeit-felder input { background: var(--karte); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .3rem .4rem; font: inherit; font-size: .8rem; color-scheme: dark; }
.sw.et0 { background: var(--gelb); }
.bar.et0 { fill: var(--gelb); }
.titel-feld { background: transparent; border: 1px solid transparent; color: var(--text); font: inherit; font-size: .95rem; font-weight: 600; padding: .2rem .4rem; border-radius: 6px; min-width: 0; }
.titel-feld:hover, .titel-feld:focus { border-color: var(--rand2); outline: none; background: var(--bg2); }
.unterkopf { display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0 .6rem; font-weight: 600; }
.unterkopf.klein { margin: .6rem 0 .3rem; font-size: .85rem; color: var(--text2); }
.sz-zeile { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; padding: .35rem 0; border-bottom: 1px solid var(--rand); }
.sz-zeile select { background: var(--karte); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .35rem .5rem; font: inherit; font-size: .85rem; color-scheme: dark; min-width: 160px; }
.sz-zeile .feld input { width: 70px; background: var(--karte); border: 1px solid var(--rand); color: var(--text); border-radius: 6px; padding: .3rem .4rem; font: inherit; color-scheme: dark; }
.sz-zeile .feld { font-size: .8rem; color: var(--text2); gap: .3rem; }
button.zonenkarte { text-align: left; width: 100%; font: inherit; color: var(--text); }
.formular input[type=number] { width: 90px; }
`;

customElements.define('iu-irrigation-panel', BeregnungPanel);
