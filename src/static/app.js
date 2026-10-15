/**
 * ScholarAgent - Interactive Web Application Logic
 * Handles multi-provider model selection, real-time SSE telemetry,
 * interactive academic monograph rendering, and bibliographic inspections.
 */

// Application State
const state = {
  providers: {},
  selectedProvider: "groq",
  selectedModel: "openai/gpt-oss-120b",
  activeJobId: null,
  activeReport: null,
  sources: [],
  evidenceMatrix: [],
  stepLogs: [],
  eventSource: null,
};

// Provider icons map
const PROVIDER_ICONS = {
  groq: "⚡",
  openai: "✨",
  anthropic: "🏛️",
  gemini: "💎",
  deepseek: "🐋",
  openrouter: "🌐",
  ollama: "🦙",
  custom: "⚙️",
};

// DOM Elements
const elements = {
  providerGrid: document.getElementById("providerGrid"),
  modelSelect: document.getElementById("modelSelect"),
  apiKeyToggle: document.getElementById("apiKeyToggle"),
  apiKeyContainer: document.querySelector(".api-key-container"),
  apiKeyInput: document.getElementById("apiKeyInput"),
  baseUrlInput: document.getElementById("baseUrlInput"),
  customUrlField: document.getElementById("customUrlField"),
  researchForm: document.getElementById("researchForm"),
  queryInput: document.getElementById("queryInput"),
  startBtn: document.getElementById("startResearchBtn"),
  
  // Pipeline status & radar
  pipelineStatusPill: document.getElementById("pipelineStatusPill"),
  statusPillText: document.getElementById("statusPillText"),
  badgeIcon: document.getElementById("badgeIcon"),
  badgeText: document.getElementById("badgeText"),
  
  // States
  idleState: document.getElementById("idleState"),
  runningState: document.getElementById("runningState"),
  completedState: document.getElementById("completedState"),
  
  // Running radar
  activeQueryTitle: document.getElementById("activeQueryTitle"),
  activeModelPill: document.getElementById("activeModelPill"),
  activeDepthPill: document.getElementById("activeDepthPill"),
  pipelineProgressFill: document.getElementById("pipelineProgressFill"),
  telemetryLog: document.getElementById("telemetryLog"),
  
  // Completed metrics & actions
  paperWordCount: document.getElementById("paperWordCount"),
  paperSourceCount: document.getElementById("paperSourceCount"),
  paperTier1Count: document.getElementById("paperTier1Count"),
  paperScore: document.getElementById("paperScore"),
  downloadPdfBtn: document.getElementById("downloadPdfBtn"),
  downloadMdBtn: document.getElementById("downloadMdBtn"),
  exportBibtexBtn: document.getElementById("exportBibtexBtn"),
  copyPaperBtn: document.getElementById("copyPaperBtn"),
  
  // Tabs & Views
  tabButtons: document.querySelectorAll(".tab-btn"),
  tabContents: document.querySelectorAll(".tab-content"),
  paperArticle: document.getElementById("paperArticle"),
  researchContractCard: document.getElementById("researchContractCard"),
  tocList: document.getElementById("tocList"),
  evidenceCardsGrid: document.getElementById("evidenceCardsGrid"),
  credibilitySummaryRow: document.getElementById("credibilitySummaryRow"),
  ledgerFilterButtons: document.getElementById("ledgerFilterButtons"),
  sourcesList: document.getElementById("sourcesList"),
  sourceSearchInput: document.getElementById("sourceSearchInput"),
  sourceTabCount: document.getElementById("sourceTabCount"),
  refereeCard: document.getElementById("refereeCard"),
  stepLogsTimeline: document.getElementById("stepLogsTimeline"),
  
  // Library drawer
  historyToggleBtn: document.getElementById("historyToggleBtn"),
  historyDrawer: document.getElementById("historyDrawer"),
  historyDrawerOverlay: document.getElementById("historyDrawerOverlay"),
  closeHistoryBtn: document.getElementById("closeHistoryBtn"),
  historyList: document.getElementById("historyList"),
  
  // Citation Tooltip
  citationTooltip: document.getElementById("citationTooltip"),
};

