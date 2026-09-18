const form = document.getElementById('search-form');
const input = document.getElementById('target');
const typeSel = document.getElementById('type');
const resultsEl = document.getElementById('results');
const runInfo = document.getElementById('run-info');
const runTarget = document.getElementById('run-target');
const runType = document.getElementById('run-type');
const runCount = document.getElementById('run-count');
const runDone = document.getElementById('run-done');
const progressBar = document.getElementById('progress-bar');
const mapSection = document.getElementById('map-section');
const mapCount = document.getElementById('map-count');

let currentEs = null;
let leafletMap = null;
let mapMarkers = [];
let seenCoords = new Set();

document.querySelectorAll('.hint .ex').forEach(el => {
  el.addEventListener('click', () => {
    input.value = el.dataset.v;
    input.focus();
  });
});

function initMapIfNeeded() {
  if (leafletMap) {
    setTimeout(() => leafletMap.invalidateSize(), 150);
    return;
  }
  leafletMap = L.map('map', {
    zoomControl: true,
    scrollWheelZoom: false,
  }).setView([46.603354, 1.888334], 5);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(leafletMap);

  setTimeout(() => leafletMap.invalidateSize(), 250);
}

function addCoordinateToMap(source, label, value, lat, lon, extra = {}) {
  const latNum = parseFloat(lat);
  const lonNum = parseFloat(lon);
  if (isNaN(latNum) || isNaN(lonNum)) return;

  const coordKey = `${latNum.toFixed(4)},${lonNum.toFixed(4)}`;
  if (seenCoords.has(coordKey)) return;
  seenCoords.add(coordKey);

  if (mapSection.classList.contains('hidden')) {
    mapSection.classList.remove('hidden');
    initMapIfNeeded();
  }

  const city = extra.city || '';
  const locationName = extra.location || extra.region || extra.adresse || (city ? `${city}` : '');
  
  const popupHtml = `
    <div style="font-family: var(--font-sans, sans-serif); color: #f4f4f6; padding: 2px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
        <span style="color: #60a5fa; font-family: monospace; font-size: 10px; font-weight: 700; text-transform: uppercase;">
          ◈ ${escapeHtml(source)}
        </span>
        ${city ? `<span style="background: rgba(59, 130, 246, 0.15); color: #93c5fd; font-size: 10px; padding: 1px 6px; border-radius: 4px;">${escapeHtml(city)}</span>` : ''}
      </div>
      <div style="color: #ffffff; font-weight: 600; font-size: 12px; margin-bottom: 4px;">
        ${escapeHtml(label || '')}
      </div>
      ${locationName ? `<div style="color: #cbd5e1; font-size: 11px; margin-bottom: 4px;">📍 ${escapeHtml(locationName)}</div>` : ''}
      ${value ? `<div style="color: #94a3b8; font-size: 11px; line-height: 1.4; max-height: 65px; overflow-y: auto;">${escapeHtml(value)}</div>` : ''}
      <div style="color: #64748b; font-size: 10px; font-family: monospace; margin-top: 6px; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 4px;">
        GPS: ${latNum.toFixed(4)}, ${lonNum.toFixed(4)}
      </div>
    </div>
  `;

  // Minimalist circle marker
  const marker = L.circleMarker([latNum, lonNum], {
    radius: 7,
    fillColor: '#3b82f6',
    color: '#ffffff',
    weight: 2,
    opacity: 1,
    fillOpacity: 0.9,
  }).addTo(leafletMap).bindPopup(popupHtml);

  mapMarkers.push(marker);
  const count = mapMarkers.length;
  mapCount.textContent = `${count} localisation${count > 1 ? 's' : ''} détectée${count > 1 ? 's' : ''}`;

  if (mapMarkers.length === 1) {
    leafletMap.setView([latNum, lonNum], 11);
  } else {
    const group = L.featureGroup(mapMarkers);
    leafletMap.fitBounds(group.getBounds().pad(0.3));
  }
}

