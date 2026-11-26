import { build } from "esbuild";
import { createHash } from "node:crypto";
import { gzipSync } from "node:zlib";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";

const STABLE = "public/assets/superapp-navbar.js";
await build({ entryPoints: ["navbar/superapp-navbar.ts"], outfile: STABLE, bundle: true, minify: true, format: "esm", target: "es2020", legalComments: "none" });
const bytes = readFileSync(STABLE);
const size = gzipSync(bytes).length;
console.log(`superapp-navbar.js: ${size} B gzip`);
if (size > 6144) { console.error("Melebihi anggaran 6 KB gzip"); process.exit(1); }

// Salinan immutable per versi + manifest Subresource Integrity. Micro-app yang ingin memakai `integrity` harus
// menautkan URL berversi (isinya tidak pernah berubah); URL stabil tetap ada untuk kompatibilitas kontrak v1.0.
const hash = createHash("sha384").update(bytes).digest("base64");
const version = createHash("sha256").update(bytes).digest("hex").slice(0, 12);
rmSync("public/assets/v", { recursive: true, force: true });
mkdirSync(`public/assets/v/${version}`, { recursive: true });
writeFileSync(`public/assets/v/${version}/superapp-navbar.js`, bytes);
writeFileSync("public/assets/superapp-navbar.manifest.json", JSON.stringify({ version, url: `/assets/v/${version}/superapp-navbar.js`, integrity: `sha384-${hash}` }, null, 2) + "\n");
console.log(`superapp-navbar ${version} integrity=sha384-${hash.slice(0, 12)}…`);