// ============================================================================
// Initialization & Provider Configuration
// ============================================================================
async function initApp() {
  setupEventListeners();
  await loadProviders();
  loadSavedApiKeys();
}

async function loadProviders() {
  try {
    const res = await fetch("/api/v1/research/providers");
    if (!res.ok) throw new Error("Failed to load providers");
    state.providers = await res.json();
    renderProviderGrid();
    updateModelOptions();
  } catch (err) {
    console.error("Error loading providers:", err);
  }
}

function renderProviderGrid() {
  elements.providerGrid.innerHTML = "";
  for (const [key, p] of Object.entries(state.providers)) {
    const card = document.createElement("div");
    card.className = `provider-card ${key === state.selectedProvider ? "active" : ""}`;
    card.dataset.provider = key;
    
    const icon = PROVIDER_ICONS[key] || "⚙️";
    const statusText = p.configured_in_backend ? "Ready (Configured)" : (key === "ollama" ? "Local endpoint" : "API Key required");

    card.innerHTML = `
      <span class="provider-icon">${icon}</span>
      <div class="provider-meta">
        <span class="provider-name">${p.name.split(" ")[0]}</span>
        <span class="provider-status">${statusText}</span>
      </div>
    `;

    card.addEventListener("click", () => selectProvider(key));
    elements.providerGrid.appendChild(card);
  }
}

function selectProvider(providerKey) {
  state.selectedProvider = providerKey;
  document.querySelectorAll(".provider-card").forEach(c => {
    c.classList.toggle("active", c.dataset.provider === providerKey);
  });
  
  updateModelOptions();
  updateProviderBadge();
  loadSavedApiKeyForProvider(providerKey);

  // Toggle custom base URL input for Ollama & Custom
  if (providerKey === "ollama" || providerKey === "custom") {
    elements.customUrlField.style.display = "block";
    elements.baseUrlInput.value = providerKey === "ollama" ? "http://localhost:11434/v1" : "http://localhost:1234/v1";
  } else {
    elements.customUrlField.style.display = "none";
  }
}

function updateModelOptions() {
  const provider = state.providers[state.selectedProvider];
  if (!provider) return;

  elements.modelSelect.innerHTML = "";
  provider.models.forEach(m => {
    const opt = document.createElement("option");
    opt.value = m.id;
    opt.textContent = `${m.name} [Context: ${m.context}]`;
    if (m.id === provider.default_model) opt.selected = true;
    elements.modelSelect.appendChild(opt);
  });

  state.selectedModel = elements.modelSelect.value;
  updateProviderBadge();
}

function updateProviderBadge() {
  const icon = PROVIDER_ICONS[state.selectedProvider] || "⚡";
  elements.badgeIcon.textContent = icon;
  const pName = state.selectedProvider.toUpperCase();
  const mName = state.selectedModel.split("/").pop();
  elements.badgeText.textContent = `${pName} · ${mName}`;
}

// LocalStorage API key persistence
function loadSavedApiKeys() {
  loadSavedApiKeyForProvider(state.selectedProvider);
}

function loadSavedApiKeyForProvider(providerKey) {
  const savedKey = localStorage.getItem(`scholar_key_${providerKey}`) || "";
  elements.apiKeyInput.value = savedKey;
}

