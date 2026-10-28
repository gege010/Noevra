const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  createPKCE,
  validatePending,
  authorizationUrl,
} = require("../src/static/oauth.js");

test("PKCE uses independent random states and a verifiable S256 challenge", async () => {
  const first = await createPKCE(),
    second = await createPKCE();
  assert.equal(first.verifier.length, 64);
  assert.notEqual(first.state, second.state);
  const hash = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(first.verifier),
  );
  assert.equal(first.challenge, Buffer.from(hash).toString("base64url"));
  assert.ok(validatePending(first, first.state));
});
test("callback rejects mismatched, expired, missing, and future state", async () => {
  const pending = await createPKCE();
  assert.equal(validatePending(pending, "wrong"), false);
  assert.equal(
    validatePending(pending, pending.state, pending.createdAt + 600001),
    false,
  );
  assert.equal(
    validatePending(pending, pending.state, pending.createdAt - 1),
    false,
  );
  assert.equal(validatePending(null, pending.state), false);
});
test("authorization URL contains a challenge, never its verifier or key", async () => {
  const pending = await createPKCE();
  const url = new URL(
    authorizationUrl(
      "http://localhost:8013/",
      pending.challenge,
      pending.state,
    ),
  );
  assert.equal(url.origin, "https://openrouter.ai");
  assert.equal(url.searchParams.get("code_challenge_method"), "S256");
  assert.equal(url.searchParams.get("state"), pending.state);
  assert.ok(!url.href.includes(pending.verifier));
  assert.equal(url.searchParams.get("callback_url"), "http://localhost:8013/");
});
