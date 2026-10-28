/* Account connections and live catalogs. Secrets exist only in this tab. */
(function (root) {
  const catalogs = {},
    versions = {};
  let editing = null,
    capabilities = {};
  const connection = (provider) => state.connections[provider] || {};
  function status(provider) {
    const saved = connection(provider);
    if (saved.expires_at && saved.expires_at * 1000 <= Date.now())
      return "Session expired. Reconnect.";
    if (catalogs[provider]?.loading) return "Checking available models…";
    if (catalogs[provider]?.error) return catalogs[provider].error;
    if (catalogs[provider]?.models)
      return `${catalogs[provider].models.length} available models · checked this session`;
    return saved.key
      ? "Connected · catalog not checked"
      : state.providers[provider]?.configured_in_backend
        ? "Server key configured · catalog not checked"
        : "Not connected";
  }
  function renderConnections() {
    $("providerConnections").innerHTML = Object.entries(state.providers)
      .map(
        ([id, info]) =>
          `<button class="provider-row" data-connect-provider="${esc(id)}"><span class="account-avatar">${esc(info.name.slice(0, 1))}</span><span><strong>${esc(info.name)}</strong><small>${esc(status(id))}</small><small class="auth-method">${info.oauth?.supported ? "OAuth + API key" : ["ollama", "custom"].includes(id) ? "Your endpoint" : "API key"}</small></span><span aria-hidden="true">→</span></button>`,
      )
      .join("");
  }
  function renderModels() {
    const catalog = catalogs[state.provider],
      query = $("modelSearch").value.trim().toLowerCase();
    const selected = connection(state.provider).model || state.model;
    const all = catalog?.models || [];
    const rows = all.filter((m) =>
      `${m.id} ${m.name}`.toLowerCase().includes(query),
    );
    $("modelSelect").innerHTML = rows.length
      ? rows
          .map(
            (m) =>
              `<option value="${esc(m.id)}">${esc(m.name)}${m.name !== m.id ? " · " + esc(m.id) : ""}</option>`,
          )
          .join("")
      : `<option value="">${catalog?.loading ? "Loading models…" : query ? "No matching models" : "No models available"}</option>`;
    $("modelSelect").disabled = !rows.length;
    $("modelSearch").disabled = !all.length;
    $("modelSelect").value = rows.some((m) => m.id === selected)
      ? selected
      : rows[0]?.id || "";
    $("catalogStatus").textContent = status(state.provider);
    $("refreshModelsBtn").disabled = Boolean(catalog?.loading);
    // Filtering is a view operation; it must not silently change the chosen model.
    if (!query && !catalog?.loading) selectModel();
    root.ScholarControls?.sync();
  }
  function selectModel(commitSelection = false) {
    if (!state.provider) return;
    const saved = (state.connections[state.provider] ||= {});
    saved.custom = $("customModel").value.trim();
    if ($("modelSelect").value && (commitSelection === true || !saved.model))
      saved.model = $("modelSelect").value;
    state.model =
      saved.custom ||
      (catalogs[state.provider]?.loading ? "" : saved.model) ||
      "";
    $("composerModel").textContent = state.model
      ? shortModel(state.model)
      : "Choose a model";
  }
  function selectProvider(provider) {
    if (!state.providers[provider]) return;
    state.provider = provider;
    $("providerSelect").value = provider;
    $("modelSearch").value = "";
    $("customModel").value = connection(provider).custom || "";
    state.model = connection(provider).model || "";
    renderModels();
    renderConnections();
    if (
      !catalogs[provider] &&
      (connection(provider).key ||
        state.providers[provider].configured_in_backend ||
        ["ollama", "custom"].includes(provider))
    )
      discover(provider);
  }
  async function discover(provider) {
    const version = (versions[provider] = (versions[provider] || 0) + 1);
    catalogs[provider] = { loading: true };
    if (provider === state.provider) {
      state.model = "";
      renderModels();
    }
    renderConnections();
    const saved = connection(provider);
    try {
      if (saved.expires_at && saved.expires_at * 1000 <= Date.now())
        throw new Error("Session expired. Reconnect this account.");
      const data = await request(`/api/v1/providers/${provider}/models`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: saved.key || null,
          auth_type: saved.auth === "oauth" ? "oauth" : "api_key",
          base_url: saved.endpoint || null,
        }),
      });
      if (version !== versions[provider]) return;
      catalogs[provider] = { models: data.models, checkedAt: Date.now() };
      if (!data.models.some((m) => m.id === saved.model)) {
        (state.connections[provider] ||= {}).model =
          data.models.find(
            (m) => m.id === state.providers[provider].default_model,
          )?.id ||
          data.models[0]?.id ||
          "";
      }
    } catch (error) {
      if (version !== versions[provider]) return;
      catalogs[provider] = {
        error:
          error.message ||
          "Cannot retrieve models. Check the connection and retry.",
      };
      (state.connections[provider] ||= {}).model = "";
    }
    if (provider === state.provider) renderModels();
    renderConnections();
    if (editing === provider) {
      $("connectionStatus").textContent = status(provider);
      $("useProviderBtn").disabled = !catalogs[provider]?.models?.length;
    }
  }
  function openConnection(provider) {
    editing = provider;
    for (const id of ["modelDialog", "settingsDialog"]) $(id).close();
    const info = state.providers[provider],
      saved = connection(provider);
    $("connectionTitle").textContent = info.name;
    $("useProviderBtn").disabled = !catalogs[provider]?.models?.length;
    $("apiKeyInput").value = saved.auth === "oauth" ? "" : saved.key || "";
    $("apiKeyInput").type = "password";
    $("baseUrlInput").value =
      saved.endpoint ||
      (provider === "ollama"
        ? "http://localhost:11434/v1"
        : "http://localhost:1234/v1");
    $("endpointField").hidden = !["ollama", "custom"].includes(provider);
    $("connectionStatus").textContent = status(provider);
    $("oauthConnection").hidden = !info.oauth?.supported;
    $("oauthStatus").textContent = info.oauth?.note || "";
    if (provider === "anthropic")
      $("connectionStatus").textContent += ". " + info.oauth.note;
    $("providerAuthDocs").href = info.oauth?.docs || "#";
    const local =
      location.protocol === "http:" && location.hostname === "127.0.0.1";
    $("connectProviderBtn").disabled =
      provider === "openai"
        ? !local
        : provider === "gemini"
          ? !capabilities.gemini?.configured
          : false;
    $("connectProviderBtn").textContent =
      provider === "openai" && !local
        ? "ChatGPT sign-in needs local 127.0.0.1"
        : provider === "gemini" && !capabilities.gemini?.configured
          ? "Google OAuth requires server setup"
          : `Continue with ${provider === "openai" ? "ChatGPT" : info.name}`;
    $("disconnectProviderBtn").hidden = !saved.key;
    openDialog("connectionDialog");
  }
  async function connectOAuth() {
    const provider = editing;
    if (state.running) {
      notify(
        "Complete the current research before leaving this page to sign in.",
      );
      return;
    }
    try {
      const pending = await root.ScholarOAuth.createPKCE();
      pending.provider = provider;
      pending.nonce = crypto.randomUUID();
      pending.redirect_uri = location.origin + location.pathname;
      pending.draft = $("queryInput").value;
      let target;
      if (provider === "openrouter")
        target = root.ScholarOAuth.authorizationUrl(
          pending.redirect_uri,
          pending.challenge,
          pending.state,
        );
      else {
        const url = new URL(
          provider === "openai"
            ? "https://auth.openai.com/api/accounts/authorize"
            : "https://accounts.google.com/o/oauth2/v2/auth",
        );
        const params = {
          response_type: "code",
          client_id:
            provider === "openai"
              ? localStorage.getItem("noevra_openai_client_id") ||
                capabilities[provider].client_id
              : capabilities[provider].client_id,
          redirect_uri: pending.redirect_uri,
          state: pending.state,
          code_challenge: pending.challenge,
          code_challenge_method: "S256",
        };
        if (provider === "openai") {
          let host = localStorage.getItem("noevra_host_id");
          if (!host) {
            host = crypto.randomUUID();
            localStorage.setItem("noevra_host_id", host);
          }
          Object.assign(params, {
            nonce: pending.nonce,
            scope:
              "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct",
            resource: "https://api.openai.com/v1",
            agent_name_hint: "Noevra",
            ext_agent_host_id: host,
          });
        } else
          Object.assign(params, {
            scope: "https://www.googleapis.com/auth/cloud-platform",
            prompt: "consent",
            access_type: "online",
          });
        pending.client_id = params.client_id;
        url.search = new URLSearchParams(params);
        target = url.href;
      }
      sessionStorage.setItem("scholar_oauth_pending", JSON.stringify(pending));
      location.assign(target);
    } catch (error) {
      notify(error.message || "Cannot begin authorization.", true);
    }
  }
  async function handleCallback() {
    const params = new URLSearchParams(location.search);
    if (!params.has("code") && !params.has("error")) return;
    let pending;
    try {
      pending = JSON.parse(sessionStorage.getItem("scholar_oauth_pending"));
    } catch {}
    sessionStorage.removeItem("scholar_oauth_pending");
    const code = params.get("code"),
      returnedState = params.get("state"),
      clientId = params.get("client_id"),
      error = params.get("error");
    for (const key of [
      "code",
      "state",
      "client_id",
      "error",
      "error_description",
    ])
      params.delete(key);
    history.replaceState(
      null,
      "",
      location.pathname + (params.size ? "?" + params : "") + location.hash,
    );
    if (pending?.draft) $("queryInput").value = pending.draft;
    if (error || !root.ScholarOAuth.validatePending(pending, returnedState)) {
      notify(
        "Sign-in was cancelled, expired or did not match this tab. Reconnect from Settings.",
        true,
      );
      return;
    }
    const provider = pending.provider || "openrouter";
    if (!["openai", "gemini", "openrouter"].includes(provider)) return;
    try {
      if (
        provider === "openai" &&
        pending.client_id !== "dynamic_agent_client" &&
        clientId &&
        pending.client_id !== clientId
      )
        throw new Error("The returned client ID did not match this sign-in.");
      const issuedId =
        clientId ||
        (pending.client_id !== "dynamic_agent_client" ? pending.client_id : "");
      const body = { code, code_verifier: pending.verifier };
      if (provider !== "openrouter")
        Object.assign(body, {
          redirect_uri: pending.redirect_uri,
          nonce: pending.nonce,
          client_id: issuedId || "",
        });
      const result = await request(
        provider === "openrouter"
          ? "/api/v1/auth/openrouter/exchange"
          : `/api/v1/auth/oauth/${provider}/exchange`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (provider === "openai" && result.client_id)
        localStorage.setItem("noevra_openai_client_id", result.client_id);
      state.connections[provider] = {
        key: result.key,
        auth: "oauth",
        expires_at: result.expires_at,
      };
      delete catalogs[provider];
      selectProvider(provider);
      openModelSettings();
      notify(
        `${displayProvider(provider)} connected. Loading available models.`,
      );
    } catch (error) {
      notify(error.message, true);
    }
  }
  async function unlock() {
    try {
      const response = await request("/api/v1/session");
      if (response.authenticated) {
        capabilities = await request("/api/v1/auth/capabilities");
        return true;
      }
      openDialog("unlockDialog");
      return false;
    } catch {
      notify("Cannot reach the workspace. Refresh to retry.", true);
      return false;
    }
  }
  function init() {
    $("useProviderBtn").addEventListener("click", () => {
      $("connectionDialog").close();
      selectProvider(editing);
      openModelSettings();
    });
    $("modelSearch").addEventListener("input", renderModels);
    $("refreshModelsBtn").addEventListener("click", () =>
      discover(state.provider),
    );
    $("manageConnectionBtn").addEventListener("click", () =>
      openConnection(state.provider),
    );
    $("providerConnections").addEventListener("click", (event) => {
      const id = event.target.closest("[data-connect-provider]")?.dataset
        .connectProvider;
      if (id) openConnection(id);
    });
    $("backToConnections").addEventListener("click", () => {
      $("connectionDialog").close();
      root.ScholarWorkspace.openSettings("connections");
    });
    $("saveProviderBtn").addEventListener("click", async () => {
      const previous = connection(editing),
        key = $("apiKeyInput").value.trim();
      state.connections[editing] = {
        ...previous,
        ...(key
          ? { key, auth: "key", expires_at: null }
          : previous.auth !== "oauth"
            ? { key: "", auth: "key" }
            : {}),
        endpoint: $("baseUrlInput").value.trim(),
      };
      await discover(editing);
      $("disconnectProviderBtn").hidden = !connection(editing).key;
    });
    $("connectProviderBtn").addEventListener("click", connectOAuth);
    $("disconnectProviderBtn").addEventListener("click", () => {
      state.connections[editing] = {};
      versions[editing] = (versions[editing] || 0) + 1;
      delete catalogs[editing];
      if (state.provider === editing) selectProvider(editing);
      openConnection(editing);
      renderConnections();
      notify(
        "Tab credentials removed. Revoke access at the provider to invalidate issued credentials.",
      );
    });
    $("unlockDialog").addEventListener("cancel", (event) =>
      event.preventDefault(),
    );
    $("unlockForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await request("/api/v1/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: $("workspacePassword").value }),
        });
        $("workspacePassword").value = "";
        $("unlockDialog").close();
        await Promise.allSettled([loadProviders(), loadJobs()]);
        capabilities = await request("/api/v1/auth/capabilities");
        await handleCallback();
      } catch (error) {
        $("unlockError").textContent = error.message;
      }
    });
  }
  root.NoevraProviders = {
    init,
    unlock,
    selectProvider,
    selectModel,
    renderConnections,
    handleCallback,
  };
})(window);