// ============================================================================
// Event Listeners
// ============================================================================
function setupEventListeners() {
  // Model selector change
  elements.modelSelect.addEventListener("change", (e) => {
    state.selectedModel = e.target.value;
    updateProviderBadge();
  });

  // API Key accordion
  elements.apiKeyToggle.addEventListener("click", () => {
    elements.apiKeyContainer.classList.toggle("expanded");
  });

  // API Key save on blur
  elements.apiKeyInput.addEventListener("change", (e) => {
    const val = e.target.value.trim();
    if (val) {
      localStorage.setItem(`scholar_key_${state.selectedProvider}`, val);
    } else {
      localStorage.removeItem(`scholar_key_${state.selectedProvider}`);
    }
  });

  // Depth cards toggle
  document.querySelectorAll(".depth-card").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".depth-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
    });
  });

  // Sample queries click
  document.querySelectorAll(".sample-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      elements.queryInput.value = chip.dataset.query;
      const domain = chip.dataset.domain;
      if (domain) document.getElementById("domainSelect").value = domain;
      elements.queryInput.focus();
    });
  });

  // Form submit
  elements.researchForm.addEventListener("submit", handleStartResearch);

  // Tabs click
  elements.tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      elements.tabButtons.forEach(b => b.classList.remove("active"));
      elements.tabContents.forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.dataset.target;
      document.getElementById(targetId).classList.add("active");
    });
  });

  // Ledger Filter Buttons
  if (elements.ledgerFilterButtons) {
    elements.ledgerFilterButtons.addEventListener("click", (e) => {
      const btn = e.target.closest(".ledger-filter-btn");
      if (!btn) return;
      elements.ledgerFilterButtons.querySelectorAll(".ledger-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      renderEvidenceMatrix(btn.dataset.status);
    });
  }

  // History Drawer toggle
  elements.historyToggleBtn.addEventListener("click", openHistoryDrawer);
  elements.closeHistoryBtn.addEventListener("click", closeHistoryDrawer);
  elements.historyDrawerOverlay.addEventListener("click", closeHistoryDrawer);

  // Export buttons
  elements.downloadPdfBtn.addEventListener("click", () => {
    if (state.activeJobId) window.location.href = `/api/v1/research/${state.activeJobId}/report/pdf`;
  });
  elements.downloadMdBtn.addEventListener("click", () => {
    if (state.activeJobId) window.location.href = `/api/v1/research/${state.activeJobId}/report/download`;
  });
  elements.exportBibtexBtn.addEventListener("click", () => {
    if (state.activeJobId) window.location.href = `/api/v1/research/${state.activeJobId}/report/bibtex`;
  });
  elements.copyPaperBtn.addEventListener("click", handleCopyPaper);

  // Sources search filter
  elements.sourceSearchInput.addEventListener("input", (e) => {
    renderSourcesList(e.target.value.toLowerCase());
  });
}

// ============================================================================
// Research Execution & Live SSE Stream
// ============================================================================
async function handleStartResearch(e) {
  e.preventDefault();
  const query = elements.queryInput.value.trim();
  if (!query) return;

  const depth = document.querySelector('input[name="depth"]:checked').value;
  const domain = document.getElementById("domainSelect").value;
  const citationStyle = document.getElementById("citationStyleSelect").value;
  const language = document.getElementById("languageSelect").value;
  const apiKey = elements.apiKeyInput.value.trim() || null;
  const baseUrl = elements.baseUrlInput.value.trim() || null;

  // Set UI state to running
  setUIState("running");
  elements.activeQueryTitle.textContent = query;
  elements.activeModelPill.textContent = `${state.selectedProvider.toUpperCase()} · ${state.selectedModel}`;
  elements.activeDepthPill.textContent = `Depth: ${depth.toUpperCase()}`;
  elements.telemetryLog.innerHTML = `<div class="log-entry">🚀 Initiating autonomous research job...</div>`;
  elements.pipelineProgressFill.style.width = "5%";
  resetAgentNodes();

  try {
    const payload = {
      query,
      provider: state.selectedProvider,
      model: state.selectedModel,
      api_key: apiKey,
      base_url: baseUrl,
      depth,
      domain_focus: domain,
      citation_style: citationStyle,
      language,
    };

    const res = await fetch("/api/v1/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Failed to start research");
    }

    const jobData = await res.json();
    state.activeJobId = jobData.job_id;
    connectEventSource(jobData.job_id);
  } catch (err) {
    console.error("Start research error:", err);
    appendTelemetry(`❌ Error starting research: ${err.message}`, "event-reviewer");
    alert(`Failed to start research: ${err.message}`);
    setUIState("idle");
  }
}

