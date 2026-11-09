# One-off: upgrade parse_json_loose to v3.1 — also treats a bare string
# result (from ast.literal_eval of a doubly-escaped repr) as text to unwrap.
import io
import os
import re
import glob

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../code")

V31 = (
    "def parse_json_loose(raw):\n"
    "    text = (raw or \"\").strip()\n"
    "    for _ in range(8):\n"
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
    "        if isinstance(obj, str) and obj.strip():\n"
    "            text = obj.strip()  # unwrap a string layer (repr of repr)\n"
    "            continue\n"
    "        if isinstance(obj, dict) and isinstance(obj.get(\"result\"), str):\n"
    "            text = obj[\"result\"].strip()  # unwrap the interpreter result key\n"
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
    if "unwrap a string layer" in source:
        print("skip (already v3.1):", path)
        continue
    if re.search(r"^import json$", source, re.MULTILINE) and not re.search(r"^import ast$", source, re.MULTILINE):
        source = re.sub(r"^(import json)$", "import json\\nimport ast", source, count=1, flags=re.MULTILINE)
    source = pattern.sub(V31, source, count=1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(source)
    print("upgraded to v3.1:", path)
