/* Noevra: research workspace. */
"use strict";
const $ = (id) => document.getElementById(id);
const icons = (name) =>
  `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const state = {
  providers: {},
  provider: "groq",
  model: "",
  connections: {},
  jobs: [],
  jobId: null,
  report: null,
  query: "",
  view: "home",
  stream: null,
  pollTimer: null,
  pollAttempts: 0,
  logCount: 0,
  progress: 0,
  running: false,
  settingsProvider: null,
  notificationTimer: null,
  reportLoad: 0,
};
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function safeUrl(value) {
  try {
    const url = new URL(String(value));
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}
function sourceUrl(source) {
  return (
    safeUrl(source.url) ||
    (source.doi ? safeUrl(`https://doi.org/${source.doi}`) : "")
  );
}
function formatDate(value) {
  if (!value) return "";
  const d = new Date(value);
  return Number.isNaN(d.valueOf())
    ? ""
    : d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
}
function displayProvider(key) {
  return (
    {
      groq: "Groq",
      openai: "OpenAI",
      anthropic: "Anthropic",
      gemini: "Google Gemini",
      deepseek: "DeepSeek",
      openrouter: "OpenRouter",
      ollama: "Ollama",
      custom: "Custom endpoint",
    }[key] || key
  );
}
function shortModel(value) {
  return String(value || "Choose model")
    .split("/")
    .pop();
}
function notify(message, error = false) {
  clearTimeout(state.notificationTimer);
  $("notification").textContent = message;
  $("notification").classList.toggle("error", error);
  $("notification").hidden = false;
  state.notificationTimer = setTimeout(
    () => {
      $("notification").hidden = true;
    },
    error ? 8000 : 3500,
  );
}
function apiMessage(data) {
  if (Array.isArray(data.detail))
    return data.detail.map((e) => e.msg).join(" · ");
  return typeof data.detail === "string"
    ? data.detail
    : "The request could not be completed. Please try again.";
}
async function request(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let data = {};
    try {
      data = await res.json();
    } catch {}
    throw new Error(apiMessage(data));
  }
  return res.json();
}
function closeNavigation() {
  if ($("navigationDialog").open) $("navigationDialog").close();
}
function showView(view) {
  if (view !== "report" && /^#section-/.test(location.hash))
    history.replaceState(null, "", location.pathname + location.search);
  window.ScholarControls?.close();
  closeNavigation();
  state.view = view;
  for (const name of ["home", "running", "report", "library"])
    $(name + "View").hidden = name !== view;
  $("pageLabel").textContent = {
    home: "New research",
    running: "Research in progress",
    report: "Research report",
    library: "Library",
  }[view];
  document.querySelectorAll(".primary-nav [data-view]").forEach((b) => {
    const active = b.dataset.view === (view === "library" ? "library" : "home");
    b.classList.toggle("active", active);
    if (active) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  window.scrollTo({ top: 0, behavior: "instant" });
}
function newResearch() {
  if (state.running) {
    showView("running");
    notify(
      "Your current research is still running. You can start another when it finishes.",
    );
    return;
  }
  stopObservation();
  state.reportLoad++;
  state.jobId = null;
  state.report = null;
  state.query = "";
  $("queryInput").value = "";
  $("formError").hidden = true;
  window.ScholarWorkspace?.applyDefaults();
  showView("home");
  $("queryInput").focus();
}
function openDialog(id) {
  closeNavigation();
  if (!$(id).open) $(id).showModal();
}
function saveConnection() {
  if (!state.settingsProvider) return;
  const previous = state.connections[state.settingsProvider];
  state.connections[state.settingsProvider] = {
    auth:
      previous?.key === $("apiKeyInput").value.trim() ? previous?.auth : "key",
    key: $("apiKeyInput").value.trim(),
    endpoint: $("baseUrlInput").value.trim(),
    custom: $("customModel").value.trim(),
    model: $("modelSelect").value,
  };
  state.provider = state.settingsProvider;
  state.model = $("customModel").value.trim() || $("modelSelect").value;
  updateModelLabels();
}
function populateConnection(provider) {
  state.settingsProvider = provider;
  const info = state.providers[provider];
  if (!info) return;
  const saved = state.connections[provider] || {};
  $("modelSelect").innerHTML = (info.models || [])
    .map((m) => `<option value="${esc(m.id)}">${esc(m.name || m.id)}</option>`)
    .join("");
  $("modelSelect").value = saved.model || info.default_model;
  if (!$("modelSelect").value && $("modelSelect").options.length)
    $("modelSelect").selectedIndex = 0;
  $("customModel").value = saved.custom || "";
  $("apiKeyInput").value = saved.key || "";
  $("apiKeyInput").type = "password";
  $("revealKeyBtn").textContent = "Show";
  $("revealKeyBtn").setAttribute("aria-pressed", "false");
  $("revealKeyBtn").setAttribute("aria-label", "Show API key");
  $("endpointField").hidden = !["ollama", "custom"].includes(provider);
  $("baseUrlInput").value =
    saved.endpoint ||
    (provider === "ollama"
      ? "http://localhost:11434/v1"
      : provider === "custom"
        ? "http://localhost:1234/v1"
        : "");
  $("oauthConnection").hidden = provider !== "openrouter";
  $("connectionStatus").textContent = ["ollama", "custom"].includes(provider)
    ? "Uses your endpoint. Connection and model availability are checked when research starts."
    : info.configured_in_backend
      ? "A server API key is configured. You can supply an override below."
      : "Add an API key below, or configure this provider on your research server.";
  saveConnection();
}
function updateModelLabels() {
  $("composerModel").textContent = shortModel(state.model);
  window.ScholarControls?.sync();
  window.ScholarWorkspace?.updateOAuthStatus();
}
function openModelSettings() {
  $("providerSelect").value = state.provider;
  if (state.providers[state.provider]) populateConnection(state.provider);
  openDialog("modelDialog");
}
async function loadProviders() {
  try {
    state.providers = await request("/api/v1/research/providers");
    const entries = Object.keys(state.providers);
    $("defaultProvider").innerHTML = entries
      .map(
        (key) =>
          `<option value="${esc(key)}">${esc(displayProvider(key))}</option>`,
      )
      .join("");
    const preferred = window.ScholarWorkspace?.preferences.provider;
    if (entries.includes(preferred)) state.provider = preferred;
    $("defaultProvider").value = state.provider;
    $("providerSelect").innerHTML = entries
      .map(
        (key) =>
          `<option value="${esc(key)}">${esc(displayProvider(key))}</option>`,
      )
      .join("");
    if (!entries.includes(state.provider)) state.provider = entries[0];
    if (state.provider) {
      $("providerSelect").value = state.provider;
      populateConnection(state.provider);
    }
  } catch {
    $("connectionStatus").textContent =
      "Providers could not be loaded. Close this panel and refresh the page to retry.";
    $("composerModel").textContent = "Connection unavailable";
    notify("Cannot load model providers. Refresh the page to reconnect.", true);
  }
}
function emptyState(title, text, action = "") {
  return `<div class="empty-state">${icons("book")}<h3>${esc(title)}</h3><p>${esc(text)}</p>${action ? `<button class="secondary-button" data-action="${esc(action)}">${action === "refresh" ? "Try again" : "Start a question"}${icons("arrow")}</button>` : ""}</div>`;
}
async function loadJobs() {
  try {
    state.jobs = await request("/api/v1/research?limit=100");
    $("libraryCount").textContent = state.jobs.length || "";
    renderRecents();
    renderLibrary();
  } catch {
    $("recentList").innerHTML =
      '<p class="rail-empty">History is unavailable.<br><button class="text-button" data-action="refresh">Try again</button></p>';
    $("libraryList").innerHTML = emptyState(
      "Your library could not be loaded.",
      "Check your connection and try again.",
      "refresh",
    );
  }
}
function renderRecents() {
  $("recentList").innerHTML = state.jobs.length
    ? state.jobs
        .slice(0, 7)
        .map(
          (job) =>
            `<button class="recent-item" data-job="${esc(job.job_id)}" title="${esc(job.query)}">${icons("file")}<span>${esc(job.query)}</span></button>`,
        )
        .join("")
    : '<p class="rail-empty">Your questions will find<br>a home here.</p>';
}
function statusLabel(job) {
  return job.status === "done"
    ? "Completed"
    : job.status === "failed"
      ? "Needs attention"
      : "In progress";
}
function renderLibrary() {
  const filter = $("librarySearch").value.toLowerCase();
  const jobs = state.jobs.filter((j) =>
    `${j.query} ${j.provider} ${j.model}`.toLowerCase().includes(filter),
  );
  if (!jobs.length) {
    $("libraryList").innerHTML = emptyState(
      filter ? "No matching questions." : "A fresh page.",
      filter
        ? "Try another word or clear the search."
        : "Your completed research and ongoing investigations will appear here.",
      filter ? "" : "new",
    );
    return;
  }
  $("libraryList").innerHTML = jobs
    .map(
      (job) =>
        `<button class="library-item" data-job="${esc(job.job_id)}">${icons("file")}<span class="library-item-body"><strong>${esc(job.query)}</strong><small>${esc(displayProvider(job.provider))} · ${esc(formatDate(job.created_at))}${job.sources_count ? ` · ${Number(job.sources_count)} sources` : ""}</small></span><span class="library-item-status">${esc(statusLabel(job))}${icons(job.status === "done" ? "arrow" : "clock")}</span></button>`,
    )
    .join("");
}
function stopObservation() {
  if (state.stream) state.stream.close();
  state.stream = null;
  clearTimeout(state.pollTimer);
  state.pollTimer = null;
}
function logActivity(title, detail = "") {
  state.logCount++;
  const entry = document.createElement("div");
  entry.className = "activity-entry";
  const time = document.createElement("time");
  time.textContent = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
  const body = document.createElement("span");
  body.textContent = title + (detail ? " — " + detail : "");
  entry.append(time, body);
  $("activityLog").append(entry);
  $("activityCount").textContent =
    `${state.logCount} ${state.logCount === 1 ? "event" : "events"}`;
}
function setProgress(value, label) {
  state.progress = Math.max(0, Math.min(100, Number(value) || 0));
  $("progressFill").style.transform = `scaleX(${state.progress / 100})`;
  $("progressValue").textContent = `${state.progress}%`;
  $("progressTrack").setAttribute("aria-valuenow", String(state.progress));
  if (label) $("progressLabel").textContent = label;
}
function setStage(node, complete = false) {
  const names = ["planner", "researcher", "verifier", "writer", "reviewer"];
  const index = names.indexOf(node);
  document.querySelectorAll("#researchStages li").forEach((li, i) => {
    const done = i < index || (complete && i === index);
    const active = i === (complete ? index + 1 : index);
    li.className = done ? "done" : active ? "active" : "";
    li.querySelector(".stage-symbol").innerHTML = done
      ? icons("check")
      : String(i + 1);
    li.querySelector(".stage-state").textContent = done
      ? "Complete"
      : active
        ? "In progress"
        : "Waiting";
  });
}
function prepareRunning(query, meta = "") {
  state.logCount = 0;
  state.progress = 0;
  $("activeQueryTitle").textContent = query;
  $("runningMeta").textContent = meta;
  $("activityLog").replaceChildren();
  $("activityCount").textContent = "0 events";
  $("returnToQuestionBtn").hidden = true;
  $("runningNotice").classList.remove("error");
  $("runningNotice").innerHTML =
    icons("info") +
    "<span>You can browse your library while this research continues.</span>";
  $("startResearchBtn").disabled = true;
  setStage("planner");
  setProgress(3, "Preparing your research");
  showView("running");
}
function failResearch(message) {
  stopObservation();
  state.running = false;
  $("startResearchBtn").disabled = false;
  $("runningNotice").classList.add("error");
  $("runningNotice").innerHTML =
    icons("info") +
    `<span>${esc(message)} Your original question and settings are preserved.</span>`;
  $("returnToQuestionBtn").hidden = false;
  $("progressLabel").textContent = "Research needs attention";
  logActivity("Research stopped", message);
  if (state.view !== "running") notify(message, true);
  loadJobs();
}
async function startResearch(event) {
  event.preventDefault();
  if (state.running) return;
  saveConnection();
  const query = $("queryInput").value.trim();
  let error = "";
  if (query.length < 3)
    error = "Add a research question with at least three characters.";
  else if (!$("includeAcademic").checked && !$("includeWeb").checked)
    error =
      "Choose academic literature, the open web, or both in research preferences.";
  else if (!state.model)
    error = "Choose a provider and model before starting research.";
  if (error) {
    $("formError").textContent = error;
    $("formError").hidden = false;
    $("queryInput").setAttribute("aria-invalid", "true");
    if (
      !state.model ||
      (!$("includeAcademic").checked && !$("includeWeb").checked)
    )
      openModelSettings();
    else $("queryInput").focus();
    return;
  }
  $("formError").hidden = true;
  $("queryInput").removeAttribute("aria-invalid");
  state.query = query;
  state.running = true;
  const connection = state.connections[state.provider] || {};
  prepareRunning(
    query,
    `${displayProvider(state.provider)} · ${state.model} · ${$("depthSelect").selectedOptions[0].textContent}`,
  );
  try {
    const job = await request("/api/v1/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        provider: state.provider,
        model: state.model,
        api_key: connection.key || null,
        base_url: ["ollama", "custom"].includes(state.provider)
          ? connection.endpoint || null
          : null,
        depth: $("depthSelect").value,
        domain_focus: $("domainSelect").value,
        citation_style: $("citationSelect").value,
        language: $("languageSelect").value,
        include_academic: $("includeAcademic").checked,
        include_web: $("includeWeb").checked,
        sources_limit: Number($("sourceLimit").value),
      }),
    });
    state.jobId = job.job_id;
    logActivity(
      "Research started",
      "Your question has entered the research workflow.",
    );
    connectStream(job.job_id);
    loadJobs();
  } catch (error) {
    failResearch(error.message);
  }
}
function connectStream(jobId) {
  stopObservation();
  state.pollAttempts = 0;
  const stream = new EventSource(
    `/api/v1/research/${encodeURIComponent(jobId)}/stream`,
  );
  state.stream = stream;
  function receive(type, fn) {
    stream.addEventListener(type, (event) => {
      if (state.jobId !== jobId) return;
      try {
        fn(JSON.parse(event.data));
      } catch {
        failResearch(
          "An unreadable update was received. Open the saved job from your library to reconnect.",
        );
      }
    });
  }
  receive("start", (data) =>
    logActivity(
      "Search plan started",
      `${displayProvider(data.provider)} · ${data.model || ""}`,
    ),
  );
  receive("status", (data) => {
    setProgress(data.pct, data.step);
    if (data.status)
      setStage(
        {
          planning: "planner",
          researching: "researcher",
          verifying: "verifier",
          writing: "writer",
          reviewing: "reviewer",
        }[data.status] || "planner",
      );
  });
  receive("node_complete", (data) => {
    setProgress(data.pct, data.step);
    setStage(data.node, true);
    logActivity(
      data.log?.title || `${data.node} complete`,
      data.log?.detail || "",
    );
  });
  receive("done", (data) => {
    stopObservation();
    state.running = false;
    $("startResearchBtn").disabled = false;
    displayReport({ ...data, query: state.query });
    loadJobs();
  });
  stream.addEventListener("error", (event) => {
    if (state.jobId !== jobId) return;
    if (event.data) {
      try {
        const data = JSON.parse(event.data);
        failResearch(data.error || data.message || "The research job stopped.");
      } catch {
        failResearch("The research job stopped.");
      }
    } else {
      stream.close();
      state.stream = null;
      logActivity("Reconnecting", "Checking saved job status.");
      schedulePoll(jobId);
    }
  });
}
function schedulePoll(jobId) {
  clearTimeout(state.pollTimer);
  state.pollTimer = setTimeout(() => pollJob(jobId), 3000);
}
async function pollJob(jobId) {
  if (state.jobId !== jobId || !state.running) return;
  try {
    const job = await request(`/api/v1/research/${encodeURIComponent(jobId)}`);
    state.pollAttempts = 0;
    setProgress(job.progress_pct, job.current_step);
    if (job.status === "done") {
      await loadReport(jobId, false);
      state.running = false;
      $("startResearchBtn").disabled = false;
      loadJobs();
      return;
    }
    if (job.status === "failed") {
      failResearch(job.error || "The research could not be completed.");
      return;
    }
    setStage(
      {
        queued: "planner",
        planning: "planner",
        researching: "researcher",
        verifying: "verifier",
        writing: "writer",
        reviewing: "reviewer",
      }[job.status] || "planner",
    );
  } catch {
    state.pollAttempts++;
    if (state.pollAttempts >= 5) {
      failResearch(
        "The connection could not be restored. Research may still be running on the server; reopen it from your library.",
      );
      return;
    }
  }
  schedulePoll(jobId);
}
async function openJob(jobId) {
  const job = state.jobs.find((j) => j.job_id === jobId);
  if (
    state.running &&
    state.jobId !== jobId &&
    job?.status !== "done" &&
    job?.status !== "failed"
  ) {
    notify(
      "An investigation is already being followed. Reopen it from Recent research.",
    );
    return;
  }
  if (job?.status === "failed") {
    notify(
      job.error ||
        "This research did not complete. Start a new question to try again.",
      true,
    );
    return;
  }
  if (job?.status === "done" || job?.has_report) {
    await loadReport(jobId, true);
    return;
  }
  state.reportLoad++;
  stopObservation();
  state.jobId = jobId;
  state.query = job?.query || "Research in progress";
  state.running = true;
  prepareRunning(
    state.query,
    `${displayProvider(job?.provider || "")} · ${job?.depth || "Research"}`,
  );
  connectStream(jobId);
}
async function loadReport(jobId, foreground = true) {
  const ticket = ++state.reportLoad;
  const button = document.querySelector(`[data-job="${CSS.escape(jobId)}"]`);
  if (button) {
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  }
  try {
    const data = await request(
      `/api/v1/research/${encodeURIComponent(jobId)}/report`,
    );
    if (ticket !== state.reportLoad) return;
    if (foreground && state.running && state.jobId !== jobId) {
      notify(
        "Your ongoing investigation is still running. The saved report is ready to read.",
      );
    } else {
      stopObservation();
      state.jobId = jobId;
      state.running = false;
      $("startResearchBtn").disabled = false;
    }
    displayReport(data, jobId);
  } catch (error) {
    notify(`Could not open this report. ${error.message}`, true);
  } finally {
    if (button) {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    }
  }
}
// Retrieved content stays data: raw HTML is escaped and URL schemes are constrained.
function markdownEngine() {
  const factory =
    typeof module !== "undefined" && module.exports
      ? require("./vendor/markdown-it/markdown-it.min.js")
      : window.markdownit;
  const md = factory({
    html: false,
    linkify: false,
    typographer: false,
    breaks: false,
  });
  const textRule = md.renderer.rules.text;
  md.renderer.rules.text = (tokens, index, options, env, self) => {
    const text = textRule(tokens, index, options, env, self);
    return text.replace(
      /\[(\d+)\]/g,
      (_, n) =>
        `<button class="citation" data-citation="${Number(n)}" aria-label="Inspect source ${Number(n)}">${Number(n)}</button>`,
    );
  };
  md.renderer.rules.link_open = (tokens, index, options, env, self) => {
    tokens[index].attrSet("target", "_blank");
    tokens[index].attrSet("rel", "noopener noreferrer");
    return self.renderToken(tokens, index, options);
  };
  // Preserve TeX delimiters and escapes for the local math renderer.
  md.inline.ruler.before("escape", "math_passthrough", (parser, silent) => {
    const start = parser.pos;
    const rest = parser.src.slice(start);
    let end = -1;
    if (rest.startsWith("\\(")) {
      const close = parser.src.indexOf("\\)", start + 2);
      if (close >= 0) end = close + 2;
    } else if (rest.startsWith("\\[")) {
      const close = parser.src.indexOf("\\]", start + 2);
      if (close >= 0) end = close + 2;
    } else if (rest.startsWith("$")) {
      const length = rest.startsWith("$$") ? 2 : 1;
      const close = parser.src.indexOf("$".repeat(length), start + length);
      if (close >= 0) end = close + length;
    }
    if (end < 0) return false;
    if (!silent) {
      const token = parser.push("text", "", 0);
      token.content = parser.src.slice(start, end);
    }
    parser.pos = end;
    return true;
  });
  md.renderer.rules.table_open = () =>
    '<div class="table-wrap" tabindex="0" role="region" aria-label="Research comparison table"><table>';
  md.renderer.rules.table_close = () => "</table></div>";
  md.renderer.rules.image = (tokens, index) => esc(tokens[index].content);
  return md;
}
function inlineMarkdown(value) {
  return markdownEngine().renderInline(String(value || ""));
}
function renderMarkdown(markdown) {
  const md = markdownEngine(),
    toc = [],
    env = {};
  const tokens = md.parse(String(markdown || ""), env);
  let index = 0;
  tokens.forEach((token, i) => {
    if (token.type === "heading_open") {
      const id = `section-${++index}`;
      token.attrSet("id", id);
      if (token.tag === "h2")
        toc.push({ id, text: tokens[i + 1]?.content || "" });
    }
  });
  return { html: md.renderer.render(tokens, md.options, env), toc };
}
function renderMath() {
  if (typeof window.renderMathInElement !== "function") return;
  window.renderMathInElement($("reportArticle"), {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false },
      { left: "$", right: "$", display: false },
    ],
    throwOnError: false,
    trust: false,
    maxExpand: 1000,
    strict: "ignore",
  });
}
function displayReport(data, reportJobId = state.jobId) {
  state.report = {
    ...data,
    job_id: data.job_id || reportJobId,
    sources: data.sources || [],
    evidence_matrix: data.evidence_matrix || [],
    step_logs: data.step_logs || [],
    report_markdown: data.report_markdown ?? data.draft ?? "",
  };
  const report = state.report;
  const title =
    report.query ||
    state.query ||
    report.report_markdown.match(/^#\s+(.+)$/m)?.[1] ||
    "Research report";
  $("reportTitle").textContent = title;
  const job = state.jobs.find((j) => j.job_id === report.job_id);
  $("reportMeta").textContent = [
    formatDate(report.generated_at || job?.completed_at),
    displayProvider(report.provider || job?.provider || state.provider),
    report.depth || job?.depth || "Research",
  ]
    .filter(Boolean)
    .join(" · ");
  const words = report.report_markdown
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
  const review = [...report.step_logs]
    .reverse()
    .find((l) => l.node === "reviewer");
  const score = review?.critique?.overall_score ?? review?.score;
  $("reportStats").innerHTML =
    `<span>${words.toLocaleString()} words</span><span>${report.sources.length} sources</span><span>${report.evidence_matrix.length} evidence claims</span>${typeof score === "number" && Number.isFinite(score) && review?.critique?.verdict !== "UNAVAILABLE" ? `<span>Automated review ${esc(score)}/10</span>` : ""}`;
  $("evidenceCount").textContent = report.evidence_matrix.length;
  $("sourceCount").textContent = report.sources.length;
  let markdown = report.report_markdown.replace(/^#\s+[^\n]+\n+/, "");
  const firstSection = markdown.search(/^##\s/m);
  if (
    firstSection > 0 &&
    /research contract/i.test(markdown.slice(0, firstSection)) &&
    /json/i.test(markdown.slice(0, firstSection))
  )
    markdown = markdown.slice(firstSection);
  const parsed = renderMarkdown(markdown);
  $("reportArticle").innerHTML =
    parsed.html || "<p>No report text was recorded.</p>";
  renderMath();
  $("reportToc").innerHTML = parsed.toc.length
    ? parsed.toc
        .map(
          (h) =>
            `<a href="#${esc(h.id)}">${esc(h.text.replace(/\*+/g, ""))}</a>`,
        )
        .join("")
    : "<span>No section headings were recorded.</span>";
  const statuses = ["supported", "contested", "unverified", "stale"];
  $("marginEvidence").innerHTML =
    `<h3>Evidence at a glance</h3>${statuses.map((status) => `<div class="evidence-summary-line"><span>${status[0].toUpperCase() + status.slice(1)}</span><b>${report.evidence_matrix.filter((e) => (e.status || "unverified") === status).length}</b></div>`).join("")}`;
  $("evidenceFilter").value = "all";
  $("sourceSearch").value = "";
  renderEvidence();
  renderSources();
  renderProcess();
  window.ScholarWorkspace?.setupReportNavigation();
  setReportTab("Document");
  showView("report");
  window.ScholarWorkspace?.updateReportNavigation();
}
function setReportTab(name, focus = false) {
  for (const tab of document.querySelectorAll("[data-tab]")) {
    const selected = tab.dataset.tab === name;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    if (selected && focus) tab.focus();
    $("panel" + tab.dataset.tab).hidden = !selected;
  }
}
function renderEvidence() {
  if (!state.report) return;
  const filter = $("evidenceFilter").value;
  const claims = state.report.evidence_matrix.filter(
    (c) => filter === "all" || (c.status || "unverified") === filter,
  );
  $("evidenceList").innerHTML = claims.length
    ? claims
        .map((claim, i) => {
          const status = ["supported", "contested", "stale"].includes(
            claim.status,
          )
            ? claim.status
            : "unverified";
          const passages = (claim.evidence || [])
            .map((e) => {
              const source = state.report.sources.find(
                (s) => s.source_id === e.source_id,
              );
              const link = sourceUrl(source || e);
              return `<blockquote>${esc(e.passage || "No passage recorded.")}<cite>${esc(e.source_id || "Source")} · ${esc(e.publisher || source?.journal || "Publisher not recorded")}${e.stance ? ` · ${esc(e.stance)}` : ""}${link ? `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer">Original source${icons("external")}</a>` : ""}</cite></blockquote>`;
            })
            .join("");
          return `<article class="evidence-item"><div class="evidence-top"><span>${esc(claim.claim_id || `C-${i + 1}`)}</span><span class="claim-status ${status}">${status[0].toUpperCase() + status.slice(1)}</span>${claim.last_checked ? `<span>Checked ${esc(claim.last_checked)}</span>` : ""}</div><h3>${esc(claim.claim)}</h3>${passages || '<p class="evidence-explanation">No source passage was recorded for this claim.</p>'}${claim.reason ? `<p class="evidence-explanation"><strong>Why this status:</strong> ${esc(claim.reason)}</p>` : ""}${claim.open_question ? `<p class="evidence-explanation"><strong>Still open:</strong> ${esc(claim.open_question)}</p>` : ""}${claim.methodological_caveats ? `<p class="evidence-explanation"><strong>Limitations:</strong> ${esc(claim.methodological_caveats)}</p>` : ""}</article>`;
        })
        .join("")
    : emptyState(
        filter === "all"
          ? "No structured claims were recorded."
          : "No claims in this category.",
        "Inspect the report and original sources for further context.",
      );
}
function renderSources() {
  if (!state.report) return;
  const filter = $("sourceSearch").value.toLowerCase();
  const rows = state.report.sources
    .map((source, index) => ({ source, index }))
    .filter(({ source: s }) =>
      `${s.title} ${(s.authors || []).join(" ")} ${s.journal || ""} ${s.doi || ""}`
        .toLowerCase()
        .includes(filter),
    );
  $("sourcesList").innerHTML = rows.length
    ? rows
        .map(({ source: s, index }) => {
          const url = sourceUrl(s);
          return `<article class="source-item" id="source-${index + 1}"><span class="source-number">[${index + 1}]</span><div class="source-item-body"><h3>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(s.title || "Untitled source")}${icons("external")}</a>` : esc(s.title || "Untitled source")}</h3><p>${esc((s.authors || []).slice(0, 4).join(", ") || "Author not recorded")}${s.published_date ? ` · ${esc(s.published_date)}` : ""}${s.journal ? ` · ${esc(s.journal)}` : ""}${s.doi ? `<br>DOI: ${esc(s.doi)}` : ""}</p>${s.snippet || s.abstract ? `<p class="source-snippet">${esc(String(s.snippet || s.abstract).slice(0, 700))}</p>` : ""}<span class="source-type">${esc(s.source_type || "Source")}${s.accessed_at ? ` · Accessed ${esc(s.accessed_at)}` : ""}</span></div></article>`;
        })
        .join("")
    : emptyState("No matching sources.", "Try another author, title or DOI.");
}
function renderProcess() {
  const report = state.report;
  const plan = report.step_logs.find((l) => l.node === "planner");
  const contract = report.contract || plan?.contract;
  const reviewer = [...report.step_logs]
    .reverse()
    .find((l) => l.node === "reviewer");
  let html = "";
  if (contract) {
    html += `<section class="process-block"><h3>Research brief</h3><p>${esc(contract.question || report.query || "")}</p>${contract.scope ? `<p><strong>Scope:</strong> ${esc(contract.scope)}</p>` : ""}${contract.as_of ? `<p><strong>As of:</strong> ${esc(contract.as_of)}</p>` : ""}${contract.must_resolve?.length ? `<h4>Questions to resolve</h4><ul>${contract.must_resolve.map((q) => `<li>${esc(q)}</li>`).join("")}</ul>` : ""}</section>`;
  }
  html += `<section class="process-block"><h3>Automated review</h3><p>${esc(reviewer?.critique?.verdict || reviewer?.verdict || "No review verdict was recorded.")}</p>${reviewer?.detail ? `<p>${esc(reviewer.detail)}</p>` : ""}${reviewer?.critique?.weaknesses?.length ? `<h4>Limitations identified</h4><ul>${reviewer.critique.weaknesses.map((w) => `<li>${esc(w)}</li>`).join("")}</ul>` : ""}<p>Automated review does not replace expert or journal peer review.</p></section>`;
  html += report.step_logs
    .map(
      (log) =>
        `<div class="process-stage">${icons("check")}<div><h3>${esc(log.title || log.node || "Research step")}</h3><p>${esc(log.detail || "No additional details recorded.")}</p></div></div>`,
    )
    .join("");
  $("processContent").innerHTML = html;
}
async function copyReport() {
  if (!state.report) return;
  try {
    await navigator.clipboard.writeText(state.report.report_markdown);
    notify("Report copied to clipboard.");
  } catch {
    notify(
      "Could not access the clipboard. Export the Markdown file instead.",
      true,
    );
  }
}
async function exportReport(format) {
  if (!state.report?.job_id) return;
  document.querySelector(".export-menu").open = false;
  const button = document.querySelector(`[data-export="${format}"]`);
  button.disabled = true;
  try {
    const res = await fetch(
      `/api/v1/research/${encodeURIComponent(state.report.job_id)}/report/${format}`,
    );
    if (!res.ok) {
      let data = {};
      try {
        data = await res.json();
      } catch {}
      throw new Error(apiMessage(data));
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const disposition = res.headers.get("Content-Disposition") || "";
    a.download =
      disposition.match(/filename="([^"]+)"/)?.[1] ||
      `research-${state.report.job_id.slice(0, 8)}.${format === "download" ? "md" : format === "bibtex" ? "bib" : "pdf"}`;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    notify("Your export is ready.");
  } catch (error) {
    notify(`Export failed. ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}
function toggleTheme() {
  window.ScholarWorkspace.setTheme(
    document.documentElement.dataset.theme === "dark" ? "light" : "dark",
  );
}
function updateThemeButton() {
  const dark = document.documentElement.dataset.theme === "dark";
  $("themeToggle").innerHTML = icons(dark ? "sun" : "moon");
  $("themeToggle").setAttribute(
    "aria-label",
    `Switch to ${dark ? "light" : "dark"} theme`,
  );
}
function bindEvents() {
  document.addEventListener("click", (event) => {
    const action = event.target.closest("[data-action]")?.dataset.action;
    if (action === "new") newResearch();
    if (action === "settings") window.ScholarWorkspace.openSettings();
    if (action === "model") openModelSettings();
    if (action === "manage-model") {
      $("settingsDialog").close();
      openModelSettings();
    }
    if (action === "how") openDialog("helpDialog");
    if (action === "refresh") {
      loadJobs();
      notify("Refreshing your research library.");
    }
    const view = event.target.closest("[data-view]")?.dataset.view;
    if (view === "library") {
      showView("library");
      renderLibrary();
    }
    if (view === "home") {
      showView(state.running ? "running" : "home");
    }
    const close = event.target.closest("[data-close]")?.dataset.close;
    if (close) $(close).close();
    const job = event.target.closest("[data-job]")?.dataset.job;
    if (job) openJob(job);
    const suggestion = event.target.closest("[data-query]");
    if (suggestion) {
      $("queryInput").value = suggestion.dataset.query;
      $("domainSelect").value = suggestion.dataset.domain;
      $("queryInput").focus();
    }
    const citation = event.target.closest("[data-citation]");
    if (citation) {
      const index = Number(citation.dataset.citation);
      if (state.report?.sources[index - 1]) {
        setReportTab("Sources");
        $("sourceSearch").value = "";
        renderSources();
        $(`source-${index}`).scrollIntoView({
          block: "center",
          behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "instant"
            : "smooth",
        });
        $(`source-${index}`).querySelector("a")?.focus({ preventScroll: true });
      } else
        notify("This citation does not have a matching source record.", true);
    }
    const tab = event.target.closest("[data-tab]")?.dataset.tab;
    if (tab) setReportTab(tab);
    const format = event.target.closest("[data-export]")?.dataset.export;
    if (format) exportReport(format);
  });
  $("researchForm").addEventListener("submit", startResearch);
  $("queryInput").addEventListener("input", () => {
    $("queryInput").removeAttribute("aria-invalid");
    $("formError").hidden = true;
  });
  $("providerSelect").addEventListener("change", () => {
    saveConnection();
    populateConnection($("providerSelect").value);
  });
  for (const id of [
    "modelSelect",
    "customModel",
    "apiKeyInput",
    "baseUrlInput",
  ])
    $(id).addEventListener("input", saveConnection);
  $("modelDialog").addEventListener("close", saveConnection);
  $("revealKeyBtn").addEventListener("click", () => {
    const reveal = $("apiKeyInput").type === "password";
    $("apiKeyInput").type = reveal ? "text" : "password";
    $("revealKeyBtn").textContent = reveal ? "Hide" : "Show";
    $("revealKeyBtn").setAttribute(
      "aria-label",
      reveal ? "Hide API key" : "Show API key",
    );
    $("revealKeyBtn").setAttribute("aria-pressed", String(reveal));
  });
  $("howItWorksBtn").addEventListener("click", () => openDialog("helpDialog"));
  $("mobileMenuBtn").addEventListener("click", () =>
    openDialog("navigationDialog"),
  );
  $("themeToggle").addEventListener("click", toggleTheme);
  $("librarySearch").addEventListener("input", renderLibrary);
  $("sourceSearch").addEventListener("input", renderSources);
  $("evidenceFilter").addEventListener("change", renderEvidence);
  $("copyReportBtn").addEventListener("click", copyReport);
  $("returnToQuestionBtn").addEventListener("click", () => {
    showView("home");
    $("queryInput").focus();
  });
  document
    .querySelector(".report-tabs")
    .addEventListener("keydown", (event) => {
      const tabs = [...document.querySelectorAll("[data-tab]")];
      const current = tabs.indexOf(document.activeElement);
      if (current < 0) return;
      let next = current;
      if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
      else if (event.key === "ArrowLeft")
        next = (current + tabs.length - 1) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      setReportTab(tabs[next].dataset.tab, true);
    });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (!document.querySelector("dialog[open]")) newResearch();
    }
    if (
      (event.ctrlKey || event.metaKey) &&
      event.key === "Enter" &&
      state.view === "home" &&
      !document.querySelector("dialog[open]")
    ) {
      event.preventDefault();
      $("researchForm").requestSubmit();
    }
    if (event.key === "Escape")
      document.querySelector(".export-menu").open = false;
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".export-menu"))
      document.querySelector(".export-menu").open = false;
  });
  window.addEventListener("beforeunload", stopObservation);
}
async function init() {
  try {
    const theme = localStorage.getItem("scholar_theme");
    if (["light", "dark"].includes(theme))
      document.documentElement.dataset.theme = theme;
    for (const key of Object.keys(localStorage))
      if (key.startsWith("scholar_key_")) localStorage.removeItem(key);
  } catch {}
  window.ScholarWorkspace.init();
  window.ScholarControls.init();
  updateThemeButton();
  bindEvents();
  await Promise.allSettled([loadProviders(), loadJobs()]);
  await window.ScholarWorkspace.handleOAuthCallback();
  window.ScholarControls.sync();
}
if (typeof module !== "undefined" && module.exports)
  module.exports = { esc, safeUrl, inlineMarkdown, renderMarkdown };
else document.addEventListener("DOMContentLoaded", init);
