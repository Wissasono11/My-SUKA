// Membangun artefak dari tokens.json. `--check` gagal bila artefak tidak sinkron atau kontras tidak lolos.
import { readFile, writeFile, mkdir, copyFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));
const check = process.argv.includes("--check");
const t = JSON.parse(await readFile(path.join(root, "tokens.json"), "utf8"));

const kebab = (s) => s.replace(/([A-Z])/g, "-$1").toLowerCase();

/* ---- kontras (WCAG 2.x) ---- */
const lum = (hex) => {
  const h = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
export const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const failures = t.contrastPairs.filter((p) => contrast(t.color[p.fg], t.color[p.bg]) < p.min);
if (failures.length) {
  for (const p of failures) console.error(`KONTRAS GAGAL ${p.fg} on ${p.bg}: ${contrast(t.color[p.fg], t.color[p.bg]).toFixed(2)} < ${p.min}`);
  process.exit(1);
}

/* ---- CSS ---- */
const lines = [];
const add = (k, v) => lines.push(`  --ms-${k}: ${v};`);
for (const [k, v] of Object.entries(t.color)) add(`color-${kebab(k)}`, v);
add("font", t.font.family);
for (const [k, v] of Object.entries(t.type)) add(`text-${kebab(k)}`, v);
for (const [k, v] of Object.entries(t.radius)) add(`radius-${k}`, v);
for (const [k, v] of Object.entries(t.space)) add(`space-${k}`, v);
for (const [k, v] of Object.entries(t.elevation)) add(`elevation-${k}`, v);
for (const [k, v] of Object.entries(t.motion)) add(`motion-${kebab(k)}`, v);
for (const [k, v] of Object.entries(t.z)) add(`z-${k}`, String(v));
for (const [k, v] of Object.entries(t.layout)) add(kebab(k), v);
const aliasLines = Object.entries(t.legacyAliases).map(([name, ref]) => {
  const [group, key] = ref.split(".");
  const canon = group === "color" ? `color-${kebab(key)}` : group === "font" ? "font" : `${group}-${key}`;
  return `  ${name}: var(--ms-${canon});`;
});
const css = `/* Dihasilkan dari design-system/tokens.json v${t.version}. Jangan edit manual. */
:root {
${lines.join("\n")}
  /* Alias kompatibilitas v1 (SISKA dan layanan lama). Hapus setelah semua layanan memakai --ms-*. */
${aliasLines.join("\n")}
  color-scheme: light;
}
@media (prefers-reduced-motion: reduce) {
  :root { --ms-motion-fast: 0ms; --ms-motion-base: 0ms; --ms-motion-slow: 0ms; }
}
@media (forced-colors: active) {
  :focus-visible { outline: 3px solid Highlight; }
}
`;

/* ---- TypeScript ---- */
const ts = `// Dihasilkan dari design-system/tokens.json. Jangan edit manual.
export const tokens = ${JSON.stringify({ version: t.version, color: t.color, radius: t.radius, space: t.space, layout: t.layout }, null, 2)} as const;
`;

/* ---- Flutter / Dart ---- */
const dartColor = (hex) => `Color(0xFF${hex.replace("#", "").toUpperCase()})`;
const dart = `// Dihasilkan dari design-system/tokens.json v${t.version}. Jangan edit manual.
import 'package:flutter/material.dart';

class MySukaColors {
${Object.entries(t.color).map(([k, v]) => `  static const ${k} = ${dartColor(v)};`).join("\n")}
}

ThemeData mySukaTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: MySukaColors.primary).copyWith(
    primary: MySukaColors.primary,
    onPrimary: MySukaColors.textOnPrimary,
    secondary: MySukaColors.secondary,
    surface: MySukaColors.surface,
    onSurface: MySukaColors.text,
    error: MySukaColors.danger,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: MySukaColors.background,
    fontFamily: 'Plus Jakarta Sans',
  );
}
`;

const outputs = { "dist/tokens.css": css, "dist/tokens.ts": ts, "dist/tokens.dart": dart };
await mkdir(path.join(root, "dist"), { recursive: true });
let stale = false;
for (const [rel, body] of Object.entries(outputs)) {
  const file = path.join(root, rel);
  const current = await readFile(file, "utf8").catch(() => null);
  if (check) { if (current !== body) { console.error(`Tidak sinkron: design-system/${rel}. Jalankan npm run assets.`); stale = true; } }
  else await writeFile(file, body);
}
if (check) process.exit(stale ? 1 : 0);

const pub = path.join(root, "..", "public", "assets", "design", "v1");
await mkdir(pub, { recursive: true });
await copyFile(path.join(root, "dist", "tokens.css"), path.join(pub, "tokens.css"));
console.log(`Token v${t.version} dibangun (${t.contrastPairs.length} pasangan kontras lolos).`);
