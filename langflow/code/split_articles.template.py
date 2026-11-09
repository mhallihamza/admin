# Document ingestion — split by legal article / section (deterministic).
# Inputs: @@VAR:metadata_json@@ = metadata JSON from the Doc Metadata step
#                { document_id, title, language, effective_date, version, approval_status }
#         @@VAR:text_json@@ = JSON from the text-security step { text_safe, flags, cleaned_text }
# Output: printed JSON { chunks: [ {text, article_number, section_title, ...metadata} ], meta, total }

import json
import ast
import re

META_RAW = r@@QUOTE@@
@@VAR:metadata_json@@
@@QUOTE@@

TEXT_RAW = r@@QUOTE@@
@@VAR:text_json@@
@@QUOTE@@

def parse_json_loose(raw):
    text = (raw or "").strip()
    for _ in range(8):
        if not text:
            return None
        obj = None
        try:
            obj = json.loads(text)
        except Exception:
            pass
        if obj is None:
            try:
                obj = ast.literal_eval(text)
            except Exception:
                pass
        if obj is None:
            match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
            if not match:
                return None
            fragment = match.group(0)
            try:
                obj = json.loads(fragment)
            except Exception:
                try:
                    obj = ast.literal_eval(fragment)
                except Exception:
                    obj = None
        if isinstance(obj, dict) and isinstance(obj.get("result"), str):
            text = obj["result"].strip()  # unwrap the interpreter result key
            continue
        if isinstance(obj, str) and obj.strip():
            text = obj.strip()  # unwrap a string layer (repr of repr)
            continue
        if isinstance(obj, (dict, list)):
            return obj
        BS = chr(92)
        unescaped = text.replace(BS + BS, chr(1) + "B" + chr(1))
        unescaped = unescaped.replace(BS + "'", "'")
        unescaped = unescaped.replace(BS + '"', '"')
        unescaped = unescaped.replace(BS + "n", chr(10))
        unescaped = unescaped.replace(BS + "r", chr(13))
        unescaped = unescaped.replace(chr(1) + "B" + chr(1), BS)
        if unescaped != text:
            text = unescaped.strip()
            continue
        return None
    return None






meta = parse_json_loose(META_RAW) or {}
body = (parse_json_loose(TEXT_RAW) or {}).get("cleaned_text", "")

# Article headings: FR "Article 12", AR "المادة 12", or "Section I / القسم الأول"
article_pattern = re.compile(
    r"^(?:(?:Article|Art\.|المادة)\s*(\d+[\w-]*)|(Section|Chapitre|Titre|القسم|الباب)\s+([IVXLC\dأ-ي]+))\s*[:.\-—]?\s*(.*)$",
    re.MULTILINE,
)

matches = list(article_pattern.finditer(body))
chunks = []
if not matches:
    chunks.append({"text": body, "article_number": None, "section_title": None})
else:
    first_start = matches[0].start()
    if first_start > 0:
        preamble = body[:first_start].strip()
        if preamble:
            chunks.append({"text": preamble, "article_number": None, "section_title": "PREAMBLE"})
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        heading = match.group(0).strip()
        content = body[match.end():end].strip()
        chunks.append({
            "text": (heading + "\n" + content).strip(),
            "article_number": match.group(1),
            "section_title": (match.group(2) or "") + " " + (match.group(3) or "") if match.group(2) else heading,
        })

for chunk in chunks:
    chunk["document_id"] = meta.get("document_id")
    chunk["title"] = meta.get("title")
    chunk["language"] = meta.get("language", "fr")
    chunk["effective_date"] = meta.get("effective_date")
    chunk["version"] = meta.get("version", 1)
    chunk["approval_status"] = "PENDING_REVIEW"  # ingestion NEVER publishes

print(json.dumps({"chunks": chunks, "meta": meta, "total": len(chunks)}, ensure_ascii=True))
