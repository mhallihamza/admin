# Removes orphan module-level code left by earlier regex patchers: dead
# parser fragments (starting with "    text = (raw or" after the function's
# final return) that execute at module level and crash with NameError.
import io
import os
import re
import glob

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../code")

for path in sorted(glob.glob("*.template.py")):
    source = io.open(path, encoding="utf-8").read()
    if "def parse_json_loose" not in source:
        continue

    lines = source.split("\n")
    # find the parse function's LAST "    return None" (its true end)
    fn_start = next(i for i, l in enumerate(lines) if l.startswith("def parse_json_loose"))
    fn_end = None
    for i in range(fn_start, len(lines)):
        if lines[i] == "    return None":
            fn_end = i
    if fn_end is None:
        continue

    # scan the lines after the function for orphan indented code blocks that
    # reference undefined names (the old parser tail)
    orphan_start = None
    for i in range(fn_end + 1, len(lines)):
        line = lines[i]
        if line.strip() == "" or line.startswith("#"):
            continue
        # any indented code after the function that is not a comment/blank
        # and comes BEFORE the main logic (which starts at column 0) is orphan
        if line.startswith("    ") and orphan_start is None:
            orphan_start = i
        elif not line.startswith("    ") and orphan_start is not None:
            break

    if orphan_start is None:
        continue

    # find where the orphan block ends (first column-0 line after it)
    orphan_end = len(lines)
    for i in range(orphan_start, len(lines)):
        if lines[i].strip() != "" and not lines[i].startswith("    "):
            orphan_end = i
            break

    removed = lines[orphan_start:orphan_end]
    print(f"{path}: removing {len(removed)} orphan lines:")
    for r in removed[:4]:
        print("   ", r[:90])

    del lines[orphan_start:orphan_end]
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
