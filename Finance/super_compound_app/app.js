// Super Compound app.js — handles scenarios, calculations, charting, exports, PWA install prompts
const qs = sel => document.querySelector(sel);
const qsa = sel => Array.from(document.querySelectorAll(sel));

// Utilities
function fmt(e){ return typeof e === 'number' ? e.toLocaleString('nl-NL',{minimumFractionDigits:2,maximumFractionDigits:2}) : e }
function randomColor(i){ const palette=['#0b4f6c','#0077a3','#00a8cc','#7bd389','#ffb86b','#ff7b7b','#9b8cff']; return palette[i % palette.length]}

// State
let scenarios = []; // {id,name,principal,monthly,rate,years,fee,inflation,tax,monthlyCompounding,showMonths}
let activeId = null;

// Elements
const listEl = qs('#list');
const formEls = {
  name: qs('#sc_name'),
  principal: qs('#sc_principal'),
  monthly: qs('#sc_monthly'),
  rate: qs('#sc_rate'),
  years: qs('#sc_years'),
  fee: qs('#sc_fee'),
  inflation: qs('#sc_inflation'),
  tax: qs('#sc_tax'),
  compoundMonthly: qs('#sc_compoundMonthly'),
  includeMonthlyTable: qs('#sc_includeMonthlyTable')
};
const saveBtn = qs('#saveScenario');
const runBtn = qs('#runCalc');
const addBtn = qs('#addScenarioBtn');
const compareBtn = qs('#compareBtn');
const exportCSVBtn = qs('#exportCSV');
const exportJSONBtn = qs('#exportJSON');
const saveLocalBtn = qs('#saveLocal');
const downloadZipBtn = qs('#downloadZipBtn');
const themeToggle = qs('#themeToggle');

// Init
loadFromLocal();
renderList();
attachEvents();
tryRegisterServiceWorker();

function attachEvents(){
  saveBtn.addEventListener('click', e => { e.preventDefault(); saveScenario(); });
  runBtn.addEventListener('click', e => { e.preventDefault(); runCalculation(activeId || createScenarioFromForm()); });
  addBtn.addEventListener('click', e => { e.preventDefault(); clearForm(); activeId = null; });
  compareBtn.addEventListener('click', e => { e.preventDefault(); compareAll(); });
  exportCSVBtn.addEventListener('click', e => { e.preventDefault(); exportCurrentCSV(); });
  exportJSONBtn.addEventListener('click', e => { e.preventDefault(); downloadJSON(); });
  saveLocalBtn.addEventListener('click', e => { e.preventDefault(); saveAllToLocal(); });
  downloadZipBtn.addEventListener('click', e => { e.preventDefault(); window.location.href = 'super_compound_app.zip'; });
  themeToggle.addEventListener('click', toggleTheme);
}

function saveScenario(){
  const sc = createScenarioFromForm();
  const existing = scenarios.find(s => s.id === sc.id);
  if(existing){
    Object.assign(existing, sc);
  } else scenarios.push(sc);
  saveToLocal();
  renderList();
  alert('Scenario opgeslagen');
}

function createScenarioFromForm(){
  // create or update
  const id = activeId || ('sc_' + Date.now());
  return {
    id,
    name: formEls.name.value || 'Scenario ' + (scenarios.length+1),
    principal: Number(formEls.principal.value) || 0,
    monthly: Number(formEls.monthly.value) || 0,
    rate: Number(formEls.rate.value) || 0,
    years: Number(formEls.years.value) || 1,
    fee: Number(formEls.fee.value) || 0,
    inflation: Number(formEls.inflation.value) || 0,
    tax: Number(formEls.tax.value) || 0,
    monthlyCompounding: formEls.compoundMonthly.checked,
    showMonths: formEls.includeMonthlyTable.checked
  };
}