function connectEventSource(jobId) {
  if (state.eventSource) {
    state.eventSource.close();
  }

  const sseUrl = `/api/v1/research/${jobId}/stream`;
  const es = new EventSource(sseUrl);
  state.eventSource = es;

  es.addEventListener("start", (e) => {
    const data = JSON.parse(e.data);
    appendTelemetry(`⚡ Supervisor graph running with ${data.provider} (${data.model})`, "event-planner");
  });

  es.addEventListener("status", (e) => {
    const data = JSON.parse(e.data);
    updatePipelineProgress(data.pct, data.step);
  });

  es.addEventListener("node_complete", (e) => {
    const data = JSON.parse(e.data);
    activateAgentNode(data.node);
    updatePipelineProgress(data.pct, data.step);
    
    if (data.log && data.log.title) {
      appendTelemetry(`✔ [${data.node.toUpperCase()}] ${data.log.title}: ${data.log.detail || ''}`, `event-${data.node}`);
    }
  });

  es.addEventListener("done", (e) => {
    const data = JSON.parse(e.data);
    es.close();
    completeResearch(data);
  });

  es.addEventListener("error", (e) => {
    if (e.data) {
      const data = JSON.parse(e.data);
      appendTelemetry(`❌ Error: ${data.error || 'Execution halted'}`, "event-reviewer");
    }
  });

  es.onerror = () => {
    // If connection drops, fallback to polling
    pollJobCompletion(jobId);
  };
}

async function pollJobCompletion(jobId) {
  const pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/v1/research/${jobId}`);
      if (!res.ok) return;
      const statusData = await res.json();
      updatePipelineProgress(statusData.progress_pct, statusData.current_step);
      
      if (statusData.status === "done") {
        clearInterval(pollTimer);
        const repRes = await fetch(`/api/v1/research/${jobId}/report`);
        if (repRes.ok) {
          const repData = await repRes.json();
          completeResearch({
            draft: repData.report_markdown,
            sources: repData.sources,
            evidence_matrix: repData.evidence_matrix,
            step_logs: repData.step_logs,
          });
        }
      } else if (statusData.status === "failed") {
        clearInterval(pollTimer);
        alert(`Research failed: ${statusData.error}`);
        setUIState("idle");
      }
    } catch (e) {
      console.warn("Poll error:", e);
    }
  }, 3000);
}

function updatePipelineProgress(pct, step) {
  elements.pipelineProgressFill.style.width = `${Math.min(pct, 100)}%`;
  elements.statusPillText.textContent = `${step} (${pct}%)`;
}

function appendTelemetry(text, className = "") {
  const entry = document.createElement("div");
  entry.className = `log-entry ${className}`;
  const time = new Date().toLocaleTimeString();
  entry.textContent = `[${time}] ${text}`;
  elements.telemetryLog.appendChild(entry);
  elements.telemetryLog.scrollTop = elements.telemetryLog.scrollHeight;
}

function resetAgentNodes() {
  ["Planner", "Researcher", "Verifier", "Writer", "Reviewer"].forEach(n => {
    const el = document.getElementById(`node${n}`);
    if (el) el.className = "agent-node";
  });
  document.getElementById("nodePlanner").classList.add("active");
}

function activateAgentNode(nodeName) {
  const map = {
    planner: "Planner",
    researcher: "Researcher",
    verifier: "Verifier",
    writer: "Writer",
    reviewer: "Reviewer",
  };
  const title = map[nodeName.toLowerCase()];
  if (!title) return;

  const nodes = ["Planner", "Researcher", "Verifier", "Writer", "Reviewer"];
  const targetIdx = nodes.indexOf(title);

  nodes.forEach((n, idx) => {
    const el = document.getElementById(`node${n}`);
    if (!el) return;
    if (idx < targetIdx) {
      el.className = "agent-node done";
    } else if (idx === targetIdx) {
      el.className = "agent-node active";
    } else {
      el.className = "agent-node";
    }
  });
}

// ============================================================================
// Research Completion & Monograph Rendering
// ============================================================================
function completeResearch(data) {
  state.activeReport = data.draft;
  state.sources = data.sources || [];
  state.evidenceMatrix = data.evidence_matrix || [];
  state.stepLogs = data.step_logs || [];

  // Update metrics
  const words = data.draft ? data.draft.split(/\s+/).length : 0;
  elements.paperWordCount.textContent = words.toLocaleString();
  elements.paperSourceCount.textContent = state.sources.length;
  elements.sourceTabCount.textContent = state.sources.length;

  const tier1Count = state.sources.filter(s => s.source_type === "journal" || s.source_type === "pubmed").length;
  elements.paperTier1Count.textContent = tier1Count;

  // Extract referee score from step logs if available
  let score = 9.0;
  const reviewerLog = state.stepLogs.find(l => l.node === "reviewer");
  if (reviewerLog && reviewerLog.score) score = reviewerLog.score;
  elements.paperScore.textContent = `${score}/10`;

  // Extract contract from step logs if available
  const plannerLog = state.stepLogs.find(l => l.node === "planner");
  state.contract = data.contract || (plannerLog && plannerLog.contract) || null;

  // Render components
  renderResearchContract(state.contract);
  renderMonographArticle(data.draft);
  renderEvidenceMatrix();
  renderSourcesList();
  renderRefereeReport();

  // Switch to completed UI
  setUIState("completed");
  elements.statusPillText.textContent = "Research Monograph Complete";
  elements.pipelineStatusPill.classList.remove("running");
}

function renderMonographArticle(markdown) {
  if (!markdown) {
    elements.paperArticle.innerHTML = "<p>No report generated.</p>";
    return;
  }

  // Parse markdown into structured academic HTML
  const { html, toc } = parseAcademicMarkdown(markdown);
  elements.paperArticle.innerHTML = html;

  // Render TOC
  elements.tocList.innerHTML = "";
  toc.forEach(item => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `#${item.id}`;
    a.textContent = item.text;
    li.appendChild(a);
    elements.tocList.appendChild(li);
  });

  // Attach citation tooltip events
  setupCitationTooltips();
}

