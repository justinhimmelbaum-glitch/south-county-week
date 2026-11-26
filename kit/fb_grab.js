// Run on https://www.facebook.com/events/search/?q=<query> with javascript_tool.
// Set RS/RE first line to the range (YYYY-MM-DD). Scrolls, keeps events in range,
// then replaces the page body with one line per event so get_page_text can read them all:
// "<event id> :: <date line> | <title> | <where>"
const RS = "__RS__", RE = "__RE__";
await new Promise(r => setTimeout(r, 3000));
for (let i = 0; i < 10; i++) { window.scrollTo(0, document.body.scrollHeight); await new Promise(r => setTimeout(r, 1800 + Math.random() * 1200)); }
const out = {};
document.querySelectorAll('a[href*="/events/"]').forEach(a => { const m = a.href.match(/\/events\/(\d{6,})/); if (!m) return;
  let el = a; for (let k = 0; k < 6 && el.parentElement; k++) { el = el.parentElement; if (el.innerText && el.innerText.split('\n').length >= 3) break; }
  const t = (el.innerText || '').replace(/\n+/g, ' | ').slice(0, 300); if (!out[m[1]] || t.length > out[m[1]].length) out[m[1]] = t; });
const MON = {JAN:1,FEB:2,MAR:3,APR:4,MAY:5,JUN:6,JUL:7,AUG:8,SEP:9,OCT:10,NOV:11,DEC:12};
const yr = +RS.slice(0, 4), toIso = (mo, d, y) => `${y || (MON[mo] < +RS.slice(5, 7) - 6 ? yr + 1 : yr)}-${String(MON[mo]).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
const res = [];
for (const [id, t] of Object.entries(out)) {
  const m = t.match(/^(?:[A-Z]{3}, )?([A-Z]{3}) (\d+)(?:, (\d{4}))?/); if (!m || !MON[m[1]]) continue;
  const s = toIso(m[1], m[2], m[3]); const m2 = t.match(/- (?:[A-Z]{3}, )?([A-Z]{3}) (\d+)(?:, (\d{4}))?/);
  const e = m2 && MON[m2[1]] ? toIso(m2[1], m2[2], m2[3]) : s;
  if (e < RS || s > RE) continue;
  res.push(id + ' :: ' + t.replace(/ \| Interested$/, '').replace(/ \| [^|]*(is|are) (interested|going)/, '').slice(0, 220));
}
document.body.innerHTML = '<main><article><pre id="dump"></pre></article></main>';
document.getElementById('dump').textContent = res.join('\n');
res.length
