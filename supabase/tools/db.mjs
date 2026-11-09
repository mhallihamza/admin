// Shared DB helpers. Reads the root .env.local (never committed) for SUPABASE_DB_URL.
// Server-side only: this connection string must never reach the frontend.
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

const here = dirname(fileURLToPath(import.meta.url));

export function loadRootEnv() {
  const envPath = join(here, "..", "..", ".env.local");
  const raw = readFileSync(envPath, "utf8");
  const env = {};
  for (const line of raw.split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (match && !line.trim().startsWith("#")) {
      env[match[1]] = match[2];
    }
  }
  return env;
}

export function makeClient(env = loadRootEnv()) {
  const connectionString = env.SUPABASE_DB_URL;
  if (!connectionString) {
    throw new Error("SUPABASE_DB_URL missing in .env.local");
  }
  return new pg.Client({
    connectionString,
    ssl: { rejectUnauthorized: false },
  });
}