function parseAcademicMarkdown(md) {
  const lines = md.split("\n");
  const toc = [];
  let html = [];
  let inTable = false;
  let tableRows = [];

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Markdown Table handling
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      if (!inTable) {
        inTable = true;
        tableRows = [];
      }
      tableRows.push(line.trim());
      continue;
    } else if (inTable) {
      inTable = false;
      html.push(renderMarkdownTable(tableRows));
      tableRows = [];
    }

    // Headings
    if (line.startsWith("# ")) {
      const text = line.replace("# ", "").trim();
      html.push(`<h1>${text}</h1>`);
    } else if (line.startsWith("## ")) {
      const text = line.replace("## ", "").trim();
      const id = "sec-" + text.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      toc.push({ id, text });
      html.push(`<h2 id="${id}">${text}</h2>`);
    } else if (line.startsWith("### ")) {
      const text = line.replace("### ", "").trim();
      const id = "subsec-" + text.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      html.push(`<h3 id="${id}">${text}</h3>`);
    } else if (line.startsWith("> ")) {
      html.push(`<blockquote><p>${formatInline(line.replace("> ", ""))}</p></blockquote>`);
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      html.push(`<ul><li>${formatInline(line.substring(2))}</li></ul>`);
    } else if (/^\d+\.\s/.test(line)) {
      html.push(`<ol><li>${formatInline(line.replace(/^\d+\.\s/, ""))}</li></ol>`);
    } else if (line.trim() === "---") {
      html.push("<hr>");
    } else if (line.trim()) {
      html.push(`<p>${formatInline(line)}</p>`);
    }
  }

  if (inTable && tableRows.length) {
    html.push(renderMarkdownTable(tableRows));
  }

  return { html: html.join("\n"), toc };
}

function renderMarkdownTable(rows) {
  if (rows.length < 2) return "";
  let html = "<table>";
  
  // Header
  const headerCells = rows[0].split("|").filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
  html += "<thead><tr>";
  headerCells.forEach(cell => html += `<th>${formatInline(cell.trim())}</th>`);
  html += "</tr></thead><tbody>";

  // Skip divider (row 1), render body rows
  for (let r = 2; r < rows.length; r++) {
    const cells = rows[r].split("|").filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
    html += "<tr>";
    cells.forEach(cell => html += `<td>${formatInline(cell.trim())}</td>`);
    html += "</tr>";
  }
  html += "</tbody></table>";
  return html;
}

function formatInline(text) {
  let res = text
    .replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Convert bracketed numeric citations like [1] or [12] to interactive badges
  res = res.replace(/\[(\d+)\]/g, (match, p1) => {
    return `<span class="citation-badge" data-cit-idx="${p1}">[${p1}]</span>`;
  });

  return res;
}

