"""Referenz-Verdunstung ET₀ nach FAO-56 (Penman-Monteith, Tageswerte).

Reine Berechnung ohne Home Assistant, damit sie auch in tests/ läuft.
Quelle: Allen et al., FAO Irrigation and Drainage Paper 56, Kap. 3–4.
"""

from __future__ import annotations

import math

SIGMA = 4.903e-9  # Stefan-Boltzmann, MJ K⁻⁴ m⁻² Tag⁻¹


def saettigungsdampfdruck(t: float) -> float:
    """e°(T) in kPa (Gl. 11)."""
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def luftdruck_aus_hoehe(hoehe_m: float) -> float:
    """Luftdruck in kPa aus der Höhe (Gl. 7)."""
    return 101.3 * ((293 - 0.0065 * hoehe_m) / 293) ** 5.26


def wind_2m(wind_ms: float, messhoehe_m: float) -> float:
    """Windgeschwindigkeit auf 2 m umrechnen (Gl. 47)."""
    if abs(messhoehe_m - 2) < 0.05:
        return wind_ms
    return wind_ms * 4.87 / math.log(67.8 * messhoehe_m - 5.42)


def extraterrestrische_strahlung(tag_im_jahr: int, breite_grad: float) -> float:
    """Ra in MJ m⁻² Tag⁻¹ (Gl. 21–25)."""
    phi = math.radians(breite_grad)
    dr = 1 + 0.033 * math.cos(2 * math.pi * tag_im_jahr / 365)
    delta = 0.409 * math.sin(2 * math.pi * tag_im_jahr / 365 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    return 24 * 60 / math.pi * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )


def strahlung_aus_bewoelkung(ra: float, hoehe_m: float, bewoelkung_prozent: float) -> float:
    """Globalstrahlung Rs aus der Bewölkung (Kasten & Czeplak), MJ m⁻² Tag⁻¹."""
    rso = (0.75 + 2e-5 * hoehe_m) * ra
    return rso * (1 - 0.75 * (max(0.0, min(100.0, bewoelkung_prozent)) / 100) ** 3.4)


def strahlung_aus_temperatur(ra: float, tmin: float, tmax: float, hoehe_m: float, krs: float = 0.16) -> float:
    """Globalstrahlung Rs aus der Temperaturspanne (Hargreaves, Gl. 50),
    MJ m⁻² Tag⁻¹ – Ersatz, wenn keine Einstrahlung gemessen wird. kRs 0,16
    im Binnenland, 0,19 an der Küste; höchstens die Strahlung bei klarem
    Himmel."""
    rso = (0.75 + 2e-5 * hoehe_m) * ra
    return min(rso, krs * math.sqrt(max(0.0, tmax - tmin)) * ra)


def et0_tag(
    tmin: float,
    tmax: float,
    rh_mittel: float,
    wind_ms: float,
    rs_mj: float,
    tag_im_jahr: int,
    breite_grad: float,
    hoehe_m: float,
    wind_messhoehe_m: float = 2.0,
    rh_min: float | None = None,
    rh_max: float | None = None,
) -> float:
    """ET₀ in mm/Tag.

    tmin/tmax °C, rh_mittel %, wind_ms Mittel in m/s auf wind_messhoehe_m,
    rs_mj Globalstrahlung des Tages in MJ m⁻² (= mittlere W/m² × 0.0864).
    Mit rh_min/rh_max (Tagesminimum/-maximum) genauer als mit dem Mittel.
    """
    if tmax < tmin:
        tmin, tmax = tmax, tmin
    tmittel = (tmin + tmax) / 2
    druck = luftdruck_aus_hoehe(hoehe_m)
    gamma = 0.000665 * druck
    es = (saettigungsdampfdruck(tmax) + saettigungsdampfdruck(tmin)) / 2
    if rh_min is not None and rh_max is not None:
        # Gl. 17
        ea = (saettigungsdampfdruck(tmin) * min(100.0, rh_max) / 100
              + saettigungsdampfdruck(tmax) * max(0.0, rh_min) / 100) / 2
    else:
        # Gl. 19
        ea = max(0.0, min(100.0, rh_mittel)) / 100 * es
    steigung = 4098 * saettigungsdampfdruck(tmittel) / (tmittel + 237.3) ** 2
    # FAO empfiehlt mindestens 0,5 m/s (Messfehler bei Windstille)
    u2 = max(0.5, wind_2m(max(0.0, wind_ms), wind_messhoehe_m))

    ra = extraterrestrische_strahlung(tag_im_jahr, breite_grad)
    rso = (0.75 + 2e-5 * hoehe_m) * ra
    rs = max(0.0, rs_mj)
    rns = (1 - 0.23) * rs
    verhaeltnis = min(1.0, rs / rso) if rso > 0 else 0.0
    rnl = (
        SIGMA
        * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2
        * (0.34 - 0.14 * math.sqrt(ea))
        * (1.35 * verhaeltnis - 0.35)
    )
    rn = rns - rnl
    et0 = (0.408 * steigung * rn + gamma * 900 / (tmittel + 273) * u2 * (es - ea)) / (
        steigung + gamma * (1 + 0.34 * u2)
    )
    return max(0.0, et0)
