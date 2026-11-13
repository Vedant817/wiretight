"""The demo page: one HTML document that plays the whole scripted run.

Twenty-two frames, each advanced by one click or keypress so the recording is
deterministic. The disclosure footer is rendered on every frame,
and every frame is rendered from the payload the seed module
computed with the real core modules.
"""

from __future__ import annotations

from typing import Any, Final

_PAGE: Final[str] = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Wiretight</title>
<style>
:root{
  --bg:#0e1116; --panel:#171c24; --panel2:#1d242f; --line:#2a3342;
  --text:#e8edf4; --dim:#93a1b5; --red:#e5544b; --red-bg:#3a1715;
  --green:#3fb374; --green-bg:#12281c; --amber:#d99a2b; --amber-bg:#332510;
  --blue:#5b9bd5; --blue-bg:#14222f; --purple:#8f7ad6;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
  font-size:20px;overflow:hidden}
#app{position:absolute;inset:0;display:flex;flex-direction:column}
#badge{position:fixed;top:14px;right:16px;z-index:50;background:#401313;color:#ffd9d6;
  border:1px solid #a34a44;padding:8px 14px;border-radius:6px;font-weight:700;
  font-size:15px;letter-spacing:.4px}
#chips{position:fixed;top:14px;left:16px;z-index:50;display:flex;gap:8px}
.chip{background:var(--panel2);border:1px solid var(--line);color:var(--dim);
  padding:6px 12px;border-radius:6px;font-size:14px;font-weight:600;letter-spacing:.5px}
