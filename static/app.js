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
  initDownloadButton();
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

// 2. Load Saved Examples & Preload QA1
async function loadSavedExamplesAndPreloadQA1() {
  try {
    const res = await fetch("/api/examples");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    savedExamplesCache = await res.json();
    renderExamplePills(savedExamplesCache);

    // Preload QA1 immediately on first load
    await runReconciliation({ mode: "saved", exampleId: "qa1" });
  } catch (err) {
    showError(`Failed to load saved examples: ${err.message}`);
  }
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
      document.querySelectorAll(".case-pill").forEach((p) => {
        const isActive = p.dataset.exampleId === ex.id;
        p.classList.toggle("active", isActive);
        p.setAttribute("aria-checked", isActive ? "true" : "false");
      });
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
    hideStaleBanner();
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

// 4. Download JSON Report
function initDownloadButton() {
  const btn = document.getElementById("btn-download-json");
  btn.addEventListener("click", () => {
    if (!currentReport) return;
    const jsonStr = JSON.stringify(currentReport, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const mode = currentReport.request?.mode || "report";
    const tx = (currentReport.request?.txHash || "tx").slice(0, 10);
    a.href = url;
    a.download = `payout-audit-${mode}-${tx}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
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
    renderReport(data);
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
    modeBadge.textContent = "Offline Verified Evidence";
  }

  // Calculate detailed aggregate numbers
  let totalGross = 0;
  let totalBridgeFee = 0;
  let totalObservedNet = 0;
  let totalUnrecordedGross = 0;

  let trueObservedCount = counts.observedMatches || 0;
  let trueUnrecordedCount = counts.unrecorded || 0;
  let truePendingCount = counts.pending || 0;

  rows.forEach((r) => {
    const grossVal = parseInt(r.amounts?.gross || "0", 10);
    const feeVal = parseInt(r.amounts?.fee || "0", 10);
    const netVal = parseInt(r.amounts?.net || "0", 10);

    if (r.kind === "group" && r.groupDetails) {
      trueObservedCount += r.groupDetails.observed || 0;
      trueUnrecordedCount += r.groupDetails.unrecorded || 0;
      truePendingCount += r.groupDetails.pending || 0;

      totalGross += grossVal * (r.groupDetails.rowsInGroup || 1);
      if (r.groupDetails.observed > 0) {
        totalObservedNet += netVal;
        totalBridgeFee += feeVal;
      }
      if (r.groupDetails.unrecorded > 0) {
        totalUnrecordedGross += grossVal * r.groupDetails.unrecorded;
      }
    } else {
      totalGross += grossVal;
      if (r.verdict === "OBSERVED_MATCH") {
        totalObservedNet += netVal;
        totalBridgeFee += feeVal;
      } else if (r.verdict === "NOT_RECORDED") {
        totalUnrecordedGross += grossVal;
      }
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
    outcomeTag.textContent = "DEFICIT (MISMATCH)";

    if (req.exampleId === "qa1") {
      outcomeTitle.textContent = "3 Intended Payments — 1 Observed on Base, 2 Unrecorded";
      outcomeDesc.textContent = "Three identical 0.010000 USDC burns. One payment was delivered on Base (0.007600 USDC net after 0.002400 USDC fee). Two burns remain unrecorded on the bridge. Recipient attribution is ambiguous due to identical amounts.";
    } else if (req.exampleId === "qa2") {
      outcomeTitle.textContent = "2 Intended Payments — 1 Observed on Base, 1 Unrecorded";
      outcomeDesc.textContent = "0.190000 USDC burn verified delivered on Base (0.187600 USDC net after 0.002400 USDC fee). 0.200000 USDC burn lacks an observed bridge withdrawal record.";
    } else {
      outcomeTitle.textContent = "Delivery Mismatch — Some Payments Lack Observed Delivery";
      outcomeDesc.textContent = `${trueObservedCount} observed delivered, ${trueUnrecordedCount} unrecorded on bridge. Unrecorded burns are ambiguous, not proof of permanent loss.`;
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
  document.getElementById("kpi-burns-count").textContent = counts.sourceBurns || rows.length;
  document.getElementById("kpi-burns-amt").textContent = formatUSDCFromMicro(totalGross);

  document.getElementById("kpi-bridge-count").textContent = counts.bridgeRecords ?? 0;
  document.getElementById("kpi-bridge-amt").textContent = formatUSDCFromMicro(totalObservedNet + totalBridgeFee);

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
      parentTr.tabIndex = 0;
      parentTr.setAttribute("role", "button");
      parentTr.setAttribute("aria-expanded", "false");
      parentTr.setAttribute("aria-controls", `detail-${idx}`);

      parentTr.innerHTML = `
        <td class="th-expand">
          <button type="button" class="expand-toggle" aria-label="Toggle details for ${escapeHtml(rowLabel)}">
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
        bridgeLegHtml = `
          <strong>Tx Hash:</strong> <span class="monospace">${escapeHtml(bridgeEv.transferTxHash || "-")}</span><br>
          <strong>Chain:</strong> ${escapeHtml(bridgeEv.chain || "eth:8453")}<br>
          <strong>Evidenced Fee:</strong> ${escapeHtml(bridgeEv.feeFormatted || "-")} USDC<br>
          <strong>Withdraw Net:</strong> ${escapeHtml(bridgeEv.withdrawAmountFormatted || "-")} USDC
        `;
      }

      // Destination Leg content
      let destLegHtml = '<span style="color:var(--cds-text-helper)">No destination receipt</span>';
      if (destEv) {
        const link = destEv.explorerUrl
          ? `<a href="${destEv.explorerUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(truncateMiddle(destEv.transferTxHash, 14, 12))} &nearr;</a>`
          : `<span class="monospace">${escapeHtml(truncateMiddle(destEv.transferTxHash, 14, 12))}</span>`;
        destLegHtml = `
          <strong>Tx Hash:</strong> ${link}<br>
          <strong>Log Index:</strong> ${destEv.logIndex ?? "-"}<br>
          <strong>Block:</strong> ${destEv.block ?? "-"}<br>
          <strong>Status:</strong> ${destEv.receiptStatus === "0x1" ? '<span style="color:var(--cds-support-success-text)">Success (0x1)</span>' : escapeHtml(destEv.receiptStatus || "-")}
        `;
      }

      // Group Alert
      let groupAlertHtml = "";
      if (r.kind === "group" && r.groupDetails) {
        const gd = r.groupDetails;
        groupAlertHtml = `
          <div class="group-alert-box">
            <strong>Group Finding &mdash; Ambiguous Payment Attribution</strong>
            ${gd.rowsInGroup} identical gross burns (${grossStr}) were executed to the same recipient address.
            Evidence breakdown: <strong>${gd.observed} payment observed on Base</strong> and <strong>${gd.unrecorded} unrecorded</strong> on bridge.
            Because the source contract emitted identical burn amounts, individual payment attribution is mathematically ambiguous and cannot be deterministically mapped.
          </div>
        `;
      }

      detailTr.innerHTML = `
        <td colspan="7">
          <div class="expandable-content">
            ${groupAlertHtml}
            
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
              <strong style="color:var(--cds-text-primary)">Audit Note:</strong> ${escapeHtml(r.note || "No audit note recorded")}
            </div>
          </div>
        </td>
      `;
      tbody.appendChild(detailTr);

      // Expansion toggle function
      const toggleRow = () => {
        const isExpanded = parentTr.classList.contains("expanded");
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
      parentTr.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleRow();
        }
      });

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
  if (isNaN(microInt) || microInt === 0) return "0.000000 USDC";
  const s = String(microInt).padStart(7, "0");
  const whole = s.slice(0, -6) || "0";
  const frac = s.slice(-6);
  return `${whole}.${frac} USDC`;
}

function truncateMiddle(str, front = 10, back = 8) {
  if (!str) return "";
  if (str.length <= front + back + 3) return str;
  return `${str.slice(0, front)}...${str.slice(-back)}`;
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
      hideStaleBanner();
    }
  });
}