function renderList(){
  listEl.innerHTML='';
  scenarios.forEach((s, idx) => {
    const li = document.createElement('li');
    li.innerHTML = `<div><strong>${s.name}</strong><div class="muted">€${fmt(s.principal)} • €${fmt(s.monthly)}/m • ${s.rate}% • ${s.years} jaar</div></div>`;
    const btns = document.createElement('div');
    const edit = document.createElement('button'); edit.textContent='Bewerk'; edit.onclick = () => { loadIntoForm(s); activeId = s.id; };
    const run = document.createElement('button'); run.textContent='Bereken'; run.onclick = () => runCalculation(s.id);
    const del = document.createElement('button'); del.textContent='Verwijder'; del.onclick = () => { if(confirm('Verwijder scenario?')){ scenarios = scenarios.filter(x=>x.id!==s.id); saveToLocal(); renderList(); }};
    btns.appendChild(edit); btns.appendChild(run); btns.appendChild(del);
    li.appendChild(btns);
    listEl.appendChild(li);
  });
  if(scenarios.length===0){
    listEl.innerHTML = '<li class="muted">Nog geen scenario\'s. Maak er een aan!</li>';
  }
}

function loadIntoForm(s){
  formEls.name.value = s.name;
  formEls.principal.value = s.principal;
  formEls.monthly.value = s.monthly;
  formEls.rate.value = s.rate;
  formEls.years.value = s.years;
  formEls.fee.value = s.fee;
  formEls.inflation.value = s.inflation;
  formEls.tax.value = s.tax;
  formEls.compoundMonthly.checked = s.monthlyCompounding;
  formEls.includeMonthlyTable.checked = s.showMonths;
  activeId = s.id;
  window.scrollTo({top:0,behavior:'smooth'});
}

function clearForm(){ document.querySelector('#scenarioForm').reset(); formEls.name.value='Nieuw'; }

function runCalculation(id){
  const sc = scenarios.find(s=>s.id===id) || createScenarioFromForm();
  if(!scenarios.find(s=>s.id===sc.id)) scenarios.push(sc);
  saveToLocal();
  const result = calculateScenario(sc);
  renderSummary(sc, result);
  renderYearTable(result, sc);
  if(sc.showMonths) renderMonthTable(result, sc);
  drawChart([result], [sc.name]);
}

function calculateScenario(sc){
  // monthly simulation
  const monthlyRate = (sc.rate/100)/12;
  const monthlyFee = (sc.fee/100)/12;
  const months = sc.years * 12;
  let balance = sc.principal;
  const history = [];
  for(let m=1;m<=months;m++){
    // interest
    balance = balance * (1 + monthlyRate);
    // fees on balance
    balance = balance - (balance * monthlyFee);
    // add monthly contribution at end of month
    balance += sc.monthly;
    history.push({month:m, balance: Number(balance.toFixed(2))});
  }
  const totalInput = sc.principal + sc.monthly * months;
  const gross = balance;
  const gains = gross - totalInput;
  const taxAmount = gains * (sc.tax/100);
  const afterTax = gross - taxAmount;
  const inflationFactor = Math.pow(1 + sc.inflation/100, sc.years);
  const realValue = afterTax / inflationFactor;
  return {history, gross, totalInput, gains, taxAmount, afterTax, realValue};
}

function renderSummary(sc, res){
  qs('#summary').innerHTML = `
    <p><strong>${sc.name}</strong> — ${sc.years} jaar</p>
    <p>Eindwaarde (bruto): €${fmt(res.gross)}</p>
    <p>Totaal ingelegd: €${fmt(res.totalInput)}</p>
    <p>Winst (bruto): €${fmt(res.gains)}</p>
    <p>Belasting: €${fmt(res.taxAmount)} ( ${sc.tax}% )</p>
    <p>Eindwaarde (na belasting): €${fmt(res.afterTax)}</p>
    <p>Reële waarde (na inflatie): €${fmt(res.realValue)}</p>
  `;
}

function renderYearTable(res, sc){
  const years = [];
  const months = res.history;
  for(let i=0;i<months.length;i++){
    const y = Math.floor(i/12)+1;
    if(!years[y]) years[y] = {year:y, endBalance: months[i].balance, months:[]};
    years[y].months.push(months[i]);
    years[y].endBalance = months[i].balance;
  }
  let html = `<table><tr><th>Jaar</th><th>Eindwaarde</th><th>Ingelegd tot nu</th><th>Winst</th></tr>`;
  for(let y=1;y<years.length;y++){
    const end = years[y].endBalance;
    const input = sc.principal + sc.monthly * 12 * y;
    html += `<tr><td>${y}</td><td>€${fmt(end)}</td><td>€${fmt(input)}</td><td>€${fmt(end - input)}</td></tr>`;
  }
  html += `</table>`;
  qs('#yearTable').innerHTML = html;
}

