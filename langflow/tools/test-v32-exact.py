# Tests the CURRENT v3.2 parser against the EXACT platform-wrapped string
# captured by the echo run (run-echo2.json) — ground truth, not assumption.
import ast
import json
import re

s = open(__file__.replace("tools" + chr(92) + "test-v32-exact.py", "code" + chr(92) + "gate_merge_l1.template.py"), encoding="utf-8").read()

# extract the parse_json_loose function source
start = s.index("def parse_json_loose")
end = s.index("\n\nlayer1 = parse_json_loose")
fn_src = s[start:end]
ns = {"json": json, "re": re, "ast": ast}
exec(compile(fn_src, "parse_fn", "exec"), ns)
parse_json_loose = ns["parse_json_loose"]

# the EXACT text captured by the echo from the platform
run = json.load(open("C:/Users/PC/AppData/Local/Temp/run-echo2.json", encoding="utf-8"))


def find_text(n, d=0):
    if d > 10 or not isinstance(n, (dict, list)):
        return None
    if isinstance(n, dict) and isinstance(n.get("text"), str) and len(n["text"]) > 5:
        return n["text"]
    if isinstance(n, dict):
        for v in n.values():
            t = find_text(v, d + 1)
            if t:
                return t
    if isinstance(n, list):
        for v in n:
            t = find_text(v, d + 1)
            if t:
                return t
    return None


ECHO_TEXT = find_text(run)
# the echo output = str({'result': '<merge stdout>'}) — the merge stdout itself
# was str({'RECEIVED_EXACT': RAW}). For the LAYER1->MERGE test we reconstruct
# the exact wrapped form the merge received:
inner_result = ECHO_TEXT  # {'RECEIVED_EXACT': '...'} repr — same wrapping shape
print("=== captured text (exact) ===")
print(json.dumps(inner_result[:180]))

result = parse_json_loose(inner_result)
print("=== v3.2 parse result ===")
print(json.dumps(result, ensure_ascii=False)[:400] if result else "NONE -> would BLOCK (fallback)")
assert isinstance(result, dict) and "RECEIVED_EXACT" in result, "v3.2 FAILED on the exact platform string"
print("PASS: v3.2 parses the exact platform wrapping")
