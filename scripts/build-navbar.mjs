import { build } from "esbuild";
import { gzipSync } from "node:zlib";
import { readFileSync } from "node:fs";

await build({ entryPoints: ["navbar/superapp-navbar.ts"], outfile: "public/assets/superapp-navbar.js", bundle: true, minify: true, format: "esm", target: "es2020", legalComments: "none" });
const size = gzipSync(readFileSync("public/assets/superapp-navbar.js")).length;
console.log(`superapp-navbar.js: ${size} B gzip`);
if (size > 6144) { console.error("Melebihi anggaran 6 KB gzip"); process.exit(1); }
