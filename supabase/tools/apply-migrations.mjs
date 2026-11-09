// Applies every .sql file from ../migrations in filename order, exactly once.
// Tracks applied files in the schema_migrations table.
import { readdirSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { makeClient } from "./db.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const migrationsDir = join(here, "..", "migrations");

const client = makeClient();
await client.connect();

await client.query(`
  create table if not exists schema_migrations (
    filename text primary key,
    applied_at timestamptz not null default now()
  );
`);

const files = readdirSync(migrationsDir)
  .filter((f) => f.endsWith(".sql"))
  .sort();

const { rows } = await client.query("select filename from schema_migrations");
const applied = new Set(rows.map((r) => r.filename));

for (const file of files) {
  if (applied.has(file)) {
    console.log(`= ${file} (already applied)`);
    continue;
  }
  const sql = readFileSync(join(migrationsDir, file), "utf8");
  try {
    await client.query("begin");
    await client.query(sql);
    await client.query("insert into schema_migrations (filename) values ($1)", [file]);
    await client.query("commit");
    console.log(`+ ${file} applied`);
  } catch (error) {
    await client.query("rollback");
    console.error(`! ${file} FAILED: ${error.message}`);
    process.exitCode = 1;
    break;
  }
}

await client.end();
