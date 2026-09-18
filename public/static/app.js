const form = document.getElementById('search-form');
const input = document.getElementById('target');
const typeSel = document.getElementById('type');
const runInfo = document.getElementById('run-info');
const runTarget = document.getElementById('run-target');
const runType = document.getElementById('run-type');
const runCount = document.getElementById('run-count');
const runDone = document.getElementById('run-done');
const progressBar = document.getElementById('progress-bar');
const systemStatus = document.getElementById('system-status');

// Sections
const mapSection = document.getElementById('map-section');
const mapCount = document.getElementById('map-count');
const socialSection = document.getElementById('social-section');
const socialGrid = document.getElementById('social-grid');
const socialFoundCount = document.getElementById('social-found-count');
const socialTotalCount = document.getElementById('social-total-count');
const webSection = document.getElementById('web-section');
const webGrid = document.getElementById('web-grid');
const webCount = document.getElementById('web-count');
const otherSections = document.getElementById('other-sections');

let currentEs = null;
let leafletMap = null;
let mapMarkers = [];
let seenCoords = new Set();
let detectedLocations = new Map(); // key -> { city, country, flag, text }

// State for Social Media & Web Deduplication
let socialMap = new Map(); // platformName -> { name, url, exists, checked }
let seenWebUrls = new Map(); // normalizedUrl -> { el, finding }
let otherSourceCards = new Map(); // sourceName -> cardEl

// Flag dictionary for countries & common aliases
const COUNTRY_FLAGS = {
  "france": "🇫🇷", "fr": "🇫🇷",
  "algeria": "🇩🇿", "algérie": "🇩🇿", "algerie": "🇩🇿", "dz": "🇩🇿",
  "morocco": "🇲🇦", "maroc": "🇲🇦", "ma": "🇲🇦",
  "tunisia": "🇹🇳", "tunisie": "🇹🇳", "tn": "🇹🇳",
  "united states": "🇺🇸", "usa": "🇺🇸", "us": "🇺🇸", "états-unis": "🇺🇸", "etats-unis": "🇺🇸",
  "united kingdom": "🇬🇧", "uk": "🇬🇧", "gb": "🇬🇧", "royaume-uni": "🇬🇧", "great britain": "🇬🇧", "angleterre": "🇬🇧",
  "belgium": "🇧🇪", "belgique": "🇧🇪", "be": "🇧🇪",
  "switzerland": "🇨🇭", "suisse": "🇨🇭", "ch": "🇨🇭",
  "germany": "🇩🇪", "allemagne": "🇩🇪", "de": "🇩🇪",
  "canada": "🇨🇦", "ca": "🇨🇦",
  "spain": "🇪🇸", "espagne": "🇪🇸", "es": "🇪🇸",
  "italy": "🇮🇹", "italie": "🇮🇹", "it": "🇮🇹",
  "japan": "🇯🇵", "japon": "🇯🇵", "jp": "🇯🇵",
  "united arab emirates": "🇦🇪", "uae": "🇦🇪", "ae": "🇦🇪", "émirats arabes unis": "🇦🇪", "emirats arabes unis": "🇦🇪",
  "russia": "🇷🇺", "russie": "🇷🇺", "ru": "🇷🇺",
  "netherlands": "🇳🇱", "pays-bas": "🇳🇱", "nl": "🇳🇱",
  "brazil": "🇧🇷", "brésil": "🇧🇷", "bresil": "🇧🇷", "br": "🇧🇷",
  "portugal": "🇵🇹", "pt": "🇵🇹",
  "senegal": "🇸🇳", "sénégal": "🇸🇳", "sn": "🇸🇳",
  "turkey": "🇹🇷", "turquie": "🇹🇷", "tr": "🇹🇷",
  "mexico": "🇲🇽", "mexique": "🇲🇽", "mx": "🇲🇽",
  "australia": "🇦🇺", "australie": "🇦🇺", "au": "🇦🇺",
  "india": "🇮🇳", "inde": "🇮🇳", "in": "🇮🇳",
  "china": "🇨🇳", "chine": "🇨🇳", "cn": "🇨🇳",
  "côte d'ivoire": "🇨🇮", "cote d'ivoire": "🇨🇮", "ivory coast": "🇨🇮", "ci": "🇨🇮",
  "cameroon": "🇨🇲", "cameroun": "🇨🇲", "cm": "🇨🇲",
  "egypt": "🇪🇬", "égypte": "🇪🇬", "egypte": "🇪🇬", "eg": "🇪🇬",
};