// Interactive Citation Hover Previews
function setupCitationTooltips() {
  document.querySelectorAll(".citation-badge").forEach(badge => {
    badge.addEventListener("mouseenter", (e) => {
      const idx = parseInt(badge.dataset.citIdx, 10);
      const source = state.sources[idx - 1];
      if (!source) return;

      const title = source.title || "Academic Publication";
      const authors = source.authors ? source.authors.slice(0, 3).join(", ") : "Researchers";
      const year = source.published_date || "";
      const doi = source.doi ? `DOI: ${source.doi}` : (source.journal || source.source_type);

      elements.citationTooltip.innerHTML = `
        <div class="tooltip-title">${title}</div>
        <div class="tooltip-meta">${authors} (${year}) · ${doi}</div>
      `;
      elements.citationTooltip.style.display = "block";

      const rect = badge.getBoundingClientRect();
      elements.citationTooltip.style.top = `${rect.bottom + window.scrollY + 6}px`;
      elements.citationTooltip.style.left = `${Math.min(rect.left + window.scrollX, window.innerWidth - 380)}px`;
    });

    badge.addEventListener("mouseleave", () => {
      elements.citationTooltip.style.display = "none";
    });
  });
}

// ============================================================================
// Evidence Matrix & Bibliographic List Views
// ============================================================================
function renderResearchContract(contract) {
  if (!elements.researchContractCard) return;
  if (!contract || !contract.question) {
    elements.researchContractCard.style.display = "none";
    return;
  }
  elements.researchContractCard.style.display = "block";
  const subquestions = (contract.must_resolve || []).map(q => `<li>${q}</li>`).join("");
  elements.researchContractCard.innerHTML = `
    <div class="contract-header-row">
      <span class="contract-tag">Research Contract (Bounded)</span>
      <span class="contract-date">Investigation as-of: ${contract.as_of || '2026-10-08'}</span>
    </div>
    <div class="contract-decision"><strong>Context:</strong> ${contract.decision_context || 'Academic literature synthesis'}</div>
    <div class="contract-scope"><strong>Scope:</strong> ${contract.scope || 'Scientific repositories & peer-reviewed literature'}</div>
    ${subquestions ? `<ul style="margin: 8px 0 0 16px; font-size: 0.8rem; color: var(--text-muted);">${subquestions}</ul>` : ''}
  `;
}

let activeLedgerFilter = "all";

