import { test } from "node:test";
import assert from "node:assert/strict";
import { SignJWT, generateKeyPair, exportJWK, createLocalJWKSet } from "jose";
import { verifySessionToken, AUDIENCE } from "../src/lib/sso/verify";

const ISS = "https://mysuka.test";
const user = { id: "usr_x", nim_nip: "1", email: "a@student.uin-suka.ac.id", name: "A", primary_role: "MAHASISWA", faculty: "", department: "" };

async function setup() {
  const { privateKey, publicKey } = await generateKeyPair("RS256");
  const jwk = { ...(await exportJWK(publicKey)), kid: "k1", alg: "RS256", use: "sig" };
  const keys = createLocalJWKSet({ keys: [jwk] });
  const sign = (over: { iss?: string; aud?: string; exp?: string | number; jti?: string | null; alg?: "RS256" } = {}) => {
    const b = new SignJWT({ user }).setProtectedHeader({ alg: "RS256", kid: "k1" }).setIssuer(over.iss ?? ISS).setAudience(over.aud ?? AUDIENCE).setSubject("mhs_1").setIssuedAt().setExpirationTime(over.exp ?? "60s");
    if (over.jti !== null) b.setJti(over.jti ?? "abc");
    return b.sign(privateKey);
  };
  return { keys, sign, privateKey };
}

test("token valid dari portal-api diterima Next lewat JWKS", async () => {
  const { keys, sign } = await setup();
  assert.equal((await verifySessionToken(await sign(), keys, ISS))?.email, "a@student.uin-suka.ac.id");
});
test("issuer, audience, kedaluwarsa, tanpa jti, dan tanda tangan salah ditolak", async () => {
  const { keys, sign } = await setup();
  assert.equal(await verifySessionToken(await sign({ iss: "https://lain" }), keys, ISS), null);
  assert.equal(await verifySessionToken(await sign({ aud: "lain" }), keys, ISS), null);
  assert.equal(await verifySessionToken(await sign({ exp: Math.floor(Date.now() / 1000) - 10 }), keys, ISS), null);
  assert.equal(await verifySessionToken(await sign({ jti: null }), keys, ISS), null);
  const other = await setup();
  assert.equal(await verifySessionToken(await other.sign(), keys, ISS), null);
  assert.equal(await verifySessionToken("bukan.token.sama", keys, ISS), null);
});
test("alg none/HS256 ditolak (hanya RS256)", async () => {
  const { keys } = await setup();
  const hs = await new SignJWT({ user }).setProtectedHeader({ alg: "HS256", kid: "k1" }).setIssuer(ISS).setAudience(AUDIENCE).setSubject("s").setIssuedAt().setExpirationTime("60s").setJti("j").sign(new TextEncoder().encode("secret-secret-secret-secret-secret!!"));
  assert.equal(await verifySessionToken(hs, keys, ISS), null);
});
