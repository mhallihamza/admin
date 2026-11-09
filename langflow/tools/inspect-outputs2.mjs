// Extracts every text field from the last run response with sources.
import { readFileSync } from "node:fs";

const run = JSON.parse(readFileSync("C:/Users/PC/AppData/Local/Temp/run-c2.json", "utf8"));
const s = JSON.stringify(run);

const re = new RegExp('"text": ?("(?:[^"\\\\]|\\\\.)*")', "g");
let m;
let i = 0;
while ((m = re.exec(s)) !== null && i < 12) {
  const val = JSON.parse(m[1]);
  if (val.length > 3) {
    // find the nearest component source before this match
    const before = s.slice(Math.max(0, m.index - 600), m.index);
    const srcMatch = before.match(/"display_name":"([^"]+)"/g);
    const src = srcMatch ? srcMatch[srcMatch.length - 1] : "?";
    console.log("--- text", i, "(near", src, ") ---");
    console.log(val.slice(0, 350));
    i += 1;
  }
}
if (i === 0) console.log("no texts; response head:", s.slice(0, 400));
