"use strict";
// All financial terms and statuses come from authenticated server observations.
const $ = (id) => document.getElementById(id);
let user = null, data = null, csrf = "", serverOffset = 0, cancelId = null, refreshing = false;
const pathId = (value) => encodeURIComponent(value);
function node(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
function notify(message, error = false) { const target = $(error ? "error" : "notice"); target.textContent = message; target.hidden = false; }
async function api(path, options = {}) {
  const headers = { ...options.headers };
  if (options.method && options.method !== "GET") headers["x-csrf-token"] = csrf;
  if (options.body && typeof options.body !== "string") { headers["content-type"] = "application/json"; options.body = JSON.stringify(options.body); }
  let response;
  try { response = await fetch(path, { credentials: "same-origin", cache: "no-store", ...options, headers }); }
  catch { throw new Error("The service could not be reached. Your last request may have been received. Refresh its status before retrying."); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/login") { showLogin(); throw new Error("Your session expired or the security token was refused. Sign in again."); }
    const message = typeof body.detail === "string" ? body.detail : response.status === 422 ? "Check the form fields and try again." : "The request was refused. Refresh the current state before retrying.";
    throw new Error(message);
  }
  return body;
}
function showLogin() { user = null; data = null; $("workspace").hidden = true; $("login-panel").hidden = false; $("logout").hidden = true; $("identity").textContent = ""; }
function button(label, action, className = "") { const b = node("button", label, className); b.type = "button"; b.addEventListener("click", async () => { b.disabled = true; $("error").hidden = true; try { await action(); } catch (e) { notify(e.message, true); } finally { b.disabled = false; } }); return b; }
function table(target, columns, rows, empty) {
  const container = $(target); container.replaceChildren();
  if (!rows.length) { container.append(node("p", empty, "empty")); return; }
  const wrap = node("div", undefined, "table-wrap"), t = node("table"), head = node("thead"), h = node("tr");
  columns.forEach(([label]) => h.append(node("th", label))); head.append(h); t.append(head);
  const body = node("tbody"); rows.forEach((row) => { const tr = node("tr"); columns.forEach(([, key]) => { const td = node("td"); const value = typeof key === "function" ? key(row) : row[key]; if (value instanceof Node) td.append(value); else td.textContent = value ?? "—"; tr.append(td); }); body.append(tr); });
  t.append(body); wrap.append(t); container.append(wrap);
}
function countdown(until) { const span = node("span", undefined, "countdown"); if (until) span.dataset.until = until; else span.textContent = "Independent callback required"; return span; }
function tick() { document.querySelectorAll("[data-until]").forEach((element) => { const seconds = Math.ceil((Date.parse(element.dataset.until) - Date.now() - serverOffset) / 1000); if (!Number.isFinite(seconds)) { element.textContent = "Timing unavailable"; return; } element.textContent = seconds <= 0 ? "Cooling window elapsed · server checks still apply" : `${Math.floor(seconds / 86400)}d ${Math.floor(seconds % 86400 / 3600)}h ${Math.floor(seconds % 3600 / 60)}m ${seconds % 60}s remaining`; }); }
async function dependency() {
  try { const response = await fetch("/ready", { cache: "no-store" }); const body = await response.json(); $("readiness").textContent = body.ready ? "Provider connected · operational controls ready" : "Execution unavailable until these setup or dependency issues are resolved"; $("setup-errors").replaceChildren(...(body.setup_errors || []).map((e) => node("li", e))); }
  catch { $("readiness").textContent = "Service unavailable. Previously displayed observations may be stale."; }
}
function decode(value) { return Uint8Array.from(atob(value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - value.length % 4) % 4)), (c) => c.charCodeAt(0)); }
function encode(value) { return btoa(String.fromCharCode(...new Uint8Array(value))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
async function ceremony(optionsPath, finishPath, body, register = false) {
  if (!window.PublicKeyCredential || !navigator.credentials) throw new Error("Passkeys require a supported browser on localhost or HTTPS.");
  const prompt = await api(optionsPath, { method: "POST", body });
  const pk = prompt.publicKey; pk.challenge = decode(pk.challenge);
  if (pk.user) pk.user.id = decode(pk.user.id);
  for (const field of ["allowCredentials", "excludeCredentials"]) if (pk[field]) pk[field].forEach((c) => { c.id = decode(c.id); });
  let credential;
  try { credential = register ? await navigator.credentials.create({ publicKey: pk }) : await navigator.credentials.get({ publicKey: pk }); }
  catch { throw new Error("Passkey verification was cancelled or unavailable. No approval was recorded."); }
  if (!credential) throw new Error("No passkey response was received.");
  const response = { clientDataJSON: encode(credential.response.clientDataJSON) };
  for (const key of ["authenticatorData", "signature", "attestationObject", "userHandle"]) if (credential.response[key]) response[key] = encode(credential.response[key]);
  if (credential.response.getTransports) response.transports = credential.response.getTransports();
  await api(finishPath, { method: "POST", body: { ceremony_id: prompt.ceremony_id, credential: { id: credential.id, rawId: encode(credential.rawId), type: credential.type, response, clientExtensionResults: credential.getClientExtensionResults() } } });
}
async function requestAction(id, action) { const result = await api(`/api/approvals/${pathId(id)}/${action}`, { method: "POST" }); notify(`Request accepted. Job ${result.job_id} will recheck the current approval and execution controls.`); await refresh(); }
function approvals() {
  const container = $("approval-list"); container.replaceChildren();
  $("approval-count").textContent = `${data.approvals.length} recorded`;
  if (!data.approvals.length) { container.append(node("p", "No approval packets yet. Prepare an eligible invoice in Runs & planning.", "empty")); return; }
  data.approvals.forEach((packet) => {
    const card = node("article", undefined, "card"), heading = node("div", undefined, "card-head");
    heading.append(node("h3", packet.kind === "CONVERSION" ? "FX funding" : "Supplier payment"), node("span", packet.state, "pill")); card.append(heading);
    const terms = packet.terms, item = terms.items?.[0];
    card.append(node("p", item ? `${item.transfer_currency} ${item.transfer_amount}` : `${terms.sell_currency || ""} ${terms.sell_amount || terms.max_sell_amount || ""}`, "amount"));
    const dl = node("dl");
    for (const [label, value] of [["Recipient", item?.vendor_name || "Funding approved obligations"], ["Destination", item?.masked_destination || terms.buy_currency || "See locked quote"], ["Signatures", `${packet.signed_count} / ${packet.required_approvers}`], ["Expires", new Date(packet.expires_at).toLocaleString()], ["Packet", packet.id]]) { dl.append(node("dt", label), node("dd", value)); }
    card.append(dl);
    const details = node("details"), summary = node("summary", "Review complete terms, evidence and digest"); details.append(summary, node("p", `SHA-256 ${packet.sha256}`, "muted"), node("pre", JSON.stringify(terms, null, 2))); card.append(details);
    const active = ["OPEN", "APPROVED"].includes(packet.state) && Date.parse(packet.expires_at) > Date.now() + serverOffset;
    if (user.role === "approver" && active) {
      const toolbar = node("div", undefined, "toolbar");
      if (packet.state === "OPEN") toolbar.append(button("Approve with passkey", async () => { await ceremony(`/api/approvals/${pathId(packet.id)}/options`, "/api/passkeys/finish"); notify("Approval signature recorded."); await refresh(); }, "primary"));
      if (packet.state === "APPROVED") { toolbar.append(button("Request execution", () => requestAction(packet.id, "execute"), "primary")); if (packet.kind === "PAYMENT") toolbar.append(button("Request FX quote", () => requestAction(packet.id, "quote"))); }
      toolbar.append(button("Cancel approval", async () => { cancelId = packet.id; $("cancel-form").reset(); $("cancel-dialog").showModal(); }, "danger")); card.append(toolbar);
    }
    container.append(card);
  });
}
function setOptions(select, rows, label) { const previous = select.value; select.replaceChildren(node("option", "Choose…")); select.firstChild.value = ""; rows.forEach((r) => { const o = node("option", label(r)); o.value = r.id; select.append(o); }); if (rows.some((r) => r.id === previous)) select.value = previous; }
async function invoiceBanks() {
  const select = $("plan").elements.obligation_id, invoice = (data.invoices || []).find((i) => i.id === select.value);
  const banks = invoice ? await api(`/api/suppliers/${pathId(invoice.vendor_id)}/banks`) : [];
  setOptions($("plan").elements.payee_id, banks, (r) => `${r.masked} · ${r.currency} · ${r.status}`);
}
async function refresh() {
  if (refreshing) return; refreshing = true;
  try {
    await dependency(); if (!user) return;
    const result = await api("/api/operations"); data = result; serverOffset = Date.parse(data.server_now) - Date.now();
    approvals();
    table("cooling-list", [["Supplier", "display_name"], ["Destination", "masked"], ["State", "status"], ["Cooling-off", (r) => countdown(r.cooling_off_until)]], data.cooling, "No pending bank changes.");
    table("payment-list", [["Invoice", "obligation_id"], ["Provider transfer", "transfer_id"], ["Airwallex", "awx_status"], ["Wiretight", "wt_state"], ["Failure", "failure_type"], ["Observed", "updated_at"]], data.payments, "No payment executions recorded. Provider status appears after an approved action is submitted.");
    table("job-list", [["Job", "id"], ["Kind", "kind"], ["State", "state"], ["Outcome", (r) => r.error || r.result_json]], data.jobs, "No jobs requested.");
    table("tie-out-list", [["Run", "run_id"], ["Currency", "currency"], ["Actual cash", "b_actual"], ["Computed cash", "b_close_computed"], ["Residual", "residual"], ["Result", "state"]], data.tie_outs, "No reconciliation observation yet. Open a run and request reconciliation.");
    table("exception-list", [["Exception", "kind"], ["Source", "source_id"], ["Reason", "reason"], ["Observed", "created_at"]], data.exceptions, "No recorded reconciliation exception rows. Review residuals and failed jobs above as well.");
    table("run-list", [["Run", "id"], ["State", "state"], ["Opened", "started_at"], ["Actions", (r) => { const actions = node("div", undefined, "toolbar"); if (r.state === "OPEN" && user.role === "approver") for (const action of ["reconcile", "close"]) actions.append(button(action === "close" ? "Close if fully resolved" : "Reconcile", async () => { const job = await api(`/api/runs/${pathId(r.id)}/${action}`, { method: "POST" }); notify(`Requested ${action}. Job ${job.job_id}.`); await refresh(); })); return actions; }]], data.runs, "No runs yet. Opening a run captures actual provider cash and transaction history.");
    const form = $("plan"); setOptions(form.elements.run_id, data.runs.filter((r) => r.state === "OPEN"), (r) => r.id);
    data.invoices = await api("/api/invoices"); setOptions(form.elements.obligation_id, data.invoices.filter((r) => ["READY", "PLANNED", "APPROVED"].includes(r.state)), (r) => `${r.invoice_no_raw || r.id} · ${r.currency} ${r.amount}`); await invoiceBanks();
    $("observed-at").textContent = `Workspace observed ${new Date(data.server_now).toLocaleString()}. Status refreshes every 10 seconds. Source observations retain their own timestamps.`;
    tick();
  } catch (e) { notify(e.message, true); } finally { refreshing = false; }
}
async function signedIn() {
  user = await api("/api/session"); csrf = document.cookie.split("; ").find((c) => c.startsWith("wt_csrf="))?.slice(8) || csrf;
  $("login-panel").hidden = true; $("workspace").hidden = false; $("logout").hidden = false; $("identity").textContent = `${user.name} · ${user.role}`;
  document.querySelectorAll("[data-approver]").forEach((n) => { n.hidden = user.role !== "approver"; }); $("register").hidden = user.passkey_registered;
  await refresh();
}
$("login").addEventListener("submit", async (e) => { e.preventDefault(); const form = e.currentTarget, b = form.querySelector("button"); b.disabled = true; $("error").hidden = true; try { const result = await api("/api/login", { method: "POST", body: { email: form.elements.email.value, password: form.elements.password.value } }); csrf = result.csrf_token; form.reset(); await signedIn(); } catch (err) { notify(err.message, true); } finally { b.disabled = false; } });
$("logout").addEventListener("click", async () => { try { await api("/api/logout", { method: "POST" }); showLogin(); } catch (e) { notify(e.message, true); } });
$("refresh").addEventListener("click", refresh);
$("plan").elements.obligation_id.addEventListener("change", () => invoiceBanks().catch((e) => notify(e.message, true)));
$("plan").addEventListener("submit", async (e) => { e.preventDefault(); const b = e.currentTarget.querySelector("button[type=submit]"); b.disabled = true; try { const terms = Object.fromEntries(new FormData(e.currentTarget)); terms.tranche_no = Number(terms.tranche_no); const job = await api("/api/plans", { method: "POST", body: terms }); notify(`Planning queued. Job ${job.job_id}.`); await refresh(); } catch (err) { notify(err.message, true); } finally { b.disabled = false; } });
$("open-run").replaceWith(button("Open a run from provider balances", async () => { const job = await api("/api/runs", { method: "POST" }); notify(`Opening a run. Job ${job.job_id}.`); await refresh(); }));
// Replaced action retains the server-derived role visibility rule.
$("runs").querySelector(".toolbar button").dataset.approver = "";
$("provider-refresh").replaceWith(button("Refresh wallet observation", async () => { await api("/api/provider/refresh", { method: "POST" }); notify("Wallet refresh requested."); await refresh(); }));
$("register").addEventListener("click", async () => { try { await ceremony("/api/passkeys/register/options", "/api/passkeys/finish", undefined, true); notify("Passkey registered. Ask the installation owner to pin the updated roster before execution."); await signedIn(); } catch (e) { notify(e.message, true); } });
$("policy-sign").addEventListener("click", async () => { try { const policy = await api("/api/policy"); $("policy").replaceChildren(node("pre", JSON.stringify(policy, null, 2)), button("Sign this policy with passkey", async () => { await ceremony("/api/policy/options", "/api/policy/finish"); notify("Policy signature recorded."); await refresh(); })); } catch (e) { notify(e.message, true); } });
$("cancel-back").addEventListener("click", () => $("cancel-dialog").close());
$("cancel-form").addEventListener("submit", async (e) => { e.preventDefault(); try { await api(`/api/approvals/${pathId(cancelId)}/cancel`, { method: "POST", body: { reason: e.currentTarget.elements.reason.value } }); $("cancel-dialog").close(); notify("Approval cancelled. No future signature or execution may use it."); await refresh(); } catch (err) { notify(err.message, true); } });
dependency(); signedIn().catch(() => showLogin()); setInterval(() => { if (!document.hidden) refresh(); }, 10000); setInterval(tick, 1000);