const CANONICAL_COUNTRIES = {
  "france": "France", "fr": "France",
  "algeria": "Algérie", "algérie": "Algérie", "algerie": "Algérie", "dz": "Algérie",
  "morocco": "Maroc", "maroc": "Maroc", "ma": "Maroc",
  "tunisia": "Tunisie", "tunisie": "Tunisie", "tn": "Tunisie",
  "united states": "États-Unis", "usa": "États-Unis", "us": "États-Unis", "états-unis": "États-Unis", "etats-unis": "États-Unis",
  "united kingdom": "Royaume-Uni", "uk": "Royaume-Uni", "gb": "Royaume-Uni", "royaume-uni": "Royaume-Uni", "angleterre": "Royaume-Uni",
  "belgium": "Belgique", "belgique": "Belgique", "be": "Belgique",
  "switzerland": "Suisse", "suisse": "Suisse", "ch": "Suisse",
  "germany": "Allemagne", "allemagne": "Allemagne", "de": "Allemagne",
  "canada": "Canada", "ca": "Canada",
  "spain": "Espagne", "espagne": "Espagne", "es": "Espagne",
  "italy": "Italie", "italie": "Italie", "it": "Italie",
  "japan": "Japon", "japon": "Japon", "jp": "Japon",
  "united arab emirates": "Émirats Arabes Unis", "uae": "Émirats Arabes Unis", "ae": "Émirats Arabes Unis", "émirats arabes unis": "Émirats Arabes Unis", "emirats arabes unis": "Émirats Arabes Unis",
  "russia": "Russie", "russie": "Russie", "ru": "Russie",
  "netherlands": "Pays-Bas", "pays-bas": "Pays-Bas", "nl": "Pays-Bas",
  "brazil": "Brésil", "brésil": "Brésil", "bresil": "Brésil", "br": "Brésil",
  "portugal": "Portugal", "pt": "Portugal",
  "senegal": "Sénégal", "sénégal": "Sénégal", "sn": "Sénégal",
  "turkey": "Turquie", "turquie": "Turquie", "tr": "Turquie",
  "mexico": "Mexique", "mexique": "Mexique", "mx": "Mexique",
  "australia": "Australie", "australie": "Australie", "au": "Australie",
  "india": "Inde", "inde": "Inde", "in": "Inde",
  "china": "Chine", "chine": "Chine", "cn": "Chine",
  "côte d'ivoire": "Côte d'Ivoire", "cote d'ivoire": "Côte d'Ivoire", "ivory coast": "Côte d'Ivoire", "ci": "Côte d'Ivoire",
  "cameroon": "Cameroun", "cameroun": "Cameroun", "cm": "Cameroun",
  "egypt": "Égypte", "égypte": "Égypte", "egypte": "Égypte", "eg": "Égypte",
};

function detectCountry(str) {
  if (!str) return null;
  const lower = str.toLowerCase().trim();
  for (const [key, canonical] of Object.entries(CANONICAL_COUNTRIES)) {
    if (key.length <= 2) {
      if (new RegExp(`(?:^|[^a-z0-9])${key}(?:$|[^a-z0-9])`, 'i').test(lower)) {
        return { country: canonical, flag: COUNTRY_FLAGS[key] || "📍" };
      }
    } else {
      if (lower.includes(key)) {
        return { country: canonical, flag: COUNTRY_FLAGS[key] || "📍" };
      }
    }
  }
  return null;
}

function getCountryFlag(countryName) {
  if (!countryName) return "📍";
  const detected = detectCountry(countryName);
  if (detected) return detected.flag;
  const str = countryName.toLowerCase().trim();
  for (const [k, v] of Object.entries(COUNTRY_FLAGS)) {
    if (str === k || str.includes(k)) return v;
  }
  return "📍";
}

// Clickable hints
document.querySelectorAll('.hint .ex').forEach(el => {
  el.addEventListener('click', () => {
    input.value = el.dataset.v;
    input.focus();
  });
});

