import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";

function mount(attrs = 'active-app="sukaketemu" theme="light" user-name="Radinka Rafie" user-role="MAHASISWA"') {
  const dom = new JSDOM(`<!doctype html><body><superapp-navbar ${attrs}></superapp-navbar></body>`, { runScripts: "outside-only", url: "https://mysuka.portal.ac.id/sukaketemu/" });
  dom.window.eval(readFileSync("public/assets/superapp-navbar.js", "utf8").replace(/^export\s*\{[^}]*\};?/m, ""));
  const host = dom.window.document.querySelector("superapp-navbar") as HTMLElement;
  return { dom, host, root: host.shadowRoot! };
}

test("navbar merender merek, nama layanan aktif, dan identitas pengguna", () => {
  const { root } = mount();
  assert.equal(root.querySelector(".brand")?.textContent, "MySuka");
  assert.equal(root.querySelector(".current")?.textContent, "SukaKetemu");
  assert.match(root.querySelector(".user")!.textContent!, /Radinka Rafie/);
});
test("menu memuat 5 layanan lewat launcher SSO dan menandai aplikasi aktif", () => {
  const { root } = mount();
  const items = [...root.querySelectorAll<HTMLAnchorElement>(".item")];
  assert.equal(items.length, 5);
  assert.ok(items.every((a) => a.getAttribute("href")!.startsWith("/api/sso/launch?app=")));
  assert.equal(root.querySelector('.item[aria-current="page"]')?.textContent, "SukaKetemu");
});
test("tombol 9 titik: aria-expanded berubah dan Escape menutup menu", () => {
  const { dom, root } = mount();
  const toggle = root.querySelector("button.btn") as HTMLButtonElement;
  const menu = root.querySelector(".menu") as HTMLElement;
  assert.equal(toggle.getAttribute("aria-expanded"), "false"); assert.equal(menu.hidden, true);
  toggle.click();
  assert.equal(toggle.getAttribute("aria-expanded"), "true"); assert.equal(menu.hidden, false);
  menu.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.equal(menu.hidden, true); assert.equal(toggle.getAttribute("aria-expanded"), "false");
});
test("Keluar memancarkan event superapp:logout sesuai kontrak", () => {
  const { dom, root } = mount();
  let fired = false;
  dom.window.addEventListener("superapp:logout", () => { fired = true; });
  try { (root.querySelector(".out") as HTMLButtonElement).click(); } catch { /* jsdom: navigasi tidak diimplementasikan */ }
  assert.equal(fired, true);
});
test("anggaran ukuran: kurang dari 6 KB gzip", async () => {
  const { gzipSync } = await import("node:zlib");
  assert.ok(gzipSync(readFileSync("public/assets/superapp-navbar.js")).length < 6144);
});
