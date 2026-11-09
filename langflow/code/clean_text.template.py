# Document ingestion — clean extracted text (deterministic).
# Input : @@VAR:context@@ = JSON { text, file_name }
# Output: printed JSON { clean_text, original_length, cleaned_length }

import json
import re

RAW = r@@QUOTE@@
@@VAR:context@@
@@QUOTE@@

try:
    payload = json.loads(RAW)
except Exception:
    payload = {"text": RAW, "file_name": ""}

text = payload.get("text") or ""

# Normalize line endings and unicode spaces
text = text.replace("\r\n", "\n").replace("\r", "\n")
text = text.replace("\u00a0", " ").replace("\u200f", "").replace("\u200e", "")
# Remove control characters except \n and \t
text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
# Collapse runs of spaces / tabs
text = re.sub(r"[ \t]{2,}", " ", text)
# Collapse 3+ blank lines to one blank line
text = re.sub(r"\n{3,}", "\n\n", text)
text = text.strip()

print(json.dumps({
    "clean_text": text,
    "original_length": len(payload.get("text") or ""),
    "cleaned_length": len(text),
}, ensure_ascii=True))
