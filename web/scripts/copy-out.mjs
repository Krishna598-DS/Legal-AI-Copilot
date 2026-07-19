import { cpSync, mkdirSync, rmSync, existsSync, writeFileSync, readdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "out");
// In Docker multi-stage, copy to /frontend; locally to ../frontend
const dest = process.env.FRONTEND_OUT || join(root, "..", "frontend");

if (!existsSync(outDir)) {
  console.error("Missing web/out — run next build first");
  process.exit(1);
}

mkdirSync(dest, { recursive: true });
rmSync(join(dest, "_next"), { recursive: true, force: true });

for (const name of ["index.html", "404.html", "favicon.ico"]) {
  const from = join(outDir, name);
  if (existsSync(from)) cpSync(from, join(dest, name), { force: true });
}
cpSync(join(outDir, "_next"), join(dest, "_next"), { recursive: true, force: true });

for (const entry of readdirSync(outDir)) {
  if (entry === "_next" || entry === "index.html" || entry === "404.html") continue;
  const from = join(outDir, entry);
  const to = join(dest, entry);
  cpSync(from, to, { recursive: true, force: true });
}

writeFileSync(join(dest, ".gitkeep-built"), "Built from web/ via npm run build:static\n");
console.log("Copied static export to frontend/");