.chip.on{background:#243b53;color:#cfe6ff;border-color:#3f6d9e}
.chip.goal.on{background:#123322;color:#9fe6bd;border-color:#2c6e4b}
.chip.rev.on{background:#3a1715;color:#ffb3ae;border-color:#a34a44}
#stage{flex:1;display:flex;align-items:center;justify-content:center;padding:70px 90px 90px}
.frame{width:100%;max-width:1640px;display:none}
.frame.on{display:block}
h1{font-size:56px;margin-bottom:10px}
h2{font-size:36px;margin-bottom:8px}
.sub{color:var(--dim);font-size:22px;margin-bottom:22px}
.tag{display:inline-block;background:#2c3442;color:#b8c4d6;border:1px solid #3d4859;
  font-size:16px;padding:2px 8px;border-radius:4px;margin-left:8px;vertical-align:middle}
.tag.mock{background:#2b2113;color:#e8c377;border-color:#6d5728}
.tag.fix{background:#1d2b3a;color:#8fc1e8;border-color:#33628c}
.tag.red{background:#3a1715;color:#ffb3ae;border-color:#a34a44}
.tag.grn{background:#12281c;color:#8fdcae;border-color:#2c6e4b}
.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:16px 20px;font-size:19px}
.card .amt{font-size:30px;font-weight:700;float:right}
.card .vend{font-weight:700}
.card .meta{color:var(--dim);font-size:15px;margin-top:4px}
.card.blocked{border-color:#a34a44;background:var(--red-bg)}
.card.void{border-color:#a34a44;background:var(--red-bg);animation:pop .4s ease}
.card.paid{border-color:#2c6e4b}
.card.held{border-color:#6d5728;background:var(--amber-bg)}
.card.defer{border-color:#33628c}
@keyframes pop{0%{transform:scale(.98);background:#171c24}100%{}}
.big{font-size:26px}
.mono{font-family:Consolas,monospace}
.dim{color:var(--dim)}
.red{color:var(--red)} .green{color:var(--green)} .amber{color:var(--amber)} .blue{color:var(--blue)}
.row{display:flex;gap:24px;align-items:stretch}
.col{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px}
.stat{font-size:44px;font-weight:800;color:#cfe6ff}
table{width:100%;border-collapse:collapse;font-size:18px}
td,th{border-bottom:1px solid var(--line);padding:9px 12px;text-align:left}
th{color:var(--dim);font-size:14px;text-transform:uppercase;letter-spacing:.6px}
.num{text-align:right;font-family:Consolas,monospace}
.tot td{font-weight:800;border-top:2px solid var(--line)}
.badge-ok{color:var(--green);font-weight:700}
.btn{display:inline-block;padding:9px 22px;border-radius:8px;border:1px solid var(--line);
  background:var(--panel2);color:var(--text);font-size:18px;font-weight:600}
.btn.dis{opacity:.45;border-color:#5b2c28;background:#2a1614;color:#d99e99}
.btn.go{background:#123322;border-color:#2c6e4b;color:#9fe6bd}
.banner{background:var(--blue-bg);border:1px solid #2d4f6e;border-radius:10px;
  padding:18px 24px;font-size:26px;font-weight:600;margin-bottom:20px}
.rulebar{background:#241012;border:1px solid #a34a44;border-radius:10px;padding:22px 28px;
  font-size:30px;font-weight:700}
.evid{display:inline-block;background:#3a1715;border:1px solid #a34a44;color:#ffb3ae;
  border-radius:20px;padding:5px 14px;font-size:16px;margin:4px 6px 0 0}
.steps{display:flex;gap:12px;margin:18px 0}
.step{flex:1;background:var(--panel2);border:1px solid var(--line);border-radius:10px;
  padding:16px;text-align:center;font-size:17px}
.step .n{display:block;width:max-content;min-width:34px;min-height:34px;
  line-height:34px;padding:0 12px;border-radius:17px;
  background:#243b53;color:#cfe6ff;margin:0 auto 12px;font-weight:700}
#nav{position:fixed;bottom:18px;right:20px;z-index:50;display:flex;gap:10px;align-items:center}
#frameinfo{color:var(--dim);font-size:13px;margin-right:6px}
#next{background:#243b53;border-color:#3f6d9e;color:#cfe6ff;padding:10px 26px;font-size:17px}
#cap{position:fixed;bottom:18px;left:20px;color:var(--dim);font-size:14px;z-index:50}
.footnote{color:var(--dim);font-size:16px;margin-top:14px;line-height:1.5}
.slide{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:44px 48px}
.center{text-align:center}
li{margin:8px 0 8px 24px;font-size:20px}
.capline{font-size:34px;font-weight:800;color:#ffb3ae;margin-top:18px}
</style>
</head>
<body>
<div id="app">
  <div id="chips"></div>
  <div id="stage"></div>
  <div id="cap">Synthetic company data · Airwallex API responses simulated · cooling-off shortened for recording</div>
  <div id="nav">
    <span id="frameinfo"></span>
    <button id="next" class="btn">Next &gt;</button>
  </div>
</div>
<script id="payload" type="application/json">__PAYLOAD_JSON__</script>
<script>
const P = JSON.parse(document.getElementById('payload').textContent);
const CHIPS = ['GOAL','INITIAL PLAN','NEW INFO','REVISED DECISION','RESULT'];

const T = {
  synth: ()=>'',
  mock: ()=>'',
  fix: ()=>'',
  red: (t)=>`<span class="tag red">${t}</span>`,
  grn: (t)=>`<span class="tag grn">${t}</span>`,
  dt: ()=>'',
  ass: (t)=>`<span class="tag">${t||'ASSUMPTION'}</span>`,
};
const inc = P.incident, cb = P.callbacks, tr = P.transfers;

function payCards(filter){
  return P.payments.filter(filter).map(p=>{
    let cls='';
    if(p.no===2) cls = window.__flipped ? 'void' : '';
    else if(p.no===4) cls='blocked';
    else if(p.state.startsWith('PAID')) cls='paid';
    else if(p.state==='DEFERRED') cls='defer';
    const st = p.no===2 ? (window.__flipped ? 'VOID: bank fingerprint changed' : 'SIGNED OFF') : p.state.replace('_',' ');
    return `<div class="card ${cls}">
      <span class="amt">${p.currency==='EUR'?'&euro;':p.currency==='GBP'?'&pound;':'$'}${Number(p.amount).toLocaleString('en-IE')}</span>
      <div class="vend">#${p.no} ${p.vendor}</div>
      <div class="meta">INV ${p.invoice_no} · ${p.currency} ${p.amount} · ${p.method} · ${st}</div>
    </div>`;
  }).join('');
}

const FRAMES = [
 {chips:['RESULT'], title:'Cold open',
  html:()=>`<h1 id="cohead">Payment run - week of 9 Nov 2026</h1>
  <div class="sub">Halden Robotics</div>
  <div class="cards">${payCards(()=>true)}</div>`},

 {chips:[], title:'Title',
  html:()=>`<div class="slide center"><h1>Wiretight</h1>
  <div class="big dim">Supplier payouts that can't be quietly redirected.</div>
  </div>`},

 {chips:[], title:'Problem - the numbers',
  html:()=>`<div class="slide"><h2>Supplier payment fraud, 2024-2026</h2>
  <div class="cards" style="margin-top:20px">
   <div class="card"><div class="stat">74%</div>of US organisations hit by business email compromise in 2025</div>
   <div class="card"><div class="stat">45%</div>cited vendor imposter fraud - up 11 points on the year before</div>
   <div class="card"><div class="stat">$2.77B</div>BEC losses reported to the FBI in 2024</div>
   <div class="card"><div class="stat">2nd channel</div>the FBI's advice: verify account-change requests out of band</div>
  </div>
  <div class="footnote">Sources: AFP 2026 Payments Fraud and Control Survey (74%, 17% AI adoption);
  AFP 2025 survey (45%, +11 pts); FBI IC3 2024 Annual Report ($2.77B); FBI PSA 240911 (secondary channel).</div></div>`},

 {chips:[], title:'Who it is for',
  html:()=>`<div class="slide"><h2>Who Wiretight is for</h2>
  <div class="card" style="margin-top:18px;font-size:24px;padding:26px">
    Finance lead / founder-operator, 10-200 people ${T.ass()}<br>
    <span class="dim" style="font-size:20px">pays USD · EUR · GBP suppliers from Airwallex, weekly run</span>
  </div>
  <div class="banner" style="margin-top:22px">The fraud loss lands on the payer. So the payer owns the check.</div>
  <div class="footnote">Company size is an assumption for the pitch, not a measured claim.</div></div>`},

 {chips:[], title:'Why now',
  html:()=>`<div class="slide"><h2>Why now</h2>
  <div class="cards" style="margin-top:18px">
   <div class="card"><b>One API.</b><br><span class="dim">Balances, FX, beneficiaries, payouts and the ledger - all through Airwallex.</span></div>
   <div class="card"><b>Models that can read the inbox.</b><br><span class="dim">Messy bills and emails parsed well enough to raise flags.</span></div>
  </div>
  <div class="banner" style="margin-top:22px">Yet only <b>17%</b> of organisations use AI against payments fraud.</div>
  <div class="footnote">Source: AFP 2026 Payments Fraud and Control Survey. API surface: public Airwallex documentation.</div></div>`},

 {chips:[], title:'The rule',
  html:()=>`<div class="rulebar">No payout reaches bank details a human hasn't confirmed and signed off on exact terms.</div>
  <div class="dim" style="margin-top:14px">Every decision you are about to see is computed by the real Wiretight modules - parsers, duplicate detection, fingerprints, callback rules, the ledger.</div>`},

 {chips:['GOAL','INITIAL PLAN'], title:'The run and the plan',
  html:()=>`<div class="banner">Pay this week's bills on time, once, to the real supplier - never below the USD 8,000 reserve.</div>
  <div class="cards">${payCards(p=>true)}</div>
  <div class="row" style="margin-top:14px">
    <div class="col"><b>Reserve check</b><br><span class="dim">Opening $26,400 · floor $8,000 · after planned payouts $8,240; paying #6 would drop it to $4,340 → deferred.</span></div>
    <div class="col"><b>One conversion for two bills</b><br><span class="dim">Single GBP conversion funds #3 and #7. EUR 7,500 conversion funds #2.</span></div>
  </div>`},

 {chips:['NEW INFO'], title:'The email',
  html:()=>`<div class="slide"><h2>Inbox - new info ${T.synth()}</h2>
  <div class="card" style="margin-top:18px;font-size:20px">
    <div><b>From:</b> arun.schmidt@<span class="red mono">brandt-gmbh.co</span>
      <span class="dim">(on file: brandt-gmbh.de - edit distance 2, flagged by the real lookalike detector)</span></div>
    <div style="margin-top:8px"><b>Subject:</b> New bank account for INV-2291 - urgent before Friday</div>
    <div style="margin-top:8px" class="mono">"New bank account for INV-2291, urgent before Friday.
    Call me back on +370 604 22114 to confirm." <span class="red">NEW COUNTRY: LT</span></div>
    <div style="margin-top:10px"><b>New IBAN:</b> <span class="mono">LT12 •••• •••• •••• 2000</span>
      (on file: DE89 •••• •••• 3000)</div>
  </div>
  <div class="banner" style="margin-top:20px">New account · urgent · one letter off.</div>`},

 {chips:['REVISED DECISION'], title:'The lock fires (1 of 2)',
  html:()=>`<div class="row">
   <div class="col"><h2 style="font-size:28px">Fingerprint diff</h2>
    <table>
     <tr><th></th><th>On file</th><th>In email</th></tr>
     <tr><td>IBAN</td><td class="mono">DE89 •••• 3000</td><td class="mono red">LT12 •••• 2000</td></tr>
     <tr><td>Country</td><td>DE</td><td class="red">LT</td></tr>
     <tr><td>BIC</td><td class="mono">COBADEFF</td><td class="mono red">REVOLT21</td></tr>
     <tr><td>Fingerprint</td><td class="mono">${inc.fingerprint.on_file.fingerprint.slice(0,10)}…</td>
         <td class="mono red">${inc.fingerprint.new.fingerprint.slice(0,10)}…</td></tr>
     <tr><td>Format check</td><td class="green">VALID</td><td class="green">VALID</td></tr>
    </table>
    <div style="margin-top:14px"><span class="big red">Format VALID &ne; legitimate.</span></div>
    <div style="margin-top:8px">${inc.evidence_chips.map(c=>`<span class="evid">${c}</span>`).join('')}</div>
   </div>
   <div class="col"><h2 style="font-size:28px">What the code refused</h2>
    <ul>
     ${inc.rule_refusals.map(r=>`<li><b class="red">${r.rule} - refused:</b><br><span class="dim" style="font-size:17px">${r.detail}</span></li>`).join('')}
     <li><b>Sign-off voided:</b> the signature covered the old account. A new fingerprint kills it.</li>
    </ul>
    <div class="card blocked" style="margin-top:14px"><b>#2 Brandt GmbH - EUR 7,500</b><br>
      <span class="dim">state: SIGNED OFF → <b class="red">VOID</b></span></div>
   </div></div>`},

 {chips:['REVISED DECISION'], title:'Plan diff - surgical',
  html:()=>`<div class="banner">Only #2 is blocked. Everything else still goes out.</div>
  <div class="cards">${payCards(p=>p.no!==2)}
   <div class="card blocked"><span class="amt red">BLOCKED</span>
    <div class="vend">#2 Brandt GmbH</div>
    <div class="meta">EUR 7,500 · sign-off VOID · awaiting callback</div></div>
  </div>
  <div class="row" style="margin-top:14px">
   <div class="col"><b>EUR conversion for #2</b> - <span class="amber">WITHDRAWN ${T.mock()}</span>
     <div class="dim" style="font-size:17px">before any money moves. EUR 7,500 never leaves the USD balance.</div></div>
   <div class="col"><b>Everything else</b> - unchanged
     <div class="dim" style="font-size:17px">#1 · #3 · #7 proceed; #6 stays deferred; #4 stays hard-blocked.</div></div>
  </div>`},

 {chips:['RESULT'], title:'Rule 3 - requester cannot confirm',
  html:()=>`<div class="slide"><h2>Record callback - payment #2</h2>
  <div class="card" style="margin-top:18px;font-size:22px">
    <div><b>Requester:</b> Arun <span class="dim">(raised the change request)</span></div>
    <div style="margin-top:12px"><button class="btn dis" disabled>Record callback</button>
    <span class="red" style="margin-left:12px">disabled - the requester cannot confirm their own request</span></div>
  </div>
  <div class="dim" style="margin-top:16px">Rule: the callback must be recorded by someone independent of the request. Enforced in code, not by convention.</div></div>`},

 {chips:['RESULT'], title:'Priya calls the number on file',
  html:()=>`<div class="slide"><h2>Record callback - payment #2</h2>
  <div class="row" style="margin-top:16px">
   <div class="col"><b>Calls the contact on file ${T.fix()}</b><br>
    <span class="dim">+49 89 •••• 08400 · created 2025-09-10 · 14 months on file · NOT the number in the email</span></div>
   <div class="col"><b>Outcome recorded by Priya</b><br>
    <span class="green big">"No change made."</span><br>
    <span class="dim" style="font-size:17px">readback: last-4 OK · name OK · recorder signature verified (${cb.rejection.signature_method})</span></div>
  </div></div>`},

 {chips:['RESULT'], title:'Request rejected, real invoice paid',
  html:()=>`<div class="slide">
   <div class="banner" style="background:var(--red-bg);border-color:#a34a44">Change request → REJECTED · fraudulent IBAN: never paid.</div>
   <div class="row" style="margin-top:14px">
    <div class="col"><b>Sign-off (2, flagged supplier)</b><br>
      <span class="dim">Meera (passkey) · Kabir (passkey) - to the account on file,
      exact terms: Brandt GmbH · EUR 7,500 · DE89 •••• 3000</span></div>
    <div class="col"><b>Why two?</b><br>
      <span class="dim">The vendor was flagged by the incident, so the policy escalates this
      payout to two signatures.</span></div>
   </div></div>`},

 {chips:['NEW INFO'], title:'The payout comes back',
  html:()=>`<div class="slide"><h2>Transfer status timeline - #2 original ${T.mock()}</h2>
  <div class="steps" style="margin-top:22px">
    <div class="step"><div class="n">1</div>SENT<div class="dim" style="font-size:15px">money left</div></div>
    <div class="step"><div class="n">2</div><span class="red"><b>FAILED</b></span><div class="dim" style="font-size:15px">ACCOUNT_CLOSED</div></div>
    <div class="step"><div class="n">3</div><b>CANCELLED</b><div class="dim" style="font-size:15px">original outcome recorded</div></div>
  </div>
  <div class="banner">The supplier's account was closed. The payout came back.</div></div>`},

 {chips:['REVISED DECISION'], title:'The genuine request (2 of 2)',
  html:()=>`<div class="slide"><h2>Recovery - same lock, no shortcut</h2>
  <div class="card" style="margin-top:16px;font-size:20px">
    <div><b>From:</b> arun.schmidt@<span class="green mono">brandt-gmbh.de</span> ${T.synth()}
      <span class="dim">- the known domain this time</span></div>
    <div style="margin-top:8px"><b>New IBAN:</b> <span class="mono">DE44 •••• •••• •••• 4931</span>
      ${T.fix('documented shape')}</div>
  </div>
  <div class="row" style="margin-top:14px">
   <div class="col"><b>Priya's callback</b><br><span class="green">CONFIRMED</span>
     <span class="dim">· signed (${cb.recovery.signature_method}) · to the older contact on file</span></div>
   <div class="col"><b>Lock steps</b><br><span class="dim">callback to older contact ✓ · cooling-off · 2 sign-offs · capped first payment</span></div>
  </div>
  <div class="banner" style="margin-top:16px">That is exactly where redirection fraud hides. So recovery gets no shortcut.</div></div>`},

 {chips:['REVISED DECISION'], title:'Cooling-off, sign-offs, cap',
  html:()=>`<div class="slide"><h2>The lock, in order</h2>
  <div class="steps" style="margin-top:18px">
    <div class="step"><div class="n">1</div>Cooling-off<div class="dim" style="font-size:15px">72h policy · shown as 2:00 ${T.dt()}<br>until ${cb.recovery.cooling_off_until.slice(0,10)}</div></div>
    <div class="step"><div class="n">2</div>Two sign-offs<div class="dim" style="font-size:15px">${cb.recovery.sign_offs.join(' · ')}</div></div>
    <div class="step"><div class="n">3</div>First payment capped<div class="dim" style="font-size:15px">min(floor, 50%×median) = USD ${cb.recovery.cap_usd}</div></div>
  </div>
  <div class="card" style="margin-top:14px"><b>Tranches (real tranche_split)</b><br>
    <span class="big">Tranche 1: EUR ${cb.recovery.tranches[0].amount}</span>
    <span class="dim"> · Tranche 2: EUR ${cb.recovery.tranches[1].amount} (held)</span></div>
  <div style="margin-top:14px"><button class="btn go">Replace original transfer</button>
    <span class="dim" style="margin-left:10px">enabled only because the original is CANCELLED</span></div></div>`},

 {chips:['RESULT'], title:'Tranche 1 out, tranche 2 held',
  html:()=>`<div class="slide"><h2>Recovery payout ${T.mock()}</h2>
  <div class="steps" style="margin-top:20px">
   <div class="step"><div class="n">T1</div><span class="green"><b>EUR ${tr.tranche1.amount} · PAID · provisional</b></span>
     </div>
   <div class="step"><div class="n">T2</div><span class="amber"><b>EUR ${tr.tranche2.amount} · HELD</b></span>
     <div class="dim" style="font-size:15px">until tranche 1 is final</div></div>
  </div>
  <div class="banner">${tr.paid_can_still_fail_note}</div>
  <div class="dim">Airwallex transfer-status documentation: PAID is not a guarantee of settlement.</div></div>`},

 {chips:['RESULT'], title:'Tie-out',
  html:()=>`<div class="slide"><h2>Tie-out, per currency ${T.fix()}</h2>
  <table style="margin-top:14px">
   <tr><th>Currency</th><th class="num">Opening</th><th class="num">+ In</th><th class="num">- Out</th>
       <th class="num">+ Refunds</th><th class="num">- Fees</th><th class="num">= Closing</th></tr>
   ${P.tieout.rows.map(r=>`<tr><td><b>${r.currency}</b> <span class="dim" style="font-size:14px">${r.note||''}</span></td>
     <td class="num">${r.opening}</td><td class="num">${r['in']}</td><td class="num">${r.out}</td>
     <td class="num">${r.refunds}</td><td class="num">${r.fees}</td>
     <td class="num badge-ok">${r.closing}</td></tr>`).join('')}
   <tr class="tot"><td class="dim">ledger check</td><td colspan="6" class="badge-ok">BALANCED - real ledger legs, real balance check; a gap would be shown, never plugged</td></tr>
  </table>
  <div class="dim" style="margin-top:12px">Journal export for the books: one CSV per run. ${P.tieout.journal_export}</div></div>`},

 {chips:['RESULT'], title:'Status board',
  html:()=>`<div class="slide"><h2>End-of-run status board ${T.fix()}</h2>
  <div class="row" style="margin-top:12px">
   <div class="col" style="padding:10px 20px"><table style="font-size:17px">
     ${P.status_board.map(s=>`<tr><td>${s.item}</td><td style="text-align:right;font-weight:700">${s.state}</td></tr>`).join('')}
   </table></div>
   <div class="col" style="flex:.6"><b>Audit chain</b><br>
     <span class="dim" style="font-size:17px">${P.audit.checked} entries · verified · head ${P.audit.head}</span><br>
     <span class="dim" style="font-size:15px">hash chain computed by the real audit module</span></div>
  </div></div>`},

 {chips:[], title:'Architecture',
  html:()=>`<div class="slide"><h2>Controlled autonomy</h2>
  <div class="steps" style="margin-top:20px">
    <div class="step"><div class="n">LLM</div>at the edge<div class="dim" style="font-size:15px">reads · flags · drafts. Never decides money.</div></div>
    <div class="step"><div class="n">CODE</div>deterministic core<div class="dim" style="font-size:15px">parsers · duplicates · planner · reserve floor</div></div>
    <div class="step"><div class="n">HUMAN</div>passkey sign-off<div class="dim" style="font-size:15px">exact payee · account · amount · currency</div></div>
    <div class="step"><div class="n">EXEC</div>executor<div class="dim" style="font-size:15px">the only holder of the Airwallex key · re-checks every signature</div></div>
  </div>
  <div class="banner" style="margin-top:16px">Airwallex API surface: Balances · FX rates, quotes &amp; conversions · Beneficiaries · Transfers · Simulation · Financial transactions</div>
  <div class="footnote">The executor itself is not yet built.</div></div>`},

 {chips:[], title:'Business model',
  html:()=>`<div class="slide"><h2>Adoption path</h2>
  <div class="steps" style="margin-top:18px">
    <div class="step"><div class="n">1</div>Existing Airwallex account</div>
    <div class="step"><div class="n">2</div>Shadow mode<div class="dim" style="font-size:15px">moves no money · reports what it would have caught</div></div>
    <div class="step"><div class="n">3</div>One sign-off</div>
    <div class="step"><div class="n">4</div>Auto-pay, earned per supplier</div>
  </div>
  <div class="banner" style="margin-top:16px">Pricing: per-entity monthly for SMBs; later per-client for bookkeeping firms ${T.ass('hypothesis, unvalidated')}</div></div>`},

 {chips:[], title:'Close',
  html:()=>`<div class="slide"><h2>Shadow mode, this run ${T.fix('synthetic rows')}</h2>
  <table style="margin-top:14px;font-size:19px">
   ${P.shadow_rows.map(r=>`<tr><td>${r.row}</td><td style="text-align:right;font-weight:700" class="green">${r.would_catch}</td></tr>`).join('')}
  </table>
  <div class="center" style="margin-top:30px">
    <div class="big" style="font-size:40px;font-weight:800">Wiretight.</div>
    <div class="dim" style="font-size:24px">Supplier payouts that can't be quietly redirected.</div>
    <div class="footnote">all data synthetic</div>
  </div></div>`},
];

let idx = 0;
let __flipped = false;
window.__flipped = false;
function chipHtml(active){
  return CHIPS.map(c=>{
    const on = active.includes(c);
    const cls = c==='GOAL' ? 'goal' : (c==='REVISED DECISION' ? 'rev' : '');
    return `<div class="chip ${cls} ${on?'on':''}">${c}</div>`;
  }).join('');
}
function render(){
  if(idx < 0 || idx >= FRAMES.length) return;
  const f = FRAMES[idx];
  const stage = document.getElementById('stage');
  stage.innerHTML = `<div class="frame on">${f.html()}</div>`;
  document.getElementById('chips').innerHTML = chipHtml(f.chips);
  document.getElementById('frameinfo').textContent = (idx+1) + ' / ' + FRAMES.length;
}
function next(){ if(idx < FRAMES.length-1){ idx++; render(); } }
function prev(){ if(idx > 0){ idx--; render(); } }
window.__wt = {next, prev, go:(i)=>{idx=i;render();}, state:()=>idx,
  title:()=>FRAMES[idx].title,
  flip:(value)=>{window.__flipped=value;render();}};
document.getElementById('next').addEventListener('click', next);
document.addEventListener('keydown', e=>{
  if(e.key==='ArrowRight' || e.key===' ') next();
  if(e.key==='ArrowLeft') prev();
});
// Cold-open flip: payment #2 flips to VOID five seconds into frame 0.
if(!new URLSearchParams(location.search).has('capture')) setTimeout(()=>{
  __flipped = true;
  window.__flipped = true;
  const h = document.getElementById('cohead');
  if(h){ h.textContent = 'VOID: bank fingerprint changed'; h.className = 'red'; }
  if(window.__wt.state()===0){ idx=0; render(); }
}, 5000);
render();
</script>
</body>
</html>
"""


def render_page(payload: dict[str, Any]) -> str:
    """Inject the seed payload into the page template."""
    import json

    return _PAGE.replace("__PAYLOAD_JSON__", json.dumps(payload, ensure_ascii=True))
