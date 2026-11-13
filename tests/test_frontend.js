// Optional pure controller regression checks: node tests/test_frontend.js.
// No browser, network, packages, or application build step required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

class Element {
  constructor() {
    this.style = {};
    this.children = [];
    this.classes = new Set();
    this.classList = {
      add: (name) => this.classes.add(name),
      remove: (name) => this.classes.delete(name),
      contains: (name) => this.classes.has(name),
    };
  }
  querySelector() { return new Element(); }
  setAttribute() {}
  addEventListener() {}
  appendChild(child) { this.children.push(child); }
}
const elements = new Map();
const document = {
  addEventListener() {},
  createElement() { return new Element(); },
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  },
};
const context = vm.createContext({ document, console });
vm.runInContext(fs.readFileSync(path.join(root, 'static/app.js'), 'utf8'), context);
const reports = JSON.parse(execFileSync(process.env.PYTHON || 'python3', ['-c', [
  'import json',
  'from pathlib import Path',
  'from app.adapter import reconcile_fixture',
  'print(json.dumps({p.stem:reconcile_fixture(json.loads(p.read_text())) for p in Path("reader/fixtures").glob("*.json")}))',
].join('\n')], { cwd: root }));
const text = (id) => String(document.getElementById(id).textContent);

for (const report of Object.values(reports)) {
  context.renderReport(report); // All error/pending/extra fixtures must render.
}
context.renderReport(reports.fx_g3_permutation_rev);
assert.equal(text('kpi-observed-count'), '2');
assert.equal(text('kpi-observed-amt'), '0.015200 USDC');
assert.equal(text('kpi-burns-amt'), '0.030000 USDC');
assert.equal(text('kpi-bridge-amt'), '0.020000 USDC');
assert.match(context.generateMarkdownProof(reports.fx_g3_permutation_rev), /2 observed; 1 unrecorded/);
assert.match(context.generateMarkdownProof(reports.fx_g3_permutation_rev), /Gross\/burn/);

// Above Number.MAX_SAFE_INTEGER: a micro-USDC must never be rounded away.
const large = structuredClone(reports.control_prod_fd7g);
large.normalizedEvidence.sourceBurns[0].amount = '9007199254740993';
large.normalizedEvidence.bridgeWithdrawals[0].amount = '9007199254740993';
large.rows[0].amounts.net = '9007199254738593';
context.renderReport(large);
assert.equal(text('kpi-burns-amt'), '9007199254.740993 USDC');
assert.equal(text('kpi-observed-amt'), '9007199254.738593 USDC');
assert.equal(context.formatUSDCFromMicro(-1n), '-0.000001 USDC');

// Provider failure after source extraction must still show the known burns;
// unmatched extra findings must not inflate the source amount.
large.rows = [];
context.renderReport(large);
assert.equal(text('kpi-burns-amt'), '9007199254.740993 USDC');
const extra = structuredClone(reports.control_prod_fd7g);
extra.rows.push({ kind: 'unmatched_bridge', verdict: 'UNMATCHED_BRIDGE_RECORD', amounts: { gross: '1000000' } });
context.renderReport(extra);
assert.equal(text('kpi-burns-amt'), '1.000000 USDC');

// Browser CSV and Python CSV must represent the same report rows.
const csvRows = JSON.parse(execFileSync(process.env.PYTHON || 'python3', ['-c', [
  'import csv,io,json,sys',
  'from app.formatting import report_to_csv',
  'parse=lambda x:list(csv.reader(io.StringIO(x)))',
  'print(json.dumps([[parse(js),parse(report_to_csv(report))] for js,report in json.load(sys.stdin)]))',
].join('\n')], {
  cwd: root,
  input: JSON.stringify(Object.values(reports).map(report => [context.generateCsvReport(report), report])),
  encoding: 'utf8',
}));
for (const [browserRows, pythonRows] of csvRows) assert.deepEqual(browserRows, pythonRows);
for (const row of reports.fx_g3_permutation_rev.rows) {
  for (const observation of row.evidence.observedTransfers) {
    assert.ok(context.generateMarkdownProof(reports.fx_g3_permutation_rev).includes(observation.destTransfer.transferTxHash));
  }
}
console.log('Frontend regressions passed: all fixtures render, exact/group totals, extras, CSV parity.');
