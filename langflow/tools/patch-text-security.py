# One-off: text_security_check receives a wrapped REPL result — give it the
# robust parser (same as the other templates).
import io
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../code")

path = "text_security_check.template.py"
source = io.open(path, encoding="utf-8").read()

robust = io.open("gate_merge_l1.template.py", encoding="utf-8").read()
start = robust.index("def parse_json_loose(raw):")
end = robust.index("\n\nMETA_RAW") if "\n\nMETA_RAW" in robust else None
helper = robust[start: robust.index("\nRAW = r")]

if "def parse_json_loose" not in source:
    # insert helper before its use, plus the ast import
    source = source.replace("import json\nimport re", "import json\nimport re\nimport ast", 1)
    old_block = '''try:
    payload = json.loads(RAW)
except Exception:
    payload = {"clean_text": RAW}'''
    assert old_block in source, "direct parse block not found"
    source = source.replace(old_block, "payload = parse_json_loose(RAW) or {\"clean_text\": RAW}")
    marker = "RAW = r@@QUOTE@@"
    source = source.replace(marker, helper + "\nRAW = r@@QUOTE@@", 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(source)
    print("patched:", path)
else:
    print("already has parser:", path)
