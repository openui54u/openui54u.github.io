// Advanced Market Analyst app.js
// - Multiple providers (finnhub, alpha) with fallback
// - Multi-symbol fetching (daily/intraday)
// - TA indicators (SMA, EMA, RSI, MACD)
// - Simple SMA crossover backtester (50/200)
// NOTE: supply API keys in the format: finnhub=KEY;alpha=KEY

const providersInput = document.getElementById('providers');
const keysInput = document.getElementById('keys');
const symbolsInput = document.getElementById('symbols');
const intervalInput = document.getElementById('interval');
const loadAllBtn = document.getElementById('loadAll');
const backtestAllBtn = document.getElementById('backtestAll');
const listEl = document.getElementById('list');
const chartsEl = document.getElementById('charts');
const analysisEl = document.getElementById('analysis');
const backtestEl = document.getElementById('backtestResults');

loadAllBtn.addEventListener('click', async ()=>{
  clearUI();
  const providers = providersInput.value.split(',').map(s=>s.trim()).filter(Boolean);
  const keys = parseKeys(keysInput.value);
  const symbols = symbolsInput.value.split(',').map(s=>s.trim()).filter(Boolean);
  const interval = intervalInput.value;
  for(const sym of symbols){
    try{
      const data = await fetchWithFallback(sym, interval, providers, keys);
      renderSymbol(sym, data);
    } catch(err){
      console.error('Error', sym, err);
      addToWatchlist(sym, 'error: '+err.message);
    }
  }
});

backtestAllBtn.addEventListener('click', async ()=>{
  backtestEl.innerHTML = '<div class="card"><strong>Backtest running…</strong></div>';
  const symbols = symbolsInput.value.split(',').map(s=>s.trim()).filter(Boolean);
  const providers = providersInput.value.split(',').map(s=>s.trim()).filter(Boolean);
  const keys = parseKeys(keysInput.value);
  const results = [];
  for(const sym of symbols){
    try{
      const data = await fetchWithFallback(sym, 'daily', providers, keys);
      const bt = backtestSMACrossover(data, 50, 200);
      results.push({symbol:sym, result:bt});
    }catch(e){
      results.push({symbol:sym, error:e.message});
    }
  }
  renderBacktest(results);
});

function parseKeys(s){
  const map = {};
  s.split(';').map(x=>x.trim()).forEach(pair=>{
    if(!pair) return;
    const [k,v]=pair.split('=').map(t=>t.trim());
    if(k && v) map[k]=v;
  });
  return map;
}

async function fetchWithFallback(symbol, interval, providers, keys){
  let lastErr = null;
  for(const p of providers){
    try{
      if(p==='finnhub') return await fetchFinnhub(symbol, interval, keys['finnhub']);
      if(p==='alpha') return await fetchAlpha(symbol, interval, keys['alpha']);
    }catch(e){
      lastErr = e;
      console.warn('Provider failed', p, e.message);
    }
  }
  throw lastErr || new Error('No provider succeeded');
}

async function fetchAlpha(symbol, interval, apikey){
  if(!apikey) throw new Error('Alpha key missing');
  const base = 'https://www.alphavantage.co/query?';
  if(interval==='daily'){
    const url = base + new URLSearchParams({function:'TIME_SERIES_DAILY_ADJUSTED',symbol,outputsize:'compact',apikey});
    const res = await fetch(url); const j = await res.json();
    if(j['Error Message']) throw new Error('Alpha error: '+j['Error Message']);
    const ts = j['Time Series (Daily)'] || j['Time Series (Daily)'];
    if(!ts) throw new Error('Alpha returned no time series');
    const entries = Object.keys(ts).sort().map(date=>({date, open:+ts[date]['1. open'], high:+ts[date]['2. high'], low:+ts[date]['3. low'], close:+ts[date]['4. close'], volume:+ts[date]['6. volume']||+ts[date]['5. volume']}));
    return entries;
  } else {
    const url = base + new URLSearchParams({function:'TIME_SERIES_INTRADAY',symbol,interval:interval,outputsize:'compact',apikey});
    const res = await fetch(url); const j = await res.json();
    const key = 'Time Series ('+interval+')';
    const ts = j[key];
    if(!ts) throw new Error('Alpha intraday no data or rate limited');
    const entries = Object.keys(ts).sort().map(date=>({date, open:+ts[date]['1. open'], high:+ts[date]['2. high'], low:+ts[date]['3. low'], close:+ts[date]['4. close'], volume:+ts[date]['5. volume']}));
    return entries;
  }
}

async function fetchFinnhub(symbol, interval, apikey){
  if(!apikey) throw new Error('Finnhub key missing');
  const base = 'https://finnhub.io/api/v1/';
  const now = Math.floor(Date.now()/1000);
  const days = interval==='daily'? 365 : 30;
  const from = now - 3600*24*days;
  const resolution = interval==='15min'?'15': interval==='60min'?'60':'D';
  const url = base + 'stock/candle?' + new URLSearchParams({symbol, resolution, from, to:now, token:apikey});
  const res = await fetch(url); const j = await res.json();
  if(j.s!=='ok') throw new Error('Finnhub error: ' + JSON.stringify(j));
  const entries = j.t.map((t,i)=>({date:new Date(j.t[i]*1000).toISOString(), open:j.o[i], high:j.h[i], low:j.l[i], close:j.c[i], volume:j.v[i]}));
  return entries;
}

