# Behavioral test harness: substitutes the @@ markers in every code template,
# EXECUTES it in an isolated namespace, and verifies parse_json_loose handles
# the real interpreter-output wrapping (single and double repr layers).
import ast
import io
import json
import os
import re

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../code")

SAMPLE = json.dumps({"layer1_violations": [{"rule": "ROLE_VS_REQUEST", "detail": "x"}], "checked": ["A"]})
WRAPPED_1 = str({"result": SAMPLE})                      # single repr layer
WRAPPED_2 = str({"result": WRAPPED_1})                   # double repr layer
NEWLINE_WRAPPED = "\n" + WRAPPED_2 + "\n"                # with stray newlines

CASES = [
    ("plain json", SAMPLE, json.loads(SAMPLE)),
    ("wrapped once", WRAPPED_1, json.loads(SAMPLE)),
    ("wrapped twice", WRAPPED_2, json.loads(SAMPLE)),
    ("newline + double wrap", NEWLINE_WRAPPED, json.loads(SAMPLE)),
]

failures = []
for path in sorted(os.listdir(".")):
    if not path.endswith(".template.py"):
        continue
    source = io.open(path, encoding="utf-8").read()
    if "def parse_json_loose" not in source:
        continue

    prepared = source
    prepared = re.sub(r"@@VAR:[a-z_0-9]+@@", SAMPLE, prepared)
    prepared = prepared.replace("@@QUOTE@@", "'''")
    prepared = prepared.replace("@@TOOL@@", "TEST_TOOL")
    prepared = prepared.replace("@@AGENT@@", "TEST_AGENT")
    prepared = re.sub(r"\{\{([A-Za-z_0-9]+)\}\}", r"{\1}", prepared)

    namespace = {}
    try:
        exec(compile(prepared, path, "exec"), namespace)
    except SystemExit:
        pass  # templates legitimately raise SystemExit in their sample paths
    except BaseException as error:
        failures.append((path, "exec failed: " + repr(error)[:200]))
        continue

    parser = namespace.get("parse_json_loose")
    if parser is None:
        continue  # template has no parser (e.g. pure prompts)

    for label, payload, expected in CASES:
        try:
            result = parser(payload)
        except Exception as error:
            failures.append((path, f"{label}: raised {error!r}"[:180]))
            continue
        if result != expected:
            failures.append((path, f"{label}: got {repr(result)[:140]}"))

if failures:
    print("FAILURES:")
    for path, message in failures:
        print(" -", path, "::", message)
else:
    print("ALL TEMPLATES PASS all 4 wrap cases")
