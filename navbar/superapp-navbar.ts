/**
 * <superapp-navbar> — Web Component Shadow DOM (kontrak v1.0 bagian 3 dan 5).
 * Atribut: active-app, theme (light|dark), user-name, user-role. Tanpa dependensi.
 */
const APPS = [
  { id: "sukaketemu", name: "SukaKetemu" },
  { id: "campusfix", name: "CampusFix" },
  { id: "siska", name: "SISKA" },
  { id: "archive", name: "Archive" },
  { id: "paas", name: "PaaS Praktikum" },
];

const CSS = `
:host{position:fixed;inset:0 0 auto 0;z-index:9999;display:block;height:64px;
  font-family:"Plus Jakarta Sans",ui-sans-serif,system-ui,sans-serif;font-size:14px;line-height:1.4;
  --bg:#0F4A2C;--fg:#fff;--fg-muted:#DCEBE2;--panel:#fff;--panel-fg:#14261B;--hover:#E4F1E8;--ring:#fff;--ring-panel:#1C5DA8}
:host([theme="light"]){--bg:#fff;--fg:#14261B;--fg-muted:#44574B;--ring:#1C5DA8;box-shadow:0 1px 0 #DCE7E0}
*{box-sizing:border-box}
.bar{height:100%;display:flex;align-items:center;gap:12px;padding:0 16px;background:var(--bg);color:var(--fg)}
.brand{font-weight:800;font-size:16px;color:inherit;text-decoration:none;min-height:44px;display:inline-flex;align-items:center;padding:0 8px;border-radius:6px}
.current{color:var(--fg-muted);font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.spacer{flex:1}
button,a{font:inherit}
.btn{min-width:44px;min-height:44px;display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:0 10px;border:0;border-radius:10px;background:transparent;color:inherit;cursor:pointer;text-decoration:none}
.btn:hover{background:rgb(127 127 127 / .16)}
:is(.btn,.brand,.item):focus-visible{outline:3px solid var(--ring);outline-offset:2px}
.menu :is(.item,.out):focus-visible{outline-color:var(--ring-panel)}
.user{display:none;text-align:right;max-width:220px}
.user b{display:block;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.user span{font-size:12px;color:var(--fg-muted)}
.wrap{position:relative}
.menu{position:absolute;right:0;top:calc(100% + 8px);min-width:240px;max-width:calc(100vw - 24px);background:var(--panel);color:var(--panel-fg);border-radius:16px;box-shadow:0 12px 32px rgb(20 38 27 / .22);padding:8px;margin:0;list-style:none}
.menu[hidden]{display:none}
.item,.out{display:flex;align-items:center;min-height:44px;padding:0 12px;border-radius:10px;color:inherit;text-decoration:none;width:100%;background:none;border:0;cursor:pointer;text-align:left}
.item:hover,.out:hover{background:var(--hover)}
.item[aria-current="page"]{background:var(--hover);font-weight:700}
.sep{height:1px;background:#DCE7E0;margin:6px 4px}
@media (min-width:768px){.user{display:block}}
@media (max-width:767px){:host{height:56px}}
@media (prefers-reduced-motion:no-preference){.menu{animation:in .12s ease-out}@keyframes in{from{opacity:0;transform:translateY(-4px)}}}
@media (forced-colors:active){.btn,.item,.out{border:1px solid ButtonText}}
`;

class SuperappNavbar extends HTMLElement {
  static observedAttributes = ["active-app", "theme", "user-name", "user-role"];
  #root: ShadowRoot;
  #menu!: HTMLElement;
  #toggle!: HTMLButtonElement;
  #onDocClick = (e: Event) => { if (!e.composedPath().includes(this)) this.#close(false); };

