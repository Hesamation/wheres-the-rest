/**
 * Payout Reader — Cross-Chain Audit Workbench Frontend Controller
 * Vanilla ES2022+ JavaScript, zero external runtime dependencies.
 */

let currentReport = null;
let savedExamplesCache = [];
let activeExampleId = "qa1";
let activeMode = "saved";
let isInputsDirty = false;

document.addEventListener("DOMContentLoaded", () => {
  initModeTabs();
  initLiveForm();
  initExportButtons();
  initStaleControls();
  initKeyboardNavigation();
  loadSavedExamplesAndPreloadQA1();
});

// 1. Mode Switching (Saved vs Live)
function initModeTabs() {
  const tabSaved = document.getElementById("tab-saved");
  const tabLive = document.getElementById("tab-live");
  const savedPanel = document.getElementById("saved-controls-panel");
  const livePanel = document.getElementById("live-form-panel");

  tabSaved.addEventListener("click", () => {
    if (activeMode === "saved") return;
    activeMode = "saved";
    tabSaved.classList.add("active");
    tabSaved.setAttribute("aria-selected", "true");
    tabLive.classList.remove("active");
    tabLive.setAttribute("aria-selected", "false");

    savedPanel.style.display = "flex";
    livePanel.style.display = "none";
    clearError();

    // Check if displayed report matches active saved example
    checkStaleStatus();
  });

  tabLive.addEventListener("click", () => {
    if (activeMode === "live") return;
    activeMode = "live";
    tabLive.classList.add("active");
    tabLive.setAttribute("aria-selected", "true");
    tabSaved.classList.remove("active");
    tabSaved.setAttribute("aria-selected", "false");

    savedPanel.style.display = "none";
    livePanel.style.display = "block";
    clearError();

    // Check if displayed report is stale
    checkStaleStatus();
  });
}

// 2. Load Saved Examples & Preload QA1 (with URL Deep-Linking)
async function loadSavedExamplesAndPreloadQA1() {
  try {
    const res = await fetch("/api/examples");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    savedExamplesCache = await res.json();
    renderExamplePills(savedExamplesCache);

    // Deep-linking via query parameters: ?example=qa1 or ?tx=...&signer=...
    const urlParams = new URLSearchParams(window.location.search);
    const exampleParam = urlParams.get("example");
    const txParam = urlParams.get("tx");
    const signerParam = urlParams.get("signer");

    if (exampleParam && savedExamplesCache.some((ex) => ex.id === exampleParam)) {
      activeExampleId = exampleParam;
      highlightActivePill(activeExampleId);
      await runReconciliation({ mode: "saved", exampleId: exampleParam });
    } else if (txParam && signerParam) {
      const tabLive = document.getElementById("tab-live");
      if (tabLive) tabLive.click();
      document.getElementById("live-tx").value = txParam;
      document.getElementById("live-signer").value = signerParam;
      await runReconciliation({ mode: "live", txHash: txParam, signerId: signerParam });
    } else {
      // Preload QA1 immediately on first load
      await runReconciliation({ mode: "saved", exampleId: "qa1" });
    }
  } catch (err) {
    showError(`Failed to load saved examples: ${err.message}`);
  }
}

function highlightActivePill(exampleId) {
  document.querySelectorAll(".case-pill").forEach((p) => {
    const isActive = p.dataset.exampleId === exampleId;
    p.classList.toggle("active", isActive);
    p.setAttribute("aria-checked", isActive ? "true" : "false");
  });
}

function renderExamplePills(examples) {
  const container = document.getElementById("example-pills-container");
  container.innerHTML = "";

  const labels = {
    qa1: "QA1: Group Deficit (3 × 0.01)",
    qa2: "QA2: Mixed Delivery (0.19 / 0.20)",
    prod_control: "Control: 1.00 USDC",
  };

  examples.forEach((ex) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `case-pill ${ex.id === activeExampleId ? "active" : ""}`;
    btn.dataset.exampleId = ex.id;
    btn.setAttribute("role", "radio");
    btn.setAttribute("aria-checked", ex.id === activeExampleId ? "true" : "false");
    btn.textContent = labels[ex.id] || ex.label;
    btn.title = ex.summary;

    btn.addEventListener("click", () => {
      if (activeExampleId === ex.id && currentReport?.request?.exampleId === ex.id) return;
      activeExampleId = ex.id;
      highlightActivePill(ex.id);
      runReconciliation({ mode: "saved", exampleId: ex.id });
    });

    container.appendChild(btn);
  });
}

