import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const t = JSON.parse(readFileSync("design-system/tokens.json", "utf8"));
const lum = (hex: string) => { const h = hex.slice(1); const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const ratio = (a: string, b: string) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

test("setiap pasangan kontras memenuhi minimum WCAG AA", () => {
  for (const p of t.contrastPairs) assert.ok(ratio(t.color[p.fg], t.color[p.bg]) >= p.min, `${p.fg} on ${p.bg}`);
});
test("warna emas dekoratif tetap sesuai pedoman dan tidak dipakai sebagai teks", () => {
  assert.equal(t.color.secondary, "#C59B27");
  assert.ok(ratio(t.color.secondary, t.color.surface) < 3, "emas asli memang tidak aman untuk teks");
  assert.ok(!t.contrastPairs.some((p: { fg: string }) => p.fg === "secondary"));
});
test("palet inti sesuai Panduan Design System", () => {
  assert.equal(t.color.primary, "#155E38");
  assert.equal(t.color.primaryDark, "#0F4A2C");
  assert.equal(t.color.primarySoft, "#E4F1E8");
  assert.deepEqual(Object.values(t.radius).slice(0, 3), ["6px", "10px", "16px"]);
  assert.equal(t.layout.navbarHeight, "64px");
  assert.equal(t.layout.navbarHeightMobile, "56px");
});
test("ukuran teks minimum 12px", () => { assert.equal(t.type.caption, "0.75rem"); });
