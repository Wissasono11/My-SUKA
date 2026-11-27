// Gagalkan build bila ada kunci privat / berkas rahasia di pohon proyek (kunci penandatangan SSO hanya boleh di ENV/secret manager).
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const SKIP = new Set(["node_modules", ".next", ".git", ".venv", ".lighthouseci", "__pycache__", ".pytest_cache"]);
const SELF = ["scripts", "check-secrets.mjs"].join(sep);
const BAD_NAME = /(\.(pem|key|p12|pfx|jks)$|^service-?account.*\.json$|^firebase-adminsdk.*\.json$)/i;
// .env* wajar ada di mesin pengembang (di-gitignore) tetapi TIDAK boleh masuk Git: hanya yang terlacak Git yang digagalkan.
const ENV_NAME = /^\.env(\..+)?$/;
const ALLOWED_ENV = /^\.env\.example$/;
let tracked = new Set();
try { tracked = new Set(execFileSync("git", ["ls-files"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).split("\n").filter(Boolean)); } catch { /* bukan repo Git (mis. build Docker): lewati */ }
// Isi: kunci privat, rahasia Google OAuth, kunci AWS, token GitHub/Slack, dan kredensial service account.
const BAD_BODY = new RegExp([
  "-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
  "GOCSPX-[A-Za-z0-9_-]{20,}",
  "AKIA[0-9A-Z]{16}",
  "gh[pousr]_[A-Za-z0-9]{36,}",
  "xox[baprs]-[A-Za-z0-9-]{10,}",
  '"type"\\s*:\\s*"service_account"',
].join("|"));
const found = [];

function walk(dir) {
  for (const name of readdirSync(dir)) {
    if (SKIP.has(name)) continue;
    const path = join(dir, name);
    const st = statSync(path);
    if (st.isDirectory()) { walk(path); continue; }
    const rel = relative(".", path);
    if (rel === SELF) continue;
    if (ENV_NAME.test(name) && !ALLOWED_ENV.test(name) && tracked.has(rel.split(sep).join("/"))) { found.push(`${rel} (berkas environment terlacak Git)`); continue; }
    if (BAD_NAME.test(name)) { found.push(`${rel} (berkas kunci/sertifikat)`); continue; }
    if (st.size < 2_000_000 && BAD_BODY.test(readFileSync(path, "latin1"))) found.push(`${rel} (memuat kunci privat atau kredensial)`);
  }
}
walk(".");
if (found.length) {
  console.error("Rahasia terdeteksi di repositori:\n - " + found.join("\n - ") + "\nHapus, rotasi kunci (SSO_KEY_ID baru), dan bersihkan riwayat Git (git filter-repo).");
  process.exit(1);
}
console.log("secrets:check OK");