// 3. Live Form Handling & Dirty State
function initLiveForm() {
  const form = document.getElementById("live-form-panel");
  const txInput = document.getElementById("live-tx");
  const signerInput = document.getElementById("live-signer");

  const markDirty = () => {
    isInputsDirty = true;
    checkStaleStatus();
  };

  txInput.addEventListener("input", markDirty);
  signerInput.addEventListener("input", markDirty);

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    clearError();

    const txHash = txInput.value.trim();
    const signerId = signerInput.value.trim();

    if (!txHash) {
      showError("Please enter a NEAR transaction hash.");
      txInput.focus();
      return;
    }
    if (!signerId) {
      showError("Please enter a NEAR signer account ID.");
      signerInput.focus();
      return;
    }

    runReconciliation({ mode: "live", txHash, signerId });
  });
}

function initStaleControls() {
  const btnReReconcile = document.getElementById("btn-re-reconcile");
  const btnDismissStale = document.getElementById("btn-dismiss-stale");

  btnReReconcile.addEventListener("click", () => {
    if (activeMode === "saved") {
      runReconciliation({ mode: "saved", exampleId: activeExampleId });
    } else {
      const form = document.getElementById("live-form-panel");
      form.requestSubmit();
    }
  });

  btnDismissStale.addEventListener("click", () => {
    document.getElementById("stale-banner").style.display = "none";
  });
}

function checkStaleStatus() {
  if (!currentReport) return;
  const req = currentReport.request || {};
  let isStale = false;

  if (activeMode !== req.mode) {
    isStale = true;
  } else if (activeMode === "saved" && activeExampleId !== req.exampleId) {
    isStale = true;
  } else if (activeMode === "live") {
    const tx = document.getElementById("live-tx").value.trim();
    const signer = document.getElementById("live-signer").value.trim();
    if (tx !== req.txHash || signer !== req.signerId) {
      isStale = true;
    }
  }

  if (isStale) {
    showStaleBanner();
  } else {
    hideStaleBanner();
  }
}

function showStaleBanner() {
  const banner = document.getElementById("stale-banner");
  const body = document.getElementById("workbench-body");
  banner.style.display = "flex";
  body.classList.add("stale");
}

function hideStaleBanner() {
  const banner = document.getElementById("stale-banner");
  const body = document.getElementById("workbench-body");
  banner.style.display = "none";
  body.classList.remove("stale");
}

// 4. Export Buttons: JSON, CSV, Copy Proof
function initExportButtons() {
  // 4a. Download JSON Report
  const jsonBtn = document.getElementById("btn-download-json");
  if (jsonBtn) {
    jsonBtn.addEventListener("click", () => {
      if (!currentReport) return;
      const jsonStr = JSON.stringify(currentReport, null, 2);
      downloadBlob(jsonStr, "application/json", `payout-audit-${getReportFileSlug()}.json`);
    });
  }

  // 4b. Download CSV Report
  const csvBtn = document.getElementById("btn-download-csv");
  if (csvBtn) {
    csvBtn.addEventListener("click", () => {
      if (!currentReport) return;
      const csvStr = generateCsvReport(currentReport);
      downloadBlob(csvStr, "text/csv;charset=utf-8;", `payout-audit-${getReportFileSlug()}.csv`);
    });
  }

  // 4c. Copy Markdown Audit Proof
  const copyBtn = document.getElementById("btn-copy-proof");
  const copyLabel = document.getElementById("copy-proof-label");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      if (!currentReport) return;
      const markdownProof = generateMarkdownProof(currentReport);
      try {
        await navigator.clipboard.writeText(markdownProof);
        if (copyLabel) copyLabel.textContent = "✓ Copied!";
        setTimeout(() => {
          if (copyLabel) copyLabel.textContent = "Copy Proof";
        }, 2500);
      } catch (err) {
        console.error("Clipboard copy failed", err);
      }
    });
  }
}

function getReportFileSlug() {
  const mode = currentReport?.request?.mode || "report";
  const ex = currentReport?.request?.exampleId;
  const tx = (currentReport?.request?.txHash || "tx").slice(0, 10);
  return ex ? `${mode}-${ex}` : `${mode}-${tx}`;
}

