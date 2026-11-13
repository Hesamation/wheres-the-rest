/**
 * Payout Reader frontend controller.
 * Vanilla JavaScript (ES2022+), zero external runtime dependencies.
 */

let currentReport = null;
let savedExamplesCache = [];

document.addEventListener("DOMContentLoaded", () => {
  initModeTabs();
  initLiveForm();
  initDownloadButton();
  loadSavedExamples();
});

function initModeTabs() {
  const modeSaved = document.getElementById("mode-saved");
  const modeLive = document.getElementById("mode-live");
  const savedControls = document.getElementById("saved-controls");
  const liveForm = document.getElementById("live-form");

  modeSaved.addEventListener("change", () => {
    if (modeSaved.checked) {
      savedControls.style.display = "block";
      liveForm.style.display = "none";
      clearError();
    }
  });

  modeLive.addEventListener("change", () => {
    if (modeLive.checked) {
      savedControls.style.display = "none";
      liveForm.style.display = "block";
      clearError();
    }
  });
}

async function loadSavedExamples() {
  const container = document.getElementById("examples-grid");
  try {
    const res = await fetch("/api/examples");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    savedExamplesCache = await res.json();
    renderExampleCards(savedExamplesCache);
  } catch (err) {
    container.innerHTML = `<div class="alert alert-error">Failed to load saved examples: ${escapeHtml(err.message)}</div>`;
  }
}

function renderExampleCards(examples) {
  const container = document.getElementById("examples-grid");
  container.innerHTML = "";

  examples.forEach((ex) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "example-card";
    card.setAttribute("role", "listitem");
    card.dataset.exampleId = ex.id;

    let badgeClass = "qa1";
    let badgeText = "QA Case";
    if (ex.id === "prod_control") {
      badgeClass = "control";
      badgeText = "Control";
    }

    card.innerHTML = `
      <div class="example-card-header">
        <span class="example-title">${escapeHtml(ex.label)}</span>
        <span class="example-badge ${badgeClass}">${badgeText}</span>
      </div>
      <p class="example-desc">${escapeHtml(ex.summary)}</p>
      <div class="example-meta">
        <span><strong>Tx:</strong> <span class="monospace">${escapeHtml(ex.txHash.slice(0, 16))}...</span></span>
        <span><strong>Signer:</strong> <span class="monospace">${escapeHtml(ex.signerId)}</span></span>
        <span><strong>Captured:</strong> ${escapeHtml(ex.capturedAt)}</span>
      </div>
    `;

    card.addEventListener("click", () => {
      document.querySelectorAll(".example-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      runReconciliation({ mode: "saved", exampleId: ex.id });
    });

    container.appendChild(card);
  });
}

