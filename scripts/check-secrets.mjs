// Gagalkan build bila ada kunci privat / berkas rahasia di pohon proyek (kunci penandatangan SSO hanya boleh di ENV/secret manager).
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const SKIP = new Set(["node_modules", ".next", ".git", ".venv", ".lighthouseci", "__pycache__", ".pytest_cache"]);
const SELF = ["scripts", "check-secrets.mjs"].join(sep);
const BAD_NAME = /\.(pem|key|p12|pfx|jks)$/i;
const BAD_BODY = /-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----/;
const found = [];

function walk(dir) {
  for (const name of readdirSync(dir)) {
    if (SKIP.has(name)) continue;
    const path = join(dir, name);
    const st = statSync(path);
    if (st.isDirectory()) { walk(path); continue; }
    const rel = relative(".", path);
    if (rel === SELF) continue;
    if (BAD_NAME.test(name)) { found.push(`${rel} (berkas kunci/sertifikat)`); continue; }
    if (st.size < 2_000_000 && BAD_BODY.test(readFileSync(path, "latin1"))) found.push(`${rel} (memuat kunci privat)`);
  }
}
walk(".");
if (found.length) {
  console.error("Rahasia terdeteksi di repositori:\n - " + found.join("\n - ") + "\nHapus, rotasi kunci (SSO_KEY_ID baru), dan bersihkan riwayat Git (git filter-repo).");
  process.exit(1);
}
console.log("secrets:check OK");
