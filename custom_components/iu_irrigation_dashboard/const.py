"""Konstanten der Integration „IU Irrigation Dashboard“."""

DOMAIN = "iu_irrigation_dashboard"
NAME = "IU Irrigation Dashboard"

STORAGE_KEY = f"{DOMAIN}.einstellungen"
LAUFDATEN_KEY = f"{DOMAIN}.laufdaten"
STORAGE_VERSION = 1

PANEL_URL_PATH = "irrigation"
PANEL_ELEMENT = "iu-irrigation-panel"
STATIC_URL = f"/{DOMAIN}_static"

# Erzeugte Irrigation-Unlimited-Konfiguration (relativ zu /config)
IU_DATEI = f"packages/{DOMAIN}.yaml"
IU_DOMAIN = "irrigation_unlimited"

# Wird nach jedem Neuladen/Durchsetzen der IU-Konfiguration ausgelöst
EVENT_IU_NEU = f"{DOMAIN}_iu_reloaded"

SIGNAL_EINSTELLUNGEN = f"{DOMAIN}_geaendert"

WOCHENTAGE = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MONATE = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

BETRIEB_WASSERHAHN = "wasserhahn"
BETRIEB_BEREGNUNG = "beregnung"

# Wasserhahn: Ventil schließen, wenn die Pumpe so lange aus ist
WASSERHAHN_AUS_VERZOEGERUNG = 30
# Änderungen sammeln, bevor die IU-Datei geschrieben wird
ANWENDEN_VERZOEGERUNG = 3
