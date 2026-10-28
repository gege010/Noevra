/* OpenRouter's documented PKCE flow. API keys never enter browser storage. */
(function (root) {
  function base64url(bytes) {
    return btoa(String.fromCharCode(...new Uint8Array(bytes)))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  }
  async function createPKCE() {
    const verifier = base64url(crypto.getRandomValues(new Uint8Array(48)));
    const state = base64url(crypto.getRandomValues(new Uint8Array(32)));
    const challenge = base64url(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)),
    );
    return { verifier, state, challenge, createdAt: Date.now() };
  }
  function validatePending(pending, state, now = Date.now()) {
    return Boolean(
      pending &&
        typeof pending.verifier === "string" &&
        /^[A-Za-z0-9_-]{64}$/.test(pending.verifier) &&
        typeof state === "string" &&
        state.length >= 32 &&
        pending.state === state &&
        Number.isFinite(pending.createdAt) &&
        now >= pending.createdAt &&
        now - pending.createdAt < 10 * 60 * 1000,
    );
  }
  function authorizationUrl(callback, challenge, state) {
    const url = new URL("https://openrouter.ai/auth");
    url.search = new URLSearchParams({
      callback_url: callback,
      code_challenge: challenge,
      code_challenge_method: "S256",
      state,
      key_label: "Noevra",
    });
    return url.href;
  }
  const api = { createPKCE, validatePending, authorizationUrl };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ScholarOAuth = api;
})(typeof window === "undefined" ? {} : window);