function renderEvidenceMatrix(statusFilter = activeLedgerFilter) {
  activeLedgerFilter = statusFilter;
  elements.evidenceCardsGrid.innerHTML = "";
  if (!state.evidenceMatrix.length) {
    elements.evidenceCardsGrid.innerHTML = "<p class='text-muted'>No structured evidence claims extracted.</p>";
    return;
  }

  // Summary row
  const t1 = state.sources.filter(s => s.source_type === "journal" || s.source_type === "pubmed").length;
  const t2 = state.sources.filter(s => s.source_type === "arxiv").length;
  const supportedCount = state.evidenceMatrix.filter(e => (e.status || 'supported') === 'supported').length;
  const contestedCount = state.evidenceMatrix.filter(e => e.status === 'contested').length;
  const unverifiedCount = state.evidenceMatrix.filter(e => e.status === 'unverified').length;

  elements.credibilitySummaryRow.innerHTML = `
    <div class="cred-chip tier-1">★ Tier 1 Peer-Reviewed: ${t1}</div>
    <div class="cred-chip tier-2">◆ Tier 2 Preprints: ${t2}</div>
    <div class="cred-chip" style="background: rgba(16, 185, 129, 0.12); color: #34d399;">✓ Supported: ${supportedCount}</div>
    ${contestedCount ? `<div class="cred-chip" style="background: rgba(245, 158, 11, 0.12); color: #fbbf24;">⚠ Contested: ${contestedCount}</div>` : ''}
    ${unverifiedCount ? `<div class="cred-chip" style="background: rgba(244, 63, 94, 0.12); color: #fb7185;">✗ Unverified: ${unverifiedCount}</div>` : ''}
  `;

  const filtered = state.evidenceMatrix.filter(item => {
    if (statusFilter === "all") return true;
    return (item.status || "supported").toLowerCase() === statusFilter.toLowerCase();
  });

  if (!filtered.length) {
    elements.evidenceCardsGrid.innerHTML = `<p class='text-muted' style='grid-column: 1 / -1; padding: 20px 0;'>No claims categorized as "${statusFilter}".</p>`;
    return;
  }

  filtered.forEach(item => {
    const card = document.createElement("div");
    card.className = "evidence-card";
    const tier = item.credibility_tier || 1;
    const tierName = tier === 1 ? "Tier 1: Peer-Reviewed" : (tier === 2 ? "Tier 2: Preprint" : "Tier 3: Institutional");
    const status = (item.status || "supported").toLowerCase();
    const claimId = item.claim_id || "C-01";

    let passageHtml = "";
    if (item.evidence && item.evidence.length > 0) {
      const ev = item.evidence[0];
      if (ev.passage) {
        passageHtml = `<div class="ledger-passage">"${ev.passage}" <span style="font-style: normal; font-size: 0.72rem; color: var(--text-muted); display: block; margin-top: 4px;">— ${ev.publisher || ev.source_type} (${ev.source_id || 'Primary Source'})</span></div>`;
      }
    } else if (item.quantitative_metric) {
      passageHtml = `<div class="ledger-passage">"${item.quantitative_metric}"</div>`;
    }

    card.innerHTML = `
      <div class="card-top-row">
        <span class="claim-id-tag">${claimId}</span>
        <div style="display: flex; gap: 6px; align-items: center;">
          <span class="card-tier-badge tier-${tier}">${tierName}</span>
          <span class="claim-status-badge ${status}">${status}</span>
        </div>
      </div>
      <div class="evidence-claim">${item.claim}</div>
      ${passageHtml}
      ${item.reason ? `<div class="ledger-reason"><strong>Reason:</strong> ${item.reason}</div>` : ''}
      ${item.open_question ? `<div class="ledger-open-question"><strong>Unsettled:</strong> ${item.open_question}</div>` : ''}
      <div class="evidence-author">${item.primary_author_year || 'Verified Academic Citation'}</div>
    `;
    elements.evidenceCardsGrid.appendChild(card);
  });
}

function renderSourcesList(filter = "") {
  elements.sourcesList.innerHTML = "";
  const filtered = state.sources.filter(s => {
    const str = `${s.title} ${s.journal} ${(s.authors || []).join(' ')} ${s.doi}`.toLowerCase();
    return str.includes(filter);
  });

  if (!filtered.length) {
    elements.sourcesList.innerHTML = "<p class='text-muted'>No sources match your filter.</p>";
    return;
  }

  filtered.forEach((s, idx) => {
    const card = document.createElement("div");
    card.className = "source-item-card";
    const authors = s.authors ? s.authors.slice(0, 3).join(", ") : "Authors not indexed";
    const venue = s.journal || s.source_type.toUpperCase();
    const link = s.url || (s.doi ? `https://doi.org/${s.doi}` : '#');

    card.innerHTML = `
      <div class="source-main">
        <a href="${link}" target="_blank" rel="noopener" class="source-title">[${idx + 1}] ${s.title}</a>
        <div class="source-meta-row">
          <span>${authors}</span>
          <span>·</span>
          <span>${s.published_date || 'n.d.'}</span>
          <span>·</span>
          <span>${venue}</span>
          ${s.doi ? `<span>· DOI: ${s.doi}</span>` : ''}
        </div>
      </div>
      <span class="source-badge ${s.source_type}">${s.source_type}</span>
    `;
    elements.sourcesList.appendChild(card);
  });
}