function renderMonthTable(res, sc){
  let html = `<table><tr><th>Maand</th><th>Jaar</th><th>Saldo</th></tr>`;
  res.history.forEach(h => {
    const year = Math.floor((h.month-1)/12)+1;
    html += `<tr><td>${h.month}</td><td>${year}</td><td>€${fmt(h.balance)}</td></tr>`;
  });
  html += `</table>`;
  qs('#monthTable').innerHTML = html;
}

function drawChart(results, labels){
  const canvas = qs('#chart'); const ctx = canvas.getContext('2d');
  ctx.clearRect(0,0,canvas.width,canvas.height);
  const maxLen = Math.max(...results.map(r=>r.history.length));
  const maxVal = Math.max(...results.map(r=>Math.max(...r.history.map(h=>h.balance))));
  const pad = 40; const w = canvas.width; const h = canvas.height;
  ctx.strokeStyle = '#e6eef2'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad,h-pad); ctx.lineTo(w-pad,h-pad); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(pad,h-pad); ctx.lineTo(pad,pad); ctx.stroke();
  const legend = qs('#legend'); legend.innerHTML='';
  results.forEach((res, i)=>{
    const color = randomColor(i);
    ctx.beginPath();
    res.history.forEach((pt, idx)=>{
      const x = pad + (idx/(maxLen-1))*(w-2*pad||1);
      const y = h - pad - (pt.balance/maxVal)*(h-2*pad||1);
      if(idx===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    });
    ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
    const item = document.createElement('div'); item.className='item';
    item.innerHTML = `<span class="swatch" style="background:${color}"></span> ${labels[i]}`;
    legend.appendChild(item);
  });
  ctx.fillStyle = '#6b7280'; ctx.font='12px Inter, Arial';
  for(let i=0;i<=4;i++){
    const val = Math.round(maxVal * i/4);
    const y = h - pad - (i/4)*(h-2*pad);
    ctx.fillText('€'+fmt(val), 6, y+4);
  }
}

function exportCurrentCSV(){
  const sc = scenarios.find(s=>s.id===activeId) || createScenarioFromForm();
  const res = calculateScenario(sc);
  let csv = 'Maand,Jaar,Saldo\n';
  res.history.forEach(h=>{
    const year = Math.floor((h.month-1)/12)+1;
    csv += `${h.month},${year},${h.balance}\n`;
  });
  const blob = new Blob([csv], {type:'text/csv'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download = (sc.name || 'scenario') + '.csv'; a.click();
}

function downloadJSON(){
  const data = JSON.stringify(scenarios, null, 2);
  const blob = new Blob([data], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download = 'scenarios.json'; a.click();
}

function saveToLocal(){ localStorage.setItem('super_compound.scenarios', JSON.stringify(scenarios)); }
function loadFromLocal(){ try{ const raw = localStorage.getItem('super_compound.scenarios'); if(raw){ scenarios = JSON.parse(raw); } }catch(e){ scenarios=[] } }
function saveAllToLocal(){ saveToLocal(); alert('Opgeslagen in localStorage'); }

function downloadAllFiles(){ window.location.href = 'super_compound_app.zip'; }

function compareAll(){
  if(scenarios.length===0){ alert('Geen scenario\'s om te vergelijken'); return; }
  const results = scenarios.map(s => calculateScenario(s));
  drawChart(results, scenarios.map(s=>s.name));
  qs('#summary').innerHTML = `<p>Vergelijking van ${scenarios.length} scenario(s)</p>`;
  qs('#yearTable').innerHTML=''; qs('#monthTable').innerHTML='';
}

// Theme toggle (dark/light)
function toggleTheme(){
  const root = document.documentElement;
  root.classList.toggle('dark');
  localStorage.setItem('super_compound.theme', root.classList.contains('dark') ? 'dark' : 'light');
}
(function applySavedTheme(){ const t=localStorage.getItem('super_compound.theme'); if(t==='dark') document.documentElement.classList.add('dark'); })();

// PWA: service worker registration
function tryRegisterServiceWorker(){
  if('serviceWorker' in navigator){
    navigator.serviceWorker.register('sw.js').then(()=>console.log('SW registered')).catch(()=>console.log('SW failed'));
  }
}