async function tryGeocode(locStr, source, label, value, extra) {
  if (!locStr || seenCoords.size > 15) return;
  try {
    const r = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(locStr)}&format=json&limit=1`);
    if (r.ok) {
      const data = await r.json();
      if (data && data.length) {
        addCoordinateToMap(source, label, value, data[0].lat, data[0].lon, { ...extra, location: locStr });
      }
    }
  } catch (_) {}
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const target = input.value.trim();
  if (!target) return;
  if (currentEs) currentEs.close();

  resultsEl.innerHTML = '';
  runInfo.classList.add('hidden');
  mapSection.classList.add('hidden');
  mapMarkers.forEach(m => m.remove());
  mapMarkers = [];
  seenCoords.clear();
  mapCount.textContent = '0 localisation';

  const body = { target };
  if (typeSel.value !== 'auto') body.type = typeSel.value;

  let data;
  try {
    const r = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const text = await r.text();
    try {
      data = JSON.parse(text);
    } catch (parseErr) {
      throw new Error(`Server returned non-JSON response (${r.status}): ${text.slice(0, 120)}`);
    }
    if (!r.ok) throw new Error(data.error || 'request failed');
  } catch (err) {
    resultsEl.innerHTML = `<div class="error-msg">[FATAL] ${escapeHtml(err.message)}</div>`;
    return;
  }

  const total = data.sources.length;
  let done = 0;

  runTarget.textContent = data.target;
  runType.textContent = data.input_type.toUpperCase();
  runCount.textContent = String(total);
  runDone.textContent = '0';
  runInfo.classList.remove('hidden');
  progressBar.style.width = '0%';

  for (const s of data.sources) {
    resultsEl.appendChild(skeletonCard(s.name, s.description));
  }

  const es = new EventSource(
    `/api/stream/${encodeURIComponent(data.job_id)}?target=${encodeURIComponent(target)}&type=${encodeURIComponent(data.input_type)}`
  );
  currentEs = es;

  es.addEventListener('result', (ev) => {
    const res = JSON.parse(ev.data);
    fillCard(res);

    // Extract geolocation coordinates or location names for map
    if (res.findings && res.findings.length) {
      for (const f of res.findings) {
        if (f.extra && f.extra.latitude != null && f.extra.longitude != null) {
          addCoordinateToMap(res.source, f.label, f.value, f.extra.latitude, f.extra.longitude, f.extra);
        } else if (f.extra && (f.extra.city || f.extra.location || f.extra.adresse)) {
          const locStr = f.extra.location || f.extra.adresse || f.extra.city;
          tryGeocode(locStr, res.source, f.label, f.value, f.extra);
        }
      }
    }

    done++;
    runDone.textContent = String(done);
    progressBar.style.width = `${(done / total) * 100}%`;
  });

  es.addEventListener('done', () => {
    progressBar.style.width = '100%';
    es.close();
    currentEs = null;
    if (leafletMap) setTimeout(() => leafletMap.invalidateSize(), 300);
  });

  es.onerror = () => { es.close(); currentEs = null; };
});

function skeletonCard(name, desc) {
  const c = document.createElement('div');
  c.className = 'card scanning';
  c.dataset.name = name;
  c.innerHTML = `
    <div class="card-head">
      <span class="card-name">${escapeHtml(name)}</span>
      <span class="card-meta"><span class="spinner"></span><span class="tag tag-scan">scan</span></span>
    </div>
    <div class="card-body">
      <div class="card-desc">${escapeHtml(desc || '')}</div>
    </div>
  `;
  return c;
}

function fillCard(res) {
  const card = resultsEl.querySelector(`.card[data-name="${cssEscape(res.source)}"]`);
  if (!card) return;

  card.classList.remove('scanning');
  card.classList.toggle('empty', !res.found && !res.error);
  card.classList.toggle('error', !!res.error);

  const meta = card.querySelector('.card-meta');
  let tag;
  if (res.error) tag = '<span class="tag tag-error">erreur</span>';
  else if (res.found) tag = `<span class="tag tag-found">${res.findings.length} hit${res.findings.length === 1 ? '' : 's'}</span>`;
  else tag = '<span class="tag tag-empty">vide</span>';
  meta.innerHTML = `${tag}<span>${res.elapsed_ms}ms</span>`;

  const body = card.querySelector('.card-body');
  if (res.error) {
    body.innerHTML = `<div class="error-msg">${escapeHtml(res.error)}</div>`;
  } else if (!res.findings.length) {
    body.innerHTML = `<div class="empty-msg">Aucun résultat concluant</div>`;
  } else {
    body.innerHTML = res.findings.map(renderFinding).join('');
  }
}

function renderFinding(f) {
  const value = escapeHtml(f.value || '');
  const url = f.url
    ? `<div class="url"><a href="${escapeAttr(f.url)}" target="_blank" rel="noopener">${escapeHtml(f.url)}</a></div>`
    : '';
  const extras = renderExtra(f.extra || {});
  return `
    <div class="finding">
      <span class="label">${escapeHtml(f.label || '')}</span>
      ${value ? `<div class="value">${value}</div>` : ''}
      ${url}
      ${extras}
    </div>
  `;
}

function renderExtra(extra) {
  const entries = Object.entries(extra).filter(([, v]) =>
    v != null && v !== '' && !(Array.isArray(v) && v.length === 0)
  );
  if (!entries.length) return '';
  const parts = entries.map(([k, v]) => {
    let val;
    if (Array.isArray(v)) val = v.join(', ');
    else if (typeof v === 'object') val = JSON.stringify(v);
    else val = String(v);
    return `<div><span class="k">${escapeHtml(k)}:</span> ${escapeHtml(val)}</div>`;
  });
  return `<div class="extra">${parts.join('')}</div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function escapeAttr(s) { return escapeHtml(s); }
function cssEscape(s) { return String(s).replace(/[^a-zA-Z0-9_-]/g, '\\$&'); }
