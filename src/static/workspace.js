/* Durable non-secret preferences, report wayfinding, and tab-scoped OAuth. */
(function (root) {
  const defaults = {
    theme: "light",
    reading: "standard",
    collapsed: false,
    motion: false,
    provider: "groq",
    depth: "standard",
    language: "en",
    citation: "ieee",
    sources: "20",
  };
  let preferences = { ...defaults },
    headings = [],
    pendingSection = null,
    navigationFrame = 0,
    sectionTimer;
  function save() {
    try {
      localStorage.setItem("scholar_preferences", JSON.stringify(preferences));
    } catch {
      notify(
        "Browser storage is unavailable. Preferences apply only until reload.",
      );
    }
  }
  function setCollapsed(value) {
    preferences.collapsed = Boolean(value);
    document.documentElement.classList.toggle(
      "sidebar-collapsed",
      preferences.collapsed,
    );
    $("compactSidebar").checked = preferences.collapsed;
    $("sidebarToggle").setAttribute(
      "aria-expanded",
      String(!preferences.collapsed),
    );
    $("sidebarToggle").setAttribute(
      "aria-label",
      preferences.collapsed ? "Expand sidebar" : "Minimize sidebar",
    );
    $("sidebarToggle").title = preferences.collapsed
      ? "Expand sidebar"
      : "Minimize sidebar";
    save();
  }
  function applyAppearance() {
    const theme =
      preferences.theme === "system"
        ? matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light"
        : preferences.theme;
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.readingSize = preferences.reading;
    document.documentElement.dataset.reduceMotion = String(preferences.motion);
    $("appearanceTheme").value = preferences.theme;
    $("readingSize").value = preferences.reading;
    $("reduceMotion").checked = preferences.motion;
    updateThemeButton();
    root.ScholarControls?.sync();
  }
  function setTheme(theme) {
    if (!["light", "dark", "system"].includes(theme)) return;
    preferences.theme = theme;
    applyAppearance();
    save();
  }
  function applyDefaults() {
    for (const [id, value] of Object.entries({
      depthSelect: preferences.depth,
      languageSelect: preferences.language,
      citationSelect: preferences.citation,
      sourceLimit: preferences.sources,
    }))
      $(id).value = value;
    if (state.providers[preferences.provider]) {
      state.provider = preferences.provider;
      $("providerSelect").value = state.provider;
      populateConnection(state.provider);
    }
    root.ScholarControls?.sync();
  }
  function settingsTab(name) {
    document.querySelectorAll("[data-settings-tab]").forEach((button) => {
      const active = button.dataset.settingsTab === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    document
      .querySelectorAll("[data-settings-panel]")
      .forEach(
        (panel) => (panel.hidden = panel.dataset.settingsPanel !== name),
      );
    root.ScholarControls?.close();
  }
  function openSettings() {
    for (const [id, key] of Object.entries({
      defaultProvider: "provider",
      defaultDepth: "depth",
      defaultLanguage: "language",
      defaultCitation: "citation",
      defaultSources: "sources",
    }))
      $(id).value = preferences[key];
    applyAppearance();
    updateOAuthStatus();
    openDialog("settingsDialog");
    root.ScholarControls?.sync();
  }
  function activeSection(id) {
    $("reportToc")
      .querySelectorAll("a")
      .forEach((link) => {
        const active = link.hash === "#" + id;
        link.classList.toggle("active", active);
        if (active) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
  }
  function updateReportNavigation() {
    if (
      state.view !== "report" ||
      $("panelDocument").hidden ||
      !headings.length
    )
      return;
    if (pendingSection) {
      activeSection(pendingSection);
      return;
    }
    let active = headings[0].id;
    const boundary = Math.max(180, Math.min(innerHeight * 0.28, 240));
    for (const heading of headings) {
      if (heading.getBoundingClientRect().top <= boundary) active = heading.id;
      else break;
    }
    if (
      scrollY > 0 &&
      scrollY + innerHeight >= document.documentElement.scrollHeight - 5
    )
      active = headings.at(-1).id;
    activeSection(active);
  }
  function setupReportNavigation() {
    headings = [...$("reportArticle").querySelectorAll("h2[id]")];
    pendingSection = null;
    if (headings.length) activeSection(headings[0].id);
  }
  function requestNavigationUpdate() {
    if (navigationFrame) return;
    navigationFrame = requestAnimationFrame(() => {
      navigationFrame = 0;
      updateReportNavigation();
    });
  }
  function releaseSection() {
    pendingSection = null;
    clearTimeout(sectionTimer);
    requestNavigationUpdate();
  }
  function updateOAuthStatus() {
    const connected =
      state.connections.openrouter?.auth === "oauth" &&
      Boolean(state.connections.openrouter?.key);
    if (state.settingsProvider === "openrouter")
      $("connectionStatus").textContent = connected
        ? "Connected using OAuth for this tab."
        : "Connect your OpenRouter account below, or supply an API key.";
    $("globalOAuthStatus").textContent = connected
      ? "Connected for this tab"
      : "Not connected in this tab";
    $("globalConnectBtn").textContent = connected ? "Manage" : "Connect";
    $("connectOpenRouterBtn").hidden = connected;
    $("disconnectOpenRouterBtn").hidden = !connected;
    $("oauthStatus").textContent = connected
      ? "Your OpenRouter account is connected. Credentials stay in memory until this tab reloads or closes."
      : "Sign in securely using OAuth. Model usage is billed to your OpenRouter credits. This connection lasts until you reload or close this tab.";
  }
  async function connectOAuth() {
    if (state.running) {
      notify("Wait for the current research to finish before signing in.");
      return;
    }
    const button = $("connectOpenRouterBtn");
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    try {
      if (!isSecureContext || !crypto.subtle)
        throw new Error("OAuth requires HTTPS, localhost, or 127.0.0.1.");
      const pending = await root.ScholarOAuth.createPKCE();
      sessionStorage.setItem(
        "scholar_oauth_pending",
        JSON.stringify({ ...pending, draft: $("queryInput").value }),
      );
      const callback = location.origin + location.pathname;
      location.assign(
        root.ScholarOAuth.authorizationUrl(
          callback,
          pending.challenge,
          pending.state,
        ),
      );
    } catch (error) {
      notify(error.message || "Could not start sign-in. Try again.", true);
      button.disabled = false;
      button.removeAttribute("aria-busy");
    }
  }
  async function handleOAuthCallback() {
    const params = new URLSearchParams(location.search);
    const code = params.get("code"),
      error = params.get("error");
    if (!code && !error) return;
    const returnedState = params.get("state");
    params.delete("code");
    params.delete("state");
    params.delete("error");
    params.delete("error_description");
    history.replaceState(
      null,
      "",
      location.pathname +
        (params.size ? "?" + params.toString() : "") +
        location.hash,
    );
    let pending;
    try {
      pending = JSON.parse(
        sessionStorage.getItem("scholar_oauth_pending") || "null",
      );
      sessionStorage.removeItem("scholar_oauth_pending");
    } catch {}
    if (pending?.draft) $("queryInput").value = pending.draft;
    if (error) {
      notify(
        "OpenRouter sign-in was not completed. You can connect again from Settings.",
        true,
      );
      return;
    }
    if (!root.ScholarOAuth.validatePending(pending, returnedState)) {
      notify(
        "This sign-in expired or does not match this tab. Connect again from Settings.",
        true,
      );
      return;
    }
    try {
      const response = await request("/api/v1/auth/openrouter/exchange", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, code_verifier: pending.verifier }),
      });
      if (!state.providers.openrouter)
        throw new Error(
          "Provider settings could not be loaded. Refresh and connect again.",
        );
      state.connections.openrouter = {
        ...state.connections.openrouter,
        key: response.key,
        auth: "oauth",
      };
      state.provider = "openrouter";
      $("providerSelect").value = "openrouter";
      populateConnection("openrouter");
      updateOAuthStatus();
      notify("OpenRouter connected. Your research will use this account.");
    } catch (error) {
      notify(error.message || "Could not complete OpenRouter sign-in.", true);
    }
  }
  function init() {
    try {
      const saved = JSON.parse(
        localStorage.getItem("scholar_preferences") || "{}",
      );
      for (const key of [
        "theme",
        "reading",
        "provider",
        "depth",
        "language",
        "citation",
        "sources",
      ])
        if (typeof saved[key] === "string") preferences[key] = saved[key];
      for (const key of ["collapsed", "motion"])
        if (typeof saved[key] === "boolean") preferences[key] = saved[key];
      if (!["light", "dark", "system"].includes(preferences.theme))
        preferences.theme = "light";
      if (!["standard", "large", "extra"].includes(preferences.reading))
        preferences.reading = "standard";
      if (!["quick", "standard", "deep"].includes(preferences.depth))
        preferences.depth = "standard";
      if (!["en", "id"].includes(preferences.language))
        preferences.language = "en";
      if (!["ieee", "apa", "nature", "harvard"].includes(preferences.citation))
        preferences.citation = "ieee";
      if (!["10", "20", "30", "50"].includes(preferences.sources))
        preferences.sources = "20";
    } catch {}
    applyAppearance();
    setCollapsed(preferences.collapsed);
    applyDefaults();
    $("sidebarToggle").addEventListener("click", () =>
      setCollapsed(!preferences.collapsed),
    );
    $("compactSidebar").addEventListener("change", () =>
      setCollapsed($("compactSidebar").checked),
    );
    $("appearanceTheme").addEventListener("change", () =>
      setTheme($("appearanceTheme").value),
    );
    $("readingSize").addEventListener("change", () => {
      preferences.reading = $("readingSize").value;
      applyAppearance();
      save();
      requestNavigationUpdate();
    });
    $("reduceMotion").addEventListener("change", () => {
      preferences.motion = $("reduceMotion").checked;
      applyAppearance();
      save();
    });
    for (const [id, key] of Object.entries({
      defaultProvider: "provider",
      defaultDepth: "depth",
      defaultLanguage: "language",
      defaultCitation: "citation",
      defaultSources: "sources",
    }))
      $(id).addEventListener("change", () => {
        preferences[key] = $(id).value;
        save();
      });
    document
      .querySelectorAll("[data-settings-tab]")
      .forEach((button) =>
        button.addEventListener("click", () =>
          settingsTab(button.dataset.settingsTab),
        ),
      );
    $("reportToc").addEventListener("click", (event) => {
      const link = event.target.closest("a");
      if (!link) return;
      const target = document.getElementById(link.hash.slice(1));
      if (!target) return;
      event.preventDefault();
      pendingSection = target.id;
      activeSection(target.id);
      history.replaceState(
        null,
        "",
        location.pathname + location.search + link.hash,
      );
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
      target.scrollIntoView({
        block: "start",
        behavior:
          preferences.motion ||
          matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "instant"
            : "smooth",
      });
      clearTimeout(sectionTimer);
      sectionTimer = setTimeout(releaseSection, 1000);
    });
    addEventListener("scroll", requestNavigationUpdate, { passive: true });
    addEventListener("scrollend", releaseSection);
    addEventListener("wheel", releaseSection, { passive: true });
    addEventListener("touchstart", releaseSection, { passive: true });
    addEventListener("resize", requestNavigationUpdate);
    matchMedia("(prefers-color-scheme: dark)").addEventListener(
      "change",
      () => {
        if (preferences.theme === "system") applyAppearance();
      },
    );
    $("connectOpenRouterBtn").addEventListener("click", connectOAuth);
    $("globalConnectBtn").addEventListener("click", () => {
      $("settingsDialog").close();
      $("providerSelect").value = "openrouter";
      populateConnection("openrouter");
      openModelSettings();
    });
    $("disconnectOpenRouterBtn").addEventListener("click", () => {
      if (state.connections.openrouter) {
        state.connections.openrouter.key = "";
        state.connections.openrouter.auth = "key";
      }
      if (state.settingsProvider === "openrouter") $("apiKeyInput").value = "";
      updateOAuthStatus();
      notify(
        "OpenRouter disconnected from this tab. Revoke the key in OpenRouter to invalidate it.",
      );
    });
    updateOAuthStatus();
  }
  root.ScholarWorkspace = {
    init,
    openSettings,
    setTheme,
    applyDefaults,
    updateOAuthStatus,
    setupReportNavigation,
    updateReportNavigation,
    handleOAuthCallback,
    get preferences() {
      return preferences;
    },
  };
})(window);