// Map Initializer using ESRI Dark Gray Canvas (100% free, no API key required, sleek dark base)
function initMapIfNeeded() {
  if (leafletMap) {
    setTimeout(() => leafletMap.invalidateSize(), 150);
    return;
  }
  leafletMap = L.map('map', {
    zoomControl: true,
    scrollWheelZoom: false,
  }).setView([46.603354, 1.888334], 5);

  // ESRI Dark Gray Base: free, fast, modern, zero watermark, zero API key
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
    attribution: '&copy; <a href="https://www.esri.com" target="_blank" rel="noopener">Esri</a> &mdash; World Dark Canvas',
    maxZoom: 16,
  }).addTo(leafletMap);

  // ESRI Dark Gray Reference: labels for cities & countries
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
    attribution: '',
    maxZoom: 16,
  }).addTo(leafletMap);

  setTimeout(() => leafletMap.invalidateSize(), 250);
}

function updateMapHeader() {
  if (!detectedLocations.size) {
    mapCount.textContent = `${mapMarkers.length} localisation${mapMarkers.length > 1 ? 's' : ''}`;
    return;
  }
  const pills = Array.from(detectedLocations.values())
    .map(l => `<span class="loc-pill"><span class="loc-flag">${l.flag}</span> ${escapeHtml(l.label)}</span>`)
    .join(' ');
  mapCount.innerHTML = pills;
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

  let city = (extra.city || '').trim();
  let country = (extra.country || '').trim();
  let rawLoc = (extra.location || extra.region || '').trim();

  // Strip generic placeholder phrases (e.g. "Localisation détectée", "location found")
  if (/^(localisation|location\s+found|detected\s+location|probable|inconnu)/i.test(rawLoc)) {
    rawLoc = '';
  }

  // Infer country if not explicitly provided
  if (!country) {
    const fromLoc = detectCountry(rawLoc) || detectCountry(value) || detectCountry(label);
    if (fromLoc) {
      country = fromLoc.country;
    }
  }

  // If city is identical to country, clear city to avoid duplicate display
  if (city && country && city.toLowerCase() === country.toLowerCase()) {
    city = '';
  }

  const flag = extra.flag || (country ? getCountryFlag(country) : getCountryFlag(rawLoc));

  // Determine display label: city + country, or city alone, or country alone (never generic placeholder)
  let displayLocation = '';
  if (city && country) {
    displayLocation = `${city}, ${country}`;
  } else if (city) {
    displayLocation = city;
  } else if (country) {
    displayLocation = country;
  } else if (rawLoc) {
    displayLocation = rawLoc;
  } else {
    displayLocation = 'Position GPS';
  }

  const locKey = displayLocation || coordKey;
  
  if (!detectedLocations.has(locKey)) {
    detectedLocations.set(locKey, {
      city,
      country,
      flag,
      label: displayLocation,
    });
  }

  updateMapHeader();

  const popupHtml = `
    <div style="font-family: var(--font-sans, sans-serif); color: #f4f4f6; padding: 2px;">
      <div class="map-popup-header">
        <span style="font-size: 16px;">${flag}</span>
        <span>${escapeHtml(displayLocation)}</span>
      </div>
      <div style="color: #ffffff; font-weight: 600; font-size: 12px; margin-bottom: 4px;">
        ${escapeHtml(label || '')}
      </div>
      ${value ? `<div style="color: #94a3b8; font-size: 11px; line-height: 1.4; max-height: 70px; overflow-y: auto; margin-bottom: 6px;">${escapeHtml(value)}</div>` : ''}
      <div style="color: #64748b; font-size: 10px; font-family: monospace; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 5px;">
        GPS: ${latNum.toFixed(4)}, ${lonNum.toFixed(4)}
      </div>
    </div>
  `;

  const marker = L.circleMarker([latNum, lonNum], {
    radius: 7,
    fillColor: '#3b82f6',
    color: '#ffffff',
    weight: 2,
    opacity: 1,
    fillOpacity: 0.9,
  }).addTo(leafletMap).bindPopup(popupHtml);

  mapMarkers.push(marker);

  if (mapMarkers.length === 1) {
    leafletMap.setView([latNum, lonNum], 11);
  } else {
    const group = L.featureGroup(mapMarkers);
    leafletMap.fitBounds(group.getBounds().pad(0.3));
  }
}

