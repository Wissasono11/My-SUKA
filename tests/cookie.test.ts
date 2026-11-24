import { test } from "node:test";
import assert from "node:assert/strict";
import { sessionCookieName } from "../src/lib/sso/cookie";

test("nama cookie mengikuti ENV, bukan NODE_ENV", () => {
  assert.equal(sessionCookieName({ ENV: "production", NODE_ENV: "development" }), "__Host-mysuka_session");
  assert.equal(sessionCookieName({ ENV: "development", NODE_ENV: "production" }), "mysuka_session");
  assert.equal(sessionCookieName({}), "mysuka_session");
});
test("SESSION_COOKIE_NAME menimpa default", () => {
  assert.equal(sessionCookieName({ ENV: "production", SESSION_COOKIE_NAME: "x_session" }), "x_session");
});