function downloadBlob(content, mimeType, filename) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function generateCsvReport(envelope) {
  const headers = [
    "row_indices",
    "row_type",
    "recipient",
    "gross_usdc",
    "fee_usdc",
    "net_usdc",
    "verdict",
    "near_tx",
    "base_tx",
    "base_block",
    "note",
  ];
  const lines = [headers.join(",")];
  const reqTx = envelope.request?.txHash || "";

  for (const r of envelope.rows || []) {
    const rowIndices = (r.rowIndices || []).join(",");
    const rowType = r.kind || "";
    const recipient = r.recipient || "";
    const amts = r.amounts || {};
    const gross = amts.grossFormatted || "";
    const fee = amts.feeFormatted || "";
    const net = amts.netFormatted || "";
    const verdict = r.verdict || "";
    const ev = r.evidence || {};
    const destTx = ev.destTransfer?.transferTxHash || ev.bridgeRecord?.transferTxHash || "";
    const destBlock = ev.destTransfer?.block || "";
    const note = (r.note || "").replace(/"/g, '""');

    const row = [
      `"${rowIndices}"`,
      `"${rowType}"`,
      `"${recipient}"`,
      gross,
      fee,
      net,
      `"${verdict}"`,
      `"${reqTx}"`,
      `"${destTx}"`,
      destBlock,
      `"${note}"`,
    ];
    lines.push(row.join(","));
  }
  return lines.join("\r\n");
}

function generateMarkdownProof(envelope) {
  const req = envelope.request || {};
  const summary = envelope.summary || {};
  const prov = envelope.provenance || {};
  const rows = envelope.rows || [];

  const txHash = req.txHash || "-";
  const signer = req.signerId || "-";
  const overall = summary.overall || "UNKNOWN";
  const overallCode = summary.overallCode || "UNKNOWN";
  const captured = prov.capturedAt || "-";
  const shaRaw = prov.readerSha256 || "";
  const readerSha = shaRaw ? `${shaRaw.slice(0, 16)}...` : "-";

  const lines = [
    "### NEAR USDC Cross-Chain Payout Audit Proof",
    `- **Transaction**: \`${txHash}\``,
    `- **Signer**: \`${signer}\``,
    `- **Audit Status**: **${overallCode}** (${overall})`,
    "- **Route**: `base-0x8335...omft.near` → Base USDC (`eth:8453`)",
    `- **Evidence Timestamp**: ${captured}`,
    `- **Auditor**: Payout Reader (SHA-256 \`${readerSha}\`)`,
    "",
    "| Row(s) | Recipient | Gross/burn (USDC) | Observed fees (USDC) | Observed net (USDC) | Verdict | Base Tx |",
    "|---|---|---|---|---|---|---|",
  ];

  for (const r of rows) {
    const indices = (r.rowIndices || []).join(",");
    let recip = r.recipient || "-";
    if (recip.length > 12) {
      recip = `\`${recip.slice(0, 6)}...${recip.slice(-4)}\``;
    }
    const amts = r.amounts || {};
    const gross = amts.grossFormatted || "-";
    const fee = amts.feeFormatted || "-";
    const net = amts.netFormatted || "-";
    const verdict = r.verdict || "-";
    const ev = r.evidence || {};
    const destTx = ev.destTransfer?.transferTxHash || ev.bridgeRecord?.transferTxHash;
    const destLink = destTx ? `[\`${destTx.slice(0, 8)}...\`](https://basescan.org/tx/${destTx})` : "-";
    lines.push(`| ${indices} | ${recip} | ${gross} | ${fee} | ${net} | ${verdict} | ${destLink} |`);
  }

  lines.push("");
  for (const r of rows) {
    if (r.groupDetails) {
      lines.push(`Group [${(r.rowIndices || []).join(",")}]: ${r.groupDetails.observed} observed; ${r.groupDetails.unrecorded} unrecorded. Source-burn attribution remains ambiguous.`);
    }
  }
  lines.push(`Evidence mode: ${req.mode || "unknown"}. Amounts are provider observations; “proof” is not a cryptographic proof.`);
  lines.push("> **Conservative Evidence Disclaimer**: Missing observations are ambiguous, not proof of permanent loss. OBSERVED_MATCH represents receipt-level provider evidence with block confirmations, not final settlement.");
  return lines.join("\n");
}

// 5. Run Reconciliation API
async function runReconciliation(payload) {
  clearError();
  hideStaleBanner();
  setLoading(true, payload.mode);

  try {
    const res = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }

    currentReport = data;
    isInputsDirty = false;

    // Sync URL query params with current reconciliation
    if (payload.mode === "saved" && payload.exampleId) {
      history.replaceState(null, "", `?example=${encodeURIComponent(payload.exampleId)}`);
    } else if (payload.mode === "live" && payload.txHash && payload.signerId) {
      history.replaceState(
        null,
        "",
        `?tx=${encodeURIComponent(payload.txHash)}&signer=${encodeURIComponent(payload.signerId)}`
      );
    }

    renderReport(data);
    checkStaleStatus();
  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

function setLoading(isLoading, mode = "saved") {
  const loadingBar = document.getElementById("loading-state");
  const submitBtn = document.getElementById("btn-submit-live");
  const pills = document.querySelectorAll(".case-pill");
  const loadingTitle = document.getElementById("loading-title");
  const loadingDesc = document.getElementById("loading-desc");

  if (isLoading) {
    loadingBar.style.display = "flex";
    if (mode === "live") {
      loadingTitle.textContent = "Querying Live Network RPCs...";
      loadingDesc.textContent = "Fetching NEAR outcomes, Chaindefuser bridge logs, and Base USDC receipts...";
    } else {
      loadingTitle.textContent = "Loading Saved Audit Evidence...";
      loadingDesc.textContent = "Verifying offline evidence graph and receipts against reader invariants...";
    }
    if (submitBtn) submitBtn.disabled = true;
    pills.forEach((p) => (p.disabled = true));
  } else {
    loadingBar.style.display = "none";
    if (submitBtn) submitBtn.disabled = false;
    pills.forEach((p) => (p.disabled = false));
  }
}

function showError(msg) {
  const banner = document.getElementById("error-banner");
  const msgSpan = document.getElementById("error-message");
  msgSpan.textContent = msg;
  banner.style.display = "flex";
  document.getElementById("btn-clear-error").onclick = clearError;
}

function clearError() {
  const banner = document.getElementById("error-banner");
  banner.style.display = "none";
}

// 6. Report Rendering (Carbon Workbench)
function renderReport(report) {
  const req = report.request || {};
  const prov = report.provenance || {};
  const summary = report.summary || {};
  const counts = report.counts || {};
  const rows = report.rows || [];
  const normEv = report.normalizedEvidence || {};

  // A. Header Provenance Chip
  const chip = document.getElementById("provenance-chip");
  const chipDot = chip.querySelector(".chip-dot");
  const chipText = document.getElementById("provenance-chip-text");

  if (req.mode === "live") {
    chipDot.className = "chip-dot live";
    chipText.textContent = `Live Query: ${req.txHash?.slice(0, 8)}...`;
  } else {
    chipDot.className = "chip-dot";
    const caseLabels = {
      qa1: "Saved: QA1 (Ambiguous Deficit)",
      qa2: "Saved: QA2 (Mixed Delivery)",
      prod_control: "Saved: Prod Control (1.00 USDC)",
    };
    chipText.textContent = caseLabels[req.exampleId] || `Saved: ${req.exampleId}`;
  }

  // B. 5-Second Executive Outcome Card
  const outcomeCard = document.getElementById("outcome-card");
  const outcomeTag = document.getElementById("outcome-tag");
  const modeBadge = document.getElementById("outcome-mode-badge");
  const metaCaptured = document.getElementById("meta-captured");
  const outcomeTitle = document.getElementById("outcome-title");
  const outcomeDesc = document.getElementById("outcome-desc");

  const overallCode = summary.overallCode || "NEEDS_INSPECTION";
  metaCaptured.textContent = prov.capturedAt || prov.generatedAt || "-";

  // Mode badge
  if (req.mode === "live") {
    modeBadge.textContent = "Live Network Observation";
  } else {
    modeBadge.textContent = "Saved Provider Evidence";
  }

  // Monetary totals stay in atomic BigInt units, including grouped observations.
  const sumAmounts = (items, field) => items.reduce((sum, item) =>
    sum === null || item[field] == null ? null : sum + BigInt(item[field]), 0n);
  const totalGross = sumAmounts(normEv.sourceBurns || [], "amount");
  const totalBridgeGross = sumAmounts(normEv.bridgeWithdrawals || [], "amount");
  let totalObservedNet = 0n;
  let totalUnrecordedGross = 0n;

  let trueObservedCount = counts.observedMatches || 0;
  let trueUnrecordedCount = counts.unrecorded || 0;

  rows.forEach((r) => {
    const grossVal = r.amounts?.gross == null ? null : BigInt(r.amounts.gross);
    const observed = r.kind === "group"
      ? r.groupDetails?.observed || 0 : Number(r.verdict === "OBSERVED_MATCH");
    const unrecorded = r.kind === "group"
      ? r.groupDetails?.unrecorded || 0 : Number(r.verdict === "NOT_RECORDED");
    if (r.kind === "group") {
      trueObservedCount += observed;
      trueUnrecordedCount += unrecorded;
    }
    if (observed) {
      totalObservedNet = totalObservedNet === null || r.amounts?.net == null
        ? null : totalObservedNet + BigInt(r.amounts.net);
    }
    if (unrecorded) {
      totalUnrecordedGross = totalUnrecordedGross === null || grossVal === null
        ? null : totalUnrecordedGross + grossVal * BigInt(unrecorded);
    }
  });

  // Set card classes and headlines
  outcomeCard.className = "outcome-card";
  if (overallCode === "ALL_ROWS_OBSERVED") {
    outcomeCard.classList.add("verdict-all-observed");
    outcomeTag.className = "carbon-tag carbon-tag--green";
    outcomeTag.textContent = "ALL OBSERVED";
    outcomeTitle.textContent = "All Payments Observed on Base (Receipt-Level)";
    outcomeDesc.textContent = "Every intended token burn has a completed bridge withdrawal record and a verified Base USDC transfer receipt. Receipt-level provider evidence confirmed.";
  } else if (overallCode === "MISMATCH") {
    outcomeCard.classList.add("verdict-mismatch");
    outcomeTag.className = "carbon-tag carbon-tag--red";
    outcomeTag.textContent = "DELIVERY MISMATCH";

    if (req.exampleId === "qa1") {
      outcomeTitle.textContent = "3 Intended Payments — 1 Observed on Base, 2 Unrecorded";
      outcomeDesc.textContent = "Three identical 0.010000 USDC burns. One payment was delivered on Base (0.007600 USDC net after 0.002400 USDC fee). Two burns remain unrecorded on the bridge. All three burns name the same recipient. Which source burn corresponds to the observed transfer is ambiguous.";
    } else if (req.exampleId === "qa2") {
      outcomeTitle.textContent = "2 Intended Payments — 1 Observed on Base, 1 Unrecorded";
      outcomeDesc.textContent = "0.190000 USDC burn verified delivered on Base (0.187600 USDC net after 0.002400 USDC fee). 0.200000 USDC burn lacks an observed bridge withdrawal record.";
    } else {
      outcomeTitle.textContent = "Delivery Mismatch — Inspect the Findings";
      outcomeDesc.textContent = summary.overall || `${trueObservedCount} observed on Base, ${trueUnrecordedCount} unrecorded on bridge. Inspect each finding.`;
    }
  } else if (overallCode === "IN_PROGRESS") {
    outcomeCard.classList.add("verdict-inconclusive");
    outcomeTag.className = "carbon-tag carbon-tag--yellow";
    outcomeTag.textContent = "IN PROGRESS";
    outcomeTitle.textContent = "Reconciliation In Progress — Transactions Pending";
    outcomeDesc.textContent = "Source burns executed; bridge transfer or destination transaction is currently in flight.";
  } else {
    outcomeCard.classList.add("verdict-inconclusive");
    outcomeTag.className = "carbon-tag carbon-tag--yellow";
    outcomeTag.textContent = overallCode;
    outcomeTitle.textContent = summary.overall || "Audit Inconclusive";
    outcomeDesc.textContent = "Required provider leg unavailable or non-standard evidence encountered.";
  }

  // C. KPI Metrics Grid (Accurate calculations)
  document.getElementById("kpi-burns-count").textContent = counts.sourceBurns ?? 0;
  document.getElementById("kpi-burns-amt").textContent = formatUSDCFromMicro(totalGross);

  document.getElementById("kpi-bridge-count").textContent = counts.bridgeRecords ?? 0;
  document.getElementById("kpi-bridge-amt").textContent = formatUSDCFromMicro(totalBridgeGross);

  document.getElementById("kpi-observed-count").textContent = trueObservedCount;
  document.getElementById("kpi-observed-amt").textContent = formatUSDCFromMicro(totalObservedNet);

  document.getElementById("kpi-unrecorded-count").textContent = trueUnrecordedCount;
  document.getElementById("kpi-unrecorded-amt").textContent = formatUSDCFromMicro(totalUnrecordedGross);

  // D. Carbon Data Table: Withdrawal Leg Findings
  const tbody = document.getElementById("findings-tbody");
  tbody.innerHTML = "";
  document.getElementById("table-row-count").textContent = `${rows.length} ${rows.length === 1 ? "finding" : "findings"}`;

  if (rows.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="7" style="text-align: center; color: var(--cds-text-helper); padding: 24px;">No withdrawal rows or findings found in evidence.</td>`;
    tbody.appendChild(tr);
  } else {
    rows.forEach((r, idx) => {
      const amts = r.amounts || {};
      const grossStr = amts.grossFormatted ? `${amts.grossFormatted} USDC` : "-";
      const feeStr = amts.feeFormatted ? `${amts.feeFormatted} USDC` : "-";
      const netStr = amts.netFormatted ? `${amts.netFormatted} USDC` : "-";

      let rowLabel = `Row ${r.rowIndices?.join(", ")}`;
      if (r.kind === "group") {
        rowLabel = `Group [${r.rowIndices?.join(", ")}]`;
      } else if (r.kind === "unmatched_bridge") {
        rowLabel = "[Bridge Extra]";
      } else if (r.kind === "unmatched_dest") {
        rowLabel = "[Base Extra]";
      } else if (r.kind === "invalid_record") {
        rowLabel = "[Invalid Rec]";
      }

      const pillClass = getVerdictTagClass(r.verdict);
      const recipientText = r.recipient
        ? `<span class="monospace" title="${escapeHtml(r.recipient)}">${escapeHtml(truncateMiddle(r.recipient, 12, 10))}</span>`
        : '<span style="color:var(--cds-text-helper);">-</span>';

      // 1. Parent Data Row
      const parentTr = document.createElement("tr");
      parentTr.className = "parent-row";
      parentTr.setAttribute("aria-expanded", "false");
      parentTr.setAttribute("aria-controls", `detail-${idx}`);

      parentTr.innerHTML = `
        <td class="th-expand">
          <button type="button" class="expand-toggle" aria-expanded="false" aria-controls="detail-${idx}" aria-label="Toggle details for ${escapeHtml(rowLabel)}">
            <svg class="carbon-icon expand-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M6 3.7L7.4 2.3 13.1 8l-5.7 5.7L6 12.3 10.3 8z"/>
            </svg>
          </button>
        </td>
        <td class="th-row"><strong>${escapeHtml(rowLabel)}</strong></td>
        <td class="th-recipient">${recipientText}</td>
        <td class="th-num">${escapeHtml(grossStr)}</td>
        <td class="th-num" style="color: var(--cds-text-helper);">${escapeHtml(feeStr)}</td>
        <td class="th-num"><strong style="color: ${r.verdict === 'OBSERVED_MATCH' || (r.kind === 'group' && r.groupDetails?.observed > 0) ? 'var(--cds-support-success-text)' : 'inherit'};">${escapeHtml(netStr)}</strong></td>
        <td class="th-status"><span class="carbon-tag ${pillClass}">${escapeHtml(r.verdict)}</span></td>
      `;
      tbody.appendChild(parentTr);

      // 2. Expandable Child Row
      const detailTr = document.createElement("tr");
      detailTr.id = `detail-${idx}`;
      detailTr.className = "expandable-row";
      detailTr.style.display = "none";

      const ev = r.evidence || {};
      const burnEv = ev.sourceBurn;
      const groupBurns = ev.groupBurns;
      const observations = ev.observedTransfers || [];
      const bridgeEv = ev.bridgeRecord;
      const destEv = ev.destTransfer;

      // Source Leg content
      let sourceLegHtml = '<span style="color:var(--cds-text-helper)">No source burn record</span>';
      if (burnEv) {
        sourceLegHtml = `
          <strong>Outcome:</strong> <span class="monospace">${escapeHtml(burnEv.outcomeId || "-")}</span><br>
          <strong>Log Index:</strong> ${burnEv.logIndex ?? 0}<br>
          <strong>Executor:</strong> <span class="monospace">${escapeHtml(burnEv.executor || "-")}</span>
        `;
      } else if (groupBurns && groupBurns.length > 0) {
        sourceLegHtml = `
          <strong>Group Burns (${groupBurns.length} identical):</strong>
          <div class="trail-sublist">
            ${groupBurns.map((b) => `<div>&bull; Row ${b.rowIndex}: <span class="monospace">${escapeHtml((b.outcomeId || "").slice(0, 16))}...</span> (log ${b.logIndex})</div>`).join("")}
          </div>
        `;
      }

      // Bridge Leg content
      let bridgeLegHtml = '<span style="color:var(--cds-text-helper)">No bridge record</span>';
      if (bridgeEv) {
        bridgeLegHtml = (observations.length ? observations : [{bridgeRecord: bridgeEv}]).map(({bridgeRecord: bridgeEv}) => `
          <strong>Tx Hash:</strong> <span class="monospace">${escapeHtml(bridgeEv.transferTxHash || "-")}</span><br>
          <strong>Chain:</strong> ${escapeHtml(bridgeEv.chain || "eth:8453")}<br>
          <strong>Evidenced Fee:</strong> ${escapeHtml(bridgeEv.feeFormatted || "-")} USDC<br>
          <strong>Withdraw Net:</strong> ${escapeHtml(bridgeEv.withdrawAmountFormatted || "-")} USDC
        `).join("<hr>");
      }

      // Destination Leg content
      let destLegHtml = '<span style="color:var(--cds-text-helper)">No destination receipt</span>';
      if (destEv) {
        destLegHtml = (observations.length ? observations : [{destTransfer: destEv}]).map(({destTransfer: destEv}) => {
        const link = destEv.explorerUrl
          ? `<a href="${destEv.explorerUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(truncateMiddle(destEv.transferTxHash, 14, 12))} &nearr;</a>`
          : `<span class="monospace">${escapeHtml(truncateMiddle(destEv.transferTxHash, 14, 12))}</span>`;
        return `
          <strong>Tx Hash:</strong> ${link}<br>
          <strong>Log Index:</strong> ${destEv.logIndex ?? "-"}<br>
          <strong>Block:</strong> ${destEv.block ?? "-"}<br>
          <strong>Status:</strong> ${destEv.receiptStatus === "0x1" ? '<span style="color:var(--cds-support-success-text)">Success (0x1)</span>' : escapeHtml(destEv.receiptStatus || "-")}
        `;
        }).join("<hr>");
      }

      // Group Alert
      let groupAlertHtml = "";
      if (r.kind === "group" && r.groupDetails) {
        const gd = r.groupDetails;
        groupAlertHtml = `
          <div class="group-alert-box">
            <strong>Group Finding &mdash; Ambiguous Burn Attribution</strong>
            ${gd.rowsInGroup} identical gross burns (${grossStr}) were executed to the same recipient address.
            Evidence breakdown: <strong>${gd.observed} payment(s) observed on Base</strong> and <strong>${gd.unrecorded} unrecorded</strong> on bridge.
            Because the source contract emitted identical burn amounts, individual source-burn attribution is ambiguous and cannot be deterministically mapped.
          </div>
        `;
      }

      detailTr.innerHTML = `
        <td colspan="7">
          <div class="expandable-content">
            ${groupAlertHtml}
            ${ev.projectionWarning ? `<p role="status">${escapeHtml(ev.projectionWarning)}</p>` : ""}
            
            <div class="trail-grid">
              <div class="trail-card">
                <div class="trail-card__header">
                  <span class="trail-step-tag">Step 1</span>
                  <span class="trail-title">Source Leg (NEAR ft_burn)</span>
                </div>
                <div class="trail-card__body">${sourceLegHtml}</div>
              </div>

              <div class="trail-card">
                <div class="trail-card__header">
                  <span class="trail-step-tag">Step 2</span>
                  <span class="trail-title">Bridge Leg (Chaindefuser)</span>
                </div>
                <div class="trail-card__body">${bridgeLegHtml}</div>
              </div>

              <div class="trail-card">
                <div class="trail-card__header">
                  <span class="trail-step-tag">Step 3</span>
                  <span class="trail-title">Destination Leg (Base Receipt)</span>
                </div>
                <div class="trail-card__body">${destLegHtml}</div>
              </div>
            </div>

            <div class="note-box">
              <strong style="color:var(--cds-text-primary)">Audit Note:</strong> ${escapeHtml(humanizeNote(r.note) || "No audit note recorded")}
            </div>
          </div>
        </td>
      `;
      tbody.appendChild(detailTr);

      // Expansion toggle function
      const toggleRow = () => {
        const isExpanded = parentTr.classList.contains("expanded");
        parentTr.querySelector(".expand-toggle").setAttribute("aria-expanded", String(!isExpanded));
        if (isExpanded) {
          parentTr.classList.remove("expanded");
          parentTr.setAttribute("aria-expanded", "false");
          detailTr.style.display = "none";
        } else {
          parentTr.classList.add("expanded");
          parentTr.setAttribute("aria-expanded", "true");
          detailTr.style.display = "table-row";
        }
      };

      parentTr.addEventListener("click", toggleRow);

      // Expand the first row by default for immediate 5-second evidence legibility
      if (idx === 0) {
        toggleRow();
      }
    });
  }

  // E. Technical Provenance Accordion Details
  document.getElementById("meta-tx").textContent = req.txHash || "-";
  document.getElementById("meta-signer").textContent = req.signerId || "-";
  document.getElementById("meta-status").textContent = `${prov.sourceStatus || "-"} (${prov.finalExecutionStatus || "final"})`;
  document.getElementById("meta-sha256").textContent = prov.readerSha256 || "-";

  const comp = summary.completeness || {};
  document.getElementById("meta-completeness").textContent = comp.complete
    ? "Complete (Graph fully resolved)"
    : `Incomplete (${comp.reason || "missing nodes"})`;

  // Explorers
  const explorerContainer = document.getElementById("explorer-links");
  explorerContainer.innerHTML = "";
  const exLinks = report.explorerLinks || {};

  if (exLinks.nearTx) addExplorerLink(explorerContainer, "NEAR Transaction", exLinks.nearTx);
  if (exLinks.nearSigner) addExplorerLink(explorerContainer, "Signer Account", exLinks.nearSigner);
  if (exLinks.bridge) addExplorerLink(explorerContainer, "Chaindefuser Bridge", exLinks.bridge);
  if (exLinks.baseToken) addExplorerLink(explorerContainer, "Base USDC Contract", exLinks.baseToken);
  (exLinks.destTransfers || []).forEach((url, i) => {
    addExplorerLink(explorerContainer, `Base Receipt #${i + 1}`, url);
  });

  // Raw Dumps
  document.getElementById("burns-dump").textContent = JSON.stringify(normEv.sourceBurns || [], null, 2);
  document.getElementById("bridge-dump").textContent = JSON.stringify(normEv.bridgeWithdrawals || [], null, 2);
  document.getElementById("dest-dump").textContent = JSON.stringify(normEv.destTransfers || [], null, 2);
  document.getElementById("burn-diag-dump").textContent = JSON.stringify(summary.burnDiag || {}, null, 2);

  // Semantics Disclaimer
  if (summary.disclaimer) {
    document.getElementById("disclaimer-text").textContent = summary.disclaimer;
  }
}

