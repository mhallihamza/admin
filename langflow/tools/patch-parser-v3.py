# One-off: upgrade parse_json_loose to v3 — iterative unwrapping of
# {'result': "<json>"} repr layers (any number of levels, any quote style).
import io
import os
import re
import glob

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../code")

V3 = (
    "def parse_json_loose(raw):\n"
    "    text = (raw or \"\").strip()\n"
    "    for _ in range(6):\n"
    "        if not text:\n"
    "            return None\n"
    "        obj = None\n"
    "        try:\n"
    "            obj = json.loads(text)\n"
    "        except Exception:\n"
    "            pass\n"
    "        if obj is None:\n"
    "            try:\n"
    "                obj = ast.literal_eval(text)\n"
    "            except Exception:\n"
    "                pass\n"
    "        if obj is None:\n"
    "            match = re.search(r\"\\{.*\\}|\\[.*\\]\", text, re.DOTALL)\n"
    "            if not match:\n"
    "                return None\n"
    "            fragment = match.group(0)\n"
    "            try:\n"
    "                obj = json.loads(fragment)\n"
    "            except Exception:\n"
    "                try:\n"
    "                    obj = ast.literal_eval(fragment)\n"
    "                except Exception:\n"
    "                    return None\n"
    "        if isinstance(obj, dict) and isinstance(obj.get(\"result\"), str):\n"
    "            text = obj[\"result\"].strip()  # unwrap one repr layer, try again\n"
    "            continue\n"
    "        if isinstance(obj, (dict, list)):\n"
    "            return obj\n"
    "        return None\n"
    "    return None\n"
    "\n"
)

pattern = re.compile(r"def parse_json_loose\(raw\):[\s\S]*?\n    return None\n")

for path in sorted(glob.glob("*.template.py")):
    source = io.open(path, encoding="utf-8").read()
    if "def parse_json_loose" not in source:
        continue
    if "for _ in range(6):" in source:
        print("skip (already v3):", path)
        continue
    if re.search(r"^import json$", source, re.MULTILINE) and not re.search(r"^import ast$", source, re.MULTILINE):
        source = re.sub(r"^(import json)$", "import json\\nimport ast", source, count=1, flags=re.MULTILINE)
    source = pattern.sub(V3, source, count=1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(source)
    print("upgraded to v3:", path)