// Indicators
function sma(values, period){
  const out = [];
  for(let i=0;i<values.length;i++){
    if(i<period-1) { out.push(null); continue; }
    let sum=0; for(let j=0;j<period;j++) sum+=values[i-j];
    out.push(sum/period);
  }
  return out;
}
function ema(values, period){
  const out=[]; const k=2/(period+1); let prev=null;
  for(let i=0;i<values.length;i++){ const v=values[i]; if(i===0){ prev=v; out.push(v); continue;} const cur=(v-prev)*k+prev; out.push(cur); prev=cur; }
  for(let i=0;i<period-1 && i<out.length;i++) out[i]=null; return out;
}
function rsi(values, period=14){
  const out=[]; let gains=0, losses=0;
  for(let i=0;i<values.length;i++){ if(i===0){ out.push(null); continue;} const change=values[i]-values[i-1]; const g=Math.max(0,change), l=Math.max(0,-change);
    if(i<=period){ gains+=g; losses+=l; if(i===period){ const avgG=gains/period, avgL=losses/period; const rs=avgG/(avgL||1e-9); out.push(100-(100/(1+rs))); } else out.push(null);
    } else { gains=(gains*(period-1)+g)/period; losses=(losses*(period-1)+l)/period; const rs=gains/(losses||1e-9); out.push(100-(100/(1+rs))); } }
  return out;
}
function macd(values, fast=12, slow=26, signal=9){ const ef=ema(values,fast), es=ema(values,slow); const macdLine=values.map((v,i)=> (ef[i]==null||es[i]==null)?null:ef[i]-es[i]); const sig=ema(macdLine.map(x=>x==null?0:x), signal); const hist=macdLine.map((m,i)=> m==null||sig[i]==null?null:m-sig[i]); return {macdLine:sig?macdLine:[], signalLine:sig, hist}; }

// Rendering
function addToWatchlist(symbol, note){
  const li = document.createElement('li');
  li.innerHTML = `<div><strong>${symbol}</strong><div class="muted">${note||''}</div></div>`;
  listEl.appendChild(li);
}
function clearUI(){ listEl.innerHTML=''; chartsEl.innerHTML=''; analysisEl.innerHTML=''; backtestEl.innerHTML=''; }

function renderSymbol(symbol, data){
  addToWatchlist(symbol, `Data points: ${data.length}`);
  const closes = data.map(d=>d.close);
  const dates = data.map(d=>d.date);
  const sma50 = sma(closes,50);
  const sma200 = sma(closes,200);
  const latest = closes[closes.length-1];
  const score = computeScore(closes, sma50, sma200);
  const div = document.createElement('div');
  div.className = 'card';
  div.innerHTML = `<h4>${symbol} — laatste: €${latest.toFixed(2)}</h4>
    <div>Score: ${score.toFixed(2)}</div>
    <div>Laatste SMA50: ${sma50[sma50.length-1] ? sma50[sma50.length-1].toFixed(2) : 'n/a'}</div>
    <div>Laatste SMA200: ${sma200[sma200.length-1] ? sma200[sma200.length-1].toFixed(2) : 'n/a'}</div>`;
  chartsEl.appendChild(div);
  analysisEl.appendChild(div.cloneNode(true));
}
function computeScore(closes, sma50, sma200){
  const last = closes.length-1;
  let score = 0;
  if(sma50[last] && sma200[last]) score += sma50[last] > sma200[last] ? 1 : -1;
  const avg20 = closes.slice(Math.max(0,closes.length-20)).reduce((a,b)=>a+b,0)/(Math.min(20,closes.length)||1);
  score += closes[last] > avg20 ? 0.5 : -0.5;
  return score;
}

// Backtester
function backtestSMACrossover(data, short=50, long=200){
  const closes = data.map(d=>d.close);
  const dates = data.map(d=>d.date);
  const s = sma(closes, short);
  const l = sma(closes, long);
  let position = 0;
  let cash = 10000; let shares = 0;
  const trades = [];
  for(let i=0;i<closes.length;i++){
    if(s[i] && l[i]){
      if(position===0 && s[i] > l[i]){
        shares = cash / closes[i];
        trades.push({type:'buy', date:dates[i], price:closes[i], shares});
        cash = 0; position = 1;
      } else if(position===1 && s[i] < l[i]){
        cash = shares * closes[i];
        trades.push({type:'sell', date:dates[i], price:closes[i], shares});
        shares = 0; position = 0;
      }
    }
  }
  const final = cash + (shares * closes[closes.length-1]);
  const ret = (final - 10000)/10000;
  return {final, returnPct:ret, tradesCount:trades.length, trades};
}

function renderBacktest(results){
  backtestEl.innerHTML = '<h3>Backtest results</h3>';
  results.forEach(r=>{
    const div = document.createElement('div'); div.className='card';
    if(r.error){
      div.innerHTML = `<strong>${r.symbol}</strong><div class="muted">Error: ${r.error}</div>`;
    } else {
      div.innerHTML = `<strong>${r.symbol}</strong>
        <div>Final value: €${r.result.final.toFixed(2)}</div>
        <div>Return: ${(r.result.returnPct*100).toFixed(2)}%</div>
        <div>Trades: ${r.result.tradesCount}</div>`;
    }
    backtestEl.appendChild(div);
  });
}