async function tryGeocode(locStr, source, label, value, extra) {
  if (!locStr || seenCoords.size > 15) return;
  const cleanLoc = String(locStr).replace(/^(localisation|location\s+found|detected\s+location|probable|inconnu)/i, '').trim();
  if (!cleanLoc || cleanLoc.length < 3) return;
  try {
    const r = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cleanLoc)}&format=json&limit=1`);
    if (r.ok) {
      const data = await r.json();
      if (data && data.length) {
        addCoordinateToMap(source, label, value, data[0].lat, data[0].lon, { ...extra, location: cleanLoc });
      }
    }
  } catch (_) {}
}

// Normalize URLs to deduplicate search engine links accurately
function normalizeUrl(rawUrl) {
  if (!rawUrl) return '';
  try {
    const u = new URL(rawUrl);
    let host = u.hostname.toLowerCase().replace(/^www\./, '');
    let pathname = u.pathname.replace(/\/+$/, '');
    const params = new URLSearchParams();
    for (const [k, v] of u.searchParams.entries()) {
      if (!k.startsWith('utm_') && !['ref', 'ref_src', 'fbclid', 'igshid', 's', 't'].includes(k)) {
        params.append(k, v);
      }
    }
    const q = params.toString();
    return host + pathname + (q ? '?' + q : '');
  } catch (e) {
    return rawUrl.trim().toLowerCase().replace(/\/+$/, '');
  }
}

// Identify social network from URL
function detectSocialNetworkFromUrl(url) {
  if (!url) return null;
  const l = url.toLowerCase();
  if (l.includes('instagram.com/')) return 'Instagram';
  if (l.includes('linkedin.com/in/') || l.includes('linkedin.com/posts/')) return 'LinkedIn';
  if (l.includes('github.com/')) return 'GitHub';
  if (l.includes('twitter.com/') || l.includes('x.com/')) return 'Twitter/X';
  if (l.includes('reddit.com/user/')) return 'Reddit';
  if (l.includes('tiktok.com/@')) return 'TikTok';
  if (l.includes('youtube.com/@') || l.includes('youtube.com/channel/')) return 'YouTube';
  if (l.includes('pinterest.com/')) return 'Pinterest';
  if (l.includes('t.me/')) return 'Telegram';
  if (l.includes('twitch.tv/')) return 'Twitch';
  if (l.includes('open.spotify.com/user/')) return 'Spotify';
  if (l.includes('gitlab.com/')) return 'GitLab';
  if (l.includes('medium.com/@')) return 'Medium';
  if (l.includes('steamcommunity.com/id/')) return 'Steam';
  if (l.includes('soundcloud.com/')) return 'SoundCloud';
  if (l.includes('linktr.ee/')) return 'Linktree';
  if (l.includes('chess.com/member/')) return 'Chess.com';
  if (l.includes('dev.to/')) return 'DEV.to';
  return null;
}

// Extract handle from known social profile URLs
function extractHandleFromSocialUrl(rawUrl) {
  if (!rawUrl) return null;
  try {
    const u = new URL(rawUrl);
    const path = u.pathname.replace(/^\/+|\/+$/g, '');
    const parts = path.split('/').filter(Boolean);
    const host = u.hostname.toLowerCase();
    if (!parts.length) return null;

    if (host.includes('instagram.com')) {
      if (['p', 'reel', 'reels', 'stories', 'explore', 'accounts', 'about', 'legal', 'developer', 'popular', 'tags', 'direct', 'tv', 'channel'].includes(parts[0].toLowerCase())) return null;
      return parts[0];
    }
    if (host.includes('twitter.com') || host.includes('x.com')) {
      if (['i', 'intent', 'share', 'home', 'explore', 'notifications', 'messages', 'search'].includes(parts[0].toLowerCase())) return null;
      return parts[0];
    }
    if (host.includes('linkedin.com')) {
      if (parts[0].toLowerCase() === 'in' && parts[1]) return parts[1];
      return null;
    }
    if (host.includes('reddit.com')) {
      if (parts[0].toLowerCase() === 'user' && parts[1]) return parts[1];
      return null;
    }
    if (host.includes('tiktok.com')) {
      const m = path.match(/^@([a-zA-Z0-9._-]+)/);
      return m ? m[1] : null;
    }
    if (host.includes('github.com')) {
      if (['features', 'pricing', 'marketplace', 'topics', 'collections', 'trending', 'about', 'join', 'login', 'signup', 'settings'].includes(parts[0].toLowerCase())) return null;
      return parts[0];
    }
    if (host.includes('t.me')) {
      if (['s', 'joinchat', 'addstickers', 'share', 'invoice'].includes(parts[0].toLowerCase())) return null;
      return parts[0];
    }
    if (host.includes('youtube.com')) {
      const m = path.match(/^@([a-zA-Z0-9._-]+)/);
      return m ? m[1] : null;
    }
    if (host.includes('medium.com')) {
      const m = path.match(/^@([a-zA-Z0-9._-]+)/);
      return m ? m[1] : null;
    }
    if (host.includes('pinterest.com')) {
      if (['pin', 'ideas', 'today', 'search'].includes(parts[0].toLowerCase())) return null;
      return parts[0];
    }
    if (host.includes('steamcommunity.com')) {
      if (parts[0].toLowerCase() === 'id' && parts[1]) return parts[1];
      return null;
    }
    if (host.includes('gitlab.com')) {
      return parts[0];
    }
    if (host.includes('linktr.ee')) {
      return parts[0];
    }
    if (host.includes('chess.com')) {
      if (parts[0].toLowerCase() === 'member' && parts[1]) return parts[1];
      return null;
    }
    if (host.includes('dev.to')) {
      return parts[0];
    }
    return parts[0] || null;
  } catch (e) {
    return null;
  }
}

// Derive acceptable candidate handles from user target input
function getCandidateHandles(target) {
  if (!target) return [];
  const clean = target.trim().toLowerCase();
  const cands = new Set();
  
  cands.add(clean);
  const slug = clean.replace(/[^a-z0-9]/g, '');
  if (slug) cands.add(slug);
  const dot = clean.replace(/\s+/g, '.').replace(/[^a-z0-9.]/g, '');
  if (dot) cands.add(dot);
  const underscore = clean.replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
  if (underscore) cands.add(underscore);
  const hyphen = clean.replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  if (hyphen) cands.add(hyphen);
  
  return Array.from(cands);
}

// Verify that a detected social URL genuinely corresponds to the searched target
function isSocialUrlForTarget(url, target) {
  if (!url || !target) return false;
  const handle = extractHandleFromSocialUrl(url);
  if (!handle) return false;
  const handleLower = handle.toLowerCase();
  const candidates = getCandidateHandles(target);

  // Direct candidate match (exact handle match)
  if (candidates.includes(handleLower)) return true;

  // LinkedIn suffix format: e.g. "alex-martin-123456"
  if (url.toLowerCase().includes('linkedin.com/in/')) {
    for (const c of candidates) {
      if (handleLower.startsWith(c + '-')) return true;
    }
  }

  return false;
}

// -------------------------------------------------------------
// SOCIAL MEDIA TILE MANAGEMENT (FIXED SIZE TILES WITH ✓ OR ✕)
// -------------------------------------------------------------
function renderSocialTile(name, url, exists) {
  const isFound = Boolean(exists);
  const tagEl = isFound ? 'a' : 'div';
  const hrefAttr = (isFound && url) ? `href="${escapeAttr(url)}" target="_blank" rel="noopener"` : '';
  
  return `
    <${tagEl} class="social-tile ${isFound ? 'found' : 'missing'}" data-platform="${escapeAttr(name)}" ${hrefAttr}>
      <div class="social-tile-info">
        <div class="social-tile-name">${escapeHtml(name)}</div>
        <div class="social-tile-sub">${isFound ? 'Profil détecté' : 'Non trouvé'}</div>
      </div>
      <div class="check-icon ${isFound ? 'found' : 'missing'}">
        ${isFound ? '✓' : '✕'}
      </div>
    </${tagEl}>
  `;
}

function updateSocialPlatform(name, url, exists) {
  if (!name) return;
  socialSection.classList.remove('hidden');

  const existing = socialMap.get(name);
  if (existing && existing.exists && !exists) {
    return;
  }

  socialMap.set(name, {
    name,
    url: url || (existing ? existing.url : ''),
    exists: Boolean(exists),
  });

  let tile = socialGrid.querySelector(`.social-tile[data-platform="${cssEscape(name)}"]`);
  const tileHtml = renderSocialTile(name, url, Boolean(exists));
  
  if (tile) {
    tile.outerHTML = tileHtml;
  } else {
    socialGrid.insertAdjacentHTML('beforeend', tileHtml);
  }

  let foundCount = 0;
  for (const item of socialMap.values()) {
    if (item.exists) foundCount++;
  }
  socialFoundCount.textContent = `${foundCount} profil${foundCount > 1 ? 's' : ''} détecté${foundCount > 1 ? 's' : ''}`;
  socialTotalCount.textContent = `${socialMap.size} testé${socialMap.size > 1 ? 's' : ''}`;
}

// -------------------------------------------------------------
// GLOBAL WEB FINDINGS MANAGEMENT (DEDUPLICATED SEARCH RESULTS)
// -------------------------------------------------------------
function addWebFinding(finding) {
  webSection.classList.remove('hidden');

  const norm = normalizeUrl(finding.url);
  if (norm && seenWebUrls.has(norm)) {
    const existing = seenWebUrls.get(norm);
    if ((!existing.value || existing.value.length < (finding.value || '').length) && finding.value) {
      existing.value = finding.value;
      const descEl = existing.el.querySelector('.web-desc');
      if (descEl) descEl.textContent = finding.value;
    }
    return;
  }

  const title = finding.label || '(Sans titre)';
  const desc = finding.value || '';
  const url = finding.url || '';
  
  // Format location badge with country flag emoji
  let locBadgeHtml = '';
  if (finding.extra && (finding.extra.location || finding.extra.city || finding.extra.country || finding.extra.region)) {
    let city = (finding.extra.city || '').trim();
    let country = (finding.extra.country || '').trim();
    let rawLoc = (finding.extra.location || finding.extra.region || '').trim();
    if (/^(localisation|location\s+found|detected\s+location|probable|inconnu)/i.test(rawLoc)) {
      rawLoc = '';
    }
    if (!country) {
      const fromLoc = detectCountry(rawLoc) || detectCountry(finding.value) || detectCountry(finding.label);
      if (fromLoc) country = fromLoc.country;
    }
    if (city && country && city.toLowerCase() === country.toLowerCase()) {
      city = '';
    }
    const flag = finding.extra.flag || (country ? getCountryFlag(country) : getCountryFlag(rawLoc));
    const text = city ? (country ? `${city}, ${country}` : city) : (country || rawLoc);
    if (text) {
      locBadgeHtml = `<span class="web-loc">${flag} ${escapeHtml(text)}</span>`;
    }
  }

  const card = document.createElement('div');
  card.className = 'web-finding-card';
  card.innerHTML = `
    <div>
      <div class="web-title">${escapeHtml(title)}</div>
      ${desc ? `<div class="web-desc" style="margin-top: 6px;">${escapeHtml(desc)}</div>` : ''}
    </div>
    <div class="web-meta">
      ${url ? `<div class="web-url"><a href="${escapeAttr(url)}" target="_blank" rel="noopener">${escapeHtml(url)}</a></div>` : ''}
      ${locBadgeHtml}
    </div>
  `;

  webGrid.appendChild(card);
  if (norm) {
    seenWebUrls.set(norm, { el: card, value: desc });
  }

  const total = seenWebUrls.size;
  webCount.textContent = `${total} résultat${total > 1 ? 's' : ''} unique${total > 1 ? 's' : ''}`;
}

// -------------------------------------------------------------
// DOMAIN-SPECIFIC CARDS (Phone, Domain, BSSID, Directory, etc.)
// -------------------------------------------------------------
const DOMAIN_CATEGORY_CONFIG = {
  annuaire_118712: { title: "Annuaires & Coordonnées Publiques", desc: "118 712 & PagesBlanches France" },
  phone_info: { title: "Téléphonie & Opérateur", desc: "Validation, format E.164, opérateur et fuseaux" },
  domain_info: { title: "Domaine & Résolution DNS", desc: "WHOIS, enregistrements A, MX, NS, TXT" },
  crt_sh: { title: "Sous-Domaines & Certificats", desc: "Énumération Certificate Transparency logs" },
  bssid_info: { title: "Wi-Fi & Géolocalisation BSSID", desc: "Fabricant OUI et base WiGLE / Mylnikov" },
  db_searcher: { title: "Sécurité & Fuites de Données", desc: "Recherche de comptes compromis" },
  archive_org: { title: "Archives & Historique Web", desc: "Internet Archive & snapshots Wayback" },
  wikipedia: { title: "Notices Biographiques", desc: "Wikipédia FR / EN" },
  google_activity: { title: "Empreinte Google", desc: "Activité publique et profils Google" },
  gravatar: { title: "Profil Gravatar", desc: "Avatars et profils mondiaux liés" },
};

function getOrCreateDomainCard(sourceName) {
  if (otherSourceCards.has(sourceName)) {
    return otherSourceCards.get(sourceName);
  }

  const conf = DOMAIN_CATEGORY_CONFIG[sourceName] || {
    title: sourceName.toUpperCase(),
    desc: "Informations complémentaires",
  };

  const card = document.createElement('div');
  card.className = 'domain-card';
  card.dataset.source = sourceName;
  card.innerHTML = `
    <div class="domain-card-head">
      <span class="domain-card-name">${escapeHtml(conf.title)}</span>
      <span class="domain-card-meta"><span class="tag tag-scan">scan</span></span>
    </div>
    <div class="domain-card-desc" style="font-size: 11px; color: var(--text-dim); margin-bottom: 12px;">${escapeHtml(conf.desc)}</div>
    <div class="domain-card-body">
      <div class="empty-msg">Analyse en cours...</div>
    </div>
  `;

  otherSections.appendChild(card);
  otherSourceCards.set(sourceName, card);
  return card;
}

function fillDomainCard(res) {
  const card = getOrCreateDomainCard(res.source);
  const meta = card.querySelector('.domain-card-meta');
  const body = card.querySelector('.domain-card-body');

  let tag;
  if (res.error) tag = '<span class="tag tag-error">erreur</span>';
  else if (res.found && res.findings.length) tag = `<span class="tag tag-found">${res.findings.length} hit${res.findings.length === 1 ? '' : 's'}</span>`;
  else tag = '<span class="tag tag-empty">vide</span>';
  meta.innerHTML = `${tag}<span style="font-family: monospace; font-size: 10px; color: var(--text-dim);">${res.elapsed_ms}ms</span>`;

  if (res.error) {
    body.innerHTML = `<div class="error-msg">${escapeHtml(res.error)}</div>`;
  } else if (!res.findings || !res.findings.length) {
    body.innerHTML = `<div class="empty-msg">Aucune information trouvée</div>`;
  } else {
    body.innerHTML = res.findings.map(f => {
      const url = f.url ? `<div class="finding-item-url"><a href="${escapeAttr(f.url)}" target="_blank" rel="noopener">${escapeHtml(f.url)}</a></div>` : '';
      const extraRows = Object.entries(f.extra || {})
        .filter(([k, v]) => v != null && v !== '' && !['latitude', 'longitude', 'exists', 'category', 'checked'].includes(k))
        .map(([k, v]) => `<div style="font-family: monospace; font-size: 10px; color: var(--text-dim); margin-top: 2px;"><span style="color: var(--text-muted);">${escapeHtml(k)}:</span> ${escapeHtml(String(v))}</div>`)
        .join('');

      return `
        <div class="finding-item">
          <div class="finding-item-label">${escapeHtml(f.label || '')}</div>
          ${f.value ? `<div class="finding-item-value">${escapeHtml(f.value)}</div>` : ''}
          ${url}
          ${extraRows}
        </div>
      `;
    }).join('');
  }
}

// -------------------------------------------------------------
// MAIN SEARCH EVENT HANDLER
// -------------------------------------------------------------
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const target = input.value.trim();
  if (!target) return;
  if (currentEs) currentEs.close();

  // Reset UI sections
  runInfo.classList.add('hidden');
  mapSection.classList.add('hidden');
  socialSection.classList.add('hidden');
  webSection.classList.add('hidden');

  socialGrid.innerHTML = '';
  webGrid.innerHTML = '';
  otherSections.innerHTML = '';

  mapMarkers.forEach(m => m.remove());
  mapMarkers = [];
  seenCoords.clear();
  detectedLocations.clear();
  socialMap.clear();
  seenWebUrls.clear();
  otherSourceCards.clear();

  mapCount.textContent = '0 localisation';
  socialFoundCount.textContent = '0 profil détecté';
  socialTotalCount.textContent = '0 testé';
  webCount.textContent = '0 résultat unique';

  const body = { target };
  if (typeSel.value !== 'auto') body.type = typeSel.value;

  systemStatus.textContent = 'SCANNING...';

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
    if (!r.ok) throw new Error(data.error || 'Request failed');
  } catch (err) {
    systemStatus.textContent = 'ERROR';
    webSection.classList.remove('hidden');
    webGrid.innerHTML = `<div class="error-msg" style="padding: 16px;">[FATAL] ${escapeHtml(err.message)}</div>`;
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

  // Connect SSE
  const es = new EventSource(
    `/api/stream/${encodeURIComponent(data.job_id)}?target=${encodeURIComponent(target)}&type=${encodeURIComponent(data.input_type)}`
  );
  currentEs = es;

  es.addEventListener('result', (ev) => {
    const res = JSON.parse(ev.data);
    
    // 1. Social Media Processing
    if (res.source === 'username_sites') {
      if (res.findings && res.findings.length) {
        for (const f of res.findings) {
          const platform = (f.extra && f.extra.platform) ? f.extra.platform : f.label;
          const exists = (f.extra && f.extra.exists != null) ? f.extra.exists : (f.value !== 'Non trouvé');
          updateSocialPlatform(platform, f.url, exists);
        }
      }
    } else if (res.source === 'github') {
      if (res.found && res.findings && res.findings.length) {
        updateSocialPlatform('GitHub', res.findings[0].url || `https://github.com/${target.replace(/\s+/g, '')}`, true);
      }
    } else if (res.source === 'holehe') {
      if (res.findings && res.findings.length) {
        for (const f of res.findings) {
          updateSocialPlatform(f.label, f.url, true);
        }
      }
    }

    // Also check if any search engine result discovered a social media profile
    if (res.findings && res.findings.length) {
      for (const f of res.findings) {
        if (f.url) {
          const detectedPlatform = detectSocialNetworkFromUrl(f.url);
          if (detectedPlatform && isSocialUrlForTarget(f.url, target)) {
            updateSocialPlatform(detectedPlatform, f.url, true);
          }
        }
      }
    }

    // 2. Global Unified Web Results (Google, DuckDuckGo, Yandex)
    if (['google', 'duckduckgo', 'yandex'].includes(res.source)) {
      if (res.findings && res.findings.length) {
        for (const f of res.findings) {
          addWebFinding(f);
        }
      }
    } else if (!['username_sites', 'github', 'holehe'].includes(res.source)) {
      // 3. Other Domain-Specific Cards (Directory, Phone, Domain, BSSID, Breach, Archive, Wiki)
      fillDomainCard(res);
    }

    // 4. Geolocation coordinates & Map
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
    runDone.textContent = `${done} / ${total}`;
    progressBar.style.width = `${(done / total) * 100}%`;
  });

  es.addEventListener('done', () => {
    progressBar.style.width = '100%';
    systemStatus.textContent = 'SYSTEM READY';
    runDone.textContent = 'Terminé';
    es.close();
    currentEs = null;
    if (leafletMap) setTimeout(() => leafletMap.invalidateSize(), 300);
  });

  es.onerror = () => {
    es.close();
    currentEs = null;
    systemStatus.textContent = 'SYSTEM READY';
  };
});

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function escapeAttr(s) { return escapeHtml(s); }
function cssEscape(s) { return String(s).replace(/[^a-zA-Z0-9_-]/g, '\\$&'); }
