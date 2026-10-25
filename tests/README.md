# Tests

The tests run without a Home Assistant instance. They need Python 3.12 and
the packages in `requirements.txt` (`homeassistant` for the helpers and
schemas, `mini-racer` as a JavaScript engine instead of a browser).

```sh
python3.12 -m venv tests/.venv
tests/.venv/bin/pip install -r tests/requirements.txt      # Windows: tests\.venv\Scripts\pip
```

Run from the repository root:

| Test | Command | Checks |
|---|---|---|
| Settings and IU file | `tests/.venv/bin/python tests/test_generator.py [--yaml]` | example system (`beispiel.py`) → Irrigation Unlimited configuration, YAML round trip, entity mapping, import of an existing IU configuration, rejected invalid settings. With `custom_components/irrigation_unlimited/` next to it (ignored by git), the result is also validated against the IU schema. |
| Water balance | `tests/.venv/bin/python tests/test_bilanz.py` | daily balance, soil storage limit, rain per zone, credit for runs, factors and run time percentages; ET₀ against FAO-56 example 18, radiation estimated from temperature when no sensor is set |
| Water meter | `tests/.venv/bin/python tests/test_wasser.py` | meter readings in litres, consumption shared among the zones that ran between two readings, household use without a run is not counted |
| configuration.yaml | `tests/.venv/bin/python tests/test_konfig_yaml.py` | finds an own `irrigation_unlimited:` section (nested lines, comments, `!include`, end of file, BOM; indented in a package does not count), comments it out without touching the rest of the file (line endings, YAML result), backup, nothing changed if the section differs from what was shown |
| Smart run time | `tests/.venv/bin/python tests/test_smart.py` | experimental smart run time: planning per zone (watering mode, threshold, application rate per source, maximum run time, cycles), balance with Kc and own storage, credit of measured amounts, IU sequence with cycles and soak pause, percentages per entry; with the switch off the IU file is unchanged |
| Panel | `tests/.venv/bin/python tests/js_render.py [--text]` | renders every tab in German and English, idle and during a run, and reports texts without an English translation |
| JavaScript syntax | `tests/.venv/bin/python tests/js_syntax.py custom_components/iu_irrigation_dashboard/www/*.js` | compiles the panel code |
| Python | `tests/.venv/bin/python -m pyflakes custom_components/iu_irrigation_dashboard tests` | unused or undefined names |

On Windows set `PYTHONIOENCODING=utf-8` for the umlauts in the output.
