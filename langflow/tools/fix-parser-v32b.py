# Corrects the unwrap ORDER in parse_json_loose: the {'result': "<json>"}
# layer must be unwrapped BEFORE the plain dict/list return.
import io
import os
import re
import glob

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../code")

V32B = (
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
    "                    obj = None\n"
    "        if isinstance(obj, dict) and isinstance(obj.get(\"result\"), str):\n"
    "            text = obj[\"result\"].strip()  # unwrap the interpreter result key\n"
    "            continue\n"
    "        if isinstance(obj, str) and obj.strip():\n"
    "            text = obj.strip()  # unwrap a string layer (repr of repr)\n"
    "            continue\n"
    "        if isinstance(obj, (dict, list)):\n"
    "            return obj\n"
    "        BS = chr(92)\n"
    "        unescaped = text.replace(BS + BS, chr(1) + \"B\" + chr(1))\n"
    "        unescaped = unescaped.replace(BS + \"'\", \"'\")\n"
    "        unescaped = unescaped.replace(BS + '\"', '\"')\n"
    "        unescaped = unescaped.replace(BS + \"n\", chr(10))\n"
    "        unescaped = unescaped.replace(BS + \"r\", chr(13))\n"
    "        unescaped = unescaped.replace(chr(1) + \"B\" + chr(1), BS)\n"
    "        if unescaped != text:\n"
    "            text = unescaped.strip()\n"
    "            continue\n"
    "        return None\n"
    "    return None\n"
    "\n"
)

pattern = re.compile(r"def parse_json_loose\(raw\):[\s\S]*?\n    return None\n")

for path in sorted(glob.glob("*.template.py")):
    source = io.open(path, encoding="utf-8").read()
    if "def parse_json_loose" not in source:
        continue
    if "unwrap the interpreter result key" in source and "BS = chr(92)" in source:
        print("skip (already v32b):", path)
        continue
    if re.search(r"^import json$", source, re.MULTILINE) and not re.search(r"^import ast$", source, re.MULTILINE):
        source = re.sub(r"^(import json)$", "import json\\nimport ast", source, count=1, flags=re.MULTILINE)
    source = pattern.sub(V32B, source, count=1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(source)
    print("fixed:", path)