  constructor() { super(); this.#root = this.attachShadow({ mode: "open" }); }

  connectedCallback() {
    if (!this.hasAttribute("theme")) this.setAttribute("theme", "dark");
    this.#render();
    document.addEventListener("click", this.#onDocClick);
  }
  disconnectedCallback() { document.removeEventListener("click", this.#onDocClick); }
  attributeChangedCallback() { if (this.isConnected && this.#root.firstChild) this.#render(); }

  #open() { this.#menu.hidden = false; this.#toggle.setAttribute("aria-expanded", "true"); (this.#menu.querySelector(".item") as HTMLElement | null)?.focus(); }
  #close(restoreFocus: boolean) { if (this.#menu.hidden) return; this.#menu.hidden = true; this.#toggle.setAttribute("aria-expanded", "false"); if (restoreFocus) this.#toggle.focus(); }

  #render() {
    const active = this.getAttribute("active-app") ?? "";
    const name = this.getAttribute("user-name") ?? "";
    const role = this.getAttribute("user-role") ?? "";
    const el = (tag: string, attrs: Record<string, string> = {}, text = "") => { const n = document.createElement(tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); if (text) n.textContent = text; return n; };

    const style = el("style"); style.textContent = CSS;
    const bar = el("div", { class: "bar", part: "bar" });
    const nav = el("nav", { "aria-label": "Navigasi superapp", style: "display:contents" });
    nav.append(el("a", { class: "brand", href: "/dashboard" }, "MySuka"));
    const activeApp = APPS.find((a) => a.id === active);
    if (activeApp) nav.append(el("span", { class: "current" }, activeApp.name));
    nav.append(el("span", { class: "spacer" }));
    bar.append(nav);

    if (name) { const u = el("div", { class: "user" }); u.append(el("b", {}, name)); if (role) u.append(el("span", {}, role)); bar.append(u); }

    const wrap = el("div", { class: "wrap" });
    this.#toggle = el("button", { class: "btn", type: "button", "aria-expanded": "false", "aria-haspopup": "true", "aria-controls": "menu", "aria-label": "Pindah aplikasi" }) as HTMLButtonElement;
    this.#toggle.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M5 5h3v3H5zm5.5 0h3v3h-3zM16 5h3v3h-3zM5 10.5h3v3H5zm5.5 0h3v3h-3zm5.5 0h3v3h-3zM5 16h3v3H5zm5.5 0h3v3h-3zm5.5 0h3v3h-3z"/></svg>';
    this.#menu = el("ul", { class: "menu", id: "menu", hidden: "" });
    for (const app of APPS) {
      const li = el("li");
      // Lewat portal agar silent login (kontrak 2.3) berjalan; tidak ada form login manual.
      const a = el("a", { class: "item", href: `/api/sso/launch?app=${app.id}` }, app.name);
      if (app.id === active) a.setAttribute("aria-current", "page");
      li.append(a); this.#menu.append(li);
    }
    this.#menu.append(el("li", { class: "sep", role: "separator" }));
    const outLi = el("li"); const out = el("button", { class: "out", type: "button" }, "Keluar"); outLi.append(out); this.#menu.append(outLi);
    wrap.append(this.#toggle, this.#menu); bar.append(wrap);

    this.#toggle.addEventListener("click", () => (this.#menu.hidden ? this.#open() : this.#close(true)));
    this.#menu.addEventListener("keydown", (e) => {
      const items = [...this.#menu.querySelectorAll<HTMLElement>(".item,.out")];
      const i = items.indexOf(this.#root.activeElement as HTMLElement);
      if (e.key === "Escape") { e.preventDefault(); this.#close(true); }
      else if (e.key === "ArrowDown") { e.preventDefault(); items[(i + 1) % items.length]?.focus(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); items[(i - 1 + items.length) % items.length]?.focus(); }
    });
    out.addEventListener("click", () => {
      // Kontrak 5: broadcast, biarkan micro-app membersihkan sesi lokal (gunakan fetch keepalive), lalu keluar terpusat.
      window.dispatchEvent(new CustomEvent("superapp:logout"));
      const go = () => window.location.assign("/login");
      try { fetch("/api/sso/logout", { method: "POST", credentials: "same-origin", keepalive: true }).then(go, go); } catch { go(); }
    });

    this.#root.replaceChildren(style, bar);
  }
}

if (!customElements.get("superapp-navbar")) customElements.define("superapp-navbar", SuperappNavbar);