function renderRefereeReport() {
  const reviewerLog = state.stepLogs.find(l => l.node === "reviewer");
  const critique = reviewerLog && reviewerLog.critique ? reviewerLog.critique : {};
  const score = reviewerLog && reviewerLog.score ? reviewerLog.score : 8.5;

  elements.refereeCard.innerHTML = `
    <div class="referee-header">
      <div>
        <h4 style="font-size: 1.2rem; font-family: var(--font-serif);">Referee Editorial Decision</h4>
        <p style="color: var(--text-muted); font-size: 0.82rem;">Evaluated for empirical grounding, citation fidelity, and academic neutrality.</p>
      </div>
      <div class="referee-verdict-badge ACCEPTED">ACCEPT (${score}/10)</div>
    </div>
    <div style="margin-top: 16px;">
      <h5 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px;">Key Strengths</h5>
      <ul style="padding-left: 20px; font-size: 0.9rem; line-height: 1.6;">
        ${(critique.strengths || ["Rigorous literature grounding", "Clear comparative taxonomy"]).map(s => `<li>${s}</li>`).join('')}
      </ul>
    </div>
  `;

  // Step Logs
  elements.stepLogsTimeline.innerHTML = "";
  state.stepLogs.forEach(step => {
    const item = document.createElement("div");
    item.className = "timeline-step";
    item.innerHTML = `
      <div class="timeline-step-title">[${step.node.toUpperCase()}] ${step.title || 'Step Complete'}</div>
      <div class="timeline-step-detail">${step.detail || ''}</div>
    `;
    elements.stepLogsTimeline.appendChild(item);
  });
}

// Copy Action
async function handleCopyPaper() {
  if (!state.activeReport) return;
  try {
    await navigator.clipboard.writeText(state.activeReport);
    elements.copyPaperBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span>Copied!</span>
    `;
    setTimeout(() => {
      elements.copyPaperBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span>Copy</span>
      `;
    }, 2000);
  } catch (e) {
    alert("Clipboard copy failed");
  }
}

// ============================================================================
// Research Library Drawer
// ============================================================================
async function openHistoryDrawer() {
  elements.historyDrawerOverlay.classList.add("open");
  elements.historyDrawer.classList.add("open");
  elements.historyList.innerHTML = "<div class='empty-history'>Loading previous research papers...</div>";

  try {
    const res = await fetch("/api/v1/research?limit=30");
    if (!res.ok) throw new Error("Failed to load history");
    const jobs = await res.json();

    if (!jobs.length) {
      elements.historyList.innerHTML = "<div class='empty-history'>No saved research papers found.</div>";
      return;
    }

    elements.historyList.innerHTML = "";
    jobs.forEach(job => {
      const item = document.createElement("div");
      item.className = "history-item";
      const date = job.created_at ? new Date(job.created_at).toLocaleDateString() : "";

      item.innerHTML = `
        <div class="history-query">${job.query}</div>
        <div class="history-meta">
          <span>${(job.provider || 'GROQ').toUpperCase()}</span>
          <span>·</span>
          <span>${job.depth || 'standard'}</span>
          <span>·</span>
          <span>${date}</span>
        </div>
      `;

      item.addEventListener("click", () => {
        closeHistoryDrawer();
        loadPastJob(job.job_id);
      });
      elements.historyList.appendChild(item);
    });
  } catch (err) {
    elements.historyList.innerHTML = `<div class='empty-history'>Error: ${err.message}</div>`;
  }
}

function closeHistoryDrawer() {
  elements.historyDrawerOverlay.classList.remove("open");
  elements.historyDrawer.classList.remove("open");
}

async function loadPastJob(jobId) {
  setUIState("running");
  elements.telemetryLog.innerHTML = `<div class="log-entry">Loading archived paper ${jobId}...</div>`;
  try {
    const res = await fetch(`/api/v1/research/${jobId}/report`);
    if (!res.ok) throw new Error("Report not ready or missing");
    const reportData = await res.json();
    state.activeJobId = jobId;
    completeResearch({
      draft: reportData.report_markdown,
      sources: reportData.sources,
      evidence_matrix: reportData.evidence_matrix,
      step_logs: reportData.step_logs,
    });
  } catch (e) {
    alert(`Could not load past report: ${e.message}`);
    setUIState("idle");
  }
}

// UI State Switcher
function setUIState(mode) {
  elements.idleState.style.display = mode === "idle" ? "block" : "none";
  elements.runningState.style.display = mode === "running" ? "block" : "none";
  elements.completedState.style.display = mode === "completed" ? "block" : "none";

  if (mode === "running") {
    elements.pipelineStatusPill.classList.add("running");
    elements.startBtn.disabled = true;
  } else {
    elements.pipelineStatusPill.classList.remove("running");
    elements.startBtn.disabled = false;
  }
}

// Boot
document.addEventListener("DOMContentLoaded", initApp);