// 7. Helper Utilities
function addExplorerLink(container, label, url) {
  const a = document.createElement("a");
  a.className = "explorer-pill";
  a.href = url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  a.innerHTML = `${escapeHtml(label)} <span aria-hidden="true">&nearr;</span>`;
  container.appendChild(a);
}

function getVerdictTagClass(verdict) {
  switch (verdict) {
    case "OBSERVED_MATCH":
      return "carbon-tag--green";
    case "GROUP_FINDING":
      return "carbon-tag--yellow";
    case "NOT_RECORDED":
      return "carbon-tag--red";
    case "UNMATCHED_DEST_TRANSFER":
    case "UNMATCHED_BRIDGE_RECORD":
      return "carbon-tag--blue";
    default:
      return "carbon-tag--gray";
  }
}

function formatUSDCFromMicro(microInt) {
  if (microInt == null) return "See evidence";
  const amount = BigInt(microInt);
  const sign = amount < 0n ? "-" : "";
  const s = String(amount < 0n ? -amount : amount).padStart(7, "0");
  return `${sign}${s.slice(0, -6)}.${s.slice(-6)} USDC`;
}

function truncateMiddle(str, front = 10, back = 8) {
  if (!str) return "";
  if (str.length <= front + back + 3) return str;
  return `${str.slice(0, front)}...${str.slice(-back)}`;
}

function humanizeNote(note) {
  // Display-only: rewrite the raw Python None leak in offline fixture notes.
  // Exports (JSON/CSV/Markdown) keep the original reader note untouched.
  if (!note) return note;
  return String(note).replace(
    /confirmations None vs tip None/g,
    "confirmations not captured (offline evidence)"
  );
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function initKeyboardNavigation() {
  document.addEventListener("keydown", (e) => {
    // Escape dismisses error or stale notification
    if (e.key === "Escape") {
      clearError();
      document.getElementById("stale-banner").style.display = "none";
    }
  });
}
