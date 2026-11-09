# One-off patcher: replaces parse_json_loose in all code templates with a
# robust version that also understands Python dict reprs (single quotes) —
# the format Python Interpreter results take after a Type Convert.
import io
import re
import glob
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../code")

ROBUST = (
    "def parse_json_loose(raw):\n"
    "    text = (raw or \"\").strip()\n"
    "    try:\n"
    "        text_clean = text.replace(\"'''\", '\"\\'\"\\'\"')\n"
    "    except Exception:\n"
    "        text_clean = text\n"
    "    for candidate in (text, text_clean):\n"
    "        try:\n"
    "            return json.loads(candidate)\n"
    "        except Exception:\n"
    "            pass\n"
    "        try:\n"
    "            obj = ast.literal_eval(candidate)\n"
    "        except Exception:\n"
    "            continue\n"
    "        if isinstance(obj, dict) and isinstance(obj.get(\"result\"), str):\n"
    "            try:\n"
    "                return json.loads(obj[\"result\"])\n"
    "            except Exception:\n"
    "                return obj\n"
    "        if isinstance(obj, (dict, list)):\n"
    "            return obj\n"
    "    match = re.search(r\"\\{.*\\}\", text, re.DOTALL)\n"
    "    if match:\n"
    "        try:\n"
    "            return json.loads(match.group(0))\n"
    "        except Exception:\n"
    "            try:\n"
    "                return ast.literal_eval(match.group(0))\n"
    "            except Exception:\n"
    "                return None\n"
    "    return None\n"
    "\n"
)

for path in sorted(glob.glob("*.template.py")):
    source = io.open(path, encoding="utf-8").read()
    if "def parse_json_loose" not in source:
        continue
    if "ast.literal_eval" in source:
        print("skip (already patched):", path)
        continue
    if re.search(r"^import json$", source, re.MULTILINE) and not re.search(r"^import ast$", source, re.MULTILINE):
        source = re.sub(r"^(import json)$", "import json\\nimport ast", source, count=1, flags=re.MULTILINE)
    pattern = re.compile(r"def parse_json_loose\(raw\):\n(?:[ \t]+.*\n|\n)*?")
    source = pattern.sub(ROBUST, source, count=1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(source)
    print("patched:", path)