function initLiveForm() {
  const form = document.getElementById("live-form");
  const txInput = document.getElementById("live-tx");
  const signerInput = document.getElementById("live-signer");

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
    a.download = `payout-report-${mode}-${tx}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

async function runReconciliation(payload) {
  clearError();
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
    renderReport(data);
  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

function setLoading(isLoading, mode = "saved") {
  const loadingState = document.getElementById("loading-state");
  const submitBtn = document.getElementById("btn-submit-live");
  const cards = document.querySelectorAll(".example-card");
  const resultsPanel = document.getElementById("results-panel");
  const loadingTitle = document.getElementById("loading-title");
  const loadingDesc = document.getElementById("loading-desc");

  if (isLoading) {
    loadingState.style.display = "flex";
    if (mode === "live") {
      loadingTitle.textContent = "Querying Live Network RPCs...";
      loadingDesc.textContent = "Fetching NEAR outcomes, Chaindefuser bridge logs, and Base USDC receipts...";
    } else {
      loadingTitle.textContent = "Reconciling Saved Payout Evidence...";
      loadingDesc.textContent = "Verifying offline fixture against reader invariants in isolated subprocess...";
    }
    if (submitBtn) submitBtn.disabled = true;
    cards.forEach((c) => (c.disabled = true));
  } else {
    loadingState.style.display = "none";
    if (submitBtn) submitBtn.disabled = false;
    cards.forEach((c) => (c.disabled = false));
  }
}

function showError(msg) {
  const banner = document.getElementById("error-banner");
  const msgSpan = document.getElementById("error-message");
  msgSpan.textContent = msg;
  banner.style.display = "flex";
}

function clearError() {
  const banner = document.getElementById("error-banner");
  banner.style.display = "none";
}

function renderReport(report) {
  const resultsPanel = document.getElementById("results-panel");
  resultsPanel.style.display = "flex";

  const req = report.request || {};
  const prov = report.provenance || {};
  const summary = report.summary || {};
  const counts = report.counts || {};
  const rows = report.rows || [];

  // 1. Overall Banner
  const banner = document.getElementById("overall-banner");
  const codeTag = document.getElementById("overall-code-tag");
  const title = document.getElementById("overall-title");
  const desc = document.getElementById("overall-desc");

  banner.className = "overall-banner";
  const overallCode = summary.overallCode || "NEEDS_INSPECTION";
  codeTag.textContent = overallCode;
  title.textContent = summary.overall || "Unknown Finding";

  if (overallCode === "ALL_ROWS_OBSERVED") {
    banner.classList.add("verdict-all-observed");
    desc.textContent = "All supported burn rows have corresponding completed bridge records and observed Base USDC transfer receipts. Receipt-level provider evidence confirmed.";
  } else if (overallCode === "MISMATCH") {
    banner.classList.add("verdict-mismatch");
    desc.textContent = "Discrepancy detected: Some intended payments lack observed delivery on Base (unrecorded burn deficit, revert, or missing transfer).";
  } else if (overallCode === "IN_PROGRESS") {
    banner.classList.add("verdict-inconclusive");
    desc.textContent = "Reconciliation in progress: Bridge or destination transactions are still pending.";
  } else if (overallCode === "INCONCLUSIVE") {
    banner.classList.add("verdict-inconclusive");
    desc.textContent = "Required provider leg unavailable or response was malformed. Recheck manually.";
  } else {
    banner.classList.add("verdict-invalid");
    desc.textContent = "Non-standard, unsupported, or invalid evidence encountered during audit.";
  }

  // 2. Metadata Strip
  document.getElementById("meta-mode").textContent = (req.mode || "-").toUpperCase();
  document.getElementById("meta-tx").textContent = req.txHash || "-";
  document.getElementById("meta-signer").textContent = req.signerId || "-";
  document.getElementById("meta-captured").textContent = prov.capturedAt || "-";
  document.getElementById("meta-provider").textContent = `${prov.sourceProvider || "-"} (${prov.sourceStatus || "-"})`;

  const comp = summary.completeness || {};
  document.getElementById("meta-completeness").textContent = comp.complete
    ? "Complete (Graph fully resolved)"
    : `Incomplete (${comp.reason || "missing nodes"})`;

  // 3. Metrics Cards
  document.getElementById("metric-burns").textContent = counts.sourceBurns ?? 0;
  document.getElementById("metric-bridge").textContent = counts.bridgeRecords ?? 0;
  document.getElementById("metric-observed").textContent = counts.observedMatches ?? 0;
  document.getElementById("metric-unrecorded").textContent = counts.unrecorded ?? 0;
  document.getElementById("metric-pending").textContent = counts.pending ?? 0;

  // 4. Findings Table
  const tbody = document.getElementById("findings-tbody");
  tbody.innerHTML = "";

  if (rows.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">No withdrawal rows or findings found in evidence.</td>`;
    tbody.appendChild(tr);
  } else {
    rows.forEach((r, idx) => {
      const tr = document.createElement("tr");
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

      const pillClass = getPillClass(r.verdict);
      const recipientText = r.recipient ? `<span class="monospace">${escapeHtml(r.recipient)}</span>` : '<span style="color:var(--text-muted);">-</span>';

      tr.innerHTML = `
        <td><strong>${escapeHtml(rowLabel)}</strong></td>
        <td>${recipientText}</td>
        <td class="num-col">${escapeHtml(grossStr)}</td>
        <td class="num-col">${escapeHtml(feeStr)}</td>
        <td class="num-col"><strong>${escapeHtml(netStr)}</strong></td>
        <td><span class="verdict-pill ${pillClass}">${escapeHtml(r.verdict)}</span></td>
        <td><button type="button" class="row-detail-btn" data-target="detail-${idx}">Inspect</button></td>
      `;
      tbody.appendChild(tr);

      // Detail expansion row
      const detailTr = document.createElement("tr");
      detailTr.id = `detail-${idx}`;
      detailTr.className = "expanded-detail-row";
      detailTr.style.display = "none";

      const ev = r.evidence || {};
      const burnEv = ev.sourceBurn;
      const groupBurns = ev.groupBurns;
      const bridgeEv = ev.bridgeRecord;
      const destEv = ev.destTransfer;

      let sourceLegContent = "None";
      if (burnEv) {
        sourceLegContent = `Outcome ID: ${escapeHtml(burnEv.outcomeId)}<br>Log Index: ${burnEv.logIndex}<br>Executor: ${escapeHtml(burnEv.executor)}`;
      } else if (groupBurns && groupBurns.length > 0) {
        sourceLegContent = `Group Burns (${groupBurns.length}):<br>` +
          groupBurns.map((b) => `• Row ${b.rowIndex}: ${escapeHtml((b.outcomeId || '').slice(0, 16))}... (log ${b.logIndex})`).join("<br>");
      }

      let groupAlertHtml = "";
      if (r.kind === "group" && r.groupDetails) {
        const gd = r.groupDetails;
        groupAlertHtml = `
          <div class="detail-group-alert">
            <strong>Group Finding (Ambiguous Attribution):</strong>
            ${gd.rowsInGroup} identical gross rows (${grossStr}) cannot be deterministically matched to individual recipients because the source contract emitted identical burn amounts.
            Evidenced count: ${gd.observed} observed on Base, ${gd.unrecorded} unrecorded, ${gd.pending} pending.
          </div>
        `;
      }

      detailTr.innerHTML = `
        <td colspan="7">
          <div class="detail-content">
            ${groupAlertHtml}
            <div class="evidence-grid">
              <div class="evidence-box">
                <span class="evidence-box-title">Source Leg (NEAR ft_burn)</span>
                <span class="evidence-box-body">
                  ${sourceLegContent}
                </span>
              </div>
              <div class="evidence-box">
                <span class="evidence-box-title">Bridge Leg (Chaindefuser)</span>
                <span class="evidence-box-body">
                  ${bridgeEv ? `Transfer Tx: ${escapeHtml(bridgeEv.transferTxHash || "-")}<br>Chain: ${escapeHtml(bridgeEv.chain)}<br>Evidenced Fee: ${escapeHtml(bridgeEv.feeFormatted || "-")} USDC` : "None"}
                </span>
              </div>
              <div class="evidence-box">
                <span class="evidence-box-title">Destination Leg (Base Receipt)</span>
                <span class="evidence-box-body">
                  ${destEv ? `Tx: <a href="${destEv.explorerUrl}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-blue)">${escapeHtml((destEv.transferTxHash || "").slice(0, 16))}...</a><br>Log Index: ${destEv.logIndex}<br>Confirmations: ${destEv.confirmations ?? "N/A"}` : "None"}
                </span>
              </div>
            </div>
            <div class="note-box">
              <strong>Reader Audit Note:</strong> ${escapeHtml(r.note || "No note recorded")}
            </div>
          </div>
        </td>
      `;
      tbody.appendChild(detailTr);
    });

    // Toggle handlers
    document.querySelectorAll(".row-detail-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.dataset.target;
        const targetRow = document.getElementById(targetId);
        if (targetRow.style.display === "none") {
          targetRow.style.display = "table-row";
          btn.textContent = "Close";
        } else {
          targetRow.style.display = "none";
          btn.textContent = "Inspect";
        }
      });
    });
  }

  // 5. Explorer Links
  const explorerContainer = document.getElementById("explorer-links");
  explorerContainer.innerHTML = "";
  const exLinks = report.explorerLinks || {};

  if (exLinks.nearTx) {
    addExplorerLink(explorerContainer, "NEAR Tx on NearBlocks", exLinks.nearTx);
  }
  if (exLinks.nearSigner) {
    addExplorerLink(explorerContainer, "Signer on NearBlocks", exLinks.nearSigner);
  }
  if (exLinks.bridge) {
    addExplorerLink(explorerContainer, "Chaindefuser Bridge", exLinks.bridge);
  }
  if (exLinks.baseToken) {
    addExplorerLink(explorerContainer, "Base USDC Contract", exLinks.baseToken);
  }
  (exLinks.destTransfers || []).forEach((tUrl, i) => {
    addExplorerLink(explorerContainer, `Base Tx #${i + 1}`, tUrl);
  });

  // 6. Evidence Dumps
  const normEv = report.normalizedEvidence || {};
  document.getElementById("burn-diag-dump").textContent = JSON.stringify(summary.burnDiag || {}, null, 2);
  document.getElementById("burns-dump").textContent = JSON.stringify(normEv.sourceBurns || [], null, 2);
  document.getElementById("bridge-dump").textContent = JSON.stringify(normEv.bridgeWithdrawals || [], null, 2);
  document.getElementById("dest-dump").textContent = JSON.stringify(normEv.destTransfers || [], null, 2);

  // 7. Disclaimer
  if (summary.disclaimer) {
    document.getElementById("disclaimer-text").textContent = summary.disclaimer;
  }

  resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function addExplorerLink(container, label, url) {
  const a = document.createElement("a");
  a.className = "explorer-link";
  a.href = url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  a.textContent = label;
  container.appendChild(a);
}

function getPillClass(verdict) {
  switch (verdict) {
    case "OBSERVED_MATCH":
      return "observed-match";
    case "GROUP_FINDING":
      return "group-finding";
    case "NOT_RECORDED":
      return "not-recorded";
    case "UNMATCHED_DEST_TRANSFER":
      return "unmatched-dest";
    case "UNMATCHED_BRIDGE_RECORD":
      return "unmatched-bridge";
    case "INCONCLUSIVE":
      return "inconclusive";
    case "INVALID_RECORD":
      return "invalid-record";
    default:
      return "inconclusive";
  }
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
