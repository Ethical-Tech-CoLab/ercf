'use strict';

// ═══════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════

const WEIGHTS = { d1:0.25, d2:0.15, d3:0.15, d4:0.15, d5:0.15, d6:0.10, d7:0.05 };

// Weight rationale and validation status for the Weights transparency panel.
// ALL WEIGHTS ARE MODELLED ESTIMATES — no published IHL weighting framework found (June 2026).
// "validated: false" signals the red unvalidated dot in the UI.
const WEIGHT_META = {
  d1: {
    name: 'D1 Kinetic Threat',
    rationale: 'Highest weight (25%). Direct physical threat is the primary driver of evacuation necessity. AP I Art. 57-58 precautionary measures are triggered first by active attack risk. This dimension alone determines whether movement is physically safe.',
    source: 'AP I Art. 57-58 (precautionary measures); GC IV Art. 49. Weight: modelled estimate — no peer-reviewed IHL weighting framework found.',
    validated: false,
  },
  d2: {
    name: 'D2 Mobility Constraints',
    rationale: 'Equal weight (15%) with D3-D5. Mobility constraints determine whether evacuation is physically possible. High D2 forces medical vehicle allocation and slows the entire operation, making it operationally equivalent in importance to logistics and authorization.',
    source: 'ICRC guidance on protection of persons with disabilities in armed conflict; Sphere 2018 (adapted transport). Weight: modelled estimate.',
    validated: false,
  },
  d3: {
    name: 'D3 Authorization',
    rationale: 'Equal weight (15%) with D2/D4/D5. Without consent of armed parties, evacuation is illegal under IHL and operationally blocked. Capped at 15% (not higher) because the hard trigger and decision text already capture the most extreme authorization failures.',
    source: 'GC IV Art. 49 (consent requirement); ICRC Humanitarian Access in Situations of Armed Conflict (2011). Weight: modelled estimate.',
    validated: false,
  },
  d4: {
    name: 'D4 Logistics',
    rationale: 'Equal weight (15%) with D2/D3/D5. Even where safe and authorized, evacuation fails without road access, vehicles, and fuel. Logistics collapse is empirically the leading cause of delayed evacuations (Mosul 2016, Aleppo 2016).',
    source: 'WFP Logistics Cluster field data; NATO NEO doctrine (logistics pre-staging requirement). Weight: modelled estimate.',
    validated: false,
  },
  d5: {
    name: 'D5 Destination',
    rationale: 'Equal weight (15%) with D2/D3/D4. Moving civilians to an unsafe destination creates secondary harm violating non-refoulement. Srebrenica (1995) is the canonical case: evacuation to a nominally safe zone became a site of genocide.',
    source: 'IHL non-refoulement principle; UNHCR protection guidance; Srebrenica ICTY case. Weight: modelled estimate.',
    validated: false,
  },
  d6: {
    name: 'D6 Urgency',
    rationale: 'Lower weight (10%). Urgency compresses decision timelines but is largely subsumed by D1 in the most extreme scenarios. The hard trigger (D1+D6 >= 4.5) and the evacuation window indicator capture urgency non-linearly, so the linear weight is intentionally modest.',
    source: 'NATO NEO doctrine (72-hour window standard); IHL AP I Art. 57(2)(c) advance warning. Weight: modelled estimate.',
    validated: false,
  },
  d7: {
    name: 'D7 Information',
    rationale: 'Lowest weight (5%). Information gaps increase coordination cost and civilian panic risk, but communications failure alone does not determine whether evacuation is necessary or physically possible. Physical threat and logistics dominate over information environment.',
    source: 'OCHA INFORM methodology (information as secondary risk factor); ICRC communications in emergencies guidance. Weight: modelled estimate.',
    validated: false,
  },
};

const RISK_DEF = [
  { max:1.5, level:0, label:'Baseline / Monitoring',   nato:'Permissive (Stable)',    color:'#6c757d', text:'#fff',
    decision:'Baseline — no active armed threat to civilian population',
    ihl:'GC IV Art. 49 threshold not yet met.' },
  { max:2.5, level:1, label:'Low Risk (Advisory)',      nato:'Permissive (Degrading)', color:'#0ea5e9', text:'#fff',
    decision:'Advisory — early warning phase; D1 kinetic threat emerging',
    ihl:'Art. 35 GC IV — voluntary departure right applies.' },
  { max:3.5, level:2, label:'Moderate Risk (Watchful)', nato:'Uncertain',              color:'#f59e0b', text:'#000',
    decision:'Watchful — corridor negotiation phase; D3 authorization and D6 urgency are key indicators',
    ihl:'AP I Art. 57–58 — precautionary measures required.' },
  { max:4.2, level:3, label:'High Risk (Contested)',    nato:'Hostile (Partial)',      color:'#f97316', text:'#fff',
    decision:'Contested — mass movement threshold; D2 mobility and D4 logistics are limiting factors',
    ihl:"GC IV Art. 49: 'security of the population so demand'." },
  { max:9.9, level:4, label:'Critical / Emergency',     nato:'Hostile (Imminent)',     color:'#ef4444', text:'#fff',
    decision:'Emergency — extraction phase; D1 kinetic and D6 urgency at critical levels',
    ihl:'GC IV Art. 49(1) — forced transfer = grave breach. Rome Statute Art. 8(2)(b)(viii).' },
];

const LEVEL_COLORS = ['#6c757d','#0ea5e9','#f59e0b','#f97316','#ef4444'];

// Terrain & Infrastructure multiplier — applied to transport and fuel costs only
// Sources: World Bank RAI country scores, Puga TRI dataset, NDU Press Afghanistan analysis
// Level 1=critical impediment (×4.0) … Level 5=minimal/baseline (×1.0)
const TERRAIN_MULT = { 1: 4.0, 2: 2.5, 3: 1.7, 4: 1.2, 5: 1.0 };

// Infrastructure-denial mortality multiplier — v7 calibration
// Source: GRC Mariupol 2024; UN CoI Syria 2017; ICTY Vukovar proceedings; HRW/Amnesty Angola 1994/1996
// v7 calibration: α=0.4251 (optimised jointly with base rates, differential_evolution, 16 cases)
// Applied to 4 cases: Mariupol, Aleppo, Vukovar, Huambo (infra_denial_flag=True in historical_data.py)
const INFRA_DENIAL_ALPHA        = 0.4251;
const INFRA_DENIAL_D1_THRESHOLD = 4.5;
const INFRA_DENIAL_D4_THRESHOLD = 4.0;

function infraDenialMult(infraDenialFlag, d1, d4) {
  // Flag must be explicitly true — auto-activation by D-scores alone caused calibration collapse.
  if (infraDenialFlag && d1 >= INFRA_DENIAL_D1_THRESHOLD && d4 >= INFRA_DENIAL_D4_THRESHOLD) {
    return 1.0 + INFRA_DENIAL_ALPHA * (d1 - 3.0) * (d4 - 3.0);
  }
  return 1.0;
}

function getSeasonalTerrainFactor(terrain, lat, month) {
  const base = TERRAIN_MULT[terrain] ?? 1.0;
  let zone, closureMonths, zoneLabel;
  if (lat > 30) {
    zone = 'northern_temperate';
    closureMonths = [12, 1, 2, 3];
    zoneLabel = 'northern temperate (snow/ice closure Dec–Mar)';
  } else if (lat < -30) {
    zone = 'southern_temperate';
    closureMonths = [6, 7, 8, 9];
    zoneLabel = 'southern temperate (snow/ice closure Jun–Sep)';
  } else {
    zone = 'tropical';
    closureMonths = [4, 5, 6, 7, 8, 9, 10];
    zoneLabel = 'tropical/subtropical (wet season Apr–Oct, estimated)';
  }
  const SEASONAL_BOOST = {1: 0.50, 2: 0.30, 3: 0.20, 4: 0.0, 5: 0.0};
  const boost = SEASONAL_BOOST[terrain] ?? 0.0;
  const isClosure = closureMonths.includes(month) && [1,2,3].includes(terrain);
  const potentiallyImpassable = (terrain === 1) && isClosure;
  const adjustedMult = (isClosure && boost > 0) ? Math.round(base * (1 + boost) * 100) / 100 : base;
  const note = (isClosure && boost > 0)
    ? `Terrain level ${terrain} in seasonal closure period (${zoneLabel}). Base multiplier ×${base} boosted by ${Math.round(boost*100)}% to ×${adjustedMult}.` +
      (potentiallyImpassable ? ' WARNING: route potentially impassable — consider alternative.' : '')
    : `Terrain level ${terrain} outside seasonal closure period (${zoneLabel}).`;
  return { terrainMult: adjustedMult, baseMult: base, isClosure, potentiallyImpassable, zone, zoneLabel, closureMonths, boost: isClosure ? boost : 0, note };
}

const DIM_LABELS = ['D1 Kinetic','D2 Mobility Constraints','D3 Authorization','D4 Logistics','D5 Destination','D6 Urgency','D7 Information'];
const DIM_KEYS   = ['d1','d2','d3','d4','d5','d6','d7'];

const CASE_COORDS = {
  1:  [47.0975,  37.5400],   // Mariupol, Ukraine
  2:  [31.3547,  34.3088],   // Gaza, Palestine
  3:  [44.1000,  19.2982],   // Srebrenica, Bosnia
  4:  [36.2021,  37.1343],   // Aleppo, Syria
  5:  [46.6354,  32.6169],   // Kherson, Ukraine
  6:  [36.3400,  43.1300],   // Mosul, Iraq
  7:  [42.6629,  21.1655],   // Kosovo (Pristina)
  8:  [ 4.3612,  18.5550],   // Bangui, CAR
  9:  [15.5007,  32.5599],   // Khartoum, Sudan
  10: [-1.6792,  29.2228],   // Goma, DRC
};

// Choropleth colours and opacity per ERCF level
const CHORO_COLORS  = { 4:'#ef4444', 3:'#f97316', 2:'#f59e0b', 1:'#0ea5e9', 0:'#b0c4de', '-1':'#e0e0e0' };
const CHORO_OPACITY = { 4:.82, 3:.76, 2:.72, 1:.68, 0:.60, '-1':.45 };

// Approximate country centroids for safe zone suggestion (ISO3 → [lat, lng])
const COUNTRY_CENTROIDS = {
  AGO:[-11.20,17.87], BDI:[-3.37,29.92],  BEN:[9.31,2.32],    BFA:[12.36,-1.52],
  BWA:[-22.33,24.68], CAF:[6.61,20.94],   CIV:[7.54,-5.55],   CMR:[7.37,12.35],
  COD:[-4.04,21.76],  COG:[-0.23,15.83],  DJI:[11.83,42.59],  DZA:[28.03,1.66],
  EGY:[26.82,30.80],  ETH:[9.15,40.49],   GAB:[-0.80,11.61],  GHA:[7.95,-1.02],
  GIN:[11.75,-15.45], GMB:[13.44,-15.31], GNQ:[1.65,10.27],   KEN:[-0.02,37.91],
  LBR:[6.43,-9.43],   LBY:[26.34,17.23],  MDG:[-18.77,46.87], MLI:[17.57,-3.99],
  MRT:[21.01,-10.94], MWI:[-13.25,34.30], MOZ:[-18.67,35.53], NAM:[-22.96,18.49],
  NER:[17.61,8.08],   NGA:[9.08,8.68],    RWA:[-1.94,29.87],  SDN:[12.86,30.22],
  SEN:[14.50,-14.45], SLE:[8.46,-11.78],  SOM:[5.15,46.20],   SSD:[6.88,31.57],
  TCD:[15.45,18.73],  TGO:[8.62,0.82],    TZA:[-6.37,34.89],  UGA:[1.37,32.29],
  ZAF:[-30.56,22.94], ZMB:[-13.13,27.85], ZWE:[-19.02,29.15],
  IRN:[32.43,53.69],  IRQ:[33.22,43.68],  ISR:[31.05,34.85],  JOR:[30.59,36.24],
  KWT:[29.31,47.48],  LBN:[33.85,35.86],  OMN:[21.51,55.92],  QAT:[25.35,51.18],
  SAU:[23.89,45.08],  SYR:[34.80,38.99],  TUR:[38.96,35.24],  UAE:[23.42,53.85],
  YEM:[15.55,48.52],  PSE:[31.95,35.23],
  AFG:[33.93,67.71],  ARM:[40.07,45.04],  AZE:[40.14,47.58],  BGD:[23.69,90.36],
  CHN:[35.86,104.20], GEO:[42.32,43.36],  IDN:[-0.79,113.92], IND:[20.59,78.96],
  KAZ:[48.02,66.92],  KGZ:[41.20,74.77],  KHM:[12.57,104.99], LAO:[19.86,102.50],
  MMR:[21.92,95.96],  MYS:[4.21,101.98],  NPL:[28.39,84.12],  PAK:[30.38,69.35],
  PHL:[12.88,121.77], THA:[15.87,100.99], TJK:[38.86,71.28],  TKM:[38.97,59.56],
  TLS:[-8.87,125.73], UZB:[41.38,64.59],  VNM:[14.06,108.28],
  ALB:[41.15,20.17],  BIH:[43.92,17.68],  BLR:[53.71,27.95],  DEU:[51.17,10.45],
  FRA:[46.23,2.21],   GBR:[55.38,-3.44],  GRC:[39.07,21.82],  ITA:[41.87,12.57],
  MDA:[47.41,28.37],  MKD:[41.61,21.75],  NOR:[60.47,8.47],   POL:[51.92,19.15],
  ROU:[45.94,24.97],  SRB:[44.02,21.01],  SWE:[60.13,18.64],  UKR:[48.38,31.17],
  BOL:[-16.29,-63.59],BRA:[-14.24,-51.93],CAN:[56.13,-106.35],CHL:[-35.68,-71.54],
  COL:[4.57,-74.30],  ECU:[-1.83,-78.18], GTM:[15.78,-90.23], HTI:[18.97,-72.29],
  HND:[15.20,-86.24], MEX:[23.63,-102.55],PER:[-9.19,-75.02], USA:[37.09,-95.71],
  VEN:[6.42,-66.59],
};

// Border crossing / entry-point coordinates (replaces centroid for these countries).
// Coordinates are the main land crossing or nearest safe city on the border, not the country centre.
const BORDER_ENTRY_POINTS = {
  // Eastern Europe — Ukraine neighbours
  POL: { lat: 49.84, lng: 22.78, name: 'Medyka/Przemyśl crossing' },
  ROU: { lat: 47.65, lng: 26.25, name: 'Siret crossing' },
  MDA: { lat: 47.75, lng: 30.33, name: 'Palanca crossing' },
  SVK: { lat: 48.93, lng: 22.28, name: 'Uzhhorod/Vyšné Nemecké crossing' },
  HUN: { lat: 48.39, lng: 22.15, name: 'Záhony crossing' },
  // Middle East
  TUR: { lat: 36.83, lng: 36.63, name: 'Bab al-Hawa crossing' },
  JOR: { lat: 32.65, lng: 35.55, name: 'Jaber/Nassib crossing' },
  LBN: { lat: 33.32, lng: 35.54, name: 'Masnaa crossing' },
  EGY: { lat: 31.12, lng: 34.20, name: 'Rafah crossing' },
  // Africa
  CMR: { lat: 5.88,  lng: 14.43, name: 'Garoua-Boulaï crossing' },
  TCD: { lat: 12.11, lng: 15.04, name: 'N\'Djamena entry' },
  ETH: { lat: 4.66,  lng: 34.99, name: 'Moyale crossing' },
  KEN: { lat: 3.51,  lng: 41.85, name: 'Mandera crossing' },
  UGA: { lat: 1.04,  lng: 30.46, name: 'Bunagana crossing' },
  RWA: { lat: -1.38, lng: 29.73, name: 'Gisenyi crossing' },
  // South/Central Asia
  PAK: { lat: 31.61, lng: 65.71, name: 'Spin Boldak crossing' },
  IRN: { lat: 34.49, lng: 47.09, name: 'Islam Qala crossing' },
};

// Known safe cities for specific conflict contexts (cities, not country centroids).
// Used alongside country suggestions to show realistic near-term evacuation destinations.
const KNOWN_SAFE_CITIES = [
  // Ukraine
  { name: 'Zaporizhzhia',  lat: 47.84, lng: 35.14, country: 'UKR', note: 'Major evacuation hub' },
  { name: 'Dnipro',        lat: 48.46, lng: 35.05, country: 'UKR', note: 'Major evacuation hub' },
  { name: 'Lviv',          lat: 49.84, lng: 24.03, country: 'UKR', note: 'Western Ukraine, near EU border' },
  // Iraq / Kurdistan
  { name: 'Erbil',         lat: 36.19, lng: 44.01, country: 'IRQ', note: 'Kurdistan Region capital' },
  { name: 'Sulaymaniyah',  lat: 35.56, lng: 45.43, country: 'IRQ', note: 'Kurdistan Region' },
  // Syria
  { name: 'Azaz',          lat: 36.59, lng: 37.05, country: 'SYR', note: 'Near Turkish border' },
  // Sudan
  { name: 'Port Sudan',    lat: 19.62, lng: 37.22, country: 'SDN', note: 'Main 2023 evacuation hub' },
  { name: 'Kassala',       lat: 15.45, lng: 36.40, country: 'SDN', note: 'Eastern Sudan, near Ethiopia border' },
  // DRC
  { name: 'Bukavu',        lat: -2.51, lng: 28.86, country: 'COD', note: 'South Kivu, south of Goma' },
  // Gaza / Palestine
  { name: 'Rafah',         lat: 31.30, lng: 34.25, country: 'PSE', note: 'Southern Gaza, Rafah crossing' },
  // Balkans
  { name: 'Tirana',        lat: 41.33, lng: 19.83, country: 'ALB', note: 'Albania capital' },
  { name: 'Skopje',        lat: 41.99, lng: 21.43, country: 'MKD', note: 'North Macedonia' },
];

// ═══════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════

const state = {
  dims: { d1:3, d2:3, d3:3, d4:3, d5:3, d6:3, d7:3 },
  population:      10000,
  vulnerablePct:   20,
  distanceKm:      50,
  terrain:         3,      // Terrain & Infrastructure level (1=critical, 5=minimal/baseline)
  conflictType:    5,      // 1=urban_siege 2=enclave 3=city_conflict 4=regional 5=auto
  days:            30,
  remainingPop:     10000,  // people staying in zone
  remainingPct:     100,    // percentage mode value
  remainingPctMode: true,   // true = slider %, false = absolute number
  remainingVulnPct: 20,     // derived: vulnerable % among those remaining (higher when few evacuated)
  historicalCases:  [],
  savedScenarios:   [],
  comparisonData:   null,   // set when user picks a case in Compare dropdown
  _lastResources:   null,   // cached each updateAll() for comparison panel
  _lastStayData:    null,
  _lastRisk:        null,
  _lastAltResult:   null,   // cached air/walking-evacuation API response, cleared on scenario or mode change until re-fetched
  charts: {},
  conflictCoords:    null,   // {lat, lng}
  safeZoneCoords:    null,   // {lat, lng, name}
  distanceSource:       'manual',   // 'manual' | 'map_pin' | 'ai_suggested'
  roadFactorApplied:    false,
  _haversineKm:         null,      // raw haversine distance before road factor
  _aiSuggestedSafeZone: null,      // {name, lat, lng, dist, score} — best AI candidate in modal
  startDate:            null,      // ISO date string 'YYYY-MM-DD' for climate lookup
  climateMult:          null,      // {fuel_transport: float, shelter: float} from ERA5 or null
  fuelAdjFactor:        1.0,       // FRED/EIA fuel market adjustment (1.0 = ERCF baseline)
  foodAdjFactor:        1.0,       // FRED food-basket market adjustment — also applied to water (1.0 = ERCF baseline)
  hasRunway:            null,      // true/false/null — runway availability for air_fixed feasibility; no UI control yet, always unanswered
  personnelRateMode:    'ngo',     // 'ngo' | 'un' — toggles personnel cost multiplier
  unitSystem:           'km',      // 'km' | 'mi' — display only; all internal calcs remain in km
};

const KM_TO_MI = 0.621371;

function fmtDist(km) {
  if (km == null || isNaN(km)) return '—';
  if (state.unitSystem === 'mi') return `${Math.round(km * KM_TO_MI).toLocaleString()} mi`;
  return `${Math.round(km).toLocaleString()} km`;
}

function toDisplayUnit(km) {
  if (km == null) return '';
  return state.unitSystem === 'mi' ? Math.round(km * KM_TO_MI * 10) / 10 : Math.round(km * 10) / 10;
}

function toKm(displayValue) {
  return state.unitSystem === 'mi' ? displayValue / KM_TO_MI : displayValue;
}

function toggleUnitSystem() {
  state.unitSystem = state.unitSystem === 'km' ? 'mi' : 'km';
  const distInput = document.getElementById('inDist');
  if (distInput && state.distanceKm != null) distInput.value = toDisplayUnit(state.distanceKm);
  const unitLabel = document.getElementById('distUnitLabel');
  if (unitLabel) unitLabel.textContent = state.unitSystem === 'mi' ? 'mi' : 'km';
  const toggleBtn = document.getElementById('unitToggleBtn');
  if (toggleBtn) toggleBtn.textContent = state.unitSystem === 'mi' ? 'Switch to km' : 'Switch to mi';
  updateAll();
}

const worldMapState = {
  lmap:         null,
  geojsonLayer: null,
  histMarkers:  [],
  showHist:     true,
  worldRisk:    {},   // ISO3 → {level, name, inform_score, crisis, …}
  isoLookup:    {},   // numeric string → ISO3
  initialized:  false,
  activeFilter: -1,
  selectedIso:  null,
  conflictPinMarker: null,   // red pin on world map tab
  safeZonePinMarker: null,   // green pin on world map tab
  pinLine:           null,   // dashed line between them
};

// ═══════════════════════════════════════════════════════════
// PURE CALCULATIONS (client-side for real-time response)
// ═══════════════════════════════════════════════════════════

// Decision matrix — mirrors DECISION_MATRIX in calculators.py
const DECISION_MATRIX_JS = {
  high_high: {
    recommendation: "High danger · Corridor viable — evacuation feasible",
    rationale: "Kinetic threat is severe AND a corridor exists. Conditions support movement if the decision to evacuate is made. Cost and resource data shown below.",
    ihl_trigger: "GC IV Art. 49 conditions met: danger to civilian population + viable passage.",
    color: "#dc2626", icon: "🔴",
  },
  high_low: {
    recommendation: "High danger · Corridor blocked — movement constrained",
    rationale: "Kinetic threat is severe AND no viable corridor exists. Movement carries high risk. Shelter-in-place costs shown in Assistance panel below.",
    ihl_trigger: "GC IV Art. 17: parties should endeavour to conclude agreements for removal of wounded, sick, infirm, aged, children and maternity cases.",
    color: "#ea580c", icon: "🟠",
  },
  low_high: {
    recommendation: "Moderate danger · Corridor open — voluntary movement possible",
    rationale: "Kinetic threat is below critical threshold AND a corridor exists. Conditions support voluntary departure for vulnerable groups. Evacuation cost data shown below.",
    ihl_trigger: "GC IV Art. 49 threshold not yet met for mandatory evacuation.",
    color: "#d97706", icon: "🟡",
  },
  low_low: {
    recommendation: "Low danger · Corridor constrained — monitoring phase",
    rationale: "Kinetic threat is below critical threshold AND no viable corridor exists. Situation does not yet warrant movement. Monitor D1 (kinetic) and D3 (authorization) indicators.",
    ihl_trigger: "GC IV Art. 49 threshold not met.",
    color: "#6b7280", icon: "⬜",
  },
};

function calcRisk(dims) {
  const d = dims;
  let score = Object.entries(WEIGHTS).reduce((s, [k, w]) => s + (d[k] || 1) * w, 0);
  if ((d.d1 || 0) >= 4.5 && (d.d6 || 0) >= 4.5) score = Math.max(score, 4.21);

  // ── Sub-indexes (mirrors calculators.py calculate_risk) ──────────────────
  const riskSub = (
    (d.d1 || 1) * 0.25 +
    (d.d2 || 1) * 0.15 +
    (d.d6 || 1) * 0.10
  ) / 0.50;

  const feasSub = (
    (6 - (d.d3 || 1)) * 0.15 +
    (6 - (d.d4 || 1)) * 0.15 +
    (6 - (d.d5 || 1)) * 0.15
  ) / 0.45;

  const infoSub = 6 - (d.d7 || 1);

  const riskCell = riskSub >= 3.5 ? 'high' : 'low';
  const feasCell = feasSub >= 3.0 ? 'high' : 'low';
  const matrix   = DECISION_MATRIX_JS[`${riskCell}_${feasCell}`];

  const base = (() => {
    for (const r of RISK_DEF) if (score <= r.max) return { ...r, score: +score.toFixed(2) };
    return { ...RISK_DEF[4], score: +score.toFixed(2) };
  })();

  return {
    ...base,
    subScores: {
      riskSeverity: { score: +riskSub.toFixed(2), cell: riskCell },
      feasibility:  { score: +feasSub.toFixed(2), cell: feasCell },
      infoQuality:  { score: +infoSub.toFixed(2) },
    },
    matrix,
  };
}

function calcResources(pop, vulPct, riskLevel, distKm, d2Mobility, terrain, climateMult = state.climateMult, terrainMultOverride, d4 = 3, d5 = 3) {
  const vuln    = Math.round(pop * vulPct / 100);
  const nonVuln = pop - vuln;
  const stdBus  = Math.ceil(nonVuln / 50);

  // D2 Mobility Constraints multiplier on medical vehicles
  // D2=1→×0.8  D2=2→×1.0  D2=3→×1.3  D2=4→×1.8  D2=5→×2.5 (linear interpolation)
  const d2 = (d2Mobility != null) ? d2Mobility : 3;
  const d2Mult = d2 <= 1 ? 0.8
               : d2 <= 2 ? 0.8 + (d2 - 1) * 0.2
               : d2 <= 3 ? 1.0 + (d2 - 2) * 0.3
               : d2 <= 4 ? 1.3 + (d2 - 3) * 0.5
               :            1.8 + (d2 - 4) * 0.7;
  const medBus  = Math.ceil(vuln / 20 * d2Mult);
  // Revised from 1:40 to 1:150 vulnerable. No published field standard found (ICRC 2015, WHO EMS,
  // MSF — none specify evacuation ambulance ratios). 1:150 consistent with documented field scarcity.
  const ambu    = Math.max(1, Math.ceil(vuln / 150 * d2Mult));
  const totVeh  = stdBus + medBus + ambu;
  const secR    = [99999, 500, 200, 100, 50][riskLevel];
  const sec     = riskLevel > 0 ? Math.ceil(pop / secR) : 0;
  const medS    = Math.ceil(pop / 250); // Sphere 2018: 1 clinical officer per 250 people
  const para    = Math.ceil(pop / 100);
  const fuelL   = totVeh * distKm * 2 * 0.35;
  const foodKg  = pop * 3 * 0.45; // Sphere 2018: 0.45 kg/person/day
  // WATER_L_PER_PERSON updated 15 → 20 (Tavily validation June 2026)
  // UNHCR full standard: 20 L/person/day; Sphere 2018 emergency minimum: 7.5-15 L
  const waterL  = pop * 3 * 20;
  // D5 runs 1 = destination fully equipped -> 5 = destination unsafe/non-existent
  const D5_TENT_MULT = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.5, 5: 2.0};
  const d5TentMult = D5_TENT_MULT[Math.round(d5)] ?? 1.0;
  const tents   = Math.ceil((pop / 5) * d5TentMult);
  const radios  = Math.ceil(totVeh / 5) + 5;
  const mkits   = Math.ceil(pop / 100);
  const tkits   = riskLevel >= 3 ? Math.ceil(pop / 50) : Math.ceil(pop / 200);

  const terrainMult        = terrainMultOverride ?? (TERRAIN_MULT[terrain] ?? 1.0);
  const cm                 = climateMult || {};
  const climateFuelMult    = cm.fuel_transport ?? 1.0;
  const climateShelterMult = cm.shelter        ?? 1.0;
  // UN rate multiplier: UN DSA fully loaded ($400-580/day) vs NGO base ($87-97/day MSF)
  // Midpoint ratio: ($490/$92) ≈ 4.5× — estimated, see deployNotice for sourcing
  const personnelRateMult = (typeof state !== 'undefined' && state.personnelRateMode === 'un') ? 4.5 : 1.0;
  // D4 Logistics multiplier on transport + fuel — ESTIMATED, see calculators.py
  const d4LogisticsMult = 1.0 + Math.max(0, (d4 - 1)) * 0.10;
  const c = {
    // MED_BUS_COST $250→$400; AMBULANCE_COST $400→$700 (Tavily validation June 2026)
    transport: Math.round((stdBus*200 + medBus*400 + ambu*700 + totVeh*50) * terrainMult * climateFuelMult * d4LogisticsMult),
    fuel:      Math.round(fuelL * 1.2 * terrainMult * climateFuelMult * d4LogisticsMult * (state.fuelAdjFactor ?? 1.0)),   // $1.20/L base; market-adjusted via EIA Brent
    personnel: Math.round((sec*300 + medS*200 + para*150) * personnelRateMult),
    food:      Math.round(foodKg * 3 * (state.foodAdjFactor ?? 1.0)),   // $3/kg base; market-adjusted via FRED food basket
    // $0.05/L baseline kept; field range $0.002-0.023/L found across NRC Yemen 2025, ICRC
    // Aleppo 2013-14, Ethiopia HRP 2024, Oxfam Kenya (no international index exists, not adopted)
    water:     Math.round(waterL * 0.05 * (state.foodAdjFactor ?? 1.0)),   // water priced via food/supply-chain market adjustment
    // TENT_COST $150→$380 (Tavily validation June 2026; UNHCR 2022 direct quote: $400/unit)
    shelter:   Math.round(tents * 380 * climateShelterMult),
    // MED_KIT_COST updated $50→$21/kit: WHO/UNICEF IEHK ~$20,584/10,000 pax/90d × 3d × ×3 trauma factor
    medical:   Math.round(mkits*21 + tkits*200),
    comms:     Math.round(radios * 500),
  };
  const sub = Object.values(c).reduce((a, b) => a + b, 0);
  c.contingency = Math.round(sub * 0.15);
  const total = Object.values(c).reduce((a, b) => a + b, 0);

  return {
    vehicles:  { stdBus, medBus, ambu, total: totVeh, drivers: totVeh },
    personnel: { sec, medS, para, drivers: totVeh, total: sec+medS+para+totVeh },
    supplies:  { fuelL: Math.round(fuelL), foodKg: Math.round(foodKg), waterL: Math.round(waterL), tents, radios },
    costs: c,
    totalCost: total,
    cpp: pop > 0 ? Math.round(total / pop) : 0,
  };
}

// ── Shared injury calculator ──────────────────────────────────────────────────
// ─── ERCF Mortality Model v3 — Geographic Exposure Factor ────────────────────
// Named exposure fractions per conflict pattern. Mirrors CONFLICT_TYPE_EXPOSURE
// in calculators.py — keep in sync.
const CONFLICT_EXPOSURE_NAMED = {
  'urban_siege':   0.85,
  'enclave':       0.65,
  'city_conflict': 0.40,
  'regional':      0.12,
};
// Maps UI integer (1-4) to exposure type string.
const CONFLICT_TYPE_KEY = {1:'urban_siege', 2:'enclave', 3:'city_conflict', 4:'regional'};

// Compute exposure factor from state. Uses state.conflictType and state.population.
// Must be called from updateAll() (has access to full state).
function computeExposureFactor() {
  if (state.conflictType !== 5) {
    return CONFLICT_EXPOSURE_NAMED[CONFLICT_TYPE_KEY[state.conflictType]] ?? 1.0;
  }
  // Auto (v4): steeper log falloff via exponent 1.4; Math.max(0,...) guards negative log
  const d1       = state.dims.d1 || 3;
  const popRatio = Math.max(1, Math.pow(Math.max(0, Math.log10(Math.max(1, state.population) / 10000)), 1.4));
  return Math.min(1.0, Math.max(0.05, (d1 / popRatio) / 5));
}

// Compute exposure factor for a historical case using its stored exposure_type.
// Falls back to auto formula using D1 and population if exposure_type not available.
function computeHistExposureFactor(c) {
  if (c.exposure_type && CONFLICT_EXPOSURE_NAMED[c.exposure_type] != null) {
    return CONFLICT_EXPOSURE_NAMED[c.exposure_type];
  }
  const d1       = c.risk_indicators?.d1_kinetic || 3;
  const popRatio = Math.max(1, Math.pow(Math.max(0, Math.log10(Math.max(1, c.population_at_risk) / 10000)), 1.4));
  return Math.min(1.0, Math.max(0.05, (d1 / popRatio) / 5));
}
// ─────────────────────────────────────────────────────────────────────────────

// Injury rate used by calcRemaining only.
// calcStay now derives injuries from effective_mort × 4 (ICRC 4:1 ratio against v3 rate).
// v1 rates (per 10,000 per day): 4 × DEATH_RATE_10K [0.3,0.5,1.5,4.0,10.0]
function calcInjuries(pop, riskLevel, days) {
  const baseRate = [1.2, 2.0, 6.0, 16.0, 40.0][riskLevel] / 10000;
  return baseRate * pop * days;
}

// ─── ERCF Mortality Model v4 ─────────────────────────────────────────────────
// Mirrors calculate_staying_costs() v4 in calculators.py — must stay in sync.
// v2: empirical base rates, D3×D4 confinement modifier, displacement protection.
// v3: geographic exposure factor (conflict pattern × population dispersion).
// v4: siege protection cap (D3≥4 AND D1≥4 → max 0.30); steeper log falloff (^1.4).
// ─────────────────────────────────────────────────────────────────────────────
function calcStay(pop, riskLevel, maxDays, dims, remainingPct = 1.0, exposureFactor = 1.0, siegeCapEnabled = true) {
  const base     = [1.0, 2.0, 3.5, 6.0, 12.0][riskLevel];

  // CALIBRATION v7: differential_evolution on 16 in-scope cases (31 total corpus).
  // R²=0.855, LOOCV R²=0.807, 7/16 within 2× (44%). L3>L4 empirically validated.
  // Sources: ERCF Historical Case Database 1991–2024; calibration/full_calibration.py
  const baseRate = [0.777, 0.964, 3.625, 1.805, 1.000][riskLevel] / 10000;  // v7: differential_evolution

  // Confinement modifier + extract d1/d3/d4/d6 for siege detection and infra-denial
  let confMult = 1.0;
  let d1Val = 3.0, d3Val = 3.0, d4Val = 3.0, d6Val = 3.0;
  if (dims) {
    d1Val = dims.d1_kinetic ?? dims.d1 ?? 3.0;
    d3Val = dims.d3_political ?? dims.d3 ?? 3.0;
    d4Val = dims.d4_logistics ?? dims.d4 ?? 3.0;
    d6Val = dims.d6_urgency   ?? dims.d6 ?? 3.0;
    const d4 = d4Val;
    // D3 runs 1 = full consent → 5 = active refusal (see the D3 scale criteria in
    // index.html and calculators.py's WEIGHTS block): confinement rises with D3.
    const cs = (d3Val - 1.0) * d4Val / 5.0;
    if      (cs <= 1) confMult = 0.5;
    else if (cs <= 2) confMult = 1.0;
    else if (cs <= 3) confMult = 2.0;
    else if (cs <= 4) confMult = 4.0;
    else              confMult = 8.0;
  }

  // v4: siege protection cap — displacement under fire is only half as safe.
  // Requires pop ≤ 500k: large populations with D3=5 reflect regional access denial,
  // not urban encirclement. exposureFactor proxy for conflict type: named regional
  // (0.12) and city_conflict (0.40) thresholds disable the cap via caller.
  // In auto mode, the state.conflictType guard is applied in computeExposureFactor;
  // here we use population size as the sole runtime discriminator.
  const rp             = Math.max(0, Math.min(1, remainingPct ?? 1.0));
  const isSiege        = siegeCapEnabled && (d3Val >= 4.0 && d1Val >= 4.0 && pop <= 500000);
  const maxProtection  = isSiege ? 0.30 : 0.60;
  const protectionFactor = (1 - rp) * maxProtection;
  // Geographic exposure factor (v3/v4)
  const ef               = Math.max(0.05, Math.min(1.0, exposureFactor ?? 1.0));
  const idMult             = infraDenialMult(false, d1Val, d4Val);
  const infraDenialApplied = idMult > 1.0;
  const effectiveMort      = baseRate * confMult * (1 - protectionFactor) * ef * idMult;

  const dailyFin  = base * pop;
  const dailyMort = effectiveMort * pop;
  const dailyInj  = dailyMort * 4;   // ICRC 4:1 ratio against effective rate

  const days = [], bareSurvival = [], dead = [], inj = [];
  for (let d = 1; d <= maxDays; d++) {
    // Saturation: mortality rate decays after 90 days (population adapts, survivors relocate)
    // effectiveD = 90 + sqrt((d-90) * 90) for d > 90; linear below 90 days
    const effectiveD = d <= 90 ? d : 90 + Math.sqrt((d - 90) * 90);
    days.push(d);
    bareSurvival.push(Math.round(dailyFin * d));
    dead.push(+(dailyMort * effectiveD).toFixed(1));
    inj.push( +(dailyInj  * effectiveD).toFixed(1));
  }
  return { days, fin: bareSurvival, dead, inj, infraDenialApplied };
}

function calcRemaining(pop, vulPct, riskLevel, days, distKm, dims, terrain, climateMult = state.climateMult, injuriesOverride) {
  const d = dims || { d1:3, d2:3, d3:3, d4:3, d5:3, d6:3, d7:3 };
  const vuln    = Math.round(pop * vulPct / 100);
  const nonVuln = pop - vuln;

  // Terrain multiplier — applied to supply delivery (road access affects all aid logistics)
  const terrainMult = TERRAIN_MULT[terrain] ?? 1.0;

  // Base risk-level parameters (revised June 2026)
  const accessMult = [1.0, 1.5, 2.0, 3.6, 4.0][riskLevel];
  const lossRate   = [0.05, 0.05, 0.15, 0.30, 0.50][riskLevel];
  // injRate (RC_INFIELD_INJ) removed — injuries now computed by shared calcInjuries()

  // ── Dimension modifiers ──────────────────────────────────────────────────
  // D4 Logistics: higher D4 = harder delivery = supply cost multiplier
  const d4Penalty  = d.d4 <= 3 ? (d.d4 - 1) * 0.10 : 0.20 + (d.d4 - 3) * 0.20;
  // D3 Authorization: higher D3 = consent absent/refused = more blockade/seizure = higher loss rate
  const d3LossAdd  = d.d3 <= 3 ? (d.d3 - 1) * 0.05 : 0.10 + (d.d3 - 3) * 0.075;
  // D7 Information: higher D7 = worse information environment = harder coordination
  // (D7 runs 1 = reliable comms -> 5 = complete blackout, same direction as the others)
  const d7Overhead = d.d7 <= 3 ? (d.d7 - 1) * 0.025 : 0.05 + (d.d7 - 3) * 0.05;

  // D1 Kinetic: higher D1 = more dangerous = extraction difficulty multiplier
  const d1ExtMult  = d.d1 <= 3 ? 1.0 + (d.d1 - 1) * 0.15 : 1.3 + (d.d1 - 3) * 0.35;

  // D5 Destination: higher D5 = destination overwhelmed/unsafe = fewer medical resources
  // on arrival = higher cost per injury (1 = fully equipped -> 5 = unsafe/non-existent)
  // (D2/D1 injury-count multipliers removed — WHO rates already represent typical populations)
  const d5CostMult = d.d5 <= 3 ? 1.0 + (d.d5 - 1) * 0.15 : 1.3 + (d.d5 - 3) * 0.35;

  // ── Component 1: in-situ supply ─────────────────────────────────────────
  const effectiveAccessMult = accessMult * (1 + d4Penalty);
  const effectiveLossRate   = lossRate + d3LossAdd + d7Overhead;  // D7 folded in additively
  const climateFuelMult     = (climateMult || {}).fuel_transport ?? 1.0;
  // terrainMult and climateFuelMult applied to raw supply: poor roads and adverse climate increase delivery costs
  const rawSupply  = pop * 3.50 * effectiveAccessMult * terrainMult * climateFuelMult * days;
  const supplyCost = rawSupply * (1 + effectiveLossRate);

  // ── Component 2: emergency extraction ──────────────────────────────────
  // $2.08/passenger-km is the 2023 UNHAS fleet-wide confirmed rate.
  // Ground: 30% of air rate. Air/medevac: ×3 vulnerability premium.
  const UNHAS_RATE   = 2.08;
  const perPsnGround = UNHAS_RATE * 0.30 * distKm;
  const perPsnAir    = UNHAS_RATE * 3.00 * distKm;

  // Empirical exponential saturation — calibrated from ERCF Historical Case Database (31 cases, 16 in calibration set).
  // Rate k = −ln(1−p)/days derived per level:
  //   L4: Mariupol (86d,81%→k=0.019) + Aleppo (100d,90%→k=0.023) → mean 0.021
  //   L3: Mosul (270d,90%→k=0.009) + DRC (180d,80%→k=0.009) + CAR (180d,88%→k=0.012) → mean 0.010
  //   L2/L1: interpolated (no direct cases at those levels)
  //
  // Emergency extraction rate: estimated 1-8% of remaining population requiring urgent
  // medical evacuation (critical casualties unable to self-evacuate). Based on conflict
  // casualty ratios (ICRC surgical data) — not mass evacuation rate. Revised from the prior
  // 10-95% range, which conflated "probability of a mass extraction operation" with "fraction
  // of the population needing individual medevac" — UNHAS 2022 data shows only ~0.25% of all
  // passengers transported required medical/security evacuation, two orders of magnitude below
  // the prior calibration even accounting for a higher-need trapped-population context.
  const EXTR_BASE_RATE = [0.0, 0.002, 0.005, 0.010, 0.021];  // per-day exponential rate (unchanged shape)
  const EXTR_MAX_PROB  = [0.0, 0.01,  0.02,  0.04,  0.08 ];  // cap on base_prob: L1=1%, L2=2%, L3=4%, L4=8%
  const _rate   = EXTR_BASE_RATE[riskLevel];
  const baseProb = Math.min(
    _rate > 0 ? 1.0 - Math.exp(-_rate * days) : 0.0,
    EXTR_MAX_PROB[riskLevel],
  );

  // D3 Authorization: blocked corridors → higher extraction need
  // Scaled ÷10 versus the pre-recalibration increments (Mariupol/Aleppo/Kosovo anchors below
  // are the original 10-95%-scale figures) to stay proportionate within the new 1-8% range —
  // the underlying D3 relationship is unchanged.
  // Gentler slope than supply correction; anchored by Mariupol (D3=4.5→+12.5%), Kosovo (D3=4→+10%)
  const d3ProbAdd  = d.d3 <= 3 ? (d.d3 - 1) * 0.0025 : 0.005 + (d.d3 - 3) * 0.005;
  // D6 Urgency floor: scaled ÷10 for the same reason as d3ProbAdd above.
  // Srebrenica (D6=5, 3 days) → 85% floor; Kherson/Mosul/CAR (D6=4) → 60%
  const d6FloorVal = d.d6 >= 5 ? 0.085 : d.d6 >= 4 ? 0.06 : 0.0;

  const prob     = Math.min(Math.max(baseProb + d3ProbAdd, d6FloorVal), 0.95);
  const extractBase  = prob * (nonVuln * perPsnGround + vuln * perPsnAir) * d1ExtMult;
  const extractCost  = riskLevel === 4 ? extractBase * 2.5 : extractBase;

  // ── Component 3: field medical ──────────────────────────────────────────
  // Injury count sourced from calcStay()'s dims-modulated, day-saturated model — the same
  // number shown in the "EST. INJURIES" stat card — so this dollar figure and that card never
  // disagree. Falls back to the simpler flat-rate calcInjuries() only if no override is passed
  // (i.e. calcStay() wasn't run first by the caller).
  const cumInjuries  = injuriesOverride ?? calcInjuries(pop, riskLevel, days);
  const treatCostPer = 800 * d5CostMult;  // $800 base (peer-reviewed range $211–$1,013; updated Prompt 1)
  const medCost      = cumInjuries * treatCostPer;

  // ── Component 4: vulnerable population support ──────────────────────────
  // Additional per-capita cost for special needs (mobility assistance, extra medical
  // supplies, mental health support) not captured by the flat $3.50/day survival baseline.
  // No published per-capita figure exists (Sphere 2018 does not price this) — ESTIMATED.
  const VULNERABLE_DAILY_PREMIUM = 2.50;
  const vulnerablePremium = vuln * days * VULNERABLE_DAILY_PREMIUM;

  const total = supplyCost + extractCost + medCost + vulnerablePremium;

  // baseCost: what it would cost to keep this population alive with zero conflict overhead
  // ($3.50/person/day × population × days — the UNHCR humanitarian baseline).
  // This is the same base used in section 1 ("Financial") at risk level 2 exactly.
  // At other risk levels section 1 uses a risk-scaled rate, but $3.50 is always the
  // supply-delivery anchor in section 2 regardless of level.
  const baseCost      = Math.round(pop * 3.50 * days);
  const accessPremium = Math.max(0, Math.round(supplyCost - baseCost));

  return {
    total, supplyCost, extractCost, medCost, vulnerablePremium, vuln, prob, cumInjuries,
    accessMult, effectiveAccessMult, lossRate, effectiveLossRate,
    terrainMult,
    distKm, perPsnGround, perPsnAir, treatCostPer,
    d4Penalty, d3LossAdd, d7Overhead,
    d1ExtMult, d3ProbAdd, d6FloorVal,
    d5CostMult,
    baseCost, accessPremium,
    dimVals: { d1: d.d1, d2: d.d2, d3: d.d3, d4: d.d4, d5: d.d5, d6: d.d6, d7: d.d7 },
  };
}

function findSimilar(dims, cases, n=3) {
  return cases.map(c => {
    const ri = c.risk_indicators;
    const dist = Math.sqrt(
      Math.pow(dims.d1 - ri.d1_kinetic, 2) + Math.pow(dims.d2 - ri.d2_vulnerability, 2) +
      Math.pow(dims.d3 - ri.d3_political, 2) + Math.pow(dims.d4 - ri.d4_logistics, 2) +
      Math.pow(dims.d5 - ri.d5_destination, 2) + Math.pow(dims.d6 - ri.d6_urgency, 2) +
      Math.pow(dims.d7 - ri.d7_information, 2)
    );
    return { ...c, similarity: Math.max(0, Math.round((1 - dist / 7) * 100)) };
  }).sort((a, b) => b.similarity - a.similarity).slice(0, n);
}

// ═══════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════

function reinitTooltips(root = document) {
  root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el =>
    bootstrap.Tooltip.getOrCreateInstance(el)
  );
}

// ── Escaping ────────────────────────────────────────────────
// Anything that reaches the DOM from an API, a dataset or the LLM is
// untrusted and MUST go through esc() before being interpolated into an
// innerHTML template. Model output is untrusted by definition: the prompt
// embeds caller-supplied text, so it can be coerced into emitting markup.
function esc(v) {
  if (v === null || v === undefined) return '';
  return String(v)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Escape an untrusted URL for use in href/src — anything that isn't plain
// http(s) (javascript:, data:, vbscript:, …) is dropped.
function safeUrl(v) {
  if (!v) return '';
  const s = String(v).trim();
  try {
    const u = new URL(s, window.location.origin);
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return '';
    return esc(u.href);
  } catch (e) {
    return '';
  }
}

function fmt(v) {
  if (v >= 1e9) return (v/1e9).toFixed(2).replace(/\.?0+$/, '')+'B';
  if (v >= 1e6) return (v/1e6).toFixed(1)+'M';
  if (v >= 1e3) return (v/1e3).toFixed(0)+'K';
  return String(Math.round(v));
}

function fmtFull(v) { return Number(v).toLocaleString(); }

function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  t.className = `toast align-items-center text-bg-${type} border-0`;
  bootstrap.Toast.getOrCreateInstance(t).show();
}

function levelBadgeClass(l) { return `lbadge-${l}`; }

// Tiny stat mini-card used in historical case cost panels
function costStatMini(label, val, note = '') {
  return `<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:5px;
                       padding:.25rem .45rem;min-width:4.5rem;flex:1;min-height:2.6rem">
    <div style="font-size:.76rem;font-weight:700;color:#1e293b;white-space:nowrap">${val}</div>
    ${note ? `<div style="font-size:.59rem;color:#d97706;line-height:1.2;margin-bottom:.1rem">${note}</div>` : ''}
    <div style="font-size:.61rem;color:#94a3b8;text-transform:uppercase;
                letter-spacing:.03em;line-height:1.25">${label}</div>
  </div>`;
}

// Recomputes the vulnerable % among those who REMAIN in the zone.
// Vulnerable individuals evacuate at half the rate of the general population,
// so as evacuation proceeds the remaining group becomes more vulnerable.
function updateRemainingVulnPct() {
  const totalVuln      = Math.round(state.population * state.vulnerablePct / 100);
  const evacuationRate = state.population > 0
    ? (state.population - state.remainingPop) / state.population : 0;
  const vulnEvacRate   = evacuationRate * 0.5;   // half-rate assumption
  const remainingVuln  = Math.round(totalVuln * (1 - vulnEvacRate));
  const pct            = state.remainingPop > 0
    ? Math.round(remainingVuln / state.remainingPop * 100)
    : state.vulnerablePct;
  state.remainingVulnPct = Math.min(100, Math.max(0, pct));

  const el = document.getElementById('remainVulnLabel');
  if (!el) return;
  if (evacuationRate < 0.01) { el.innerHTML = ''; return; }  // nobody evacuated yet

  const isElevated = state.remainingVulnPct > state.vulnerablePct * 1.5;
  const bg    = isElevated
    ? 'background:#fffbeb;border-left:2px solid #f59e0b;padding:.2rem .4rem;border-radius:3px;'
    : '';
  const color = isElevated ? '#92400e' : '#64748b';
  el.innerHTML = `<span style="${bg}font-size:.67rem;color:${color};line-height:1.5;display:block">
    ${isElevated ? '<i class="fas fa-triangle-exclamation me-1"></i>' : ''}
    Of ${fmtFull(state.remainingPop)} remaining, an estimated <strong>${fmtFull(remainingVuln)} (${state.remainingVulnPct}%)</strong> are vulnerable
    — proportionally higher because vulnerable individuals are ~2× less likely to evacuate
    (ref: AARP/FEMA Katrina 2006; WHO Disability &amp; Disasters 2005). Higher per-capita assistance costs applied below.
  </span>`;
}

// Children-under-5 derived display — UNICEF demographic estimate: ≈15% of
// conflict-affected LMIC population. Updated on every population change.
function updateVulnDisplay() {
  const el = document.getElementById('vulnU5Display');
  if (!el) return;
  const u5 = Math.round(state.population * 0.15);
  el.textContent = `Est. children under 5: ${fmtFull(u5)} (≈15% · UNICEF LMIC estimate)`;
}

function toggleModelLimits() {
  const body = document.getElementById('modelLimitsBody');
  const chev = document.getElementById('modelLimitsChev');
  if (!body) return;
  const opening = body.style.display === 'none';
  body.style.display = opening ? '' : 'none';
  if (chev) {
    chev.className = opening ? 'fas fa-chevron-down ms-auto' : 'fas fa-chevron-right ms-auto';
    chev.style.fontSize = '.6rem';
    chev.style.color = '#94a3b8';
  }
}

function toggleCostWarning() {
  // Cost configuration is always open — no-op
}

function toggleDeployNotice() {
  const notice = document.getElementById('deployNotice');
  const chev   = document.getElementById('deployNoticeChev');
  if (!notice) return;
  notice.classList.toggle('collapsed');
  chev.className = notice.classList.contains('collapsed')
    ? 'fas fa-chevron-right' : 'fas fa-chevron-down';
  chev.style.fontSize = '.6rem';
}

function dismissDeployNotice() {
  const notice = document.getElementById('deployNotice');
  if (notice) notice.style.display = 'none';
}

// Confidence level for each cost line (keyed to r.costs object)
// Sources updated June 2026 via seven-parameter web validation search.
const COST_CONF = {
  transport:         { conf: 'estimated',   label: 'Transport',
    note: 'Unit rates updated Tavily validation June 2026: $200 std bus (unvalidated — no primary source found); $400 medical bus (updated from $250 — medically-equipped vehicle field range $400-600; no primary source for $250); $700 ambulance (updated from $400 — EU Commission Medevac Study 2020; conflict-zone ground ambulance field range $600-1,500/day). Terrain multiplier applied (×1.0–×4.0): anchored on World Bank RAI country scores and Afghanistan infrastructure cost ratios.' },
  fuel:              { conf: 'estimated',   label: 'Fuel',
    note: '$1.20/L revised June 2026 (prior: $1.50). Source: ACAPS Yemen Analysis Hub, Sep 2022 — conflict-zone consumer price $1.02–$1.19/L. Terrain multiplier also applied to fuel (×1.0–×4.0): longer routes, off-road driving, and vehicle hardening in poor terrain increase fuel consumption. Sources: World Bank RAI (SDG 9.1.1); Puga TRI dataset (diegopuga.org/data/rugged).' },
  personnel:         { conf: 'estimated', label: 'Personnel',
    note: 'Aggregate personnel cost — see sub-component validation below. Rates assume national staff or NGO-level deployment. UN international professional rates are 3–6× higher.',
    subItems: [
      { label: 'Security · $300/day', conf: 'estimated',
        note: 'Estimated — humanitarian PSC mid-market range $200–$1,100+/day depending on context, nationality, and risk level. No single published UNDSS figure available. (ref: ODI HPG Policy Brief 33; Gaza 2025 operational reporting)' },
      { label: 'Medical staff · $200/day', conf: 'estimated',
        note: 'Estimated — MSF USA (2024): starting salary $2,365–$2,838/month = ~$79–$95/day take-home. With 2–3× operational overhead (per diem, housing, insurance, admin): ~$158–$285/day total org cost. $200/day is within range for mid-level international NGO deployment. (ref: doctorswithoutborders.org/careers, accessed June 2026; MSF Pay & Benefits Guide IRP2, Oct 2023)' },
      { label: 'Paramedics · $150/day', conf: 'estimated',
        note: 'Partially supported — five-search validation (June 2026). MSF applies a uniform starting rate to ALL international field roles regardless of specialty: $87–97/day take-home (doctorswithoutborders.org; msf.org.au; doctorswithoutborders.ca — 2022). No paramedic-specific rate is published separately from general medical staff rates in any public ICRC, MSF, WHO, or UN document. With 2–3× operational overhead, international NGO deployment costs $174–$291/day. $150/day is consistent with experienced national paramedic at total operational cost (upper end), or below mid-range for international deployment. US BLS (2024) domestic paramedic median: $58,410/year (~$160/day calendar basis) — HIGH-INCOME domestic context, not applicable to LMIC humanitarian deployment. Validation gap remains: no operational per-person-per-day figure for humanitarian paramedic in conflict zone found in peer-reviewed literature.' },
      { label: 'Drivers · $50/day', conf: 'estimated',
        note: 'Estimated by inference from LMIC wage data. South Sudan informal minimum wage: $1–3/day (TimeCamp, 2024). UN General Service salary based on local survey per ICSC methodology — not disclosed per-country in public documents. Estimated nationally-hired conflict-zone driver at total operational cost: $25–50/day. $50/day is a plausible upper bound for national staff. No direct IOM or WFP field driver rate found in public documents (June 2026 search).' },
    ]
  },
  food:              { conf: 'estimated',   label: 'Food',
    note: '0.45 kg/person/day (Sphere Handbook 2018: minimum 2,100 kcal/person/day dry-weight equivalent).' },
  water:             { conf: 'validated',   label: 'Water',               note: 'Updated 15→20 L/person/day (Tavily validation June 2026). UNHCR full planning standard: 20 L/person/day. Sphere 2018 emergency minimum: 7.5–15 L/person/day. Using UNHCR full standard for evacuation planning.' },
  shelter:           { conf: 'estimated',   label: 'Shelter',
    note: 'Quantity: Sphere 2018-consistent (3.5 m²/person × 5 pp/tent = 17.5 m²). Unit cost updated $150→$380 (Tavily validation June 2026). Source: The New Humanitarian Dec 2022 — direct UNHCR quote: "$400 to replace"; UNHCR Shelter Design Catalogue Jan 2016: $229/unit (incl. transport+labour). $380 = conservative 2024 estimate. Prior $150 = basic tarpaulin (short-duration only). Dominates subtotal.' },
  medical:           { conf: 'estimated',   label: 'Medical supplies',    note: 'Medical staff ratio 1:250 (Sphere 2018 Health chapter). Kit cost $21/kit (WHO/UNICEF IEHK anchor, PMC5321368, 2017).' },
  comms:             { conf: 'estimated',   label: 'Communications',
    note: 'Partially validated June 2026. Professional humanitarian VHF radio (Motorola DP/Icom IC-F series): $350–$700/unit at procurement (ETC Sudan SitRep Jan 2024 confirms VHF as standard field unit). Satellite phone airtime: $1–$2/min (Access Partnership 2022). $500/radio is within documented procurement range.' },
  contingency_15pct: { conf: 'estimated',   label: 'Contingency (15%)',
    note: '15% is defensible for high-risk conflict projects (PMI standard: 15–20% for high-risk). UNHCR institutional reserve = 5% (different concept — organizational buffer). CERF caps overhead at 10% personnel + 3% operating (not project contingency). 15% = lower bound of high-risk project standard.' },
};

function updateCostConfTable(costs) {
  const tbody = document.getElementById('costConfBody');
  if (!tbody) return;
  tbody.innerHTML = Object.entries(costs).map(([k, v]) => {
    const m = COST_CONF[k] || { conf: 'unvalidated', label: k, note: '' };
    const mainRow = `<tr title="${m.note}">
      <td style="width:14px"><span class="conf-dot conf-${m.conf}"></span></td>
      <td>${m.label}</td>
      <td class="text-end fw-semibold" style="white-space:nowrap">$${fmt(v)}</td>
    </tr>`;
    if (!m.subItems) return mainRow;
    // Personnel: render one indented sub-row per role with its own confidence dot
    const subRows = m.subItems.map(s => `<tr title="${s.note}" style="background:#fafbfc">
      <td style="width:14px;padding-left:.85rem">
        <span class="conf-dot conf-${s.conf}" style="width:6px;height:6px"></span>
      </td>
      <td style="font-size:.68rem;color:#64748b;padding-left:1.1rem">${s.label}</td>
      <td></td>
    </tr>`).join('');
    return mainRow + subRows;
  }).join('');
}

function toggleDimHelp(btn, panelId) {
  const panel = document.getElementById(panelId);
  const opening = !panel.classList.contains('open');
  // Close any other open panel first
  document.querySelectorAll('.dim-help-panel.open').forEach(p => p.classList.remove('open'));
  document.querySelectorAll('.dim-help-btn.active').forEach(b => b.classList.remove('active'));
  if (opening) {
    panel.classList.add('open');
    btn.classList.add('active');
  }
}

function makeDivIcon(color, size=14, pulse=false) {
  const shadow = pulse ? `box-shadow:0 0 0 4px ${color}40;` : '';
  return L.divIcon({
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.4);${shadow}"></div>`,
    iconSize: [size, size], iconAnchor: [size/2, size/2], className: '',
  });
}

// ═══════════════════════════════════════════════════════════
// CHART INIT
// ═══════════════════════════════════════════════════════════

function initCharts() {
  state.charts.radar = new Chart(document.getElementById('radarChart').getContext('2d'), {
    type: 'radar',
    data: {
      labels: DIM_LABELS,
      datasets: [
        { label:'Current Scenario', data:[3,3,3,3,3,3,3],
          backgroundColor:'rgba(239,68,68,.15)', borderColor:'#ef4444',
          pointBackgroundColor:'#ef4444', borderWidth:2, fill:true },
        { label:'Historical Case', data:[3,3,3,3,3,3,3],
          backgroundColor:'rgba(14,165,233,.1)', borderColor:'#0ea5e9',
          pointBackgroundColor:'#0ea5e9', borderWidth:2, borderDash:[5,5], fill:true, hidden:true },
      ]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      scales: { r: { min:1, max:5, ticks:{ stepSize:1, font:{size:8} }, pointLabels:{ font:{size:8} } } },
      plugins: { legend:{ labels:{ font:{size:9} } } }
    }
  });

  state.charts.costBar = new Chart(document.getElementById('costBarChart').getContext('2d'), {
    type: 'bar',
    data: {
      labels: ['Transport','Fuel','Personnel','Food','Water','Shelter','Medical','Comms','Contingency'],
      datasets: [{ label:'USD', data:[], backgroundColor:'rgba(59,130,246,.7)', borderRadius:4 }]
    },
    options: {
      responsive:true, maintainAspectRatio:false, indexAxis:'y',
      plugins:{ legend:{ display:false } },
      scales:{ x:{ ticks:{ callback: v => '$'+fmt(v), font:{size:8} } }, y:{ ticks:{ font:{size:8} } } }
    }
  });

  state.charts.fin = new Chart(document.getElementById('financialChart').getContext('2d'), {
    type: 'line',
    data: { labels:[], datasets:[{ label:'Cumulative Assistance (USD)', data:[], borderColor:'#ef4444',
      backgroundColor:'rgba(239,68,68,.08)', fill:true, tension:.35, pointRadius:0 }] },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ display:false } },
      scales: {
        y:{ ticks:{ callback: v => '$'+fmt(v), font:{size:8} } },
        x:{ title:{ display:true, text:'Days', font:{size:8} }, ticks:{ font:{size:8} } }
      }
    }
  });

  state.charts.human = new Chart(document.getElementById('humanChart').getContext('2d'), {
    type: 'line',
    data: {
      labels:[],
      datasets:[
        { label:'Deaths',   data:[], borderColor:'#dc2626', fill:false, tension:.35, pointRadius:0 },
        { label:'Injuries', data:[], borderColor:'#f97316', fill:false, tension:.35, pointRadius:0 },
      ]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ font:{size:8} } } },
      scales: {
        x:{ title:{ display:true, text:'Days', font:{size:8} }, ticks:{ font:{size:8} } },
        y:{ ticks:{ font:{size:8} } }
      }
    }
  });

  state.charts.radarHist = new Chart(document.getElementById('radarHistChart').getContext('2d'), {
    type: 'radar',
    data: {
      labels: DIM_LABELS,
      datasets: [
        { label:'Current',    data:[3,3,3,3,3,3,3], backgroundColor:'rgba(239,68,68,.15)',
          borderColor:'#ef4444', pointBackgroundColor:'#ef4444', borderWidth:2 },
        { label:'Historical', data:[3,3,3,3,3,3,3], backgroundColor:'rgba(14,165,233,.1)',
          borderColor:'#0ea5e9', pointBackgroundColor:'#0ea5e9', borderWidth:2, borderDash:[5,5] },
      ]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      scales:{ r:{ min:1, max:5, ticks:{ stepSize:1, font:{size:8} }, pointLabels:{ font:{size:8} } } },
      plugins:{ legend:{ labels:{ font:{size:8} } } }
    }
  });
}

// ═══════════════════════════════════════════════════════════
// UI UPDATE
// ═══════════════════════════════════════════════════════════

function updateStayContext() {
  const el       = document.getElementById('stayPopContext');
  const elAssist = document.getElementById('stayPopContextAssist');
  if (!el && !elAssist) return;
  const total     = state.population || 1;
  const remain    = state.remainingPop;
  const pct       = Math.round(remain / total * 100);
  const evacuated = total - remain;
  let html = `<span style="color:#94a3b8">Based on <strong style="color:#7c3aed">${fmtFull(remain)}</strong> people remaining (${pct}% of ${fmtFull(total)} total at risk)</span>`;
  if (remain < total) {
    html += `<br><span style="color:#b45309">Evacuated: ${fmtFull(evacuated)} people · Evacuation cost applied to this group</span>`;
  }
  if (el)       el.innerHTML       = html;
  if (elAssist) elAssist.innerHTML = html;
}

function updateAll() {
  const d         = state.dims;
  const risk      = calcRisk(d);

  // Seasonal terrain adjustment (requires lat from conflict pin and month from start date)
  state.seasonalTerrain = null;
  const _startDateVal = state.startDate || document.getElementById('inStartDate')?.value || '';
  if (state.conflictCoords && _startDateVal) {
    const month = new Date(_startDateVal).getMonth() + 1;
    const lat = state.conflictCoords.lat;
    state.seasonalTerrain = getSeasonalTerrainFactor(state.terrain, lat, month);
  }
  const effectiveTerrainMult = state.seasonalTerrain?.terrainMult ?? (TERRAIN_MULT[state.terrain] ?? 1.0);
  const resources = calcResources(state.population, state.vulnerablePct, risk.level, state.distanceKm, state.dims.d2, state.terrain, state.climateMult, effectiveTerrainMult, state.dims.d4, state.dims.d5);
  updateRemainingVulnPct();  // must run before calcRemaining so derived pct is current
  const remainingPct  = state.population > 0 ? state.remainingPop / state.population : 1.0;
  const exposureFactor = computeExposureFactor();
  // Siege cap disabled for regional (4) and city_conflict (3) conflict patterns
  const siegeCapEnabled = (state.conflictType !== 3 && state.conflictType !== 4);
  const stayData  = calcStay(state.remainingPop, risk.level, state.days, state.dims, remainingPct, exposureFactor, siegeCapEnabled);
  const remaining = calcRemaining(state.remainingPop, state.remainingVulnPct, risk.level, state.days, state.distanceKm, state.dims, state.terrain, undefined, stayData.inj[stayData.inj.length - 1]);

  // Cache current results so comparison panel can diff against them
  state._lastResources = resources;
  state._lastStayData  = stayData;
  state._lastRisk      = risk;

  updateRiskCard(risk);
  updateRadarChart();
  updateHardTriggers();
  updateSimilarCases(findSimilar(d, state.historicalCases));
  updateResourceDisplay(resources);
  updateCostCharts(stayData);
  const _tMode = document.getElementById('transportMode')?.value ?? 'ground';
  const _isAltMode = _tMode === 'air_fixed' || _tMode === 'air_heli' || _tMode === 'walking';
  const evacuatedPop  = Math.max(0, state.population - state.remainingPop);
  // Evacuate-now cost = full mobilization cost (resources are mobilized for the whole
  // population regardless of how many actually board), not a marginal per-evacuatedPop
  // recompute. Ground uses resources.totalCost (already computed for state.population);
  // air/walking use the alt-mode API's full-population quote directly.
  const evacuatedCost = state._lastAltResult?.total_cost_usd ?? resources.totalCost;
  // "Total crisis cost" should reflect whatever transport mode is currently selected, not
  // always the ground total — fall back to ground while an alt-mode fetch is still pending
  // (state._lastAltResult null) so the card never shows a stale/undefined value.
  const fullEvacCostForCard = _isAltMode
    ? (state._lastAltResult?.total_cost_usd ?? resources.totalCost)
    : resources.totalCost;
  updateRemainingCostCard(remaining, fullEvacCostForCard);

  // Decision analysis — Option A (evacuate now + assist remaining) vs Option B (assist all in zone)
  const BASE_DAILY = [1.0, 2.0, 3.5, 6.0, 12.0];
  const _dailyCostA = (state.days > 0 && remaining.total > 0)
    ? remaining.total / state.days
    : (BASE_DAILY[risk.level] ?? 3.5) * (state.remainingPop || 0);
  const _dailyCostB = state.remainingPop > 0
    ? _dailyCostA * ((state.population || 0) / state.remainingPop)
    : (BASE_DAILY[risk.level] ?? 3.5) * (state.population || 0);
  updateDecisionAnalysis(evacuatedCost, _dailyCostA, _dailyCostB);

  renderTransportWarnings(_tMode, state.dims, state.population);

  updateStayContext();
  updateHistRadar();
  renderCostComparePanel();
  updateWeightsPanel();
  updateVulnDisplay();

  document.getElementById('globalRiskBadge').textContent = `LEVEL ${risk.level} · SCORE ${risk.score}`;
  const globalRiskBadgeMapEl = document.getElementById('globalRiskBadgeMap');
  if (globalRiskBadgeMapEl) globalRiskBadgeMapEl.textContent = `LEVEL ${risk.level} · SCORE ${risk.score}`;

  // Refresh choropleth colours when risk level changes
  if (worldMapState.initialized && worldMapState.geojsonLayer) {
    worldMapState.geojsonLayer.setStyle(choroStyle);
  }

  // Re-fetch alt-mode result reactively when parameters change.
  // Suppressed when this updateAll() run was itself triggered by a fetch completing
  // (see fetchAltModeResult) to avoid an infinite fetch → updateAll → fetch loop.
  if (!_suppressAltFetch && (_tMode === 'walking' || _tMode === 'air_fixed' || _tMode === 'air_heli')) {
    fetchAltModeResult(_tMode);
  }
}

function evacuationWindow(level, d1, d3, d6) {
  // KEY DISTINCTION — two separate failure modes:
  //   D1 high (kinetic): movement is physically unsafe regardless of urgency. No countdown
  //     is meaningful because the route itself is under fire. → no banner shown.
  //   D6 high (urgency): situation deteriorating rapidly but movement may still be possible.
  //     → countdown banner with hours estimate.
  // These are OPPOSITE messages and must never be shown simultaneously.

  // D1 ≥ 4: kinetic impossibility conveyed by the three-index matrix banner.
  if (level >= 2 && d1 >= 4) return '';

  if (level <= 1) return '';

  const disclaimer = `<span style="font-size:.65rem;color:rgba(255,255,255,0.78);font-style:italic;display:block;margin-top:.1rem">Planning estimate — operational planning convention. GC IV Art. 49 duty to evacuate applies; no normative temporal threshold specified.</span>`;

  // Level 4, D6 ≥ 4: window closing fast (D1 < 4 guaranteed here, so movement is possible)
  if (level >= 4 && d6 >= 4) {
    return `<div class="evac-window evac-urgent">
      <i class="fas fa-clock me-1"></i>
      <span><strong>Estimated window: less than 6 hours (D6 Urgency: ${d6}/5)</strong>${disclaimer}</span>
    </div>`;
  }

  let text, cls;

  if (level === 2) {
    const lo = d6 >= 4 ? Math.round(5 * 0.7) : 5;
    const hi = d6 >= 4 ? Math.round(7 * 0.7) : 7;
    text = `Estimated window: ${lo}–${hi} days before escalation`;
    cls  = 'evac-moderate';
  } else if (level === 3) {
    if (d6 >= 4) {
      text = `Estimated window: 24–48 hours (D6 Urgency: ${d6}/5)`;
      cls  = 'evac-high';
    } else {
      text = `Estimated window: 48–72 hours (D6 Urgency: ${d6}/5)`;
      cls  = 'evac-high';
    }
  } else {
    // Level 4, D6 < 4
    text = `Estimated window: less than 24 hours (D6 Urgency: ${d6}/5)`;
    cls  = 'evac-critical';
  }
  return `<div class="evac-window ${cls}"><i class="fas fa-clock me-1"></i><span>${text}${disclaimer}</span></div>`;
}

function updateRiskCard(r) {
  const card = document.getElementById('riskCard');
  card.style.background = r.color;
  card.style.color = r.text;
  document.getElementById('riskLevelBadge').textContent = `LEVEL ${r.level}`;
  document.getElementById('riskScore').textContent = r.score;
  document.getElementById('riskLabel').textContent = r.label;
  document.getElementById('riskNato').textContent = 'NATO: ' + r.nato;
  document.getElementById('riskWindow').innerHTML = evacuationWindow(r.level, state.dims.d1, state.dims.d3, state.dims.d6);

  // Remove legacy inline sub-index element if present
  const oldSub = document.getElementById('riskSubIndexes');
  if (oldSub) oldSub.remove();

  // Three-index panel (Teresa/Yorke framework)
  renderThreeIndexPanel(r, document.getElementById('threeIndexPanel'));
}

function updateRadarChart() {
  state.charts.radar.data.datasets[0].data = DIM_KEYS.map(k => state.dims[k]);
  state.charts.radar.update('none');
}

function updateHardTriggers() {
  const triggers = [];
  if (state.dims.d1 >= 4.5 && state.dims.d6 >= 4.5)
    triggers.push('D1 Kinetic + D6 Urgency ≥ 4.5 → Hard trigger: automatic Level 4 override');
  if (state.dims.d3 >= 4.5)
    triggers.push('D3 Authorization = ' + state.dims.d3 + ' → No party consent: evacuation highly risky');
  document.getElementById('hardTriggers').innerHTML = triggers.map(t =>
    `<div class="trigger-alert"><i class="fas fa-exclamation-triangle me-1"></i>${t}</div>`
  ).join('');
}

function updateSimilarCases(similar) {
  const el = document.getElementById('similarCases');
  if (!similar.length) { el.innerHTML = '<span class="text-muted small">No data loaded.</span>'; return; }
  el.innerHTML = similar.map(c => `
    <div class="sim-row" onclick="openCaseModal(${c.id})">
      <span class="badge ${levelBadgeClass(c.risk_level)} me-1" style="font-size:.68rem">L${c.risk_level}</span>
      <div style="flex:1">
        <div style="font-size:.78rem;font-weight:600">${c.name} (${c.year})</div>
        <div style="font-size:.68rem;color:#888">${fmtFull(c.population_at_risk)} pop · ${c.similarity}% profile match</div>
      </div>
      <i class="fas fa-chevron-right" style="font-size:.65rem;color:#ccc"></i>
    </div>
  `).join('');
}

function togglePersonnelRate() {
  state.personnelRateMode = state.personnelRateMode === 'ngo' ? 'un' : 'ngo';
  updateAll();
}


function updateResourceDisplay(r) {
  const evacuatedPop = Math.max(0, state.population - state.remainingPop);
  const cppPerEvacuee = evacuatedPop > 0 ? Math.round(r.totalCost / evacuatedPop) : null;
  const _mode  = document.getElementById('transportMode')?.value ?? 'ground';
  const modeLabel = (() => {
    if (_mode === 'walking')   return 'Walking';
    if (_mode === 'air_fixed') return 'Air (fixed-wing)';
    if (_mode === 'air_heli')  return 'Air (helicopter)';
    return 'Ground';
  })();
  // Air AND walking modes drive the headline card from the alt-mode API result; only
  // ground uses the local calcResources() total.
  const _isAltMode = _mode === 'air_fixed' || _mode === 'air_heli' || _mode === 'walking';

  // ── Headline cost card (above risk level panel) ─────────────────────────────
  const headlineTotal = document.getElementById('costHeadlineTotal');
  const headlineSub   = document.getElementById('costHeadlineSub');
  const headlineNote  = document.getElementById('costHeadlineNote');
  if (headlineTotal && headlineSub) {
    if (state.population === 0) {
      headlineTotal.textContent = '—';
      headlineSub.textContent   = 'define scenario above';
      if (headlineNote) headlineNote.textContent = '';
    } else if (_isAltMode && !state._lastAltResult) {
      headlineTotal.textContent = 'Calculating…';
      headlineSub.textContent   = fmtFull(state.population) + ' persons · ' + modeLabel + ' · ' + state.distanceKm + ' km';
      if (headlineNote) headlineNote.textContent = '';
    } else if (_isAltMode) {
      const alt = state._lastAltResult;
      // Alt-mode cost is uniform per-capita, so cost/evacuee == cost/population regardless of evacuatedPop.
      const cppAlt = evacuatedPop > 0 ? Math.round(alt.total_cost_usd / state.population) : null;
      const cppStr = cppAlt !== null ? '$' + fmt(cppAlt) + '/evacuee · ' : '';
      headlineTotal.textContent = '$' + fmt(alt.total_cost_usd);
      headlineSub.textContent = cppStr + fmtFull(state.population) + ' persons · ' + modeLabel + ' · ' + state.distanceKm + ' km';
      if (headlineNote) headlineNote.textContent = '';
    } else {
      headlineTotal.textContent = '$' + fmt(r.totalCost);
      const cppStr = cppPerEvacuee !== null ? '$' + fmt(cppPerEvacuee) + '/evacuee · ' : '';
      headlineSub.textContent = cppStr + fmtFull(state.population) + ' persons · ' + modeLabel + ' · ' + state.distanceKm + ' km';
      // Ground cost is sized for the full population — clarify this differs from the
      // evacuee-only figure used in Decision Analysis's "Evacuate now" (calcResources(evacuatedPop,...)).
      if (headlineNote) headlineNote.textContent = `Full convoy mobilized for ${fmtFull(state.population)} persons. See Decision Analysis for evacuee-only cost.`;
    }
  }

  document.getElementById('resVeh').textContent   = r.vehicles.total;
  document.getElementById('resPers').textContent  = r.personnel.total;
  document.getElementById('resTotal').textContent = '$'+fmt(r.totalCost);
  document.getElementById('resCPP').textContent   = cppPerEvacuee !== null ? '$'+fmt(cppPerEvacuee) : 'N/A';

  const cppLblEl = document.querySelector('#resCPP')?.closest('.stat-mini')?.querySelector('.lbl');
  if (cppLblEl) {
    cppLblEl.innerHTML = cppPerEvacuee !== null
      ? `💵 Cost/Person <span style="font-size:.6rem;color:#94a3b8;display:block;margin-top:.1rem;font-weight:400">Per evacuee (${fmtFull(evacuatedPop)} of ${fmtFull(state.population)} evacuated). Full convoy mobilized for total population — standard humanitarian planning practice.</span>`
      : `💵 Cost/Person <span style="font-size:.6rem;color:#94a3b8;display:block;margin-top:.1rem;font-weight:400">N/A — no evacuees (100% remaining in zone)</span>`;
  }

  document.getElementById('detVehicles').innerHTML = `
    <span class="badge bg-secondary me-1 mb-1">${r.vehicles.stdBus} Standard Buses</span>
    <span class="badge bg-primary me-1 mb-1">${r.vehicles.medBus} Medical Buses</span>
    <span class="badge bg-danger me-1 mb-1">${r.vehicles.ambu} Ambulances</span>
  `;
  document.getElementById('detPersonnel').innerHTML = `
    <span class="badge bg-dark me-1 mb-1">${r.personnel.sec} Security</span>
    <span class="badge bg-success me-1 mb-1">${r.personnel.medS} Medical Staff</span>
    <span class="badge bg-info text-dark me-1 mb-1">${r.personnel.para} Paramedics</span>
    <span class="badge bg-warning text-dark me-1 mb-1">${r.personnel.drivers} Drivers</span>
  `;
  document.getElementById('detSupplies').innerHTML = `
    <div style="font-size:.75rem">⛽ Fuel: ${fmtFull(r.supplies.fuelL)} L</div>
    <div style="font-size:.75rem">🍞 Food: ${fmtFull(r.supplies.foodKg)} kg</div>
    <div style="font-size:.75rem">💧 Water: ${fmtFull(r.supplies.waterL)} L</div>
    <div style="font-size:.75rem">⛺ Tents: ${fmtFull(r.supplies.tents)}</div>
    <div style="font-size:.75rem">📻 Radios: ${r.supplies.radios}</div>
  `;

  const c = r.costs;
  state.charts.costBar.data.datasets[0].data = [
    c.transport, c.fuel, c.personnel, c.food, c.water, c.shelter, c.medical, c.comms, c.contingency
  ];
  state.charts.costBar.update('none');
  updateCostConfTable(c);
  renderSeasonalTerrainWarning(state.seasonalTerrain, state.terrain);
  const rateLabelText = state.personnelRateMode === 'un'
    ? 'Current: UN international rates (×4.5)'
    : 'Current: NGO/national staff rates';
  const rateLabel = document.getElementById('personnelRateModeLabel');
  const rateLabel2 = document.getElementById('assistPersonnelRateModeLabel');
  const rateBtn   = document.getElementById('personnelRateToggleBtn');
  if (rateLabel)  rateLabel.textContent  = rateLabelText;
  if (rateLabel2) rateLabel2.textContent = rateLabelText;
  if (rateBtn) rateBtn.textContent = state.personnelRateMode === 'un'
    ? 'Reset to NGO rates'
    : 'Switch to UN rates (×4.5)';
}

function seasonalResetToAlternatives() {
  // Restore ground panel and transport mode selector
  const groundPanel = document.getElementById('groundResourcePanel');
  const altPanel = document.getElementById('altModeResourcePanel');
  const transportRow = document.getElementById('transportMode')?.closest('div.mb-3');
  if (groundPanel) groundPanel.style.display = 'block';
  if (altPanel) { altPanel.style.display = 'none'; altPanel.innerHTML = ''; }
  if (transportRow) transportRow.style.display = '';
  // Re-render the seasonal warning with alternatives visible
  renderSeasonalTerrainWarning(state.seasonalTerrain, state.terrain);
}

async function seasonalSelectAlt(choice) {
  // Always restore transport mode row first
  const transportRow = document.getElementById('transportMode')?.closest('div.mb-3');
  if (transportRow) transportRow.style.display = '';

  // dest opens the map modal immediately — no panel expansion
  if (choice === 'dest') {
    openPinModal();
    return;
  }

  // Hide all expanded panels, then show the chosen one
  ['seasonalAltDetour', 'seasonalAltHeli'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
  const target = document.getElementById(choice === 'detour' ? 'seasonalAltDetour' : 'seasonalAltHeli');
  if (target) target.style.display = 'block';

  // For helicopter: fetch cost from backend, then swap main resource panel
  if (choice === 'heli') {
    const resultEl = document.getElementById('seasonalHeliResult');
    if (!resultEl) return;
    resultEl.textContent = 'Calculating helicopter cost...';
    try {
      const resp = await fetch('/api/air-evacuation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          population: state.population,
          distance_km: state.distanceKm,
          mode: 'helicopter',
          has_runway: null,
        }),
      });
      const data = await resp.json();
      const range = data.total_cost_usd_range;
      resultEl.innerHTML = `
        <div style="font-weight:600;color:#374151">Estimated helicopter cost: $${data.total_cost_usd.toLocaleString()}</div>
        <div style="color:#6b7280">Range: $${range.low.toLocaleString()} – $${range.high.toLocaleString()} · ${data.flights_needed} sorties · $${data.cost_per_pax_km_usd}/pax-km</div>
        <div style="color:#9ca3af;font-size:.68rem;margin-top:.2rem">${data.source}</div>
        <div style="color:#d97706;font-size:.68rem;margin-top:.2rem">⚠️ ESTIMATED — derived from UN procurement contract PD/C0164/14. Contact UNHAS for actual availability and rates.</div>
      `;
      const groundPanel = document.getElementById('groundResourcePanel');
      const altPanel    = document.getElementById('altModeResourcePanel');
      if (groundPanel) groundPanel.style.display = 'none';
      if (altPanel)    { altPanel.style.display = 'block'; renderAltModeResult(data, altPanel); }
      if (transportRow) transportRow.style.display = 'none';
      // Add back button to return to the seasonal alternatives
      const backBtn = document.createElement('div');
      backBtn.style.cssText = 'padding:.5rem .75rem;border-top:1px solid #e5e7eb;margin-top:.5rem';
      backBtn.innerHTML = `<button onclick="seasonalResetToAlternatives()" style="font-size:.72rem;padding:.2rem .6rem;background:none;border:1px solid #6b7280;border-radius:4px;cursor:pointer;color:#6b7280">← Back to route alternatives</button>`;
      document.getElementById('altModeResourcePanel')?.appendChild(backBtn);
    } catch(e) {
      resultEl.textContent = `Error calculating helicopter cost: ${e.message}`;
    }
  }
}

function applyDetourDistance(factor) {
  if (!state.distanceKm) return;
  const newKm = Math.round(state.distanceKm * factor);
  state.distanceKm = newKm;
  const distInput = document.getElementById('inDist');
  if (distInput) distInput.value = toDisplayUnit(newKm);
  const distLabel = document.getElementById('distRouteDisplay');
  if (distLabel) distLabel.textContent = `🔄 Detour applied: ${fmtDist(newKm)} (×${factor} original distance)`;
  updateAll();
}

function renderSeasonalTerrainWarning(st, terrain) {
  const el = document.getElementById('seasonalTerrainWarning');
  if (!el) return;
  if (!st || !st.isClosure) {
    el.style.display = 'none';
    return;
  }
  el.style.display = 'block';
  const impColor = st.potentiallyImpassable ? '#dc2626' : '#d97706';
  const impIcon  = st.potentiallyImpassable ? '🚫' : '⚠️';
  const impTitle = st.potentiallyImpassable
    ? 'Route potentially impassable — seasonal closure period'
    : 'Seasonal terrain constraint active';

  el.innerHTML = `
    <div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:6px;padding:.6rem .8rem;font-size:.75rem">
      <div style="font-weight:700;color:${impColor};margin-bottom:.3rem">${impIcon} ${impTitle}</div>
      <div style="color:#374151;margin-bottom:.5rem">${st.note || ''}</div>
      <div style="font-weight:600;color:#374151;margin-bottom:.3rem">Choose an operational alternative:</div>
      <div id="seasonalAltButtons" style="display:flex;flex-direction:column;gap:.35rem">
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:4px;padding:.4rem .6rem">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.3rem">
            <span>🔄 <strong>Alternative route (detour)</strong> — reroute around closure (+40–60% distance)</span>
            <button onclick="seasonalSelectAlt('detour')" style="font-size:.7rem;padding:.2rem .6rem;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer">Select</button>
          </div>
          <div id="seasonalAltDetour" style="display:none;margin-top:.4rem">
            <span style="color:#6b7280;font-size:.72rem">Current: ${fmtDist(state.distanceKm)} → Detour: ${fmtDist(Math.round(state.distanceKm * 1.5))}</span>
            <div style="display:flex;gap:.4rem;margin-top:.3rem;flex-wrap:wrap">
              <button onclick="applyDetourDistance(1.4)" style="font-size:.7rem;padding:.2rem .6rem;background:#6b7280;color:#fff;border:none;border-radius:4px;cursor:pointer">+40%</button>
              <button onclick="applyDetourDistance(1.5)" style="font-size:.7rem;padding:.2rem .6rem;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer">Apply +50% (recommended)</button>
              <button onclick="applyDetourDistance(1.6)" style="font-size:.7rem;padding:.2rem .6rem;background:#6b7280;color:#fff;border:none;border-radius:4px;cursor:pointer">+60%</button>
            </div>
          </div>
        </div>
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:4px;padding:.4rem .6rem">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.3rem">
            <span>🚁 <strong>Air transport (helicopter)</strong> — not affected by seasonal road closure</span>
            <button onclick="seasonalSelectAlt('heli')" style="font-size:.7rem;padding:.2rem .6rem;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer">Select</button>
          </div>
          <div id="seasonalAltHeli" style="display:none;margin-top:.4rem">
            <div id="seasonalHeliResult" style="color:#6b7280;font-size:.72rem">Calculating...</div>
          </div>
        </div>
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:4px;padding:.4rem .6rem">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.3rem">
            <span>📍 <strong>Alternative destination</strong> — select a safe zone on an accessible route</span>
            <button onclick="seasonalSelectAlt('dest')" style="font-size:.7rem;padding:.2rem .6rem;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer">Select</button>
          </div>
          <div id="seasonalAltDest" style="display:none;margin-top:.4rem;color:#374151;font-size:.72rem">
            Use "Set on Map" → "Nearest low-risk destinations" to identify an alternative safe zone reachable via an open route. Contact UNHAS or equivalent air operator if no ground route is available.
          </div>
        </div>
      </div>
      <div style="color:#9ca3af;font-size:.68rem;margin-top:.4rem">Seasonal closure logic: estimated from latitude zone and terrain type. See calculators.py → get_seasonal_terrain_factor() for methodology and caveats.</div>
    </div>`;
}

function updateCostCharts(data) {
  const { days, dead, inj, infraDenialApplied } = data;
  const step = Math.max(1, Math.floor(days.length / 60));
  const sl = arr => arr.filter((_, i) => i % step === 0);

  const riskLvl = calcRisk(state.dims).level;

  // Cumulative Assistance Cost — recompute calcRemaining() (supply delivery + emergency
  // extraction + field medical + vulnerable support) at each sampled day, instead of the
  // flat $3.50/person/day survival baseline previously shown here. Injuries at each day
  // come from inj[] (the same array driving EST. INJURIES) so Field medical's cost and
  // this chart never disagree, mirroring the earlier EST. INJURIES alignment fix.
  const sampledDays = sl(days);
  const assistCumulative = sampledDays.map(d => calcRemaining(
    state.remainingPop, state.remainingVulnPct, riskLvl, d, state.distanceKm,
    state.dims, state.terrain, state.climateMult, inj[d - 1],
  ).total);

  state.charts.fin.data.labels = sampledDays;
  state.charts.fin.data.datasets[0].data = assistCumulative;
  state.charts.fin.update('none');

  state.charts.human.data.labels = sl(days);
  state.charts.human.data.datasets[0].data = sl(dead);
  state.charts.human.data.datasets[1].data = sl(inj);
  state.charts.human.update('none');

  const last = days.length - 1;

  // Mortality range — derived from log-log regression (R²=0.765, p<0.00001)
  // L3: 80% PI ×0.35–×2.0 | L4: 80% PI ×0.25–×3.0
  const deadCenter = Math.round(dead[last]);
  const deadLow    = riskLvl >= 4 ? Math.round(deadCenter * 0.25) : Math.round(deadCenter * 0.35);
  const deadHigh   = riskLvl >= 4 ? Math.round(deadCenter * 3.0)  : Math.round(deadCenter * 2.0);
  const deadConf      = 'MODERATE';
  const deadConfColor = '#065f46';
  const deadConfBg    = '#d1fae5';
  document.getElementById('statDead').innerHTML =
    `${fmtFull(deadCenter)}<br>
     <span style="font-size:.62rem;color:#6b7280">${fmtFull(deadLow)}–${fmtFull(deadHigh)}</span>`;

  // Update confidence badge dynamically
  const deadLblEl = document.querySelector('#statDead')?.closest('.stat-mini')?.querySelector('.lbl');
  if (deadLblEl) {
    deadLblEl.innerHTML = `EST. DEATHS <span style="font-size:.55rem;background:${deadConfBg};color:${deadConfColor};padding:1px 4px;border-radius:2px;margin-left:2px;font-weight:700">${deadConf}</span>`;
  }

  // Infrastructure-denial note (shows when D6 ≥ 4.0 activates the multiplier)
  const infraNoteEl = document.getElementById('infraDenialNote');
  if (infraNoteEl) {
    infraNoteEl.style.display = infraDenialApplied ? '' : 'none';
  }

  // Injury range — ICRC planning standard 4:1, range 3:1–5:1
  // Source: ICRC Arms Availability study; Frontiers Israel-Gaza 2024
  const injCenter = Math.round(dead[last] * 4);
  const injLow    = Math.round(dead[last] * 3);
  const injHigh   = Math.round(dead[last] * 5);
  document.getElementById('statInj').innerHTML =
    `${fmtFull(injCenter)}<br>
     <span style="font-size:.62rem;color:#6b7280">${fmtFull(injLow)}–${fmtFull(injHigh)}</span>`;

}

function getTransportWarnings(mode, dims, population) {
  const d = dims || {};
  const d1 = d.d1 ?? 3; const d2 = d.d2 ?? 3;
  const d3 = d.d3 ?? 3; const d4 = d.d4 ?? 3;
  const warnings = [];

  if (mode === 'ground') {
    if (d4 >= 4.0) warnings.push({
      priority: 1,
      suggestAir: true,
      text: 'Ground transport may be severely compromised — D4 indicates critical logistics constraints (destroyed roads, checkpoints, fuel shortage). Consider air evacuation or verify route viability.',
    });
    if (d1 >= 4.5) warnings.push({
      priority: 2,
      suggestAir: true,
      text: 'High kinetic threat — ground convoys face significant exposure risk at D1≥4.5. Air evacuation or armoured ground transport may be required.',
    });
  }
  if (mode === 'walking') {
    if (population > 5000) warnings.push({
      priority: 1,
      text: 'Walking evacuation for >' + Math.round(population/1000) + ',000 persons is rarely feasible in conflict contexts — insufficient for this population size. Consider ground or air transport.',
    });
    if (d2 >= 3.5) warnings.push({
      priority: 2,
      text: 'Mobility constraints (D2≥3.5) indicate significant proportion of wounded/bedridden — walking evacuation not suitable for this vulnerability profile.',
    });
  }
  if ((mode === 'air_fixed' || mode === 'air_heli') && d3 >= 4.0) warnings.push({
    priority: 1,
    text: 'Air evacuation requires airspace authorization — D3 indicates limited or absent party consent. Verify airspace clearance before planning air operations.',
  });

  return warnings.sort((a, b) => a.priority - b.priority).slice(0, 2);
}

function renderTransportWarnings(mode, dims, population) {
  const el = document.getElementById('transportWarnings');
  if (!el) return;
  const warnings = getTransportWarnings(mode, dims, population);
  if (!warnings.length) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }
  el.style.display = 'block';
  const warningsHtml = warnings.map(w =>
    `<div style="background:#fefce8;border:1px solid #fde68a;border-radius:5px;padding:.3rem .5rem;font-size:.68rem;color:#78350f;margin-top:.25rem;line-height:1.4">
      <span style="font-weight:700">⚠</span> ${w.text}
    </div>`
  ).join('');
  const airLinkHtml = warnings.some(w => w.suggestAir)
    ? `<button type="button" onclick="scrollToAirEstimate()" style="margin-top:.3rem;font-size:.66rem;padding:.15rem .5rem;background:transparent;color:#1d4ed8;border:1px dashed #93c5fd;border-radius:4px;cursor:pointer">📊 View air evacuation cost estimate ↓</button>`
    : '';
  el.innerHTML = warningsHtml + airLinkHtml;
}

function scrollToAirEstimate() {
  const altPanel = document.getElementById('altModeResourcePanel');
  if (!altPanel) return;
  // Reveal the air-cost reference panel without switching the Transport Mode dropdown
  if (document.getElementById('transportMode')?.value === 'ground') {
    altPanel.style.display = 'block';
    fetchAltModeResult('air_fixed');
  }
  altPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ── Demographic vulnerability suggestion ──────────────────────────────────────
async function suggestVulnerablePct(countryName) {
  const el = document.getElementById('vulnDemographicSuggestion');
  if (!el || !countryName) return;
  try {
    const resp = await fetch(`/api/demographics/${encodeURIComponent(countryName.toLowerCase())}`);
    if (!resp.ok) { el.style.display = 'none'; return; }
    const d = await resp.json();
    const est = Math.round(d.vulnerable_estimate);
    el.style.display = 'block';
    el.innerHTML = `
      📊 <strong>Suggested for ${countryName}:</strong> ~${est}%
      (under-5: ${d.pct_under5}%, over-60: ${d.pct_over60}%, disability est.: ${d.pct_disabled}%)
      — adjust based on local assessment.
      <span style="color:#64748b">Source: ${d.source}</span>
      ${d.note ? `<br><em style="color:#64748b">${d.note}</em>` : ''}
      <br>
      <button type="button" onclick="document.getElementById('inVuln').value=${est};document.getElementById('vulnDemographicSuggestion').style.display='none';updateAll();"
              style="margin-top:.25rem;font-size:.65rem;padding:.1rem .4rem;background:#2563eb;color:#fff;border:none;border-radius:3px;cursor:pointer">
        Use suggested value (${est}%)
      </button>
      <button type="button" onclick="document.getElementById('vulnDemographicSuggestion').style.display='none';"
              style="margin-top:.25rem;margin-left:.3rem;font-size:.65rem;padding:.1rem .4rem;background:transparent;color:#64748b;border:1px solid #cbd5e1;border-radius:3px;cursor:pointer">
        Dismiss
      </button>`;
  } catch (_) {
    el.style.display = 'none';
  }
}

// ── City population lookup (GeoNames) ────────────────────────────────────────
let _cityDebounceTimer = null;

function onCityInput(val) {
  clearTimeout(_cityDebounceTimer);
  const el = document.getElementById('cityPopSuggestions');
  if (!val || val.trim().length < 2) {
    if (el) el.style.display = 'none';
    return;
  }
  _cityDebounceTimer = setTimeout(() => fetchCityPopulation(val.trim()), 600);
}

// Event delegation — works regardless of when the tab/element is first rendered
document.addEventListener('input', function(e) {
  if (e.target && e.target.id === 'inCity') {
    onCityInput(e.target.value);
  }
});

async function fetchCityPopulation(city) {
  const el = document.getElementById('cityPopSuggestions');
  if (!el) return;
  el.style.display = 'block';
  el.innerHTML = '<div style="font-size:.67rem;color:#94a3b8;padding:.2rem 0"><i class="fas fa-spinner fa-spin me-1"></i>Searching…</div>';
  try {
    const resp = await fetch(`/api/city-population/${encodeURIComponent(city)}`);
    if (!resp.ok) {
      el.innerHTML = '<div style="font-size:.67rem;color:#94a3b8;padding:.2rem 0">City not found — enter population manually</div>';
      return;
    }
    const data = await resp.json();
    const items = (data.results || []).map(r => {
      const region = r.adminName1 ? `, ${r.adminName1}` : '';
      const label  = `${r.name}, ${r.country}${region} — ${r.population.toLocaleString()}`;
      return `<button type="button" onclick='applyCityPop(${JSON.stringify(r)})'
                style="display:block;width:100%;text-align:left;background:#f8fafc;border:1px solid #e2e8f0;
                       border-radius:5px;padding:.3rem .55rem;font-size:.68rem;color:#1e3a5f;
                       margin-bottom:.25rem;cursor:pointer;line-height:1.3"
                onmouseover="this.style.background='#eff6ff'" onmouseout="this.style.background='#f8fafc'">
                🏙️ ${label}
              </button>`;
    });
    el.innerHTML = items.length
      ? items.join('')
      : '<div style="font-size:.67rem;color:#94a3b8;padding:.2rem 0">No results with population data — enter manually</div>';
  } catch(_) {
    el.innerHTML = '<div style="font-size:.67rem;color:#94a3b8;padding:.2rem 0">City lookup unavailable — enter population manually</div>';
  }
}

function applyCityPop(r) {
  const popEl  = document.getElementById('inPop');
  const noteEl = document.getElementById('cityPopNote');
  const sugEl  = document.getElementById('cityPopSuggestions');
  const cityEl = document.getElementById('inCity');
  if (popEl) {
    popEl.value = r.population;
    state.population = r.population;
  }
  if (cityEl) cityEl.value = `${r.name}, ${r.country}`;
  if (noteEl) noteEl.style.display = 'block';
  if (sugEl)  sugEl.style.display  = 'none';
  // Store city coordinates so "Set on Map" modal can pre-populate the conflict pin
  state.cityName        = `${r.name}, ${r.country}`;
  state.cityLat         = r.lat;
  state.cityLng         = r.lng;
  state._pendingCityPin = { lat: r.lat, lng: r.lng, name: state.cityName };
  // Abre o modal automaticamente
  const pinModal = document.getElementById('pinModal');
  if (pinModal) new bootstrap.Modal(pinModal).show();
  // Optionally trigger demographic suggestion for the country
  if (r.country) suggestVulnerablePct(r.country);
  if (r.countryCode) fetchCommodityPrices(r.countryCode);
  updateAll();
}

async function fetchCommodityPrices(iso3) {
  const card = document.getElementById('commodityCard');
  if (!card) return;
  card.dataset.fuelAdj = '1';
  card.dataset.foodAdj = '1';
  card.style.display = 'block';
  document.getElementById('commodityDate').textContent   = '…';
  document.getElementById('commodityBrent').textContent  = '…';
  document.getElementById('commodityWheat').textContent  = '…';
  document.getElementById('commodityCorn').textContent   = '…';
  document.getElementById('commodityRice').textContent   = '…';
  document.getElementById('commodityOil').textContent    = '…';
  document.getElementById('commodityFoodAdj').textContent = '…';
  document.getElementById('commodityNetImpact').textContent = '…';

  const sign = v => v >= 0 ? '+' : '';
  const colorFor = adj => adj > 1.05 ? '#dc2626' : adj < 0.95 ? '#16a34a' : '#64748b';
  const pctVs = (value, baseline) => ((value / baseline - 1) * 100).toFixed(0);
  // Renders "$value/mt (+X% vs $baseline/mt baseline)", or '—' if value is missing
  const renderCommodity = (value, baseline) => {
    if (value == null) return '—';
    const pct = pctVs(value, baseline);
    return `$${value}/mt <span style="color:${colorFor(value / baseline)};font-size:.68rem">(${sign(pct)}${pct}% vs $${baseline}/mt baseline)</span>`;
  };

  try {
    const data = await fetch(`/api/commodity-prices/${encodeURIComponent(iso3)}`).then(r => r.json());
    const baseline = data.ercf_baseline || {};

    const fuelAdj = data.fuel_adjustment ?? 1;
    const foodAdj = data.food_adjustment ?? 1;
    const fuelPct = ((fuelAdj - 1) * 100).toFixed(0);
    const foodPct = ((foodAdj - 1) * 100).toFixed(0);
    const fuelColor = colorFor(fuelAdj);
    const foodColor = colorFor(foodAdj);

    document.getElementById('commodityDate').textContent  = data.fuel_date || data.food_date || '—';
    document.getElementById('commodityBrent').innerHTML   = data.fuel_brent_usd_bbl != null
      ? `$${data.fuel_brent_usd_bbl}/bbl <span style="color:${fuelColor};font-size:.68rem">(${sign(fuelPct)}${fuelPct}% vs $80/bbl baseline)</span>`
      : '—';
    document.getElementById('commodityWheat').innerHTML = renderCommodity(data.wheat_usd_mt, baseline.wheat_usd_mt ?? 250);
    document.getElementById('commodityCorn').innerHTML  = renderCommodity(data.corn_usd_mt, baseline.corn_usd_mt ?? 200);
    document.getElementById('commodityRice').innerHTML  = renderCommodity(data.rice_usd_mt, baseline.rice_usd_mt ?? 500);
    document.getElementById('commodityOil').innerHTML   = renderCommodity(data.soybean_oil_usd_mt, baseline.soybean_oil_usd_mt ?? 900);
    document.getElementById('commodityFoodAdj').innerHTML = data.food_adjustment != null
      ? `<span style="color:${foodColor}">${sign(foodPct)}${foodPct}%</span> vs ERCF baseline (wheat 40% · corn 30% · rice 20% · soybean oil 10%)`
      : '—';

    // Combined net impact on evacuation cost total — fuel and food/water are weighted by their
    // approximate share of ground evacuation cost (see calcResources() cost breakdown), since
    // fuel/food price swings don't move the whole budget 1:1.
    const netImpactEl = document.getElementById('commodityNetImpact');
    if (data.fuel_adjustment != null || data.food_adjustment != null) {
      const FUEL_WEIGHT = 0.35;
      const FOOD_WEIGHT = 0.08;
      const fuelContrib = (fuelAdj - 1) * FUEL_WEIGHT * 100;
      const foodContrib = (foodAdj - 1) * FOOD_WEIGHT * 100;
      const combinedImpact = fuelContrib + foodContrib;
      const netColor = combinedImpact > 0 ? '#dc2626' : combinedImpact < 0 ? '#16a34a' : '#64748b';
      const bigger  = Math.abs(fuelContrib) >= Math.abs(foodContrib) ? 'fuel' : 'food';
      const smaller = bigger === 'fuel' ? 'food' : 'fuel';
      const biggerPct  = bigger === 'fuel' ? fuelPct : foodPct;
      const smallerPct = smaller === 'fuel' ? fuelPct : foodPct;
      const impactStr = (combinedImpact >= 0 ? '+' : '') + combinedImpact.toFixed(1);
      netImpactEl.innerHTML = `<span style="color:${netColor}">Net cost impact: ${impactStr}%</span> ` +
        `(${bigger} ${sign(biggerPct)}${biggerPct}% outweighs ${smaller} ${sign(smallerPct)}${smallerPct}%) ` +
        `<span style="font-weight:400;font-style:italic;color:#a16207">Applied to evacuation cost total</span>`;
    } else {
      netImpactEl.textContent = '—';
    }

    card.dataset.fuelAdj = fuelAdj;
    card.dataset.foodAdj = foodAdj;
  } catch(e) {
    document.getElementById('commodityBrent').textContent = 'unavailable';
    document.getElementById('commodityFoodAdj').textContent = 'unavailable';
    document.getElementById('commodityNetImpact').textContent = 'unavailable';
  }
  syncCommodityButtons();
}

function applyMarketPrices() {
  const card = document.getElementById('commodityCard');
  const fuelAdj = parseFloat(card?.dataset.fuelAdj ?? '1');
  const foodAdj = parseFloat(card?.dataset.foodAdj ?? '1');
  state.fuelAdjFactor = isFinite(fuelAdj) ? Math.round(fuelAdj * 1000) / 1000 : 1.0;
  state.foodAdjFactor = isFinite(foodAdj) ? Math.round(foodAdj * 1000) / 1000 : 1.0;
  syncCommodityButtons();
  updateAll();
}

function dismissCommodityCard() {
  document.getElementById('commodityCard').style.display = 'none';
}

function revertMarketPrices() {
  state.fuelAdjFactor = 1.0;
  state.foodAdjFactor = 1.0;
  updateAll();
  syncCommodityButtons();
}

function syncCommodityButtons() {
  const applyBtn  = document.getElementById('commodityApplyBtn');
  const revertBtn = document.getElementById('commodityRevertBtn');
  if (!applyBtn || !revertBtn) return;
  const isApplied = (state.fuelAdjFactor ?? 1.0) !== 1.0 || (state.foodAdjFactor ?? 1.0) !== 1.0;

  applyBtn.disabled        = isApplied;
  applyBtn.textContent     = isApplied ? '✓ Applied' : 'Apply price adjustment';
  applyBtn.style.background = isApplied ? '#e5e7eb' : '#78350f';
  applyBtn.style.color      = isApplied ? '#9ca3af' : '#fff';
  applyBtn.style.cursor     = isApplied ? 'default'  : 'pointer';

  revertBtn.disabled        = !isApplied;
  revertBtn.style.background = isApplied ? '#475569' : '#e5e7eb';
  revertBtn.style.color      = isApplied ? '#fff'     : '#9ca3af';
  revertBtn.style.cursor     = isApplied ? 'pointer'  : 'default';
}

// Set by fetchAltModeResult while it re-runs updateAll() to refresh dependents (headline,
// Decision Analysis) after an air-mode fetch resolves — prevents that updateAll() call from
// triggering another fetch (infinite fetch → updateAll → fetch loop).
let _suppressAltFetch = false;

// Bumped on every fetchAltModeResult() call. A response is only rendered if its token still
// matches the latest — otherwise a newer request has superseded it. Without this, an older
// in-flight request that resolves after a newer one (e.g. air_heli fetch outlasting a walking
// fetch fired right after it) overwrites the panel with stale/wrong-mode data.
let _altFetchToken = 0;

function onTransportModeChange() {
  const mode = document.getElementById('transportMode').value;
  const groundPanel = document.getElementById('groundResourcePanel');
  const altPanel    = document.getElementById('altModeResourcePanel');

  if (mode === 'ground') {
    groundPanel.style.display = 'block';
    altPanel.style.display    = 'none';
  } else {
    groundPanel.style.display = 'none';
    altPanel.style.display    = 'block';
    fetchAltModeResult(mode);
  }
  // Clear any stale alt-mode result (e.g. an air/walking total left over from before this
  // switch) and refresh the headline immediately, before any fetch resolves: air/walking
  // show "Calculating…" until fetchAltModeResult() completes, ground shows the terrestrial
  // total right away since it needs no fetch.
  state._lastAltResult = null;
  if (state._lastResources) updateResourceDisplay(state._lastResources);
  renderTransportWarnings(mode, state.dims, state.population);
}

async function fetchAltModeResult(mode) {
  const myToken = ++_altFetchToken;
  const altPanel = document.getElementById('altModeResourcePanel');
  altPanel.innerHTML = '<div class="text-muted small"><i class="fas fa-spinner fa-spin me-1"></i>Calculating...</div>';

  const isAir = mode === 'air_fixed' || mode === 'air_heli';
  const isAlt = isAir || mode === 'walking';
  const endpoint = isAir ? '/api/air-evacuation' : '/api/walking-evacuation';
  const requestBody = isAir
    ? {
        population:  state.population,
        distance_km: state.distanceKm,
        mode:        mode === 'air_fixed' ? 'fixed_wing' : 'helicopter',
        has_runway:  state.hasRunway ?? null,
      }
    : {
        population: state.population,
        distance_km: state.distanceKm,
        vulnerable_pct: state.vulnerablePct ?? 0,
      };

  try {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${resp.status})`);
    }
    const data = await resp.json();
    if (myToken !== _altFetchToken) return; // a newer fetch has already superseded this one

    if (isAir) {
      // Air cost model has no fuel/food line items of its own — approximate market exposure
      // by scaling the whole quote with the same fuel adjustment used for ground transport.
      const fuelAdj = state.fuelAdjFactor ?? 1.0;
      data.total_cost_usd = Math.round(data.total_cost_usd * fuelAdj);
      if (fuelAdj !== 1.0) data._fuelAdjApplied = fuelAdj;
    } else if (mode === 'walking') {
      // Walking's only commodity-priced line item is en-route provisions (food/water) — mirror
      // the ground model's food/water market adjustment there, then recompute the total.
      const foodAdj = state.foodAdjFactor ?? 1.0;
      const cb = data.cost_breakdown || {};
      const adjProvisions = Math.round((cb.provisions_usd || 0) * foodAdj);
      data.cost_breakdown = { ...cb, provisions_usd: adjProvisions };
      data.total_cost_usd = adjProvisions + (cb.personnel_usd || 0);
      if (foodAdj !== 1.0) data._foodAdjApplied = foodAdj;
    }
    renderAltModeResult(data, altPanel);
    if (isAlt) {
      state._lastAltResult = data;
      // Re-run updateAll() (not just updateResourceDisplay) so Decision Analysis's
      // evacuatedCost — computed inside updateAll() — also picks up the new alt-mode result.
      _suppressAltFetch = true;
      updateAll();
      _suppressAltFetch = false;
    }
  } catch (e) {
    if (myToken !== _altFetchToken) return; // a newer fetch has already superseded this one
    altPanel.innerHTML = `<div class="alert alert-danger small mb-0">Error: ${e.message}</div>`;
    if (isAlt) {
      state._lastAltResult = null;
      if (state._lastResources) updateResourceDisplay(state._lastResources);
    }
  }
}

function renderAltModeResult(data, container) {
  const confColor = data.confidence === 'validated' ? '#16a34a' : '#d97706';
  const confLabel = data.confidence === 'validated' ? 'VALIDATED' : 'ESTIMATED';
  const feasBadge = data.feasible
    ? '<span class="badge" style="background:#16a34a">Feasible</span>'
    : '<span class="badge" style="background:#dc2626">Not feasible</span>';

  let costBlock = '';
  let statRow = '';
  let suppliesRow = '';
  let personnelRow = '';
  // "aircraft" is invariant (no plural -s); "helicopter" pluralizes normally
  const aircraftLabel = n => data.mode === 'helicopter' ? (n === 1 ? 'helicopter' : 'helicopters') : 'aircraft';

  const p = data.personnel || {};
  const s = data.supplies || {};

  if (data.mode === 'walking') {
    const cb = data.cost_breakdown || {};
    const speedDisplay = state.unitSystem === 'mi'
      ? `${Math.round(data.effective_speed_kmh * 0.621371 * 10) / 10} mph`
      : `${data.effective_speed_kmh} km/h`;
    costBlock = `
      <div class="val" style="font-size:1.4rem">$${data.total_cost_usd.toLocaleString()}</div>
      <div class="text-muted small">${data.days_needed} day(s) · ${speedDisplay} effective speed</div>
      <div class="text-muted small mt-1">
        <span class="me-3">📦 Provisions: $${(cb.provisions_usd||0).toLocaleString()}</span>
        <span>👥 Personnel: $${(cb.personnel_usd||0).toLocaleString()}</span>
      </div>`;
    statRow = `
      <div class="row g-2 mb-2 mt-2">
        <div class="col-6 col-md-6"><div class="stat-mini text-center"><div class="val">${data.days_needed}</div><div class="lbl">📅 Days needed</div></div></div>
        <div class="col-6 col-md-6"><div class="stat-mini text-center"><div class="val">${speedDisplay}</div><div class="lbl">🚶 Group speed</div></div></div>
      </div>`;
    personnelRow = `
      <div class="small fw-semibold text-muted mt-2 mb-1" style="text-transform:uppercase;letter-spacing:.05em;font-size:.68rem">Personnel Required</div>
      <div class="row g-2 mb-2">
        <div class="col-6 col-md-4"><div class="stat-mini text-center"><div class="val">${p.guides_escorts ?? '—'}</div><div class="lbl">🧭 Guides/escorts</div></div></div>
        <div class="col-6 col-md-4"><div class="stat-mini text-center"><div class="val">${p.medical_staff ?? '—'}</div><div class="lbl">🏥 Medical</div></div></div>
        <div class="col-6 col-md-4"><div class="stat-mini text-center"><div class="val">${p.coordinators ?? '—'}</div><div class="lbl">📡 Coord.</div></div></div>
      </div>`;
    suppliesRow = `
      <div class="small fw-semibold text-muted mt-2 mb-1" style="text-transform:uppercase;letter-spacing:.05em;font-size:.68rem">En-Route Supplies</div>
      <div class="row g-2 mb-2">
        <div class="col-6 col-md-6"><div class="stat-mini text-center"><div class="val">${((data.supplies||{}).water_l||0).toLocaleString()}L</div><div class="lbl">💧 Water</div></div></div>
        <div class="col-6 col-md-6"><div class="stat-mini text-center"><div class="val">${((data.supplies||{}).food_kg||0).toLocaleString()}kg</div><div class="lbl">🍚 Food</div></div></div>
      </div>`;
  } else {
    const aircraftLine = data.aircraft_needed != null
      ? `<div class="text-muted small">${data.flights_needed} flight(s) needed · ${data.aircraft_needed} ${aircraftLabel(data.aircraft_needed)} in parallel (1-day operation)</div>`
      : '';
    costBlock = `<div class="val" style="font-size:1.4rem">$${data.total_cost_usd.toLocaleString()}</div>${aircraftLine}`;
    personnelRow = `
      <div class="small fw-semibold text-muted mt-2 mb-1" style="text-transform:uppercase;letter-spacing:.05em;font-size:.68rem">Personnel Required</div>
      <div class="row g-2 mb-2">
        <div class="col-6 col-md-3"><div class="stat-mini text-center"><div class="val">${p.pilots ?? '—'}</div><div class="lbl">✈️ Pilots</div></div></div>
        <div class="col-6 col-md-3"><div class="stat-mini text-center"><div class="val">${p.cabin_crew ?? '—'}</div><div class="lbl">🧑‍✈️ Cabin crew</div></div></div>
        <div class="col-6 col-md-3"><div class="stat-mini text-center"><div class="val">${p.medical_staff ?? '—'}</div><div class="lbl">🏥 Medical</div></div></div>
        <div class="col-6 col-md-3"><div class="stat-mini text-center"><div class="val">${p.coordinators ?? '—'}</div><div class="lbl">📡 Coord.</div></div></div>
      </div>`;
    suppliesRow = `
      <div class="small fw-semibold text-muted mt-2 mb-1" style="text-transform:uppercase;letter-spacing:.05em;font-size:.68rem">En-Route Supplies</div>
      <div class="row g-2 mb-2">
        <div class="col-6 col-md-6"><div class="stat-mini text-center"><div class="val">${(s.water_l||0).toLocaleString()}L</div><div class="lbl">💧 Water</div></div></div>
        <div class="col-6 col-md-6"><div class="stat-mini text-center"><div class="val">${(s.food_kg||0).toLocaleString()}kg</div><div class="lbl">🍚 Food</div></div></div>
      </div>`;
  }

  let notesHtml = '';
  if (data.fleet_planning) {
    const fp = data.fleet_planning;
    const rows = Object.values(fp).map(w => `
      <tr style="${w.within_tactical_window ? '' : 'color:#b45309'}">
        <td style="padding:.2rem .5rem;font-weight:600">${w.days} day${w.days > 1 ? 's' : ''}${w.within_tactical_window ? '' : ' ⚠'}</td>
        <td style="padding:.2rem .5rem">${w.aircraft_needed} ${aircraftLabel(w.aircraft_needed)}</td>
        <td style="padding:.2rem .5rem;color:#6b7280">${w.flights_per_day} flight(s)/day</td>
      </tr>`
    ).join('');
    notesHtml = `
      <div class="small fw-semibold text-muted mt-2 mb-1" style="text-transform:uppercase;letter-spacing:.05em;font-size:.68rem">Fleet planning (${aircraftLabel(2)} needed, operating in parallel)</div>
      <table style="width:100%;font-size:.75rem;border-collapse:collapse">
        <thead><tr style="color:#9ca3af;font-size:.68rem">
          <th style="padding:.2rem .5rem;text-align:left">Window</th>
          <th style="padding:.2rem .5rem;text-align:left">${aircraftLabel(2).charAt(0).toUpperCase()+aircraftLabel(2).slice(1)}</th>
          <th style="padding:.2rem .5rem;text-align:left">Tempo</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div style="font-size:.68rem;color:#d97706;margin-top:.3rem">⚠️ Rows marked ⚠ exceed the normal ≤3-day tactical window. UNHAS missions typically operate 1–5 aircraft — windows requiring large fleets may need multi-agency coordination.</div>`;
  } else {
    const notesList = (data.feasibility_notes || []).map(n => `<li>${n}</li>`).join('');
    notesHtml = notesList ? `<ul class="small text-muted mt-2 mb-2 ps-3">${notesList}</ul>` : '';
  }

  // Destroy previous Chart.js instance if it exists
  if (window._altModeChart) { window._altModeChart.destroy(); window._altModeChart = null; }

  const cb = data.cost_breakdown || {};
  const isWalking = data.mode === 'walking';
  const chartLabels = isWalking ? ['Provisions', 'Personnel'] : ['Transport Cost'];
  const chartData = isWalking
    ? [cb.provisions_usd || 0, cb.personnel_usd || 0]
    : [data.total_cost_usd];
  const chartColors = isWalking
    ? ['rgba(59,130,246,.7)', 'rgba(217,119,6,.7)']
    : [data.confidence === 'validated' ? 'rgba(22,163,74,.7)' : 'rgba(217,119,6,.7)'];
  const chartTitle = isWalking ? 'Cost Breakdown (USD)' : 'Transport Cost (USD)';

  const chartHtml = `
    <div class="mt-2 mb-2">
      <div class="small fw-semibold text-muted mb-1" style="text-transform:uppercase;letter-spacing:.05em;font-size:.68rem">${chartTitle}</div>
      <div style="height:${isWalking ? '64px' : '44px'}"><canvas id="altCostBarChart"></canvas></div>
    </div>`;

  // Ground-cost reference — air modes only (walking keeps its own self-contained breakdown,
  // unchanged from before this comparison line was added).
  const groundRefHtml = !isWalking && state._lastResources
    ? `<div class="text-muted small mt-2">Ground convoy cost: $${fmt(state._lastResources.totalCost)} (reference)</div>`
    : '';

  const fuelAdjNoteHtml = data._fuelAdjApplied
    ? `<div class="text-muted small mt-1">Fuel market adjustment applied: ×${data._fuelAdjApplied}</div>`
    : data._foodAdjApplied
    ? `<div class="text-muted small mt-1">Food/water market adjustment applied to provisions: ×${data._foodAdjApplied}</div>`
    : '';

  container.innerHTML = `
    <div class="d-flex justify-content-between align-items-start mb-2">
      ${feasBadge}
      <span class="badge" style="background:${confColor}">${confLabel}</span>
    </div>
    ${costBlock}
    ${statRow}
    ${personnelRow}
    ${suppliesRow}
    ${chartHtml}
    ${notesHtml}
    <div class="text-muted" style="font-size:.68rem">${data.source}</div>
    ${fuelAdjNoteHtml}
    ${groundRefHtml}
  `;

  const ctx = document.getElementById('altCostBarChart');
  if (ctx) {
    window._altModeChart = new Chart(ctx.getContext('2d'), {
      type: 'bar',
      data: {
        labels: chartLabels,
        datasets: [{ label: 'USD', data: chartData, backgroundColor: chartColors, borderRadius: 4 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { callback: v => '$' + fmt(v), font: { size: 8 } } }, y: { ticks: { font: { size: 8 } } } }
      }
    });
  }
}

// ── Decision Analysis: Act Now vs Wait ────────────────────────────────────────
function updateDecisionAnalysis(evacCost, dailyCostA, dailyCostB) {
  const elEvacCost      = document.getElementById('decisionEvacCost');
  const elEvacLabel     = document.getElementById('decisionEvacLabel');
  const elEvacDaily     = document.getElementById('decisionEvacDaily');
  const elEvacDailyWrap = document.getElementById('decisionEvacDailyWrap');
  const elNoEvac        = document.getElementById('decisionNoEvacCost');
  const elBreakEven     = document.getElementById('decisionBreakEven');
  const elBESub         = document.getElementById('decisionBreakEvenSub');
  const elNote          = document.getElementById('decisionNote');
  const elDelayNote     = document.getElementById('decisionDelayNote');
  if (!elEvacCost) return;

  const fullEvac = state.remainingPop === 0 && evacCost > 0;

  if (elEvacLabel)     elEvacLabel.textContent              = fullEvac ? 'Evacuate all now' : 'Evacuate now';
  if (elEvacDailyWrap) elEvacDailyWrap.style.display        = fullEvac ? 'none' : '';
  if (elNote) elNote.textContent = fullEvac
    ? 'Full evacuation scenario: compares one-time cost of evacuating entire population against cumulative daily assistance cost if no evacuation occurs.'
    : 'Option A: one-time evacuation cost + daily assistance for population remaining in zone. Option B: daily assistance for full population with no evacuation. Break-even: the day at which not evacuating becomes more expensive than having evacuated. Assumes static conflict conditions and costs.';

  if (!dailyCostB || dailyCostB <= 0) {
    elEvacCost.textContent  = '—';
    if (elEvacDaily) elEvacDaily.textContent = '—';
    elNoEvac.textContent    = '—';
    elBreakEven.textContent = '—';
    elBESub.textContent     = 'define scenario above';
    if (elDelayNote) elDelayNote.textContent = '';
    _renderDecisionChart(null, null, null, null);
    return;
  }

  elEvacCost.textContent = '$' + fmt(Math.round(evacCost));
  if (elEvacDaily) elEvacDaily.textContent = '+ $' + fmt(Math.round(dailyCostA)) + '/day';
  elNoEvac.textContent   = '$' + fmt(Math.round(dailyCostB)) + '/day';
  if (elDelayNote) {
    elDelayNote.textContent = `This analysis assumes evacuation begins today. Each day of delay costs an additional $${fmt(Math.round(dailyCostB))} and shifts the break-even forward by approximately 1 day.`;
  }

  const diff = dailyCostB - dailyCostA;
  if (diff <= 0) {
    elBreakEven.textContent = 'No break-even';
    elBESub.textContent     = evacCost === 0
      ? 'No evacuees defined — set population remaining below 100% to see break-even analysis'
      : 'Evacuation is always more expensive in this scenario';
    elBreakEven.style.color = '#d97706';
    _renderDecisionChart(evacCost, dailyCostA, dailyCostB, null);
    return;
  }

  const breakEvenDay = Math.ceil(evacCost / diff);
  if (breakEvenDay > 90) {
    elBreakEven.textContent = '>90 days';
    elBESub.textContent     = fullEvac
      ? 'Beyond 90 days — evacuating everyone was still cheaper long-term'
      : 'Beyond planning window — evacuation recommended on risk grounds';
    elBreakEven.style.color = '#d97706';
  } else {
    elBreakEven.textContent = 'Day ' + breakEvenDay;
    elBESub.textContent     = fullEvac
      ? 'after this point, evacuating everyone was cheaper'
      : 'after day ' + breakEvenDay + ', evacuation was the lower-cost decision';
    elBreakEven.style.color = '#16a34a';
  }

  _renderDecisionChart(evacCost, dailyCostA, dailyCostB, breakEvenDay);
}

function _renderDecisionChart(evacCost, dailyCostA, dailyCostB, breakEvenDay) {
  const canvas = document.getElementById('decisionChart');
  if (!canvas) return;

  if (state.charts._decision) {
    state.charts._decision.destroy();
    state.charts._decision = null;
  }

  if (!dailyCostB) return;

  const DAYS  = 90;
  const labels = Array.from({length: DAYS}, (_, i) => i + 1);
  // Option A: evacCost (one-time) + dailyCostA × day
  const lineA  = labels.map(d => Math.round((evacCost || 0) + dailyCostA * d));
  // Option B: dailyCostB × day (no upfront cost)
  const lineB  = labels.map(d => Math.round(dailyCostB * d));

  const beDay = breakEvenDay != null ? Math.min(breakEvenDay, DAYS) : null;

  state.charts._decision = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Option A — Evacuate now + assist remaining',
          data: lineA,
          borderColor: '#dc2626',
          backgroundColor: 'rgba(220,38,38,.06)',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Option B — No evacuation, assist all in zone',
          data: lineB,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37,99,235,.08)',
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: ctx => ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString(),
          },
        },
      },
      scales: {
        x: {
          ticks: {
            font: { size: 9 },
            maxTicksLimit: 10,
            callback: v => 'd' + (v + 1),
          },
          grid: { color: 'rgba(0,0,0,.04)' },
        },
        y: {
          ticks: {
            font: { size: 9 },
            callback: v => v >= 1e6 ? '$' + (v/1e6).toFixed(1) + 'M'
                        : v >= 1e3 ? '$' + (v/1e3).toFixed(0) + 'K' : '$' + v,
          },
          grid: { color: 'rgba(0,0,0,.04)' },
        },
      },
    },
    plugins: [{
      id: 'beMarker',
      afterDraw(chart) {
        if (beDay == null) return;
        const { ctx, scales: { x, y } } = chart;
        const xPx = x.getPixelForValue(beDay - 1);
        const top  = y.top;
        const bot  = y.bottom;
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = '#16a34a';
        ctx.lineWidth = 1.5;
        ctx.moveTo(xPx, top);
        ctx.lineTo(xPx, bot);
        ctx.stroke();
        ctx.fillStyle = '#16a34a';
        ctx.font = 'bold 8px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText('Day ' + breakEvenDay, xPx, top + 9);
        ctx.restore();
      },
    }],
  });
}

function updateRemainingCostCard(rc, fullEvacCost) {
  document.getElementById('rcTotal').textContent   = '$' + fmt(rc.total);
  document.getElementById('rcExtProb').textContent = (rc.prob * 100).toFixed(0) + '%';

  // fullEvacCost reflects whatever transport mode is currently selected (ground/air/walking —
  // see updateAll()). Decision Analysis uses a different, smaller evacuatedCost (prorated to
  // evacuatedPop) — not used here.
  const evacuatedPop = Math.max(0, (state.population || 0) - (state.remainingPop || 0));

  // Total crisis cost = cost of evacuating those who left + cost of assisting those who stayed
  const totalCrisisCost = fullEvacCost + rc.total;
  document.getElementById('rcCrisisTotal').textContent = '$' + fmt(totalCrisisCost);

  // Breakdown sub-line
  const breakdownEl = document.getElementById('rcCrisisBreakdown');
  if (evacuatedPop > 0 && rc.total > 0) {
    breakdownEl.textContent = `Evac $${fmt(fullEvacCost)} + Assist $${fmt(rc.total)}`;
  } else if (evacuatedPop === 0) {
    breakdownEl.textContent = 'Assistance only — all stayed';
  } else {
    breakdownEl.textContent = 'Evacuation only — none stayed';
  }

  // Cost per person remaining
  const remPop  = state.remainingPop;
  const cpprEl  = document.getElementById('rcCPPR');
  cpprEl.textContent = remPop > 0 ? '$' + fmt(rc.total / remPop) : '—';

  const pct = v => (v * 100).toFixed(0);
  const src = (txt, tip) =>
    `<i class="fas fa-circle-question rc-info" data-bs-toggle="tooltip"
        data-bs-placement="right" data-bs-title="${tip}"></i>`;

  // Dim modifier tag builder: renders only non-trivial modifiers
  const dimTag = parts => parts.length
    ? ` · <span style="color:#7c3aed;font-size:.68rem">${parts.join(' · ')}</span>` : '';

  const supplyDimParts = [];
  if (rc.d4Penalty  > 0.001) supplyDimParts.push(`D4=${rc.dimVals.d4} logistics +${(rc.d4Penalty*100).toFixed(0)}%`);
  if (rc.d3LossAdd  > 0.001) supplyDimParts.push(`D3=${rc.dimVals.d3} access +${(rc.d3LossAdd*100).toFixed(0)}% loss`);
  if (rc.d7Overhead > 0.001) supplyDimParts.push(`D7=${rc.dimVals.d7} coord +${(rc.d7Overhead*100).toFixed(0)}%`);

  const extractDimParts = [];
  if (rc.d1ExtMult  > 1.001) extractDimParts.push(`D1=${rc.dimVals.d1} kinetic ×${rc.d1ExtMult.toFixed(1)}`);
  if (rc.d3ProbAdd  > 0.001) extractDimParts.push(`D3=${rc.dimVals.d3} corridor +${(rc.d3ProbAdd*100).toFixed(0)}%`);
  if (rc.d6FloorVal > 0.001) extractDimParts.push(`D6=${rc.dimVals.d6} urgency floor ${(rc.d6FloorVal*100).toFixed(0)}%`);

  const medDimParts = [];
  if (rc.d5CostMult > 1.001) medDimParts.push(`D5=${rc.dimVals.d5} care $${Math.round(rc.treatCostPer).toLocaleString()}/injury`);

  // Connecting note: makes the base→overhead→total decomposition explicit
  const baseCost      = rc.baseCost;
  const accessPremium = rc.accessPremium;
  const connectingNote = `
    <div style="font-size:.7rem;color:#475569;background:#f8fafc;border:1px dashed #cbd5e1;
                border-radius:6px;padding:.4rem .65rem;margin-bottom:.45rem;line-height:1.6">
      <i class="fas fa-arrow-turn-down me-1" style="opacity:.35;font-size:.6rem"></i>
      <strong style="color:#334155">Supply delivery breakdown:</strong>
      Base survival <strong>$${fmt(baseCost)}</strong>
      <span style="color:#94a3b8;font-style:italic">(what people need — $3.50/person/day × ${fmtFull(remPop)} × ${state.days}d)</span>
      + Logistics overhead <strong style="color:#2563eb">+$${fmt(accessPremium)}</strong>
      <span style="color:#94a3b8;font-style:italic">(what it costs to deliver in this context — ×${rc.effectiveAccessMult.toFixed(2)} access · ×${rc.terrainMult.toFixed(1)} terrain · +${pct(rc.effectiveLossRate)}% loss)</span>
      = <strong>$${fmt(rc.supplyCost)}</strong> total supply delivery
    </div>`;

  const rows = [
    {
      cls:  'rc-supply',
      icon: 'fa-truck',
      label: `Supply delivery <span style="font-weight:400;color:#64748b">(×${rc.effectiveAccessMult.toFixed(2)} access · ×${rc.terrainMult.toFixed(1)} terrain · +${pct(rc.effectiveLossRate)}% loss${dimTag(supplyDimParts)})</span>`,
      value: '$' + fmt(rc.supplyCost),
      tip:   `Daily survival cost ($3.50/person/day × ${fmtFull(remPop)} remaining × ${state.days}d = $${fmt(baseCost)}) plus conflict access overhead (+$${fmt(accessPremium)}). Access multiplier ×${rc.effectiveAccessMult.toFixed(2)} (WFP Logistics Cluster 2020–2023). Terrain multiplier ×${rc.terrainMult.toFixed(1)} (Level ${state.terrain}: ${['','Critical — mountains/forest unpaved','High — hilly mostly unpaved','Moderate — mixed terrain','Low — mostly flat paved','Minimal — flat paved all-season'][state.terrain]}) reflects road access difficulty affecting all aid delivery logistics. Applied on top of conflict access multiplier. Source: World Bank RAI (SDG 9.1.1); Puga TRI dataset. Loss rate +${pct(rc.effectiveLossRate)}% (OCHA access monitoring).`,
    },
    {
      cls:  'rc-extract',
      icon: 'fa-helicopter',
      label: `Emergency extraction <span style="font-weight:400;color:#64748b">(${(rc.prob*100).toFixed(0)}% prob · ${fmtDist(rc.distKm)} · $${rc.perPsnGround.toFixed(0)}/$${rc.perPsnAir.toFixed(0)} pp${dimTag(extractDimParts)})</span>`,
      value: '$' + fmt(rc.extractCost),
      tip:   `UNHAS-anchored (WFP EB Jan 2025, $2.08/km 2023 rate). Ground: $${rc.perPsnGround.toFixed(2)}/person. Air/medevac: $${rc.perPsnAir.toFixed(2)}/person (×3 vulnerability premium). D1 kinetic ×1.0–2.0 extraction difficulty; D3 authorization adds 0–25% to probability; D6 urgency sets probability floor (60% at D6≥4, 85% at D6=5). Level 4 adds 2.5× helicopter premium.`,
    },
    {
      cls:  'rc-medical',
      icon: 'fa-kit-medical',
      label: `Field medical treatment <span style="font-weight:400;color:#64748b">(${fmtFull(Math.round(rc.cumInjuries))} injuries × $${Math.round(rc.treatCostPer).toLocaleString()}${dimTag(medDimParts)})</span>`,
      value: '$' + fmt(rc.medCost),
      tip:   `Base $800/injury. Peer-reviewed range: $211–$1,013 (MSF Nigeria 2009, inflation-adjusted to 2024 USD). $800 adopted as conservative upper-mid estimate. ICRC per-patient surgical cost data not publicly available. (ref: Chu et al. 2010, Conflict & Health; MSF Nigeria field reports). D5 destination multiplies cost/injury ×1.0–2.0 (no medical infrastructure at D5=5).`,
    },
    {
      cls:  'rc-vulnerable',
      icon: 'fa-wheelchair',
      label: `Vulnerable population support <span style="font-weight:400;color:#64748b">(${fmtFull(rc.vuln)} persons × $2.50/day premium × ${state.days}d · total $6.00/day vs $3.50/day for general population)</span> · <span style="color:#7c3aed">2× retention rate applied (ref: AARP/FEMA 2006)</span>`,
      value: '$' + fmt(rc.vulnerablePremium),
      tip:   'ESTIMATED — no published per-capita figure. The $2.50/day here is INCREMENTAL — on top of the $3.50/day base survival cost already counted for every remaining person (vulnerable included) inside "Supply delivery" above; the two are not alternatives, they stack to $6.00/day total for vulnerable individuals. Reflects mobility assistance, extra medical supplies, and mental health support. Population count reflects differential retention: vulnerable individuals are ~2× less likely to evacuate than the general population (ref: AARP/FEMA Post-Katrina Look Back 2006; WHO Disability, Disaster Risk Reduction and Emergency Preparedness 2005).',
    },
    {
      cls:  'rc-total',
      icon: 'fa-sigma',
      label: 'Total assistance cost',
      value: '$' + fmt(rc.total),
      tip:   'Sum of supply delivery, emergency extraction, and field medical. All three components now respond to D1–D7 dimension sliders.',
    },
  ];

  const breakdown = document.getElementById('rcBreakdown');
  breakdown.innerHTML = connectingNote + rows.map(r => `
    <div class="rc-row ${r.cls}">
      <span>
        <i class="fas ${r.icon} me-2" style="width:14px;text-align:center;opacity:.7"></i>
        ${r.label}
        ${src(r.label, r.tip)}
      </span>
      <span class="fw-semibold" style="white-space:nowrap">${r.value}</span>
    </div>`).join('');

  // Comparison callout
  const cpprStr      = remPop      > 0 ? `$${fmt(rc.total / remPop)} pp`      : '—';
  const cppeStr      = evacuatedPop > 0 ? `$${fmt(fullEvacCost / evacuatedPop)} pp` : '—';
  const totalCrisis  = fullEvacCost + rc.total;
  breakdown.innerHTML += `
    <div class="rc-compare">
      <i class="fas fa-scale-balanced me-1"></i>
      Total crisis cost: <strong>$${fmt(totalCrisis)}</strong> —
      <strong>${fmtFull(evacuatedPop)}</strong> evacuated at <strong>${cppeStr}</strong>,
      <strong>${fmtFull(remPop)}</strong> assisted in-zone at <strong>${cpprStr}</strong>.
    </div>`;

  reinitTooltips(breakdown);
}

function updateHistRadar() {
  state.charts.radarHist.data.datasets[0].data = DIM_KEYS.map(k => state.dims[k]);
  state.charts.radarHist.update('none');
}

// ═══════════════════════════════════════════════════════════
// HISTORICAL CASES — COST COMPUTATION HELPERS
// ═══════════════════════════════════════════════════════════

// Default terrain assumption for historical cases (no per-case terrain data available).
const HIST_TERRAIN_DEFAULT = 3;

function computeHistCaseCosts(c) {
  const ri      = c.risk_indicators;
  const vulnPct = c.vulnerable_pct ?? 20;
  const distKm  = c.distance_km    ?? 50;
  // Compute remaining_pct from historical displacement data for v3 model calibration
  const histRemainingPct = c.displaced != null && c.population_at_risk > 0
    ? Math.max(0, 1 - c.displaced / c.population_at_risk)
    : 0.5;
  const histExposure = computeHistExposureFactor(c);
  const res  = calcResources(
    c.population_at_risk, vulnPct, c.risk_level,
    distKm, ri.d2_vulnerability, HIST_TERRAIN_DEFAULT,
    undefined, undefined,
    ri.d4_logistics ?? 3, ri.d5_destination ?? 3
  );
  // Siege cap disabled for regional/city_conflict named types
  const histSiegeCap = !(c.exposure_type === 'regional' || c.exposure_type === 'city_conflict');
  const stay = calcStay(c.population_at_risk, c.risk_level, c.duration_days, ri, histRemainingPct, histExposure, histSiegeCap);
  const idx  = Math.min(c.duration_days, stay.fin.length) - 1;
  const mDead = stay.dead[idx] || 0;
  return {
    res,
    mDead,
    mInj:  stay.inj[idx]  || 0,
    mFin:  stay.fin[idx]  || 0,
    deathDiff: c.estimated_deaths > 0
      ? Math.abs(mDead - c.estimated_deaths) / c.estimated_deaths : 0,
  };
}

function buildEvacStatusSection(c, fullModal = false) {
  if (!c.corridor_status) return '';
  const BADGE = {
    open:        { bg: '#dcfce7', border: '#86efac', text: '#166534', label: 'OPEN' },
    partial:     { bg: '#fef9c3', border: '#fde047', text: '#854d0e', label: 'PARTIAL' },
    negotiated:  { bg: '#dbeafe', border: '#93c5fd', text: '#1e40af', label: 'NEGOTIATED' },
    closed:      { bg: '#fee2e2', border: '#fca5a5', text: '#991b1b', label: 'CLOSED' },
    forced:      { bg: '#f3f4f6', border: '#9ca3af', text: '#374151', label: 'FORCED TRANSFER' },
  };
  const b = BADGE[c.corridor_status] || BADGE.partial;
  const badge = `<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:.68rem;
    font-weight:700;letter-spacing:.05em;background:${b.bg};border:1px solid ${b.border};
    color:${b.text}">${b.label}</span>`;

  const total = c.population_at_risk || 1;
  const evRaw  = c.evacuated_count != null ? Math.round(c.evacuated_count / total * 100) : null;
  const remRaw = c.remaining_count != null ? Math.round(c.remaining_count / total * 100) : null;
  // If displaced exceeds population_at_risk (e.g. Srebrenica: regional displacement > enclave pop),
  // cap at 100% and flag with a note instead of showing a nonsensical percentage.
  const evExceeds  = c.evacuated_count  != null && c.evacuated_count  > total;
  const remExceeds = c.remaining_count  != null && c.remaining_count  > total;
  const evPct  = evExceeds  ? null : evRaw;
  const remPct = remExceeds ? null : remRaw;

  const statBox = (label, val, pct, col, exceedsNote) => `
    <div style="flex:1;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;
                padding:.4rem .6rem;text-align:center">
      <div style="font-size:.67rem;color:#64748b;margin-bottom:.1rem">${label}</div>
      <div style="font-weight:700;font-size:.82rem;color:${col}">${val != null ? fmtFull(val) : '—'}</div>
      ${pct  != null ? `<div style="font-size:.63rem;color:#94a3b8">${pct}%</div>` : ''}
      ${exceedsNote ? `<div style="font-size:.62rem;color:#94a3b8;line-height:1.3">${exceedsNote}</div>` : ''}
    </div>`;

  const noExit = (c.corridor_status === 'closed' || c.corridor_status === 'forced');
  const noExitNote = noExit ? `
    <div style="background:#fee2e2;border:1px solid #fca5a5;border-radius:5px;padding:.3rem .6rem;
                font-size:.7rem;color:#991b1b;margin-top:.4rem;line-height:1.4">
      <i class="fas fa-ban me-1"></i><strong>Routes ${c.corridor_status === 'forced' ? 'used for forced transfer' : 'closed'}:</strong>
      Evacuation cost model not applicable. Actual cost was the cost of remaining.
    </div>` : '';

  return `
    <div style="margin-top:.55rem;border-top:1px solid #e9ecef;padding-top:.45rem">
      <div style="font-size:.72rem;font-weight:700;color:#1a237e;text-transform:uppercase;
                  letter-spacing:.04em;margin-bottom:.35rem">
        <i class="fas fa-route me-1"></i>Evacuation Status
      </div>
      <div style="margin-bottom:.3rem">${badge}
        <span style="font-size:.7rem;color:#64748b;margin-left:.5rem">corridor status</span>
      </div>
      <div style="display:flex;gap:.4rem;margin:.35rem 0">
        ${statBox('Evacuated / Displaced', c.evacuated_count, evPct, '#166534',
            evExceeds ? 'includes regional pop. beyond enclave' : null)}
        ${statBox('Remained / Trapped', c.remaining_count, remPct, '#991b1b',
            remExceeds ? 'exceeds modelled at-risk population' : null)}
      </div>
      <div style="font-size:.72rem;color:#334155;line-height:1.45;margin-top:.3rem">
        ${c.corridor_notes || ''}
      </div>
      ${noExitNote}
    </div>`;
}

function buildDiscrepancyNote(c) {
  const expl = c.model_calibration?.discrepancy_explanation;
  if (!expl) return '';
  return `
    <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:5px;padding:.4rem .65rem;
                font-size:.71rem;color:#0c4a6e;line-height:1.5;margin-top:.4rem">
      <div style="font-weight:700;margin-bottom:.2rem">
        <i class="fas fa-microscope me-1"></i>Mortality Discrepancy — Research Findings
      </div>
      ${expl}
    </div>`;
}

function buildHistCalibWarn(cc, c) {
  if (cc.deathDiff <= 0.5) return '';
  const customNote = c.model_calibration?.discrepancy_explanation;
  const body = customNote
    ? customNote
    : `Discrepancy may reflect factors not captured by ERCF dimensions
       (siege conditions, disease outbreaks, deliberate targeting of civilians).`;
  return `
    <div style="background:#fffbeb;border:1px solid #fde68a;border-left:3px solid #f59e0b;
                border-radius:5px;padding:.4rem .65rem;font-size:.71rem;color:#92400e;
                line-height:1.5;margin-top:.4rem">
      <i class="fas fa-triangle-exclamation me-1"></i>
      <strong>Calibration:</strong>
      Model estimates <strong>${Math.round(cc.mDead).toLocaleString()}</strong> deaths
      vs recorded <strong>${fmtFull(c.estimated_deaths)}</strong>
      (${Math.round(cc.deathDiff * 100)}% difference).
      <div style="margin-top:.25rem">${body}</div>
    </div>`;
}

function buildDocumentedFiguresBlock(c, mDeadOverride) {
  const df = c.documented_figures;
  if (!df || df.deaths_verified === null && df.injuries_documented === null && df.displaced_documented === null) {
    return ''; // no documented data yet for this case
  }

  const rows = [];
  let ucdpBlock = '';

  // Deaths row
  if (df.deaths_verified !== null) {
    // mDeadOverride is the live ERCF model estimate (cc.mDead); fall back to c.estimated_deaths
    // only if no override provided (c.estimated_deaths is the historical documented figure, not model output)
    const modelDeathVal = mDeadOverride != null ? Math.round(mDeadOverride).toLocaleString() : (c.estimated_deaths ? c.estimated_deaths.toLocaleString() : '—');
    const verifiedDeaths = df.deaths_verified.toLocaleString();
    const range = df.deaths_estimate_range ? `<span style="color:#6b7280;font-size:.7rem"> (range: ${df.deaths_estimate_range})</span>` : '';
    rows.push(`
      <tr>
        <td style="padding:.3rem .5rem;font-weight:600;color:#374151">Deaths</td>
        <td style="padding:.3rem .5rem;color:#dc2626;font-weight:600">${modelDeathVal} <span style="font-size:.7rem;color:#6b7280">(model est.)</span></td>
        <td style="padding:.3rem .5rem;color:#16a34a;font-weight:600">${verifiedDeaths}${range} <span style="font-size:.7rem;color:#6b7280">(documented)</span></td>
      </tr>
      ${df.deaths_note ? `<tr><td colspan="3" style="padding:.1rem .5rem .4rem;font-size:.7rem;color:#6b7280;font-style:italic">${df.deaths_note}</td></tr>` : ''}
    `);
  }

  // Injuries row
  if (df.injuries_documented !== null) {
    rows.push(`
      <tr>
        <td style="padding:.3rem .5rem;font-weight:600;color:#374151">Injuries</td>
        <td style="padding:.3rem .5rem;color:#6b7280">—</td>
        <td style="padding:.3rem .5rem;color:#16a34a;font-weight:600">${df.injuries_documented.toLocaleString()} <span style="font-size:.7rem;color:#6b7280">(documented)</span></td>
      </tr>
      ${df.injuries_note ? `<tr><td colspan="3" style="padding:.1rem .5rem .4rem;font-size:.7rem;color:#6b7280;font-style:italic">${df.injuries_note}</td></tr>` : ''}
    `);
  }

  // Displaced row
  if (df.displaced_documented !== null) {
    const modelDisplaced = c.displaced ? c.displaced.toLocaleString() : '—';
    rows.push(`
      <tr>
        <td style="padding:.3rem .5rem;font-weight:600;color:#374151">Displaced</td>
        <td style="padding:.3rem .5rem;color:#dc2626;font-weight:600">${modelDisplaced} <span style="font-size:.7rem;color:#6b7280">(model/recorded)</span></td>
        <td style="padding:.3rem .5rem;color:#16a34a;font-weight:600">${df.displaced_documented.toLocaleString()} <span style="font-size:.7rem;color:#6b7280">(documented)</span></td>
      </tr>
      ${df.displaced_note ? `<tr><td colspan="3" style="padding:.1rem .5rem .4rem;font-size:.7rem;color:#6b7280;font-style:italic">${df.displaced_note}</td></tr>` : ''}
    `);
  }

  if (rows.length === 0) return '';

  // UCDP validation block
  const uv = df.ucdp_validation;
  if (uv && uv.ucdp_ged_version) {
    const matchColor = {
      'IN': '#0a6e50', '~50%': '#0a6e50', '~2x': '#d97706',
      'OUT': '#dc2626', 'NOT FOUND': '#6b7280', 'pre-1989': '#6b7280'
    }[uv.ucdp_match] || '#6b7280';

    const matchLabel = {
      'IN': '✓ Within UCDP range',
      '~50%': '~ Within 50% of UCDP best',
      '~2x': '~ Within 2× of UCDP best',
      'OUT': '✗ Outside UCDP range',
      'NOT FOUND': '— Not found in UCDP',
      'pre-1989': '— Pre-1989 (outside UCDP scope)',
    }[uv.ucdp_match] || uv.ucdp_match;

    ucdpBlock = `
      <div style="margin-top:.5rem;border:1px solid #e0e8f0;border-radius:5px;overflow:hidden">
        <div style="background:#f0f8ff;padding:.3rem .6rem;font-size:.68rem;font-weight:700;color:#003F87;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #e0e8f0">
          🔬 UCDP GED ${uv.ucdp_ged_version} Validation
        </div>
        <div style="padding:.4rem .6rem;font-size:.75rem;display:flex;gap:1rem;flex-wrap:wrap;align-items:center">
          <span><strong>Civilian deaths (floor):</strong> ${(uv.ucdp_civilian_deaths||0).toLocaleString()}</span>
          <span><strong>Total best:</strong> ${(uv.ucdp_best_total||0).toLocaleString()}</span>
          <span><strong>Range:</strong> ${uv.ucdp_range || '—'}</span>
          <span style="font-weight:700;color:${matchColor}">${matchLabel}</span>
        </div>
        ${uv.ucdp_note ? `<div style="padding:.2rem .6rem .4rem;font-size:.7rem;color:#6b7280;font-style:italic;border-top:1px solid #f0f4f8">${uv.ucdp_note}</div>` : ''}
        <div style="padding:.2rem .6rem .3rem;font-size:.65rem;color:#9ca3af;border-top:1px solid #f0f4f8">
          Source: Davies et al. (2025), Journal of Peace Research 62(4); Sundberg &amp; Melander (2013), JPR 50(4). CC BY 4.0.
        </div>
      </div>`;
  }

  return `
    <div style="margin-top:.75rem;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden">
      <div style="background:#f8fafc;padding:.4rem .6rem;font-size:.72rem;font-weight:700;color:#374151;border-bottom:1px solid #e5e7eb;text-transform:uppercase;letter-spacing:.05em">
        📊 Model vs. Documented Figures
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:.75rem">
        <thead>
          <tr style="background:#f1f5f9">
            <th style="padding:.25rem .5rem;text-align:left;color:#6b7280;font-size:.68rem">Metric</th>
            <th style="padding:.25rem .5rem;text-align:left;color:#dc2626;font-size:.68rem">ERCF Model</th>
            <th style="padding:.25rem .5rem;text-align:left;color:#16a34a;font-size:.68rem">Primary Sources</th>
          </tr>
        </thead>
        <tbody>${rows.join('')}</tbody>
      </table>
      ${ucdpBlock}
      ${df.sources ? `<div style="padding:.3rem .6rem;font-size:.65rem;color:#9ca3af;border-top:1px solid #e5e7eb">Sources: ${df.sources}</div>` : ''}
    </div>`;
}

function toggleHistCostPanel() {
  const body = document.getElementById('histCostBody');
  const chev = document.getElementById('histCostChev');
  if (!body) return;
  const nowOpen = body.style.display !== 'none';
  body.style.display = nowOpen ? 'none' : '';
  if (chev) chev.className = nowOpen
    ? 'fas fa-chevron-right' : 'fas fa-chevron-down';
}

// ═══════════════════════════════════════════════════════════
// HISTORICAL CASES TABLE
// ═══════════════════════════════════════════════════════════

function renderHistTable(filter) {
  const cases = filter
    ? state.historicalCases.filter(c => String(c.risk_level) === filter)
    : state.historicalCases;

  document.getElementById('histTableBody').innerHTML = cases.map(c => {
    const mc       = c.model_calibration || {};
    const isOos    = mc.out_of_scope    === true;
    const isChal   = mc.challenge_case  === true;
    const rowStyle = isOos ? ' style="opacity:.6"' : '';
    let badge;
    if (isChal) {
      badge = `<span class="badge rounded-pill" style="font-size:.7rem;background:#f97316;color:#fff">CHAL</span>`;
    } else if (isOos) {
      badge = `<span class="badge rounded-pill" style="font-size:.7rem;background:#9ca3af;color:#fff">OOS</span>`;
    } else {
      badge = `<span class="badge ${levelBadgeClass(c.risk_level)} rounded-pill" style="font-size:.7rem">L${c.risk_level}</span>`;
    }
    // mass_atrocity is a separate epistemic flag from OOS/CHAL/level — shown
    // alongside, never substituted for, the primary badge.
    const atrBadge = c.mass_atrocity
      ? ` <span class="badge rounded-pill" style="font-size:.7rem;background:#7f1d1d;color:#fff" title="Mass atrocity / deliberate civilian targeting — outside armed-conflict attrition model domain">ATR</span>`
      : '';
    return `
    <tr onclick="selectHistCase(${c.id})"${rowStyle}>
      <td class="ps-3">${badge}${atrBadge}</td>
      <td><strong>${c.name}</strong></td>
      <td>${c.year}</td>
      <td>${fmtFull(c.population_at_risk)}</td>
      <td>${fmtFull(c.estimated_deaths)}</td>
      <td>${c.duration_days}d</td>
      <td><span style="font-size:.7rem">${c.conflict_type.split('(')[0]}</span></td>
    </tr>`;
  }).join('');
}

function renderThreeIndexPanel(threeIndexResult, container) {
  if (!container) return;
  if (!threeIndexResult) { container.style.display = 'none'; return; }
  container.style.display = 'block';

  // Normalize keys: Python backend (historical cases) uses snake_case,
  // JS frontend calcRisk() uses camelCase. Accept either.
  const ss = threeIndexResult.subScores || threeIndexResult.sub_scores;
  const mx = threeIndexResult.matrix;
  if (!ss) { container.style.display = 'none'; return; }

  const riskSev = ss.riskSeverity || ss.risk_severity;
  const feas    = ss.feasibility;
  const infoQ   = ss.infoQuality  || ss.information_quality;

  const rSc = riskSev.score;
  const fSc = feas.score;
  const iSc = infoQ.score;

  // Use API-provided labels when available; derive from score when absent
  // (JS calcRisk() returns no label fields; Python three_index does)
  const rLbl = riskSev.label ||
    (rSc >= 4.5 ? 'Critical — imminent mass casualty risk'
     : rSc >= 3.5 ? 'High — direct threat to civilian life'
     : rSc >= 2.5 ? 'Moderate — elevated threat'
     : 'Low — not immediately threatened');
  const fLbl = feas.label ||
    (fSc >= 4.0 ? 'Good — organised corridor, manageable risk'
     : fSc >= 3.0 ? 'Viable — corridor open with significant risk'
     : fSc >= 2.0 ? 'Severely constrained — partial or contested'
     : 'Impossible — corridor blocked or non-existent');
  const iLbl = infoQ.label ||
    (iSc >= 4.0 ? 'Excellent — reliable comms and situational awareness'
     : iSc >= 3.0 ? 'Adequate — some gaps, manageable'
     : iSc >= 2.0 ? 'Poor — significant gaps and disinformation'
     : 'Blackout — no reliable channel');

  // Matrix banner
  const banner = container.querySelector('[data-role="matrixBanner"]');
  if (banner && mx) {
    banner.style.background   = (mx.color || '#94a3b8') + '18';
    banner.style.borderBottom = `2px solid ${(mx.color || '#94a3b8')}40`;
    banner.style.color        = '#1e293b';
    const icons = { 'ef4444': '🚨', 'f97316': '🛑', 'f59e0b': '🟡', '6c757d': '📋' };
    const iconKey = (mx.color || '').replace('#', '');
    banner.querySelector('[data-role="matrixIcon"]').textContent      = mx.icon || icons[iconKey] || '⚠';
    banner.querySelector('[data-role="matrixLabel"]').textContent     = mx.recommendation || mx.label || '';
    banner.querySelector('[data-role="matrixRationale"]').textContent = mx.rationale || '';
    banner.querySelector('[data-role="matrixIHL"]').textContent       = mx.ihl_trigger || mx.ihl || '';
  }

  function setBar(prefix, score, label, lowCol, highCol, midCol) {
    const bar = container.querySelector(`[data-role="${prefix}Bar"]`);
    const sEl = container.querySelector(`[data-role="${prefix}Score"]`);
    const lEl = container.querySelector(`[data-role="${prefix}Label"]`);
    if (!bar) return;
    const pct = Math.round(((score - 1) / 4) * 100);
    const col = score >= 3.5 ? highCol : score >= 2.5 ? midCol : lowCol;
    bar.style.width      = pct + '%';
    bar.style.background = col;
    if (sEl) { sEl.textContent = score.toFixed(1); sEl.style.color = col; }
    if (lEl) lEl.textContent = label;
  }

  setBar('riskSev', rSc, rLbl, '#22c55e', '#ef4444', '#f59e0b');
  setBar('feas',    fSc, fLbl, '#ef4444', '#22c55e', '#f59e0b');
  setBar('info',    iSc, iLbl, '#ef4444', '#7c3aed', '#f59e0b');
}

function selectHistCase(id) {
  const c = state.historicalCases.find(x => x.id === id);
  if (!c) return;

  const ri = c.risk_indicators;
  state.charts.radarHist.data.datasets[1].data = [
    ri.d1_kinetic, ri.d2_vulnerability, ri.d3_political,
    ri.d4_logistics, ri.d5_destination, ri.d6_urgency, ri.d7_information
  ];
  state.charts.radarHist.data.datasets[1].hidden = false;
  state.charts.radarHist.update();
  document.getElementById('radarHistLabel').textContent =
    `Red = current scenario · Blue = ${c.name} (${c.year})`;

  document.getElementById('caseDetailCard').style.display = 'block';
  document.getElementById('caseDetailTitle').innerHTML =
    `<div class="d-flex align-items-center justify-content-between w-100">
       <span><span class="badge ${levelBadgeClass(c.risk_level)} me-1">L${c.risk_level}</span> ${c.name} (${c.year})</span>
       <button onclick="useHistCaseAsScenario(${c.id})" class="btn btn-sm btn-outline-secondary" style="font-size:.7rem;padding:2px 8px;white-space:nowrap;flex-shrink:0;margin-left:.5rem">↗ Use as Scenario</button>
     </div>`;

  renderThreeIndexPanel(c.three_index, document.getElementById('histThreeIndexPanel'));

  // Compute ERCF model estimates using case's own population and risk level
  const cc = computeHistCaseCosts(c);

  const costSection = `
    <div style="margin-top:.55rem;border-top:1px solid #e9ecef;padding-top:.45rem">
      <button onclick="toggleHistCostPanel()"
              style="width:100%;text-align:left;padding:.3rem .5rem;
                     background:#f0f4ff;border:1px solid #c7d7f8;border-radius:5px;
                     font-size:.72rem;font-weight:800;color:#1a237e;cursor:pointer;
                     display:flex;align-items:center;justify-content:space-between;
                     letter-spacing:.03em;text-transform:uppercase">
        <span><i class="fas fa-calculator me-1"></i>ERCF Cost Estimates (model-derived)</span>
        <i class="fas fa-chevron-down" id="histCostChev" style="font-size:.6rem"></i>
      </button>
      <div id="histCostBody" style="padding-top:.4rem">
        <div style="font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;
                    color:#475569;margin-bottom:.3rem">
          Evacuation Resources — if evacuated on day 1
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:.3rem;margin-bottom:.35rem">
          ${costStatMini('Vehicles',   fmtFull(cc.res.vehicles.total))}
          ${costStatMini('Personnel',  fmtFull(cc.res.personnel.total))}
          ${costStatMini('Evac. Cost', '$'+fmt(cc.res.totalCost))}
          ${costStatMini('Cost/Person','$'+fmt(cc.res.cpp))}
        </div>
        <div style="font-size:.67rem;color:#94a3b8;margin-bottom:.45rem">
          ${cc.res.vehicles.stdBus} std · ${cc.res.vehicles.medBus} med. buses ·
          ${cc.res.vehicles.ambu} ambulances
          &nbsp;·&nbsp; ${c.vulnerable_pct ?? 20}% vulnerable · ${fmtDist(c.distance_km ?? 50)}
        </div>
        <div style="font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;
                    color:#475569;margin-bottom:.3rem">
          Cost of Remaining — actual duration: ${c.duration_days} days
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:.3rem;margin-bottom:.3rem">
          ${costStatMini('Financial',            '$'+fmt(cc.mFin))}
          ${costStatMini('Est. Deaths (model)',  Math.round(cc.mDead).toLocaleString())}
          ${costStatMini('Recorded Deaths',      fmtFull(c.estimated_deaths))}
          ${costStatMini('Est. Injuries',        Math.round(cc.mInj).toLocaleString(), 'model est.')}
        </div>
        ${buildHistCalibWarn(cc, c)}
        ${buildDocumentedFiguresBlock(c, cc.mDead)}
        <div style="font-size:.63rem;color:#94a3b8;margin-top:.4rem;line-height:1.45;
                    border-top:1px solid #f1f5f9;padding-top:.3rem">
          <span class="conf-dot conf-estimated"
                style="display:inline-block;vertical-align:middle;margin-right:.25rem"></span>
          All figures are ERCF model estimates computed from dimension scores and population data.
          They do not represent actual recorded expenditures or verified casualty counts.
        </div>
      </div>
    </div>`;

  document.getElementById('caseDetailBody').innerHTML = `
    <div style="font-size:.78rem">
      <div class="mb-2">
        <strong>Population:</strong> ${fmtFull(c.population_at_risk)} &nbsp;|&nbsp;
        <strong>Deaths:</strong> ${fmtFull(c.estimated_deaths)} &nbsp;|&nbsp;
        <strong>Displaced:</strong> ${fmtFull(c.displaced)}
      </div>
      <div class="mb-2"><strong>Duration:</strong> ${c.duration_days} days &nbsp;|&nbsp; <strong>Type:</strong> ${c.conflict_type}</div>
      <strong>Key Lessons:</strong>
      <ul class="mt-1 ps-3">${c.key_lessons.map(l => `<li>${l}</li>`).join('')}</ul>
      <div class="mt-1"><strong>IHL Issues:</strong>
        ${c.ihl_issues.map(i => `<span class="badge bg-light text-dark me-1 modal-ihl-badge">${i}</span>`).join('')}
      </div>
      <div class="mt-2 text-muted" style="font-size:.68rem">Source: ${c.source}</div>
      ${costSection}
      ${buildEvacStatusSection(c)}
    </div>
  `;
}

function useHistCaseAsScenario(id) {
  const c = state.historicalCases.find(x => x.id === id);
  if (!c) return;
  const ri = c.risk_indicators;

  const nameEl = document.getElementById('scenName');
  if (nameEl) nameEl.value = `[Historical] ${c.name}`;

  state.population = c.population_at_risk;
  const popEl = document.getElementById('inPop');
  if (popEl) popEl.value = c.population_at_risk;

  const days = Math.min(c.duration_days ?? 30, 180);
  state.days = days;
  const daysEl = document.getElementById('stayDays');
  if (daysEl) { daysEl.value = days; daysEl.style.accentColor = days > 90 ? '#94a3b8' : '#ef4444'; }
  const daysValEl = document.getElementById('stayDaysVal');
  if (daysValEl) daysValEl.textContent = days + ' days';
  const daysWarnEl = document.getElementById('daysWarn');
  if (daysWarnEl) daysWarnEl.style.display = days > 90 ? 'block' : 'none';

  const EXPOSURE_TO_PATTERN = { urban_siege: 1, enclave: 2, city_conflict: 3, regional: 4 };
  const pattern = EXPOSURE_TO_PATTERN[c.exposure_type] ?? 5;
  state.conflictType = pattern;
  const patternEl = document.getElementById('inConflictPattern');
  if (patternEl) patternEl.value = pattern;

  const dimMap = {
    d1: ri.d1_kinetic,       d2: ri.d2_vulnerability, d3: ri.d3_political,
    d4: ri.d4_logistics,     d5: ri.d5_destination,   d6: ri.d6_urgency,
    d7: ri.d7_information,
  };
  for (const [k, v] of Object.entries(dimMap)) {
    if (v == null) continue;
    state.dims[k] = v;
    const el = document.getElementById(k);
    if (el) el.value = v;
    const vEl = document.getElementById(k + 'v');
    if (vEl) vEl.textContent = (+v).toFixed(1);
  }

  document.querySelector('[href="#paneBuilder"]').click();
  updateAll();
  showToast(`Scenario loaded: ${c.name} (${c.year})`);
}

function openCaseModal(id) {
  const c = state.historicalCases.find(x => x.id === id);
  if (!c) return;

  // Compute ERCF model estimates for the full modal view
  const cc = computeHistCaseCosts(c);

  document.getElementById('modalTitle').innerHTML =
    `<span class="badge ${levelBadgeClass(c.risk_level)} me-2">LEVEL ${c.risk_level}</span>${c.name} — ${c.year}`;
  document.getElementById('modalBody').innerHTML = `
    <div class="row g-3">
      <div class="col-md-6">
        <h6 class="fw-bold">Overview</h6>
        <table class="table table-sm table-bordered" style="font-size:.8rem">
          <tr><td>Conflict Type</td><td>${c.conflict_type}</td></tr>
          <tr><td>Population at Risk</td><td>${fmtFull(c.population_at_risk)}</td></tr>
          <tr><td>Estimated Deaths</td><td>${fmtFull(c.estimated_deaths)}</td></tr>
          <tr><td>Displaced</td><td>${fmtFull(c.displaced)}</td></tr>
          <tr><td>Duration</td><td>${c.duration_days} days</td></tr>
          <tr><td>Risk Level</td><td><span class="badge ${levelBadgeClass(c.risk_level)}">L${c.risk_level} — ${RISK_DEF[c.risk_level].label}</span></td></tr>
        </table>
        <h6 class="fw-bold mt-3">Dimension Scores</h6>
        <table class="table table-sm" style="font-size:.78rem">
          ${[
            ['D1 Kinetic Threat', c.risk_indicators.d1_kinetic],
            ['D2 Vulnerability',  c.risk_indicators.d2_vulnerability],
            ['D3 Authorization',  c.risk_indicators.d3_political],
            ['D4 Logistics',      c.risk_indicators.d4_logistics],
            ['D5 Destination',    c.risk_indicators.d5_destination],
            ['D6 Urgency',        c.risk_indicators.d6_urgency],
            ['D7 Information',    c.risk_indicators.d7_information],
          ].map(([lbl, val]) => `<tr><td>${lbl}</td><td>
            <div class="d-flex align-items-center gap-2">
              <div style="flex:1;height:8px;background:#eee;border-radius:4px">
                <div style="width:${(val-1)/4*100}%;height:100%;background:#ef4444;border-radius:4px"></div>
              </div>
              <span style="font-weight:700">${val}</span>
            </div></td></tr>`).join('')}
        </table>
      </div>
      <div class="col-md-6">
        <h6 class="fw-bold">Key Lessons</h6>
        <ul class="modal-lesson ps-3">${c.key_lessons.map(l => `<li>${l}</li>`).join('')}</ul>
        <h6 class="fw-bold mt-3">IHL Issues</h6>
        <div>${c.ihl_issues.map(i => `<span class="badge bg-secondary me-1 mb-1 modal-ihl-badge">${i}</span>`).join('')}</div>
        <h6 class="fw-bold mt-3">Source</h6>
        <p style="font-size:.78rem">${c.source}</p>
        <div class="alert alert-warning py-2" style="font-size:.75rem">
          <i class="fas fa-balance-scale me-1"></i>
          <strong>IHL Classification:</strong> ${RISK_DEF[c.risk_level].ihl}
        </div>

        <!-- ERCF Cost Estimates (model-derived) -->
        <h6 class="fw-bold mt-3" style="color:#1a237e">
          <i class="fas fa-calculator me-1"></i>ERCF Cost Estimates
          <span style="font-weight:400;font-size:.72rem;color:#94a3b8"> (model-derived)</span>
        </h6>
        <div style="font-size:.7rem;color:#64748b;margin-bottom:.4rem">
          ${c.vulnerable_pct ?? 20}% vulnerable · ${fmtDist(c.distance_km ?? 50)} distance (researched)
        </div>
        <table class="table table-sm" style="font-size:.77rem">
          <tr><td>Vehicles</td>
              <td><strong>${fmtFull(cc.res.vehicles.total)}</strong>
                  <span style="color:#94a3b8;font-size:.68rem">
                    (${cc.res.vehicles.stdBus} std · ${cc.res.vehicles.medBus} med · ${cc.res.vehicles.ambu} ambu)
                  </span></td></tr>
          <tr><td>Personnel</td><td><strong>${fmtFull(cc.res.personnel.total)}</strong></td></tr>
          <tr><td>Total Evac. Cost</td>
              <td><strong>$${fmt(cc.res.totalCost)}</strong>
                  <span style="color:#94a3b8;font-size:.68rem"> ($${fmt(cc.res.cpp)}/person)</span></td></tr>
          <tr><td>Financial (${c.duration_days}d staying)</td><td><strong>$${fmt(cc.mFin)}</strong></td></tr>
          <tr><td>Est. Deaths (model)</td>
              <td><strong>${Math.round(cc.mDead).toLocaleString()}</strong>
                  <span style="color:#94a3b8;font-size:.68rem"> vs recorded ${fmtFull(c.estimated_deaths)}</span></td></tr>
          <tr><td>Est. Injuries</td><td><strong>${Math.round(cc.mInj).toLocaleString()}</strong></td></tr>
        </table>
        ${buildHistCalibWarn(cc, c)}
        ${buildDiscrepancyNote(c)}
        <div style="font-size:.63rem;color:#94a3b8;margin-top:.4rem;line-height:1.4">
          <span class="conf-dot conf-estimated"
                style="display:inline-block;vertical-align:middle;margin-right:.25rem"></span>
          Model estimates only — not actual recorded expenditures or verified casualty counts.
        </div>
      </div>
      <div class="col-12 mt-3">
        ${buildEvacStatusSection(c, true)}
      </div>
    </div>
  `;
  new bootstrap.Modal(document.getElementById('caseModal')).show();
}

// ═══════════════════════════════════════════════════════════
// SAVED SCENARIOS
// ═══════════════════════════════════════════════════════════

async function saveScenario() {
  const body = {
    name:             document.getElementById('scenName').value || 'Unnamed',
    description:      document.getElementById('scenDesc').value || '',
    population:       state.population,
    vulnerable_pct:   state.vulnerablePct,
    distance_km:      state.distanceKm,
    terrain:          state.terrain,
    conflict_pattern: state.conflictType,
    d1_kinetic:       state.dims.d1,
    d2_vulnerability: state.dims.d2,
    d3_political:     state.dims.d3,
    d4_logistics:     state.dims.d4,
    d5_destination:   state.dims.d5,
    d6_urgency:       state.dims.d6,
    d7_information:   state.dims.d7,
    conflict_lat:        state.conflictCoords?.lat ?? null,
    conflict_lng:        state.conflictCoords?.lng ?? null,
    safe_zone_lat:       state.safeZoneCoords?.lat ?? null,
    safe_zone_lng:       state.safeZoneCoords?.lng ?? null,
    safe_zone_name:      state.safeZoneCoords?.name ?? null,
    distance_source:     state.distanceSource,
    road_factor_applied: state.roadFactorApplied,
    haversine_km:        state._haversineKm ?? null,
  };
  try {
    const res = await fetch('/api/scenarios', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    showToast('Scenario saved successfully!');
    populateCompareDropdown();
  } catch(e) {
    showToast('Error saving: '+e.message, 'danger');
  }
}

async function loadSavedScenarios() {
  try {
    const scenarios = await fetch('/api/scenarios').then(r => r.json());
    const grid = document.getElementById('savedGrid');
    if (!scenarios.length) {
      grid.innerHTML = '<div class="col-12 text-muted text-center py-4">No scenarios saved yet.</div>';
      return;
    }
    grid.innerHTML = scenarios.map(s => {
      const lvl = s.risk_level ?? 0;
      return `
      <div class="col-md-4 col-lg-3">
        <div class="card sc-card" onclick="loadScenario(${s.id})">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <div class="fw-bold" style="font-size:.85rem">${s.name}</div>
                <div class="text-muted" style="font-size:.72rem">${s.created_at ? s.created_at.slice(0,10) : ''}</div>
              </div>
              <span class="badge ${levelBadgeClass(lvl)}">L${lvl}</span>
            </div>
            <div class="mt-2" style="font-size:.75rem">
              <span class="text-muted">Pop:</span> ${fmtFull(s.population)} &nbsp;
              <span class="text-muted">Score:</span> ${s.risk_score ?? '—'}
              ${s.distance_source === 'ai_suggested' ? '<div style="font-size:.67rem;color:#166534;margin-top:.15rem">✅ AI suggested route</div>' : s.distance_source === 'map_pin' ? '<div style="font-size:.67rem;color:#0369a1;margin-top:.15rem"><i class="fas fa-map-pin me-1"></i>Map pin route</div>' : ''}
              ${s.conflict_pattern && s.conflict_pattern !== 5 ? `<div style="font-size:.67rem;color:#7c3aed;margin-top:.1rem"><i class="fas fa-crosshairs me-1"></i>${['','Urban Siege','Enclave','City Conflict','Regional','Auto'][s.conflict_pattern]}</div>` : ''}
            </div>
            <div class="mt-2 d-flex gap-1">
              <button class="btn btn-sm btn-outline-primary" style="font-size:.72rem"
                onclick="event.stopPropagation();loadScenario(${s.id})">Load</button>
              <button class="btn btn-sm btn-outline-danger" style="font-size:.72rem"
                onclick="event.stopPropagation();deleteScenario(${s.id})">Delete</button>
            </div>
          </div>
        </div>
      </div>`;
    }).join('');
  } catch(e) {
    showToast('Error loading scenarios', 'danger');
  }
}

async function loadScenario(id) {
  try {
    const s = await fetch(`/api/scenarios/${id}`).then(r => r.json());
    document.getElementById('scenName').value = s.name;
    document.getElementById('scenDesc').value = s.description || '';
    document.getElementById('inPop').value    = s.population;
    document.getElementById('inVuln').value   = s.vulnerable_pct;
    document.getElementById('inDist').value   = toDisplayUnit(s.distance_km);
    state.population    = s.population;
    state.vulnerablePct = s.vulnerable_pct;
    state.distanceKm    = s.distance_km;
    state.terrain       = s.terrain ?? 3;
    state.conflictType  = s.conflict_pattern ?? 5;
    document.getElementById('inTerrain').value        = state.terrain;
    document.getElementById('inConflictPattern').value = state.conflictType;
    state.conflictCoords    = (s.conflict_lat != null && s.conflict_lng != null)
      ? { lat: s.conflict_lat, lng: s.conflict_lng } : null;
    state.safeZoneCoords    = (s.safe_zone_lat != null && s.safe_zone_lng != null)
      ? { lat: s.safe_zone_lat, lng: s.safe_zone_lng, name: s.safe_zone_name || 'Safe zone' } : null;
    state.distanceSource    = s.distance_source || 'manual';
    state.roadFactorApplied = !!s.road_factor_applied;
    state._aiSuggestedSafeZone = null;
    state._haversineKm      = s.haversine_km ?? null;
    const rfToggle = document.getElementById('roadFactorToggle');
    if (rfToggle) rfToggle.checked = state.roadFactorApplied;
    updateDistanceLabel();
    updateDistanceDisplay();
    updatePinLayerOnWorldMap();
    const map = {
      d1: s.d1_kinetic, d2: s.d2_vulnerability, d3: s.d3_political,
      d4: s.d4_logistics, d5: s.d5_destination, d6: s.d6_urgency, d7: s.d7_information,
    };
    for (const [k, v] of Object.entries(map)) {
      state.dims[k] = v;
      document.getElementById(k).value = v;
      document.getElementById(k+'v').textContent = (+v).toFixed(1);
    }
    document.querySelector('[href="#paneBuilder"]').click();
    updateAll();
    showToast(`Loaded: ${s.name}`);
  } catch(e) {
    showToast('Error loading scenario', 'danger');
  }
}

async function deleteScenario(id) {
  if (!confirm('Delete this scenario?')) return;
  try {
    await fetch(`/api/scenarios/${id}`, { method: 'DELETE' });
    loadSavedScenarios();
    populateCompareDropdown();
    showToast('Scenario deleted', 'warning');
  } catch(e) {
    showToast('Error deleting', 'danger');
  }
}

// Fetch world risk data if not yet loaded (needed before the Map View tab is opened).
async function ensureWorldRiskLoaded() {
  if (Object.keys(worldMapState.worldRisk).length > 0) return;
  try {
    worldMapState.worldRisk = await fetch('/api/world-risk').then(r => r.json());
  } catch(e) {
    console.error('Failed to load world risk data for suggestions:', e);
  }
}

// Compute and render AI suggestions. Awaits world risk data if needed.
// Called whenever the conflict pin is placed or dragged.
async function _runAiSuggestion(lat, lng) {
  await ensureWorldRiskLoaded();
  const suggs = suggestSafeZones(lat, lng);
  pinMapState.suggestions = suggs;
  _renderSuggestions(suggs);
  state._aiSuggestedSafeZone = suggs.length ? suggs[0] : null;
  _updatePinConfirmBtn();
  document.getElementById('pinInstrText').textContent =
    suggs.length
      ? 'Conflict pin set. Select a suggested safe zone (green) or search manually below.'
      : 'Conflict pin set. Click the map or search for a safe zone below.';
}

function resetSliders() {
  DIM_KEYS.forEach(k => {
    state.dims[k] = 3;
    document.getElementById(k).value = 3;
    document.getElementById(k+'v').textContent = '3.0';
  });
  state.conflictCoords        = null;
  state.safeZoneCoords        = null;
  state.distanceSource        = 'manual';
  state.roadFactorApplied     = false;
  state._haversineKm          = null;
  state._aiSuggestedSafeZone  = null;
  const rfToggle = document.getElementById('roadFactorToggle');
  if (rfToggle) rfToggle.checked = false;
  updateDistanceLabel();
  updateDistanceDisplay();
  const inDist = document.getElementById('inDist');
  if (inDist) inDist.value = toDisplayUnit(50);
  state.distanceKm = 50;
  updatePinLayerOnWorldMap();
  updateAll();
}

// ═══════════════════════════════════════════════════════════
// WEIGHTS TRANSPARENCY PANEL
// ═══════════════════════════════════════════════════════════

function toggleWeightsPanel() {
  const panel = document.getElementById('weightsPanel');
  const btn   = document.getElementById('wtToggleBtn');
  if (!panel) return;
  const opening = panel.style.display === 'none';
  panel.style.display = opening ? '' : 'none';
  if (btn) btn.classList.toggle('active', opening);
  if (opening) updateWeightsPanel();
}

function updateWeightsPanel() {
  const panel = document.getElementById('weightsPanel');
  if (!panel || panel.style.display === 'none') return;
  const body = document.getElementById('weightsPanelBody');
  if (!body) return;

  function escAttr(s) {
    return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  const dims = state.dims;
  let totalWeighted = 0;
  const rowData = DIM_KEYS.map(k => {
    const w  = WEIGHTS[k];
    const v  = dims[k];
    const ws = v * w;
    totalWeighted += ws;
    return { k, w, v, ws };
  });

  const risk      = calcRisk(dims);  // re-uses shared formula including hard-trigger logic
  const triggered = dims.d1 >= 4.5 && dims.d6 >= 4.5;
  const finalScore = triggered ? Math.max(totalWeighted, 4.21) : totalWeighted;

  // ── Table rows ────────────────────────────────────────────────────────
  const tableRows = rowData.map(({ k, w, v, ws }) => {
    const meta     = WEIGHT_META[k];
    const pctTotal = totalWeighted > 0 ? Math.round(ws / totalWeighted * 100) : 0;
    const barPct   = Math.round(v / 5 * 100);  // 20% at min (1), 100% at max (5)
    const tip      = escAttr(meta.rationale + ' — Source: ' + meta.source);
    return `<tr>
      <td style="white-space:nowrap">${meta.name}</td>
      <td class="text-center" style="white-space:nowrap">
        <span class="conf-dot conf-unvalidated"
              data-bs-toggle="tooltip" data-bs-placement="top"
              data-bs-title="Estimated — no peer-reviewed IHL weighting framework published"
              style="display:inline-block;vertical-align:middle;cursor:help"></span>
        <span style="margin-left:.2rem">${(w * 100).toFixed(0)}%</span>
        <button class="dim-help-btn ms-1" data-bs-toggle="tooltip"
                data-bs-placement="right" data-bs-title="${tip}"
                onclick="event.stopPropagation()">?</button>
      </td>
      <td class="text-center fw-semibold">${v.toFixed(1)}</td>
      <td>
        <div style="display:flex;align-items:center;gap:.35rem">
          <span style="min-width:2.9rem;text-align:right;font-weight:600">${ws.toFixed(3)}</span>
          <div class="wt-bar"><div class="wt-bar-fill" style="width:${barPct}%"></div></div>
        </div>
      </td>
      <td class="text-center">${pctTotal}%</td>
    </tr>`;
  }).join('');

  const totalRow = `<tr>
    <td><strong>TOTAL</strong></td>
    <td class="text-center"><strong>100%</strong></td>
    <td></td>
    <td><span style="padding-left:.2rem;font-weight:800">${totalWeighted.toFixed(3)}</span></td>
    <td class="text-center"><strong>100%</strong></td>
  </tr>`;

  // ── Score / level / next threshold line ───────────────────────────────
  const nextR       = RISK_DEF.find(r => r.level === risk.level + 1);
  const distToNext  = nextR ? (nextR.max - finalScore).toFixed(3) : null;
  let scoreLine = `<div class="wt-score-line">
    <i class="fas fa-calculator me-1" style="opacity:.55"></i>
    Weighted sum: <strong>${totalWeighted.toFixed(3)}</strong>`;
  if (triggered) {
    scoreLine += ` → hard-trigger floor: <strong>${finalScore.toFixed(3)}</strong>`;
  }
  scoreLine += ` → <span class="badge" style="background:${risk.color};color:${risk.text || '#fff'};font-size:.7rem">
      L${risk.level} — ${risk.label}</span>`;
  if (nextR) {
    scoreLine += `<br><span style="color:#64748b;font-size:.7rem">
      Next: ≤${nextR.max} → L${nextR.level} (${nextR.label})
      &nbsp;·&nbsp; <strong>${distToNext}</strong> points away</span>`;
  } else {
    scoreLine += `<br><span style="color:#94a3b8;font-size:.7rem">Maximum level reached</span>`;
  }
  scoreLine += `</div>`;

  // ── Hard trigger status line ──────────────────────────────────────────
  const d1 = dims.d1, d6 = dims.d6;
  const d1gap = Math.max(0, 4.5 - d1).toFixed(1);
  const d6gap = Math.max(0, 4.5 - d6).toFixed(1);
  const approaching = !triggered && d1 >= 4.0 && d6 >= 4.0;
  let triggerLine;
  if (triggered) {
    triggerLine = `<div class="wt-trigger wt-trigger-warn">
      <i class="fas fa-triangle-exclamation me-1"></i>
      <strong>Hard trigger active:</strong> D1=${d1.toFixed(1)} ≥ 4.5 <em>and</em>
      D6=${d6.toFixed(1)} ≥ 4.5 → Level 4 forced regardless of weighted score.
      Weighted sum ${totalWeighted.toFixed(3)} overridden; final score floored to 4.21.
    </div>`;
  } else if (approaching) {
    triggerLine = `<div class="wt-trigger wt-trigger-warn">
      <i class="fas fa-triangle-exclamation me-1"></i>
      <strong>Hard trigger approaching.</strong>
      Requires <em>both</em> D1 ≥ 4.5 and D6 ≥ 4.5.
      Currently: D1 needs +${d1gap}, D6 needs +${d6gap} to activate Level 4 override.
    </div>`;
  } else {
    triggerLine = `<div class="wt-trigger wt-trigger-ok">
      <i class="fas fa-circle-check me-1"></i>
      <strong>No hard trigger active.</strong>
      Trigger requires <em>both</em> D1 ≥ 4.5 and D6 ≥ 4.5
      (D1 needs +${d1gap}, D6 needs +${d6gap}).
    </div>`;
  }

  body.innerHTML = `
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:.45rem .55rem;
                margin-bottom:.35rem;overflow-x:auto">
      <table class="wt-table">
        <thead><tr>
          <th>Dimension</th>
          <th class="text-center">Weight</th>
          <th class="text-center">Current Value</th>
          <th>Weighted Score</th>
          <th class="text-center">% of Total</th>
        </tr></thead>
        <tbody>${tableRows}${totalRow}</tbody>
      </table>
    </div>
    ${scoreLine}
    ${triggerLine}
    <div class="wt-disclaimer">
      <span class="conf-dot conf-unvalidated" style="display:inline-block;vertical-align:middle;margin-right:.3rem"></span>
      All weights are modelled estimates. No published IHL or humanitarian operations framework
      specifies explicit numerical weights for these dimensions. Validation against an expert panel
      or empirical conflict data is required before operational use.
    </div>`;

  reinitTooltips(body);
}

// ═══════════════════════════════════════════════════════════
// COMPARE DROPDOWN + COST COMPARISON PANEL
// ═══════════════════════════════════════════════════════════

async function populateCompareDropdown() {
  try {
    state.savedScenarios = await fetch('/api/scenarios').then(r => r.json());
  } catch(e) {
    state.savedScenarios = [];
  }

  const histOpts = state.historicalCases.map(c =>
    `<option value="hist-${c.id}">[Historical] ${c.name} (${c.year})</option>`
  ).join('');

  const savedOpts = state.savedScenarios.map(s =>
    `<option value="saved-${s.id}">[Saved] ${s.name}</option>`
  ).join('');

  const sel = document.getElementById('compareCase');
  sel.innerHTML =
    '<option value="">— none —</option>' +
    (histOpts  ? `<optgroup label="Historical Cases">${histOpts}</optgroup>`   : '') +
    (savedOpts ? `<optgroup label="Saved Scenarios">${savedOpts}</optgroup>` : '');
}

function toggleCostComparePanel() {
  const body = document.getElementById('cmpBody');
  const chev = document.getElementById('cmpChev');
  const wasCollapsed = body.style.display === 'none';
  body.style.display = wasCollapsed ? '' : 'none';
  chev.className = wasCollapsed ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
  if (wasCollapsed) renderCostComparePanel();
}

function renderCostComparePanel() {
  const panel = document.getElementById('costComparePanel');
  if (!panel) return;

  if (!state.comparisonData || !state._lastResources || !state._lastRisk) {
    panel.style.display = 'none';
    return;
  }

  panel.style.display = 'block';
  const body = document.getElementById('cmpBody');
  if (!body) return;
  if (body.style.display === 'none') {
    body.style.display = '';
    const chev = document.getElementById('cmpChev');
    if (chev) chev.className = 'fas fa-chevron-down';
  }

  const curr = state._lastResources;
  const risk = state._lastRisk;
  const stay = state._lastStayData;
  const comp = state.comparisonData;

  // Index into stay arrays (0-based; day N → index N-1)
  const currIdx = Math.min(state.days, stay.fin.length) - 1;
  const compIdx = Math.min(comp.days, comp.stayData.fin.length) - 1;
  const currFin  = stay.fin[currIdx]  || 0;
  const currDead = stay.dead[currIdx] || 0;
  const currInj  = stay.inj[currIdx]  || 0;
  const compFin  = comp.stayData.fin[compIdx]  || 0;
  const compDead = comp.stayData.dead[compIdx] || 0;
  const compInj  = comp.stayData.inj[compIdx]  || 0;

  // Delta tag appended to the comparison column value.
  // Positive pct = current is higher; negative = current is lower.
  // lowerIsBetter=true → green when current < comparison (cheaper / fewer casualties).
  function dt(cVal, compVal, lowerIsBetter = true) {
    if (compVal == null || compVal === 0 || cVal == null) return '';
    const pct    = (cVal - compVal) / Math.abs(compVal) * 100;
    if (Math.abs(pct) < 1) return `<span style="color:#94a3b8;font-size:.6rem;margin-left:.25rem">≈</span>`;
    const better = lowerIsBetter ? cVal < compVal : cVal > compVal;
    const color  = better ? '#22c55e' : '#ef4444';
    const arrow  = cVal < compVal ? '↓' : '↑';
    const sign   = pct > 0 ? '+' : '';
    return `<span style="color:${color};font-size:.62rem;font-weight:700;margin-left:.3rem"
                  title="Current scenario is ${sign}${Math.round(pct)}% vs this case"
            >${arrow}${sign}${Math.round(pct)}%</span>`;
  }

  const compRiskDef = RISK_DEF[comp.riskLevel] || RISK_DEF[0];
  const distNote    = comp.isHistorical
    ? `<span style="color:#f59e0b;font-size:.6rem;margin-left:.2rem"
             title="Uses current scenario distance — historical evacuation distance unknown">*assumed</span>` : '';

  // Each metric: [label, currentVal, comparisonVal, deltaTag]
  // No delta on Population/Distance/RiskLevel/Days — these are inputs, not performance metrics.
  const metrics = [
    ['Population',
      fmtFull(state.population),
      fmtFull(comp.pop), ''],
    ['Distance',
      fmtDist(state.distanceKm),
      fmtDist(comp.distKm), distNote],
    ['Risk Level',
      `<span class="badge lbadge-${risk.level}" style="font-size:.63rem">L${risk.level} — ${risk.label}</span>`,
      `<span class="badge lbadge-${comp.riskLevel}" style="font-size:.63rem">L${comp.riskLevel} — ${compRiskDef.label}</span>`, ''],
    ['Days modelled',
      `${state.days} d`,
      `${comp.days} d`, ''],
    ['Vehicles',
      fmtFull(curr.vehicles.total),
      fmtFull(comp.resources.vehicles.total),
      dt(curr.vehicles.total, comp.resources.vehicles.total)],
    ['Personnel',
      fmtFull(curr.personnel.total),
      fmtFull(comp.resources.personnel.total),
      dt(curr.personnel.total, comp.resources.personnel.total)],
    ['Total Evac. Cost',
      `<span class="conf-dot conf-estimated" style="display:inline-block;vertical-align:middle;margin-right:.2rem"></span>$${fmt(curr.totalCost)}`,
      `<span class="conf-dot conf-estimated" style="display:inline-block;vertical-align:middle;margin-right:.2rem"></span>$${fmt(comp.resources.totalCost)}`,
      dt(curr.totalCost, comp.resources.totalCost)],
    ['Cost / Person',
      `$${fmt(curr.cpp)}`,
      `$${fmt(comp.resources.cpp)}`,
      dt(curr.cpp, comp.resources.cpp)],
    ['Financial cost (remaining)',
      `$${fmt(currFin)} <span style="color:#94a3b8;font-size:.6rem">(${state.days}d)</span>`,
      `$${fmt(compFin)} <span style="color:#94a3b8;font-size:.6rem">(${comp.days}d)</span>`,
      dt(currFin, compFin)],
    ['Est. Deaths — model',
      `${currDead.toFixed(1)} <span style="color:#94a3b8;font-size:.6rem">(${state.days}d)</span>`,
      `${compDead.toFixed(1)} <span style="color:#94a3b8;font-size:.6rem">(${comp.days}d)</span>`,
      dt(currDead, compDead)],
    ...(comp.isHistorical && comp.historicalDeaths != null ? [[
      'Recorded Deaths (actual)',
      '<span style="color:#94a3b8;font-size:.7rem">no historical record</span>',
      `<strong style="color:#dc2626">${fmtFull(comp.historicalDeaths)}</strong>`
        + ` <span style="color:#94a3b8;font-size:.6rem">(${comp.days}d verified)</span>`,
      '',
    ]] : []),
    ['Est. Injuries (remaining)',
      `${currInj.toFixed(1)} <span style="color:#94a3b8;font-size:.6rem">(${state.days}d)</span>`,
      `${compInj.toFixed(1)} <span style="color:#94a3b8;font-size:.6rem">(${comp.days}d)</span>`,
      dt(currInj, compInj)],
  ];

  const headerRow = `
    <div class="cmp-row" style="background:#f8fafc;border-bottom:2px solid #e2e8f0">
      <span class="cmp-row-lbl" style="font-size:.66rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:#475569">Metric</span>
      <span class="cmp-col cmp-col-curr" style="font-size:.66rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:#1a237e">Current Scenario</span>
      <span class="cmp-col" style="font-size:.66rem;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:#0369a1;max-width:9rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
            title="${comp.label}">${comp.label}</span>
    </div>`;

  const dataRows = metrics.map(([lbl, cVal, compVal, delta]) => `
    <div class="cmp-row">
      <span class="cmp-row-lbl">${lbl}</span>
      <span class="cmp-col cmp-col-curr">${cVal}</span>
      <span class="cmp-col">${compVal}${delta}</span>
    </div>`).join('');

  // Calibration warning: computed deaths vs historical record (historical cases only)
  let calibWarn = '';
  if (comp.isHistorical && comp.historicalDeaths != null && comp.historicalDeaths > 0 && compDead > 0) {
    const diff = Math.abs(compDead - comp.historicalDeaths) / comp.historicalDeaths;
    if (diff > 0.5) {
      calibWarn = `
        <div class="cmp-warn mt-2">
          <i class="fas fa-triangle-exclamation me-1"></i>
          <strong>Calibration note:</strong>
          Model estimate (${Math.round(compDead).toLocaleString()} deaths) differs from historical record
          (${fmtFull(comp.historicalDeaths)} deaths) by ${Math.round(diff * 100)}%.
          Historical context may include factors not captured by ERCF dimensions —
          siege attrition, targeted killings, healthcare collapse, or disease outbreaks.
          Model mortality rates are calibrated to typical armed conflict patterns; extreme cases will diverge.
        </div>`;
    }
  }

  // UCDP validation block (historical cases only)
  let ucdpCompBlock = '';
  if (comp.isHistorical) {
    const uv = comp.ucdpValidation;
    if (uv && uv.ucdp_ged_version) {
      const matchColor = {
        'IN': '#0a6e50', '~50%': '#0a6e50', '~2x': '#d97706',
        'OUT': '#dc2626', 'NOT FOUND': '#6b7280', 'pre-1989': '#6b7280',
      }[uv.ucdp_match] || '#6b7280';
      const matchLabel = {
        'IN':        '✓ Within UCDP range',
        '~50%':      '~ Within 50% of UCDP best',
        '~2x':       '~ Within 2× of UCDP best',
        'OUT':       '✗ Outside UCDP range',
        'NOT FOUND': '— Not found in UCDP',
        'pre-1989':  '— Pre-1989 (outside UCDP scope)',
      }[uv.ucdp_match] || uv.ucdp_match;
      ucdpCompBlock = `
        <div style="margin-top:.5rem;border:1px solid #e0e8f0;border-radius:5px;overflow:hidden">
          <div style="background:#f0f8ff;padding:.3rem .6rem;font-size:.68rem;font-weight:700;color:#003F87;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #e0e8f0">
            🔬 UCDP GED ${uv.ucdp_ged_version} Validation — ${comp.caseName||''}
          </div>
          <div style="padding:.4rem .6rem;font-size:.72rem;display:flex;gap:.8rem;flex-wrap:wrap;align-items:center">
            <span><strong>Civilian deaths (floor):</strong> ${(uv.ucdp_civilian_deaths||0).toLocaleString()}</span>
            <span><strong>Total best:</strong> ${(uv.ucdp_best_total||0).toLocaleString()}</span>
            <span><strong>Range:</strong> ${uv.ucdp_range||'—'}</span>
            <span style="font-weight:700;color:${matchColor}">${matchLabel}</span>
          </div>
          ${uv.ucdp_note ? `<div style="padding:.2rem .6rem .4rem;font-size:.68rem;color:#6b7280;font-style:italic;border-top:1px solid #f0f4f8">${uv.ucdp_note}</div>` : ''}
          <div style="padding:.2rem .6rem .3rem;font-size:.63rem;color:#9ca3af;border-top:1px solid #f0f4f8">
            Source: Davies et al. (2025), JPR 62(4); Sundberg &amp; Melander (2013), JPR 50(4). CC BY 4.0.
          </div>
        </div>`;
    } else {
      ucdpCompBlock = `
        <div style="margin-top:.5rem;padding:.35rem .6rem;background:#f8fafc;border:1px solid #e2e8f0;border-radius:4px;font-size:.68rem;color:#6b7280">
          UCDP data not available for this case.
        </div>`;
    }
  }

  body.innerHTML = `
    <div style="border:1px solid #e2e8f0;border-radius:6px;overflow:hidden">
      ${headerRow}${dataRows}
    </div>
    ${calibWarn}
    ${ucdpCompBlock}
    <div class="cmp-footnote mt-2">
      <span class="conf-dot conf-estimated" style="display:inline-block;vertical-align:middle;margin-right:.3rem"></span>
      Cost figures for comparison case are model estimates computed from ERCF dimensions and population data — not actual recorded expenditures.
      ${comp.isHistorical
        ? 'Vulnerable % and distance use researched case-specific values. Terrain uses default (Level 3).'
        : 'Days use current scenario value for saved scenarios without a stored duration.'}
      Deltas (↓↑) show current scenario relative to comparison case. Green = current is lower / fewer (better outcome); red = higher / more (worse outcome).
    </div>`;

  reinitTooltips(body);
}

document.getElementById('compareCase').addEventListener('change', function() {
  const val       = this.value;
  const lbl       = document.getElementById('compareCaseName');

  // Clear comparison
  if (!val) {
    state.charts.radar.data.datasets[1].hidden = true;
    state.charts.radar.update();
    state.comparisonData = null;
    if (lbl) lbl.textContent = '';
    renderRadarUcdpBlock(null);
    renderCostComparePanel();
    return;
  }

  let dimObj, compLabel, pop, vulPct, distKm, days, riskLevel,
      historicalDeaths = null, isHistorical = false;

  if (val.startsWith('hist-')) {
    const id = parseInt(val.slice(5));
    const c  = state.historicalCases.find(x => x.id === id);
    if (!c) return;
    const ri = c.risk_indicators;
    dimObj   = { d1: ri.d1_kinetic, d2: ri.d2_vulnerability, d3: ri.d3_political,
                 d4: ri.d4_logistics, d5: ri.d5_destination, d6: ri.d6_urgency, d7: ri.d7_information };
    riskLevel        = c.risk_level;          // use curated level, not recomputed
    compLabel        = `${c.name} (${c.year})`;
    pop              = c.population_at_risk;
    vulPct           = state.vulnerablePct;   // current scenario proxy
    distKm           = state.distanceKm;      // current scenario proxy
    days             = c.duration_days;
    historicalDeaths = c.estimated_deaths;
    isHistorical     = true;

  } else if (val.startsWith('saved-')) {
    const id = parseInt(val.slice(6));
    const s  = state.savedScenarios.find(x => x.id === id);
    if (!s) return;
    dimObj    = { d1: s.d1_kinetic, d2: s.d2_vulnerability, d3: s.d3_political,
                  d4: s.d4_logistics, d5: s.d5_destination, d6: s.d6_urgency, d7: s.d7_information };
    riskLevel = s.risk_level ?? calcRisk(dimObj).level;
    compLabel = s.name;
    pop       = s.population;
    vulPct    = s.vulnerable_pct;
    distKm    = s.distance_km;
    days      = state.days;                   // saved scenarios have no stored duration
    isHistorical = false;

  } else {
    return;
  }

  const dimArr = [dimObj.d1, dimObj.d2, dimObj.d3, dimObj.d4, dimObj.d5, dimObj.d6, dimObj.d7];

  // Compute comparison costs on-the-fly
  // For historical cases, use documented displacement rate for v2 model accuracy.
  // For saved scenarios, default 0.5 (50% displacement assumed — no stored value).
  const compDisplaced = isHistorical
    ? (state.historicalCases.find(x => x.id === parseInt(val.slice(5)))?.displaced ?? 0)
    : 0;
  const compPopForPct = isHistorical ? pop : pop;
  const compRemainingPct = isHistorical && compPopForPct > 0
    ? Math.max(0, 1 - compDisplaced / compPopForPct)
    : 0.5;

  // Exposure factor for comparison: historical cases use their named type; saved scenarios use auto
  const compExposure = isHistorical
    ? computeHistExposureFactor(state.historicalCases.find(x => x.id === parseInt(val.slice(5))) || {})
    : computeExposureFactor();   // fallback: current scenario's auto factor

  const compResources = calcResources(pop, vulPct, riskLevel, distKm, dimObj.d2, state.terrain);
  const compHistCase   = isHistorical ? state.historicalCases.find(x => x.id === parseInt(val.slice(5))) : null;
  const compSiegeCap   = !(compHistCase?.exposure_type === 'regional' || compHistCase?.exposure_type === 'city_conflict');
  const compStayData  = calcStay(pop, riskLevel, days, dimObj, compRemainingPct, compExposure, compSiegeCap);

  state.comparisonData = {
    label: compLabel, isHistorical, pop, vulPct, distKm, days, riskLevel, dims: dimObj,
    resources: compResources, stayData: compStayData, historicalDeaths,
    remainingPct: compRemainingPct,
    ucdpValidation: compHistCase?.documented_figures?.ucdp_validation || null,
    caseName: compHistCase?.name || compLabel,
  };

  if (lbl) lbl.textContent = compLabel;
  renderRadarUcdpBlock(compHistCase);
  renderCostComparePanel();
  // Radar overlay applied last — after DOM manipulation to prevent resize-triggered re-renders
  state.charts.radar.data.datasets[1].data   = dimArr;
  state.charts.radar.data.datasets[1].label  = (isHistorical ? '[Historical] ' : '[Saved] ') + compLabel;
  state.charts.radar.data.datasets[1].hidden = false;
  state.charts.radar.update();
});

function renderRadarUcdpBlock(compHistCase) {
  const el = document.getElementById('radarUcdpBlock');
  if (!el) return;

  if (!compHistCase) { el.innerHTML = ''; return; }

  // Cost comparison table
  const cc       = computeHistCaseCosts(compHistCase);
  const histPop  = compHistCase.population_at_risk;
  const histEvac = cc.res.totalCost;
  const histCPE  = histPop > 0 ? histEvac / histPop : 0;
  const histDays = compHistCase.duration_days;
  const histDead = cc.mDead;

  const curEvac    = state._lastResources?.totalCost;
  const curPop     = state.population;
  const curCPE     = curPop > 0 && curEvac ? curEvac / curPop : null;
  const curDays    = state.days;
  const deadArr    = state._lastStayData?.dead;
  const deadIdx    = deadArr ? Math.min(curDays, deadArr.length) - 1 : -1;
  const curDead    = deadIdx >= 0 ? deadArr[deadIdx] : null;

  const D = v => v != null && v > 0 ? '$' + fmt(Math.round(v)) : '—';
  const N = v => v != null          ? fmtFull(Math.round(v))   : '—';

  const costTableHtml = `
    <div style="margin-top:.5rem;border:1px solid #dce7f3;border-radius:5px;overflow:hidden">
      <div style="background:#e8f0fa;padding:.3rem .6rem;font-size:.67rem;font-weight:700;color:#1e40af;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #dce7f3">
        Cost Comparison
      </div>
      <table style="width:100%;font-size:.7rem;border-collapse:collapse">
        <thead>
          <tr style="background:#f0f4f8;color:#374151">
            <th style="padding:.25rem .5rem;text-align:left;font-weight:600;width:38%"></th>
            <th style="padding:.25rem .5rem;text-align:right;font-weight:600">Current Scenario</th>
            <th style="padding:.25rem .5rem;text-align:right;font-weight:600">${compHistCase.name} (${compHistCase.year})</th>
          </tr>
        </thead>
        <tbody>
          <tr style="border-top:1px solid #e8edf4">
            <td style="padding:.22rem .5rem;color:#64748b">Population</td>
            <td style="padding:.22rem .5rem;text-align:right">${N(curPop)}</td>
            <td style="padding:.22rem .5rem;text-align:right">${N(histPop)}</td>
          </tr>
          <tr style="border-top:1px solid #e8edf4;background:#fafbfd">
            <td style="padding:.22rem .5rem;color:#64748b">Evac. cost (model)</td>
            <td style="padding:.22rem .5rem;text-align:right">${D(curEvac)}</td>
            <td style="padding:.22rem .5rem;text-align:right">${D(histEvac)} <span style="font-size:.62rem;color:#94a3b8">ERCF est.</span></td>
          </tr>
          <tr style="border-top:1px solid #e8edf4">
            <td style="padding:.22rem .5rem;color:#64748b">Cost / evacuee</td>
            <td style="padding:.22rem .5rem;text-align:right">${curCPE != null ? '$' + fmt(Math.round(curCPE)) : '—'}</td>
            <td style="padding:.22rem .5rem;text-align:right">${D(histCPE)}</td>
          </tr>
          <tr style="border-top:1px solid #e8edf4;background:#fafbfd">
            <td style="padding:.22rem .5rem;color:#64748b">Duration</td>
            <td style="padding:.22rem .5rem;text-align:right">${curDays} days</td>
            <td style="padding:.22rem .5rem;text-align:right">${histDays} days</td>
          </tr>
          <tr style="border-top:1px solid #e8edf4">
            <td style="padding:.22rem .5rem;color:#64748b">Deaths (model est.)</td>
            <td style="padding:.22rem .5rem;text-align:right">${N(curDead)}</td>
            <td style="padding:.22rem .5rem;text-align:right">${N(histDead)}</td>
          </tr>
        </tbody>
      </table>
    </div>`;

  const uv = compHistCase.documented_figures?.ucdp_validation;

  if (!uv || !uv.ucdp_ged_version) {
    el.innerHTML = `
      <div style="padding:.3rem .5rem;background:#f8fafc;border:1px solid #e2e8f0;border-radius:4px;font-size:.68rem;color:#6b7280">
        UCDP data not available for this case.
      </div>
      ${costTableHtml}`;
    return;
  }

  const matchColor = {
    'IN': '#0a6e50', '~50%': '#0a6e50', '~2x': '#d97706',
    'OUT': '#dc2626', 'NOT FOUND': '#6b7280', 'pre-1989': '#6b7280',
  }[uv.ucdp_match] || '#6b7280';

  const matchLabel = {
    'IN':        '✓ Within UCDP range',
    '~50%':      '~ Within 50% of UCDP best',
    '~2x':       '~ Within 2× of UCDP best',
    'OUT':       '✗ Outside UCDP range',
    'NOT FOUND': '— Not found in UCDP',
    'pre-1989':  '— Pre-1989 (outside UCDP scope)',
  }[uv.ucdp_match] || uv.ucdp_match;

  el.innerHTML = `
    <div style="border:1px solid #e0e8f0;border-radius:5px;overflow:hidden">
      <div style="background:#f0f8ff;padding:.3rem .6rem;font-size:.67rem;font-weight:700;color:#003F87;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #e0e8f0">
        \U0001f52c UCDP GED ${uv.ucdp_ged_version} — ${compHistCase.name} (${compHistCase.year})
      </div>
      <div style="padding:.35rem .6rem;font-size:.71rem;display:flex;gap:.7rem;flex-wrap:wrap;align-items:center">
        <span><strong>Civilian deaths (floor):</strong> ${(uv.ucdp_civilian_deaths||0).toLocaleString()}</span>
        <span><strong>Total best:</strong> ${(uv.ucdp_best_total||0).toLocaleString()}</span>
        <span><strong>Range:</strong> ${uv.ucdp_range||'—'}</span>
        <span style="font-weight:700;color:${matchColor}">${matchLabel}</span>
      </div>
      ${uv.ucdp_note ? `<div style="padding:.2rem .6rem .35rem;font-size:.67rem;color:#6b7280;font-style:italic;border-top:1px solid #f0f4f8">${uv.ucdp_note}</div>` : ''}
      <div style="padding:.2rem .6rem .25rem;font-size:.62rem;color:#9ca3af;border-top:1px solid #f0f4f8">
        Source: Davies et al. (2025), JPR 62(4); Sundberg &amp; Melander (2013), JPR 50(4). CC BY 4.0.
      </div>
    </div>
    ${costTableHtml}`;
}

// ═══════════════════════════════════════════════════════════
// MAP PIN — CONFLICT LOCATION & DISTANCE CALCULATION
// ═══════════════════════════════════════════════════════════

function haversine(lat1, lng1, lat2, lng2) {
  const R    = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a    = Math.sin(dLat/2) ** 2 +
               Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180) *
               Math.sin(dLng/2) ** 2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)));
}

const pinMapState = {
  lmap:              null,
  conflictMarker:    null,
  safeZoneMarker:    null,
  suggestionMarkers: [],
  polyline:          null,
  suggestions:       [],
  initialized:       false,
};

function openPinModal() {
  new bootstrap.Modal(document.getElementById('pinModal')).show();
}

document.getElementById('pinModal').addEventListener('shown.bs.modal', () => {
  ensureWorldRiskLoaded(); // pre-fetch so suggestions are ready when conflict pin is placed
  if (!pinMapState.lmap) {
    pinMapState.lmap = L.map('pinMap').setView([20, 15], 2);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png', {
      attribution: '© OpenStreetMap contributors © CARTO',
      subdomains: 'abcd', maxZoom: 10, noWrap: true,
    }).addTo(pinMapState.lmap);
    pinMapState.lmap.on('click', onPinMapClick);
  } else {
    pinMapState.lmap.invalidateSize();
  }
  // City pre-population from City/Area autocomplete — one-shot flag, takes priority
  if (state._pendingCityPin) {
    const { lat, lng, name } = state._pendingCityPin;
    state._pendingCityPin = null;
    const searchEl = document.getElementById('pinLocationSearch');
    if (searchEl) searchEl.value = name;
    pinMapState.lmap.setView([lat, lng], 7);
    _placePinConflict(lat, lng);
    _runAiSuggestion(lat, lng);
    pinMapState.cPin = pinMapState.conflictMarker?.getLatLng();
    updatePinLine();
  } else {
    // Restore existing pins
    if (state.conflictCoords && !pinMapState.conflictMarker) {
      _placePinConflict(state.conflictCoords.lat, state.conflictCoords.lng);
    }
    if (state.safeZoneCoords && !pinMapState.safeZoneMarker) {
      _placePinSafeZone(state.safeZoneCoords.lat, state.safeZoneCoords.lng,
                        state.safeZoneCoords.name, null);
    }
  }

  // If arriving from buildScenarioFromCountry, pre-place the conflict pin
  if (state._pendingConflictPin) {
    const { lat, lng } = state._pendingConflictPin;
    state._pendingConflictPin = null; // consume once

    // Center the map on the country
    pinMapState.lmap.setView([lat, lng], 5);

    // Place the conflict marker at the centroid (draggable, not locked)
    if (pinMapState.conflictMarker) {
      pinMapState.conflictMarker.setLatLng([lat, lng]);
    } else {
      pinMapState.conflictMarker = L.marker([lat, lng], {
        draggable: true,
        icon: pinMapState.redIcon ?? L.icon({ iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png', iconSize: [25,41], iconAnchor: [12,41] })
      }).addTo(pinMapState.lmap);
      pinMapState.conflictMarker.on('dragend', updatePinLine);
    }

    // Update internal state so the confirm button works immediately
    pinMapState.cPin = pinMapState.conflictMarker.getLatLng();
    updatePinLine();
  }

  // Pre-populate conflict location from City/Area field (Scenario Builder → Set on Map)
  if (state.cityName && state.cityLat != null && state.cityLng != null) {
    const searchEl = document.getElementById('pinLocationSearch');
    if (searchEl) searchEl.value = state.cityName;
    // Zoom to city and place conflict pin if not already set
    if (!pinMapState.conflictMarker) {
      pinMapState.lmap.setView([state.cityLat, state.cityLng], 7);
      _placePinConflict(state.cityLat, state.cityLng);
      pinMapState.cPin = pinMapState.conflictMarker?.getLatLng();
      updatePinLine();
    }
  }

  _updatePinConfirmBtn();
  document.getElementById('pinLocationSearch').focus();
});

document.getElementById('pinModal').addEventListener('hidden.bs.modal', () => {
  // Remove temporary markers so they reset fresh next open
  if (pinMapState.conflictMarker) {
    pinMapState.lmap.removeLayer(pinMapState.conflictMarker);
    pinMapState.conflictMarker = null;
  }
  if (pinMapState.safeZoneMarker) {
    pinMapState.lmap.removeLayer(pinMapState.safeZoneMarker);
    pinMapState.safeZoneMarker = null;
  }
  pinMapState.suggestionMarkers.forEach(m => pinMapState.lmap.removeLayer(m));
  pinMapState.suggestionMarkers = [];
  if (pinMapState.polyline) {
    pinMapState.lmap.removeLayer(pinMapState.polyline);
    pinMapState.polyline = null;
  }
  document.getElementById('pinSuggestions').style.display    = 'none';
  document.getElementById('pinDistResult').style.display      = 'none';
  document.getElementById('pinLocationSearch').value          = '';
  document.getElementById('pinSearchResults').style.display   = 'none';
  document.getElementById('pinSafeZoneSearch').value          = '';
  document.getElementById('pinSafeZoneResults').style.display = 'none';
  document.getElementById('pinInstrText').textContent =
    'Click the map to place the conflict location (red pin). Then select a suggested safe zone or click to place a custom one.';
});

// ── Pin modal location search (Nominatim) ────────────────────────────────────

// ── Shared Nominatim fetch (rate-limited to 1 req/sec) ───────────────────────
let lastNominatimRequest = 0;
async function nominatimFetch(query) {
  const now  = Date.now();
  const wait = Math.max(0, 1000 - (now - lastNominatimRequest));
  if (wait > 0) await new Promise(resolve => setTimeout(resolve, wait));
  lastNominatimRequest = Date.now();
  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5&addressdetails=1`;
  const response = await fetch(url, {
    headers: { 'Accept-Language': 'en', 'User-Agent': 'ERCF-EvacuationRiskTool/1.0' },
  });
  return response.json();
}

async function searchPinLocation(query) {
  if (!query || query.length < 2) return;
  try {
    const results = await nominatimFetch(query);
    renderPinSearchResults(results);
  } catch (e) {
    console.error('Geocoding error:', e);
  }
}

async function searchSafeZoneLocation(query) {
  if (!query || query.length < 2) return;
  try {
    const results = await nominatimFetch(query);
    renderSafeZoneSearchResults(results);
  } catch (e) {
    console.error('Safe zone geocoding error:', e);
  }
}

function renderSafeZoneSearchResults(results) {
  const container = document.getElementById('pinSafeZoneResults');
  if (!results.length) { container.style.display = 'none'; return; }

  container.innerHTML = results.map((r) => {
    const primary   = r.name || r.display_name.split(',')[0];
    const secondary = r.display_name.split(',').slice(1, 3).join(',').trim();
    return `<div class="safe-zone-result"
      data-lat="${r.lat}" data-lng="${r.lon}" data-name="${r.display_name.replace(/"/g, '&quot;')}"
      style="padding:8px 12px;cursor:pointer;border-bottom:1px solid #f1f5f9;font-size:13px;background:white">
      <strong>${primary}</strong>
      <span style="color:#64748b;margin-left:6px;font-size:12px">${secondary}</span>
    </div>`;
  }).join('');

  container.style.display = 'block';
  _bindSafeZoneResultEvents();
}

function _bindSafeZoneResultEvents() {
  const container = document.getElementById('pinSafeZoneResults');
  container.querySelectorAll('.safe-zone-result').forEach(el => {
    el.addEventListener('mouseover', () => {
      container.querySelectorAll('.safe-zone-result').forEach(e => e.classList.remove('pin-result-highlighted'));
      el.classList.add('pin-result-highlighted');
    });
    el.addEventListener('mouseout', () => el.classList.remove('pin-result-highlighted'));
    el.addEventListener('click', () => _selectSafeZoneResult(el));
  });
}

function _selectSafeZoneResult(el) {
  const lat  = parseFloat(el.dataset.lat);
  const lng  = parseFloat(el.dataset.lng);
  const name = el.dataset.name.split(',').slice(0, 2).join(',').trim();

  // score=0 (truthy check: 0 != null → true) gives the green pin color
  _placePinSafeZone(lat, lng, name, 0);

  // Pan to show both pins if conflict exists, otherwise just the safe zone
  if (pinMapState.conflictMarker) {
    const c = pinMapState.conflictMarker.getLatLng();
    pinMapState.lmap.fitBounds([[c.lat, c.lng], [lat, lng]], { padding: [40, 40] });
  } else {
    pinMapState.lmap.setView([lat, lng], 7);
  }

  document.getElementById('pinSafeZoneSearch').value          = name;
  document.getElementById('pinSafeZoneResults').style.display = 'none';
}

function renderPinSearchResults(results) {
  const container = document.getElementById('pinSearchResults');
  if (!results.length) { container.style.display = 'none'; return; }

  container.innerHTML = results.map((r) => {
    const primary   = r.name || r.display_name.split(',')[0];
    const secondary = r.display_name.split(',').slice(1, 3).join(',').trim();
    return `<div class="pin-search-result"
      data-lat="${r.lat}" data-lng="${r.lon}" data-name="${r.display_name.replace(/"/g, '&quot;')}"
      style="padding:8px 12px;cursor:pointer;border-bottom:1px solid #f1f5f9;font-size:13px;background:white">
      <strong>${primary}</strong>
      <span style="color:#64748b;margin-left:6px;font-size:12px">${secondary}</span>
    </div>`;
  }).join('');

  container.style.display = 'block';
  _bindPinSearchResultEvents();
}

function _bindPinSearchResultEvents() {
  const container = document.getElementById('pinSearchResults');
  container.querySelectorAll('.pin-search-result').forEach(el => {
    el.addEventListener('mouseover', () => {
      container.querySelectorAll('.pin-search-result').forEach(e => e.classList.remove('pin-result-highlighted'));
      el.classList.add('pin-result-highlighted');
    });
    el.addEventListener('mouseout', () => el.classList.remove('pin-result-highlighted'));
    el.addEventListener('click', () => _selectPinSearchResult(el));
  });
}

function _selectPinSearchResult(el) {
  const lat  = parseFloat(el.dataset.lat);
  const lng  = parseFloat(el.dataset.lng);
  const name = el.dataset.name.split(',').slice(0, 2).join(',').trim();

  pinMapState.lmap.setView([lat, lng], 8);
  _placePinConflict(lat, lng);
  _runAiSuggestion(lat, lng); // async: loads world risk if needed, renders suggestions

  document.getElementById('pinLocationSearch').value        = name;
  document.getElementById('pinSearchResults').style.display = 'none';
}

// ── Conflict location search input/keyboard ───────────────────────────────────
let pinSearchTimeout = null;
document.getElementById('pinLocationSearch').addEventListener('input', function () {
  clearTimeout(pinSearchTimeout);
  const query = this.value.trim();
  if (query.length < 2) {
    document.getElementById('pinSearchResults').style.display = 'none';
    return;
  }
  pinSearchTimeout = setTimeout(() => searchPinLocation(query), 400);
});

document.getElementById('pinLocationSearch').addEventListener('keydown', function (e) {
  const container   = document.getElementById('pinSearchResults');
  const items       = [...container.querySelectorAll('.pin-search-result')];
  if (!items.length) return;
  const highlighted = container.querySelector('.pin-result-highlighted');
  let idx           = items.indexOf(highlighted);

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (highlighted) highlighted.classList.remove('pin-result-highlighted');
    items[Math.min(idx + 1, items.length - 1)].classList.add('pin-result-highlighted');
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (highlighted) highlighted.classList.remove('pin-result-highlighted');
    items[Math.max(idx - 1, 0)].classList.add('pin-result-highlighted');
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (highlighted) _selectPinSearchResult(highlighted);
  } else if (e.key === 'Escape') {
    container.style.display = 'none';
  }
});

// ── Safe zone search input/keyboard ──────────────────────────────────────────
let pinSafeZoneSearchTimeout = null;
document.getElementById('pinSafeZoneSearch').addEventListener('input', function () {
  clearTimeout(pinSafeZoneSearchTimeout);
  const query = this.value.trim();
  if (query.length < 2) {
    document.getElementById('pinSafeZoneResults').style.display = 'none';
    return;
  }
  pinSafeZoneSearchTimeout = setTimeout(() => searchSafeZoneLocation(query), 400);
});

document.getElementById('pinSafeZoneSearch').addEventListener('keydown', function (e) {
  const container   = document.getElementById('pinSafeZoneResults');
  const items       = [...container.querySelectorAll('.safe-zone-result')];
  if (!items.length) return;
  const highlighted = container.querySelector('.pin-result-highlighted');
  let idx           = items.indexOf(highlighted);

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (highlighted) highlighted.classList.remove('pin-result-highlighted');
    items[Math.min(idx + 1, items.length - 1)].classList.add('pin-result-highlighted');
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (highlighted) highlighted.classList.remove('pin-result-highlighted');
    items[Math.max(idx - 1, 0)].classList.add('pin-result-highlighted');
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (highlighted) _selectSafeZoneResult(highlighted);
  } else if (e.key === 'Escape') {
    container.style.display = 'none';
  }
});

// ── Close dropdowns when clicking outside ────────────────────────────────────
document.addEventListener('click', function (e) {
  if (!e.target.closest('#pinLocationSearch') && !e.target.closest('#pinSearchResults')) {
    document.getElementById('pinSearchResults').style.display = 'none';
  }
  if (!e.target.closest('#pinSafeZoneSearch') && !e.target.closest('#pinSafeZoneResults')) {
    document.getElementById('pinSafeZoneResults').style.display = 'none';
  }
});

// ─────────────────────────────────────────────────────────────────────────────

function onPinMapClick(e) {
  const { lat, lng } = e.latlng;
  if (!pinMapState.conflictMarker) {
    _placePinConflict(lat, lng);
    _runAiSuggestion(lat, lng); // async: loads world risk if needed, renders suggestions
  } else {
    // Custom safe zone
    _placePinSafeZone(lat, lng, 'Custom safe zone', null);
    document.getElementById('pinInstrText').textContent =
      'Custom safe zone set. Drag either pin to adjust, then click Confirm.';
  }
}

function _placePinConflict(lat, lng) {
  if (pinMapState.conflictMarker) pinMapState.lmap.removeLayer(pinMapState.conflictMarker);
  pinMapState.conflictMarker = L.marker([lat, lng], {
    icon: makeDivIcon('#ef4444', 14),
    draggable: true,
  }).addTo(pinMapState.lmap)
    .bindTooltip('Conflict location (drag to adjust)', {sticky: false});
  pinMapState.conflictMarker.on('drag', () => {
    _updatePinLine();
    _updatePinDistDisplay();
    const p = pinMapState.conflictMarker.getLatLng();
    _runAiSuggestion(p.lat, p.lng); // world risk already loaded by this point
  });
  _updatePinLine();
  _updatePinDistDisplay();
  _updatePinConfirmBtn();
}

function _placePinSafeZone(lat, lng, name, score) {
  if (pinMapState.safeZoneMarker) pinMapState.lmap.removeLayer(pinMapState.safeZoneMarker);
  const color = (score != null) ? '#22c55e' : '#3b82f6';
  pinMapState.safeZoneMarker = L.marker([lat, lng], {
    icon: makeDivIcon(color, 14),
    draggable: true,
  }).addTo(pinMapState.lmap)
    .bindTooltip((name || 'Safe zone') + ' (drag to adjust)', {sticky: false});
  pinMapState.safeZoneMarker.on('drag', () => {
    _updatePinLine();
    _updatePinDistDisplay();
  });
  state.safeZoneCoords = { lat, lng, name: name || 'Custom safe zone' };
  _updatePinLine();
  _updatePinDistDisplay();
  _updatePinConfirmBtn();
}

function _updatePinLine() {
  if (pinMapState.polyline) pinMapState.lmap.removeLayer(pinMapState.polyline);
  if (!pinMapState.conflictMarker || !pinMapState.safeZoneMarker) return;
  const c = pinMapState.conflictMarker.getLatLng();
  const s = pinMapState.safeZoneMarker.getLatLng();
  pinMapState.polyline = L.polyline([[c.lat, c.lng], [s.lat, s.lng]], {
    color: '#1a237e', weight: 2, dashArray: '6 4', opacity: 0.7,
  }).addTo(pinMapState.lmap);
}

function _updatePinDistDisplay() {
  const distEl  = document.getElementById('pinDistResult');
  const distTxt = document.getElementById('pinDistText');
  if (!pinMapState.conflictMarker || !pinMapState.safeZoneMarker) {
    if (distEl) distEl.style.display = 'none';
    return;
  }
  const c   = pinMapState.conflictMarker.getLatLng();
  const s   = pinMapState.safeZoneMarker.getLatLng();
  const km  = haversine(c.lat, c.lng, s.lat, s.lng);
  const rdKm = Math.round(km * 1.3);
  if (distEl)  distEl.style.display = '';
  if (distTxt) distTxt.textContent  =
    `Straight-line: ${fmtDist(km)}  ·  Road estimate (×1.3): ~${fmtDist(rdKm)}`;
}

function _updatePinConfirmBtn() {
  const btn = document.getElementById('pinConfirmBtn');
  if (!btn) return;
  const bothPins = !!(pinMapState.conflictMarker && pinMapState.safeZoneMarker);
  const aiReady  = !!(pinMapState.conflictMarker && state._aiSuggestedSafeZone);
  btn.disabled = !(bothPins || aiReady);
}

function suggestSafeZones(conflictLat, conflictLng) {
  const wr = worldMapState.worldRisk;
  if (!wr || !Object.keys(wr).length) return [];

  const results = [];

  // --- Country border / entry points ---
  for (const [iso3, centroid] of Object.entries(COUNTRY_CENTROIDS)) {
    const d = wr[iso3];
    if (!d) continue;
    const score = parseFloat(d.inform_score);
    if (isNaN(score) || score >= 2.0) continue;

    const entry = BORDER_ENTRY_POINTS[iso3];
    const ptLat = entry ? entry.lat : centroid[0];
    const ptLng = entry ? entry.lng : centroid[1];
    const dist  = haversine(conflictLat, conflictLng, ptLat, ptLng);

    results.push({
      type:    entry ? 'border' : 'country',
      iso3,
      name:    entry ? entry.name : d.name,
      country: d.name,
      lat:     ptLat,
      lng:     ptLng,
      dist,
      score,
      note:    null,
    });
  }

  // --- Known safe cities (within 1500 km) ---
  for (const city of KNOWN_SAFE_CITIES) {
    const dist = haversine(conflictLat, conflictLng, city.lat, city.lng);
    if (dist > 1500) continue;
    results.push({
      type:    'city',
      iso3:    city.country,
      name:    city.name,
      country: city.country,
      lat:     city.lat,
      lng:     city.lng,
      dist,
      score:   null,
      note:    city.note,
    });
  }

  // Sort by distance, drop duplicates by proximity (≤20 km apart → keep closer one)
  results.sort((a, b) => a.dist - b.dist);
  const deduped = [];
  for (const r of results) {
    if (!deduped.some(x => haversine(x.lat, x.lng, r.lat, r.lng) < 20)) {
      deduped.push(r);
    }
  }
  return deduped.slice(0, 5);
}

function _renderSuggestions(suggs) {
  const panel = document.getElementById('pinSuggestions');
  const list  = document.getElementById('pinSuggList');

  pinMapState.suggestionMarkers.forEach(m => pinMapState.lmap.removeLayer(m));
  pinMapState.suggestionMarkers = [];

  if (!suggs.length) {
    if (panel) panel.style.display = 'none';
    return;
  }
  if (panel) panel.style.display = '';

  suggs.forEach((s, i) => {
    const informTip = s.score != null ? ` · INFORM ${s.score.toFixed(1)}` : '';
    const noteTip   = s.note ? ` · ${s.note}` : '';
    const m = L.marker([s.lat, s.lng], {
      icon: L.divIcon({
        html: `<div style="width:12px;height:12px;border-radius:50%;background:#22c55e;border:2px solid #fff;box-shadow:0 2px 5px rgba(0,0,0,.35);opacity:.85"></div>`,
        iconSize: [12,12], iconAnchor: [6,6], className: '',
      }),
    }).addTo(pinMapState.lmap)
      .bindTooltip(`${s.name} — ${fmtDist(s.dist)}${informTip}${noteTip}`, {sticky:true});
    m.on('click', () => selectPinSuggestion(i));
    pinMapState.suggestionMarkers.push(m);
  });

  if (list) {
    list.innerHTML = suggs.map((s, i) => {
      const icon    = s.type === 'city' ? '🏙' : '🚧';
      const inform  = s.score != null ? `<span style="color:#94a3b8;font-size:.67rem;white-space:nowrap">INFORM ${s.score.toFixed(1)}</span>` : '';
      const subline = s.type === 'border'
        ? `<span style="color:#64748b;font-size:.67rem">${s.country}</span>`
        : s.note
          ? `<span style="color:#64748b;font-size:.67rem">${s.note}</span>`
          : '';
      return `
        <div class="pin-sugg" id="pinSugg_${i}" onclick="selectPinSuggestion(${i})">
          <span style="font-size:.85rem;min-width:1.4rem">${icon}</span>
          <span style="flex:1;min-width:0">
            <span style="font-weight:600">${s.name}</span>
            ${subline ? `<br>${subline}` : ''}
          </span>
          <span class="pin-sugg-dist">${fmtDist(s.dist)}</span>
          ${inform}
        </div>`;
    }).join('');
  }
}

function selectPinSuggestion(i) {
  const s = pinMapState.suggestions[i];
  if (!s) return;
  document.querySelectorAll('.pin-sugg').forEach((el, j) =>
    el.classList.toggle('active', j === i));
  // score=0 (not null) → green pin for both scored countries and unscored cities
  _placePinSafeZone(s.lat, s.lng, s.name, s.score ?? 0);
  document.getElementById('pinInstrText').textContent =
    `Safe zone set: ${s.name}. Drag pins to adjust, then click Confirm.`;
}

async function fetchClimateContext() {
  const { lat, lng } = state.conflictCoords || {};
  if (lat == null || lng == null) return;
  try {
    const res = await fetch('/api/climate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ lat, lng, start_date: state.startDate || null }),
    });
    if (!res.ok) return;
    const data = await res.json();
    state.climateMult = data.climate_mult ?? null;
    const panel   = document.getElementById('climatePanel');
    const summary = document.getElementById('climateSummary');
    const detail  = document.getElementById('climateDetail');
    if (panel) {
      const regime = data.regime || '';
      summary.innerHTML =
        `${regime} ` +
        `<i class="fas fa-circle-question rc-info" data-bs-toggle="tooltip" data-bs-placement="top" ` +
        `data-bs-title="${(data.rationale || '').replace(/"/g, '&quot;')}" ` +
        `style="cursor:help;font-size:.68rem;color:#0284c7;vertical-align:middle"></i>`;
      reinitTooltips(summary);
      const cm = state.climateMult || {};
      const parts = [];
      if (cm.fuel_transport != null) parts.push(`Fuel/transport ×${cm.fuel_transport.toFixed(2)}`);
      if (cm.shelter        != null) parts.push(`Shelter ×${cm.shelter.toFixed(2)}`);
      detail.textContent = parts.join(' · ');
      const proxyNotice = document.getElementById('climateProxyNotice');
      if (data.is_proxy) {
        if (proxyNotice) {
          proxyNotice.style.display = 'block';
          proxyNotice.textContent = `Planning estimate — using ${data.proxy_year} historical data as a seasonal proxy (no forecast model used).`;
        }
      } else if (proxyNotice) {
        proxyNotice.style.display = 'none';
      }
      panel.style.display = regime ? 'block' : 'none';
    }
    updateAll();
  } catch (e) {
    console.warn('fetchClimateContext failed:', e);
  }
}

function confirmPinDistance() {
  if (!pinMapState.conflictMarker) return;
  if (!pinMapState.safeZoneMarker && !state._aiSuggestedSafeZone) return;


  const c = pinMapState.conflictMarker.getLatLng();
  state.conflictCoords = { lat: +c.lat.toFixed(5), lng: +c.lng.toFixed(5) };

  let finalKm;
  if (pinMapState.safeZoneMarker) {
    // Both pins set: haversine
    const s  = pinMapState.safeZoneMarker.getLatLng();
    const km = haversine(c.lat, c.lng, s.lat, s.lng);
    state.safeZoneCoords       = { ...(state.safeZoneCoords || {}),
                                    lat: +s.lat.toFixed(5), lng: +s.lng.toFixed(5) };
    state.distanceSource       = 'map_pin';
    state._haversineKm         = km;
    state._aiSuggestedSafeZone = null;
    state.roadFactorApplied    = document.getElementById('roadFactorToggle')?.checked || false;
    finalKm = state.roadFactorApplied ? Math.round(km * 1.3) : km;
  } else {
    // Conflict pin only: use AI suggestion
    const sugg = state._aiSuggestedSafeZone;
    finalKm              = sugg.dist;
    state.safeZoneCoords = { lat: sugg.lat, lng: sugg.lng, name: sugg.name };
    state.distanceSource = 'ai_suggested';
    state._haversineKm   = sugg.dist;
  }

  state.distanceKm = finalKm;
  const inDist = document.getElementById('inDist');
  if (inDist) inDist.value = toDisplayUnit(finalKm);

  updateDistanceLabel();
  updateDistanceDisplay();
  updateAll();
  updatePinLayerOnWorldMap();

  bootstrap.Modal.getInstance(document.getElementById('pinModal'))?.hide();
  showToast(`Distance set to ${fmtDist(finalKm)}`, 'success');
  fetchClimateContext();
  // Suggest vulnerable % if a country was selected on the map
  if (worldMapState.selectedIso) {
    const iso = worldMapState.selectedIso;
    const d   = worldMapState.worldRisk?.[iso];
    if (d?.name) suggestVulnerablePct(d.name);
  }
}

function applyRoadFactor(checked) {
  state.roadFactorApplied = checked;
  if (state._haversineKm == null) return;
  const finalKm = checked ? Math.round(state._haversineKm * 1.3) : state._haversineKm;
  state.distanceKm = finalKm;
  const inDist = document.getElementById('inDist');
  if (inDist) inDist.value = toDisplayUnit(finalKm);
  updateDistanceLabel();
  updateAll();
}

function updateDistanceLabel() {
  const lbl      = document.getElementById('distMapLabel');
  const lblWorld = document.getElementById('distMapLabelWorld');
  const rfRow    = document.getElementById('roadFactorRow');
  if (state.distanceSource !== 'map_pin' || state._haversineKm == null) {
    if (lbl)      lbl.style.display      = 'none';
    if (lblWorld) lblWorld.style.display = 'none';
    if (rfRow)    rfRow.style.display    = 'none';
    return;
  }
  const rdKm = Math.round(state._haversineKm * 1.3);
  const html = `<i class="fas fa-map-pin me-1"></i>Set from map — straight-line `
    + `<strong>${fmtDist(state._haversineKm)}</strong>. Road estimate (×1.3): ~${fmtDist(rdKm)}.`;
  if (lbl) {
    lbl.style.display = '';
    lbl.innerHTML = html;
  }
  if (lblWorld) {
    lblWorld.style.display = '';
    lblWorld.innerHTML = html;
  }
  if (rfRow) rfRow.style.display = '';
  updateDistanceDisplay();
}

function updateDistanceDisplay() {
  const el  = document.getElementById('distRouteDisplay');
  const btn = document.getElementById('btnSetOnMapText');
  if (!el) return;
  if (state.distanceSource === 'ai_suggested' && state.safeZoneCoords) {
    el.innerHTML = `✅ AI suggested: <strong>${state.safeZoneCoords.name}</strong> — ${fmtDist(state.distanceKm)}`;
    el.style.display = '';
    if (btn) btn.textContent = 'Edit on Map';
  } else if (state.distanceSource === 'map_pin' && state.safeZoneCoords) {
    el.innerHTML = `📍 <strong>${state.safeZoneCoords.name || 'Safe zone'}</strong> — ${fmtDist(state.distanceKm)} (map pin)`;
    el.style.display = '';
    if (btn) btn.textContent = 'Edit on Map';
  } else {
    el.style.display = 'none';
    if (btn) btn.textContent = 'Set on Map';
  }
}

function updatePinLayerOnWorldMap() {
  if (!worldMapState.initialized || !worldMapState.lmap) return;
  if (worldMapState.conflictPinMarker) {
    worldMapState.lmap.removeLayer(worldMapState.conflictPinMarker);
    worldMapState.conflictPinMarker = null;
  }
  if (worldMapState.safeZonePinMarker) {
    worldMapState.lmap.removeLayer(worldMapState.safeZonePinMarker);
    worldMapState.safeZonePinMarker = null;
  }
  if (worldMapState.pinLine) {
    worldMapState.lmap.removeLayer(worldMapState.pinLine);
    worldMapState.pinLine = null;
  }
  if (!state.conflictCoords) return;

  worldMapState.conflictPinMarker = L.marker(
    [state.conflictCoords.lat, state.conflictCoords.lng],
    { icon: makeDivIcon('#ef4444', 16, true) }
  ).addTo(worldMapState.lmap)
   .bindPopup(`<strong>Conflict Location</strong><br>
     <span style="font-size:.75rem">${state.conflictCoords.lat.toFixed(3)}°,
     ${state.conflictCoords.lng.toFixed(3)}°</span>`);

  if (!state.safeZoneCoords) return;

  worldMapState.safeZonePinMarker = L.marker(
    [state.safeZoneCoords.lat, state.safeZoneCoords.lng],
    { icon: makeDivIcon('#22c55e', 16) }
  ).addTo(worldMapState.lmap)
   .bindPopup(`<strong>Safe Zone: ${state.safeZoneCoords.name || 'Custom'}</strong><br>
     <span style="font-size:.75rem">Distance: <strong>${fmtDist(state.distanceKm)}</strong></span>`);

  const km = haversine(state.conflictCoords.lat, state.conflictCoords.lng,
                       state.safeZoneCoords.lat,  state.safeZoneCoords.lng);
  worldMapState.pinLine = L.polyline([
    [state.conflictCoords.lat, state.conflictCoords.lng],
    [state.safeZoneCoords.lat, state.safeZoneCoords.lng],
  ], { color:'#1a237e', weight:2, dashArray:'6 4', opacity:.8 })
    .addTo(worldMapState.lmap)
    .bindTooltip(fmtDist(km), {permanent:true, offset:[0,0]});
}

// ═══════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════

document.querySelectorAll('.dim-slider').forEach(el => {
  el.addEventListener('input', function() {
    state.dims[this.id] = parseFloat(this.value);
    document.getElementById(this.id+'v').textContent = parseFloat(this.value).toFixed(1);
    updateAll();
  });
});

function updateRemainPopLabel() {
  const el = document.getElementById('remainPopLabel');
  if (!el) return;
  const pct = state.population > 0 ? Math.round(state.remainingPop / state.population * 100) : 100;
  el.textContent = `= ${fmtFull(state.remainingPop)} people (${pct}%)`;
}

document.getElementById('inPop').addEventListener('input', function() {
  state.population = Math.max(1, parseInt(this.value) || 1);
  if (state.remainingPctMode) {
    state.remainingPop = Math.round(state.population * state.remainingPct / 100);
  } else {
    state.remainingPop = Math.min(state.remainingPop, state.population);
    document.getElementById('remainAbs').value = state.remainingPop;
  }
  updateRemainPopLabel();
  updateAll();
});
document.getElementById('inVuln').addEventListener('input', function() {
  state.vulnerablePct = Math.min(100, Math.max(0, parseFloat(this.value) || 0));
  updateAll();
});
document.getElementById('inDist').addEventListener('input', function() {
  state.distanceKm = Math.max(1, toKm(parseFloat(this.value) || 1));
  if (state.distanceSource !== 'manual') {
    state.distanceSource        = 'manual';
    state._haversineKm          = null;
    state._aiSuggestedSafeZone  = null;
    state.roadFactorApplied     = false;
    const rfToggle = document.getElementById('roadFactorToggle');
    if (rfToggle) rfToggle.checked = false;
    updateDistanceLabel();
    updateDistanceDisplay();
  }
  updateAll();
});
document.getElementById('inTerrain').addEventListener('change', function() {
  state.terrain = parseInt(this.value, 10);
  updateAll();
});
document.getElementById('inConflictPattern').addEventListener('change', function() {
  state.conflictType = parseInt(this.value, 10);
  updateAll();
});
document.getElementById('stayDays').addEventListener('input', function() {
  state.days = parseInt(this.value);
  document.getElementById('stayDaysVal').textContent = state.days + ' days';
  this.style.accentColor = state.days > 90 ? '#94a3b8' : '#ef4444';
  document.getElementById('daysWarn').style.display = state.days > 90 ? 'block' : 'none';
  updateAll();
});
document.getElementById('remainPctToggle').addEventListener('change', function() {
  state.remainingPctMode = this.checked;
  document.getElementById('remainPctRow').style.display = this.checked ? '' : 'none';
  document.getElementById('remainAbsRow').style.display = this.checked ? 'none' : '';
  if (!this.checked) document.getElementById('remainAbs').value = state.remainingPop;
  updateRemainPopLabel();
  updateAll();
});
document.getElementById('remainPct').addEventListener('input', function() {
  state.remainingPct = parseInt(this.value);
  document.getElementById('remainPctVal').textContent = state.remainingPct + '%';
  state.remainingPop = Math.round(state.population * state.remainingPct / 100);
  updateRemainPopLabel();
  updateAll();
});
document.getElementById('remainAbs').addEventListener('input', function() {
  const typed = parseInt(this.value) || 0;
  state.remainingPop = Math.min(state.population, Math.max(0, typed));
  if (typed > state.population) this.value = state.remainingPop;  // clamp shown value
  updateRemainPopLabel();
  updateAll();
});
document.getElementById('histFilter').addEventListener('change', function() {
  renderHistTable(this.value);
});
document.querySelector('[href="#paneScenarios"]').addEventListener('click', loadSavedScenarios);

// ═══════════════════════════════════════════════════════════
// WORLD CHOROPLETH MAP (ACAPS / INFORM-inspired)
// ═══════════════════════════════════════════════════════════

// TopoJSON IDs are zero-padded strings ('032' = Argentina). Strip leading zeros
// so they match our integer-keyed lookup ('32' → 'ARG').
function topoIdToIso3(rawId) {
  const n = parseInt(rawId, 10);
  return isNaN(n) ? '' : (worldMapState.isoLookup[String(n)] || '');
}

function choroStyle(feature) {
  const iso3   = topoIdToIso3(feature.id);
  const d      = worldMapState.worldRisk[iso3];
  const lvl    = d ? d.level : -1;
  const dimmed = worldMapState.activeFilter !== -1 && lvl !== worldMapState.activeFilter;
  return {
    fillColor:   dimmed ? '#e8e8e8' : (CHORO_COLORS[lvl] ?? CHORO_COLORS['-1']),
    fillOpacity: dimmed ? 0.12      : (CHORO_OPACITY[lvl] ?? CHORO_OPACITY['-1']),
    color:  dimmed ? '#ccc' : '#fff',
    weight: 0.5,
  };
}

function onEachCountry(feature, layer) {
  const iso3 = topoIdToIso3(feature.id);
  const d    = worldMapState.worldRisk[iso3];
  const name = d ? d.name : (iso3 || `ID:${feature.id}`);

  layer.on({
    mouseover(e) {
      const lvl = d ? d.level : -1;
      e.target.setStyle({ fillOpacity: Math.min(0.92, (CHORO_OPACITY[lvl]||0.18)+0.2) });
      document.getElementById('worldHoverLabel').textContent =
        d ? `${name} — L${lvl}: ${RISK_DEF[Math.max(0,lvl)]?.label || 'No data'}`
          : `${name} — No ACAPS data`;
    },
    mouseout(e) {
      worldMapState.geojsonLayer.resetStyle(e.target);
      document.getElementById('worldHoverLabel').textContent = 'Hover a country';
    },
    click() {
      if (iso3) loadCountryContext(iso3, name);
    },
  });

  if (d && d.level >= 1) {
    layer.bindTooltip(
      `<b>${name}</b> · L${d.level} · ${d.inform_score}/5<br><span style="font-size:.68rem">${d.crisis}</span>`,
      { sticky: true }
    );
  }
}

// Fix antimeridian-crossing polygons: when consecutive longitudes jump by >180°
// Leaflet draws a line straight across the map. Normalise by accumulating offsets.
function normalizeAntimeridian(geojson) {
  function fixRing(ring) {
    for (let i = 1; i < ring.length; i++) {
      const diff = ring[i][0] - ring[i - 1][0];
      if (diff > 180)  ring[i][0] -= 360;
      else if (diff < -180) ring[i][0] += 360;
    }
  }
  geojson.features.forEach(f => {
    if (!f.geometry) return;
    const g = f.geometry;
    if (g.type === 'Polygon') {
      g.coordinates.forEach(fixRing);
    } else if (g.type === 'MultiPolygon') {
      g.coordinates.forEach(poly => poly.forEach(fixRing));
    }
  });
  return geojson;
}

async function initWorldMap() {
  if (worldMapState.initialized) return;

  // Restrict to one world copy: prevents continent duplication at low zoom
  const bounds = L.latLngBounds([[-85, -180], [85, 180]]);
  worldMapState.lmap = L.map('worldMap', {
    zoomControl:         true,
    maxBounds:           bounds,
    maxBoundsViscosity:  1.0,
    minZoom:             2,
    maxZoom:             10,
    worldCopyJump:       false,
  }).setView([20, 15], 2);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a> · ACAPS/INFORM Severity Index (updated monthly, last pull: Jun 2026) · UCDP GED v26.1 (annual, data through 2025)',
    subdomains: 'abcd', maxZoom: 10, noWrap: true,
  }).addTo(worldMapState.lmap);

  let riskData, isoData, topoData;
  try {
    [riskData, isoData, topoData] = await Promise.all([
      fetch('/api/world-risk').then(r => r.json()),
      fetch('/api/iso-lookup').then(r => r.json()),
      fetch('/static/countries-110m.json').then(r => r.json()),
    ]);
  } catch(e) {
    // Tear down the partially-created Leaflet instance so the next tab click
    // can retry cleanly (avoids "Map container is already initialized" error).
    if (worldMapState.lmap) { worldMapState.lmap.remove(); worldMapState.lmap = null; }
    throw e;
  }

  worldMapState.initialized = true;

  worldMapState.worldRisk = riskData;
  worldMapState.isoLookup = isoData;

  // Convert TopoJSON → GeoJSON then fix antimeridian-crossing polygons
  const geojson = normalizeAntimeridian(
    topojson.feature(topoData, topoData.objects.countries)
  );

  worldMapState.geojsonLayer = L.geoJSON(geojson, {
    style: choroStyle,
    onEachFeature: onEachCountry,
  }).addTo(worldMapState.lmap);

  placeHistMarkersOnWorld();
  updateWorldStats();
  updatePinLayerOnWorldMap();
  // The map container may have had zero dimensions while the tab was hidden;
  // invalidateSize() forces Leaflet to recalculate and fill the container correctly.
  worldMapState.lmap.invalidateSize();
}

function placeHistMarkersOnWorld() {
  worldMapState.histMarkers.forEach(m => worldMapState.lmap.removeLayer(m));
  worldMapState.histMarkers = [];
  if (!worldMapState.showHist) return;

  state.historicalCases.forEach(c => {
    const coords = CASE_COORDS[c.id];
    if (!coords) return;
    const m = L.marker(coords, { icon: makeDivIcon(LEVEL_COLORS[c.risk_level], 12) })
      .addTo(worldMapState.lmap)
      .bindPopup(`
        <div style="min-width:190px">
          <strong>${c.name} (${c.year})</strong><br>
          <span style="font-size:.75rem">
            <b>Level ${c.risk_level}</b> — ${RISK_DEF[c.risk_level].label}<br>
            Pop: ${fmtFull(c.population_at_risk)} · Deaths: ${fmtFull(c.estimated_deaths)}<br>
            <em style="font-size:.68rem">${c.conflict_type}</em><br>
            <a href="#" onclick="openCaseModal(${c.id});return false;"
               style="color:#1a237e;font-weight:600">View full details →</a>
          </span>
        </div>
      `, { maxWidth: 230 });
    worldMapState.histMarkers.push(m);
  });
}

function toggleHistMarkers(show) {
  worldMapState.showHist = show;
  if (worldMapState.initialized) placeHistMarkersOnWorld();
}

function setWorldFilter(level) {
  worldMapState.activeFilter = level;
  ['wfAll','wf4','wf3','wf2','wf1'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('active');
    el.style.fontWeight = '';
  });
  const active = document.getElementById(level === -1 ? 'wfAll' : `wf${level}`);
  if (active) { active.classList.add('active'); active.style.fontWeight = '700'; }
  if (worldMapState.geojsonLayer) worldMapState.geojsonLayer.setStyle(choroStyle);
}

function updateWorldStats() {
  const counts = {4:0, 3:0, 2:0, 1:0};
  Object.values(worldMapState.worldRisk).forEach(d => {
    if (counts[d.level] !== undefined) counts[d.level]++;
  });
  document.getElementById('countL4').textContent = counts[4];
  document.getElementById('countL3').textContent = counts[3];
  document.getElementById('countL2').textContent = counts[2];
  document.getElementById('countL1').textContent = counts[1];
}

async function searchWorldMap() {
  const q = document.getElementById('worldSearch')?.value?.trim();
  if (!q || !worldMapState.lmap) return;
  const match = Object.entries(worldMapState.worldRisk).find(([, d]) =>
    d.name.toLowerCase().includes(q.toLowerCase())
  );
  if (match) {
    const [iso3, data] = match;
    // Zoom to country bounds via GeoJSON layer
    if (worldMapState.geojsonLayer) {
      worldMapState.geojsonLayer.eachLayer(layer => {
        if (topoIdToIso3(layer.feature.id) === iso3) {
          worldMapState.lmap.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 6 });
        }
      });
    }
    loadCountryContext(iso3, data.name);
    return;
  }
  try {
    const data = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1`
    ).then(r => r.json());
    if (data.length) worldMapState.lmap.setView([parseFloat(data[0].lat), parseFloat(data[0].lon)], 5);
    else showToast('Country not found', 'warning');
  } catch(e) { showToast('Search failed', 'danger'); }
}

// ── Country Context Panel ────────────────────────────────────────────────────

const _countryContextCache = {};  // iso3 → { ctx, acaps, live, ucdp }

function _fetchWithTimeout(url, options, ms) {
  const ctrl  = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  return fetch(url, { ...options, signal: ctrl.signal })
    .then(r => r.json())
    .finally(() => clearTimeout(timer));
}

async function loadCountryContext(iso3, name) {
  worldMapState.selectedIso = iso3;
  suggestVulnerablePct(name);   // show demographic suggestion when country selected from map
  const d     = worldMapState.worldRisk[iso3] || {};
  const lvl   = d.level ?? 0;
  const color = LEVEL_COLORS[lvl] || '#6c757d';

  const ctxHeader = document.getElementById('ctxHeader');
  ctxHeader.innerHTML = `
    <div>
      <span class="badge me-1" style="background:${color};font-size:.7rem">LEVEL ${esc(lvl)}</span>
      <strong style="font-size:.88rem">${esc(name)}</strong>
    </div>
    <span class="badge bg-light text-dark acaps-badge">INFORM ${esc(d.inform_score ?? '—')}/5</span>
  `;

  const WORLD_MAP_DECISIONS = {
    0: { text: 'Baseline — no active armed threat',       color: '#6b7280' },
    1: { text: 'Advisory — early warning phase',          color: '#2563eb' },
    2: { text: 'Watchful — corridor negotiation phase',   color: '#d97706' },
    3: { text: 'Contested — mass movement threshold',     color: '#ea580c' },
    4: { text: 'Emergency — extraction phase',            color: '#dc2626' },
  };
  const dec = WORLD_MAP_DECISIONS[lvl] || WORLD_MAP_DECISIONS[0];
  const decBadge = document.createElement('div');
  decBadge.style.cssText = `margin-top:6px;padding:4px 10px;border-radius:4px;background:${dec.color};color:#fff;font-size:.72rem;font-weight:600;letter-spacing:.03em;display:inline-block`;
  decBadge.textContent = dec.text;
  ctxHeader.appendChild(decBadge);

  // Serve from cache if already loaded this session
  if (_countryContextCache[iso3]) {
    const { ctx, acaps, live, ucdp } = _countryContextCache[iso3];
    renderContextPanel(iso3, name, lvl, color, d, ctx, acaps, live, ucdp);
    return;
  }

  document.getElementById('ctxBody').innerHTML = `
    <div class="ctx-loading">
      <div class="spinner-ring"></div>
      <div style="font-size:.78rem;color:#888">Loading context…</div>
    </div>`;

  const currentYear = new Date().getFullYear();

  // /api/country-context calls AI — 5s timeout with local-data fallback
  const ctxFetch = _fetchWithTimeout('/api/country-context', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ iso3, country_name: name }),
  }, 5000).catch(e => ({
    summary:           d.crisis || '',
    dimension_scores:  {},
    population_at_risk: d.pop_at_risk || 0,
    _ai_note: e.name === 'AbortError'
      ? 'Context API timed out (>5s) — showing local ACAPS data only.'
      : `Data unavailable — check connection (${e.message})`,
  }));

  const [ctx, acaps, live, ucdp] = await Promise.all([
    ctxFetch,
    fetch(`/api/country-context-acaps/${iso3}`).then(r => r.json()).catch(() => null),
    fetch(`/api/acaps/${iso3}`).then(r => r.json()).catch(() => null),
    fetch(`/api/ucdp?country=${encodeURIComponent(name)}&year_start=${currentYear-3}&year_end=${currentYear}`)
      .then(r => r.json()).catch(() => null),
  ]);

  _countryContextCache[iso3] = { ctx, acaps, live, ucdp };
  renderContextPanel(iso3, name, lvl, color, d, ctx, acaps, live, ucdp);
}

function renderAcapsSection(acaps) {
  if (!acaps) {
    return '<span class="text-muted" style="font-size:.72rem">ACAPS API not available.</span>';
  }
  if (acaps.error) {
    const note = acaps._note ? `<br><span style="font-size:.65rem">${esc(acaps._note)}</span>` : '';
    return `<span class="text-muted" style="font-size:.72rem">${esc(acaps.error)}${note}</span>`;
  }
  const results = Array.isArray(acaps.results) ? acaps.results : [];
  if (!results.length) {
    return '<span class="text-muted" style="font-size:.72rem">No active crises found for this country in ACAPS.</span>';
  }
  return results.map(c => {
    // Field names vary across ACAPS API versions — try all known variants
    const crisis   = c.crisis_name   ?? c.name   ?? '—';
    const score    = c.inform_severity_score ?? c.score  ?? null;
    const affected = c.affected_population  ?? c.people_affected ?? c.people_in_need ?? null;
    const updated  = c.last_update   ?? c.date   ?? null;
    const type     = c.crisis_type   ?? '';
    return `
      <div style="font-size:.74rem;padding:.35rem .5rem;background:#f0f9ff;border:1px solid #bae6fd;border-left:3px solid #0ea5e9;border-radius:0 6px 6px 0;margin-bottom:.3rem;">
        <div class="fw-semibold">${esc(crisis)}</div>
        <div class="d-flex gap-3 flex-wrap mt-1">
          ${score    != null ? `<span>INFORM: <strong>${esc(score)}/5</strong></span>` : ''}
          ${affected != null ? `<span>Affected: <strong>${esc(fmt(affected))}</strong></span>` : ''}
          ${type              ? `<span class="text-muted">${esc(type)}</span>` : ''}
        </div>
        ${updated ? `<div class="text-muted mt-1" style="font-size:.65rem">Updated: ${esc(updated)}</div>` : ''}
      </div>`;
  }).join('');
}

function renderAcapsLiveData(live) {
  if (!live) return '<span class="text-muted" style="font-size:.72rem">ACAPS Live API not available.</span>';

  const LEVEL_BADGE = {
    'Very High': '#ef4444', 'High': '#f97316', 'Medium': '#f59e0b',
    'Low': '#0ea5e9', 'Very Low': '#6c757d',
  };
  const TREND_ICON = { 'Increasing': '▲', 'Decreasing': '▼', 'No change': '▬', 'New': '★' };

  const parts = [];

  // ── INFORM severity ──────────────────────────────────────────────────────
  if (live.inform && live.inform.length) {
    const best = live.inform.reduce((a, b) =>
      (b.inform_severity_score ?? 0) > (a.inform_severity_score ?? 0) ? b : a, live.inform[0]);
    const score = best.inform_severity_score;
    const scoreColor = score >= 4.5 ? '#ef4444' : score >= 3.5 ? '#f97316' :
                       score >= 2.5 ? '#f59e0b' : score >= 1.5 ? '#0ea5e9' : '#6c757d';
    parts.push(`
      <div class="mb-2" style="font-size:.73rem">
        <div class="fw-semibold mb-1" style="color:#374151">INFORM Severity</div>
        ${live.inform.map(r => `
          <div class="d-flex align-items-center gap-2 mb-1">
            <span class="badge" style="background:${scoreColor};font-size:.65rem;min-width:2.4rem">${esc(r.inform_severity_score ?? '—')}/5</span>
            <span>${esc(r.crisis_name || '—')}</span>
          </div>`).join('')}
      </div>`);
  }

  // ── Humanitarian access ──────────────────────────────────────────────────
  if (live.access && live.access.length) {
    const a = live.access[0];
    const sc = a.access_score != null ? parseFloat(a.access_score) : null;
    const ac = sc != null ? (sc >= 4 ? '#ef4444' : sc >= 3 ? '#f97316' : sc >= 2 ? '#f59e0b' : sc >= 1 ? '#0ea5e9' : '#6c757d') : '#6c757d';
    parts.push(`
      <div class="mb-2" style="font-size:.73rem">
        <div class="fw-semibold mb-1" style="color:#374151">Humanitarian Access</div>
        <div class="d-flex align-items-center gap-2">
          <span class="badge" style="background:${ac};font-size:.65rem;min-width:2.4rem">${esc(sc ?? '—')}/5</span>
          ${a.weighted_score != null ? `<span class="text-muted">weighted: ${esc(a.weighted_score)}</span>` : ''}
        </div>
      </div>`);
  }

  // ── Active risks ─────────────────────────────────────────────────────────
  if (live.risks && live.risks.length) {
    const rows = live.risks.map(r => {
      const lvlColor = LEVEL_BADGE[r.risk_level] || '#6c757d';
      const trendIcon = TREND_ICON[r.risk_trend] || '';
      return `
        <div style="font-size:.72rem;padding:.3rem .45rem;background:#fff7ed;border-left:3px solid #f97316;border-radius:0 4px 4px 0;margin-bottom:.25rem;">
          <div class="d-flex justify-content-between align-items-start gap-1">
            <span class="fw-semibold" style="flex:1">${esc(r.risk_title || '—')}</span>
            <span class="badge ms-1" style="background:${lvlColor};font-size:.6rem;white-space:nowrap">${esc(r.risk_level || '?')}</span>
          </div>
          <div class="d-flex gap-2 mt-1 text-muted" style="font-size:.65rem">
            ${trendIcon ? `<span>Trend: <strong>${trendIcon} ${esc(r.risk_trend)}</strong></span>` : ''}
            ${r.probability  != null ? `<span>Prob: ${esc(r.probability)}</span>`  : ''}
            ${r.impact       != null ? `<span>Impact: ${esc(r.impact)}</span>`     : ''}
          </div>
        </div>`;
    }).join('');
    parts.push(`
      <div class="mb-2" style="font-size:.73rem">
        <div class="fw-semibold mb-1" style="color:#374151">Active Risks (${live.risks.length})</div>
        ${rows}
      </div>`);
  }

  // ── Active crises count ──────────────────────────────────────────────────
  if (live.crises && live.crises.length) {
    const count = live.crises.length;
    const names = live.crises.map(c => c.crisis_name || '—').join(', ');
    parts.push(`
      <div class="mb-1" style="font-size:.72rem">
        <span class="fw-semibold" style="color:#374151">Active Crises:</span>
        <span class="badge bg-danger ms-1" style="font-size:.65rem">${esc(count)}</span>
        <div class="text-muted mt-1">${esc(names)}</div>
      </div>`);
  }

  if (!parts.length) {
    return '<span class="text-muted" style="font-size:.72rem">No ACAPS live data found for this country.</span>';
  }
  return parts.join('');
}

function renderContextPanel(iso3, name, lvl, color, sd, ctx, acaps, live, ucdp) {
  const dimKeys   = ['d1_kinetic','d2_vulnerability','d3_political','d4_logistics','d5_destination','d6_urgency','d7_information'];
  const dimLabels = ['D1 Kinetic','D2 Vulnerability','D3 Authorization','D4 Logistics','D5 Destination','D6 Urgency','D7 Information'];
  const ds = ctx.dimension_scores || {};

  // ctx is model output and sd/acaps/live/ucdp are third-party API payloads —
  // all untrusted. Every interpolation below goes through esc().
  const dimBars = dimKeys.map((k, i) => {
    const v   = Number(ds[k]) || 1;
    const pct = (v - 1) / 4 * 100;
    const c   = v >= 4.5 ? '#ef4444' : v >= 3.5 ? '#f97316' : v >= 2.5 ? '#f59e0b' : v >= 1.5 ? '#0ea5e9' : '#6c757d';
    return `<div class="mb-1">
      <div class="d-flex justify-content-between" style="font-size:.68rem">
        <span>${dimLabels[i]}</span><span class="fw-bold">${esc(v)}</span>
      </div>
      <div class="ctx-dim-bar"><div class="ctx-dim-fill" style="width:${pct}%;background:${c}"></div></div>
    </div>`;
  }).join('');

  const routes    = (ctx.exit_routes || sd.exit_routes || []).map(r => `<span class="route-pill">🛣️ ${esc(r)}</span>`).join('');
  const actors    = (ctx.humanitarian_actors || sd.actors || []).map(a => `<span class="actor-pill">${esc(a)}</span>`).join('');
  const obstacles = (ctx.main_obstacles || []).map(o => `<div class="obstacle-item">⚠️ ${esc(o)}</div>`).join('');

  const aiNote = ctx._ai_note
    ? `<div class="alert alert-info py-1 mb-2" style="font-size:.7rem"><i class="fas fa-info-circle me-1"></i>${esc(ctx._ai_note)}</div>`
    : ctx._source === 'claude-haiku-4-5'
      ? `<div class="alert alert-success py-1 mb-2" style="font-size:.7rem"><i class="fas fa-robot me-1"></i>AI analysis (Claude Haiku)</div>`
      : '';

  document.getElementById('ctxBody').innerHTML = `
    ${aiNote}
    <p style="font-size:.78rem">${esc(ctx.summary || sd.crisis || '—')}</p>

    <div class="row g-2 mb-2">
      <div class="col-6"><div class="stat-mini text-center">
        <div class="val" style="font-size:1rem">${esc(fmt(Number(ctx.population_at_risk) || sd.pop_at_risk || 0))}</div>
        <div class="lbl">Pop. at Risk</div>
      </div></div>
      <div class="col-6"><div class="stat-mini text-center">
        <div class="val" style="font-size:1rem">${esc(fmt(sd.displaced || 0))}</div>
        <div class="lbl">Displaced</div>
      </div></div>
    </div>

    <div class="mb-2" style="font-size:.75rem">
      <strong>Conflict type:</strong> ${esc(ctx.conflict_type || sd.conflict_type || '—')}<br>
      <strong>Access:</strong> ${esc(ctx.humanitarian_access || sd.access_label || '—')}
      <span class="badge ms-1" style="background:${CHORO_COLORS[ctx.access_score ?? lvl]||'#ccc'};font-size:.62rem">
        Score ${esc(ctx.access_score ?? sd.access ?? '?')}/5
      </span>
    </div>

    <div class="mb-2">
      <div class="fw-bold mb-1" style="font-size:.73rem">DIMENSION SCORES (ERCF)</div>
      ${dimBars}
    </div>

    <!-- ERCF Three-Index Panel -->
    <div id="mapThreeIndexPanel" class="mb-3">
      <div data-role="matrixBanner" style="border-radius:6px;padding:.5rem .75rem;margin-bottom:.5rem;display:none">
        <div style="display:flex;align-items:center;gap:.5rem">
          <span data-role="matrixIcon" style="font-size:1.1rem"></span>
          <strong data-role="matrixLabel" style="font-size:.85rem"></strong>
        </div>
        <div data-role="matrixRationale" style="font-size:.75rem;margin-top:.2rem;opacity:.9"></div>
        <div data-role="matrixIHL" style="font-size:.7rem;margin-top:.2rem;font-style:italic;opacity:.8"></div>
      </div>
      <div class="d-flex gap-2">
        <div class="flex-fill p-2 rounded" style="background:#f8fafc;border:1px solid #e2e8f0">
          <div class="small text-muted fw-semibold mb-1">RISK SEVERITY</div>
          <div class="d-flex align-items-baseline gap-1"><span class="fw-bold fs-4" data-role="riskSevScore" style="color:#d97706">—</span><span class="text-muted small">/5</span></div>
          <div class="progress mt-1" style="height:4px"><div class="progress-bar" data-role="riskSevBar" style="width:0%;background:#d97706"></div></div>
          <div class="small text-muted mt-1" data-role="riskSevLabel">—</div>
        </div>
        <div class="flex-fill p-2 rounded" style="background:#f8fafc;border:1px solid #e2e8f0">
          <div class="small text-muted fw-semibold mb-1">FEASIBILITY</div>
          <div class="d-flex align-items-baseline gap-1"><span class="fw-bold fs-4" data-role="feasScore" style="color:#d97706">—</span><span class="text-muted small">/5</span></div>
          <div class="progress mt-1" style="height:4px"><div class="progress-bar" data-role="feasBar" style="width:0%;background:#d97706"></div></div>
          <div class="small text-muted mt-1" data-role="feasLabel">—</div>
        </div>
        <div class="flex-fill p-2 rounded" style="background:#f8fafc;border:1px solid #e2e8f0">
          <div class="small text-muted fw-semibold mb-1">INFO QUALITY</div>
          <div class="d-flex align-items-baseline gap-1"><span class="fw-bold fs-4" data-role="infoScore" style="color:#d97706">—</span><span class="text-muted small">/5</span></div>
          <div class="progress mt-1" style="height:4px"><div class="progress-bar" data-role="infoBar" style="width:0%;background:#d97706"></div></div>
          <div class="small text-muted mt-1" data-role="infoLabel">—</div>
        </div>
      </div>
    </div>

    <div class="mb-2">
      <div class="fw-bold mb-1" style="font-size:.73rem">EXIT ROUTES / SAFE ZONES</div>
      ${routes || '<span class="text-muted small">No data</span>'}
    </div>

    <div class="mb-2">
      <div class="fw-bold mb-1" style="font-size:.73rem">HUMANITARIAN ACTORS</div>
      ${actors || '<span class="text-muted small">No data</span>'}
    </div>

    ${obstacles ? `<div class="mb-2">
      <div class="fw-bold mb-1" style="font-size:.73rem">MAIN OBSTACLES</div>
      ${obstacles}
    </div>` : ''}

    <div class="mb-2" style="font-size:.73rem">
      <strong>IHL Framework:</strong> ${esc(ctx.ihl_framework || '—')}
    </div>

    <div class="mb-2">
      <div class="fw-bold mb-1" style="font-size:.73rem">ACAPS CRISIS DATA</div>
      ${renderAcapsSection(acaps)}
    </div>

    ${(() => {
      if (!ucdp || ucdp.error || !ucdp.total_events) return '';
      const yr = `${new Date().getFullYear()-3}–${new Date().getFullYear()}`;
      return `<div style="margin-top:.6rem;margin-bottom:.5rem">
        <div style="font-size:.68rem;font-weight:700;color:#003F87;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.3rem">
          🔬 UCDP GED v26.1 — Conflict Data (${yr})
        </div>
        <div style="background:#f0f8ff;border:1px solid #a8d4f0;border-left:3px solid #009EDB;border-radius:4px;padding:.4rem .6rem;font-size:.72rem">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:.2rem .8rem;margin-bottom:.3rem">
            <span><strong>Events:</strong> ${esc(ucdp.total_events.toLocaleString())}</span>
            <span><strong>One-sided:</strong> ${esc(ucdp.one_sided_events.toLocaleString())}</span>
            <span><strong>Civilian deaths (floor):</strong> ${esc((ucdp.deaths_civilians_explicit||0).toLocaleString())}</span>
            <span><strong>Total best:</strong> ${esc((ucdp.total_best||0).toLocaleString())}</span>
          </div>
          <div style="font-size:.68rem;color:#4a5568">
            <strong>Range:</strong> ${esc(ucdp.uncertainty_range||'—')}
          </div>
          ${ucdp.total_best === 0 ? '<div style="color:#6b7280;font-size:.68rem;margin-top:.2rem">No conflict events recorded in UCDP for this period.</div>' : ''}
        </div>
        <div style="font-size:.63rem;color:#9ca3af;margin-top:.2rem">
          Source: Davies et al. (2025), JPR 62(4) · CC BY 4.0 · ucdp.uu.se
        </div>
      </div>`;
    })()}

    <div class="mb-2">
      <button class="btn btn-sm w-100 d-flex justify-content-between align-items-center py-1 px-2"
        style="background:#f0f9ff;border:1px solid #bae6fd;font-size:.73rem;font-weight:700;color:#0369a1"
        type="button" data-bs-toggle="collapse" data-bs-target="#acapsLiveCollapse-${esc(iso3)}" aria-expanded="false">
        <span><i class="fas fa-satellite-dish me-1"></i>ACAPS LIVE DATA</span>
        <i class="fas fa-chevron-down" style="font-size:.6rem"></i>
      </button>
      <div class="collapse" id="acapsLiveCollapse-${esc(iso3)}">
        <div style="border:1px solid #bae6fd;border-top:none;border-radius:0 0 6px 6px;padding:.5rem .5rem .25rem">
          ${renderAcapsLiveData(live)}
        </div>
      </div>
    </div>

    <div class="d-grid gap-1 mt-3">
      <button class="btn btn-primary btn-sm" onclick="buildScenarioFromCountry('${esc(String(iso3).replace(/[^A-Za-z0-9]/g, ''))}')">
        <i class="fas fa-sliders me-1"></i>Build Scenario from this Country
      </button>
    </div>
    <div class="text-muted mt-2" style="font-size:.65rem">
      Source: ${esc(sd.source || 'ACAPS/INFORM')} · ${esc(ctx.last_updated || 'June 2025')}
    </div>
  `;

  // Render ERCF three-index panel for this country (ds already declared above)
  const mapDims = {
    d1: ds.d1_kinetic       || 1,
    d2: ds.d2_vulnerability || 1,
    d3: ds.d3_political     || 1,
    d4: ds.d4_logistics     || 1,
    d5: ds.d5_destination   || 1,
    d6: ds.d6_urgency       || 1,
    d7: ds.d7_information   || 1,
  };
  const mapRisk = calcRisk(mapDims);
  const mapThreeIndexContainer = document.getElementById('mapThreeIndexPanel');
  if (mapThreeIndexContainer) renderThreeIndexPanel(mapRisk, mapThreeIndexContainer);
}

async function buildScenarioFromCountry(iso3) {
  const d   = worldMapState.worldRisk[iso3] || {};
  const lvl = d.level ?? 0;

  let ds = {
    d1_kinetic:       lvl===4?5 : lvl===3?4 : lvl===2?3 : lvl===1?2 : 1,
    d2_vulnerability: 3,
    d3_political:     1 + lvl,
    d4_logistics:     lvl===4?4 : lvl===3?3.5 : 2.5,
    d5_destination:   3,
    d6_urgency:       lvl===4?4.5 : lvl===3?3.5 : 2,
    d7_information:   lvl >= 3 ? 3.5 : 2,
  };

  try {
    const ctx = await fetch('/api/country-context', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ iso3, country_name: d.name }),
    }).then(r => r.json());
    if (ctx.dimension_scores) ds = ctx.dimension_scores;
  } catch(e) { /* use defaults */ }

  const mapping = {
    d1_kinetic:'d1', d2_vulnerability:'d2', d3_political:'d3',
    d4_logistics:'d4', d5_destination:'d5', d6_urgency:'d6', d7_information:'d7',
  };
  for (const [apiKey, sliderKey] of Object.entries(mapping)) {
    const v = Math.min(5, Math.max(1, parseFloat(ds[apiKey]) || 3));
    state.dims[sliderKey] = v;
    const el  = document.getElementById(sliderKey);
    const vEl = document.getElementById(sliderKey + 'v');
    if (el)  el.value = v;
    if (vEl) vEl.textContent = v.toFixed(1);
  }

  if (d.pop_at_risk > 0) {
    state.population = d.pop_at_risk;
    const popEl = document.getElementById('inPop');
    if (popEl) popEl.value = d.pop_at_risk;
  }

  const nameEl = document.getElementById('scenName');
  const descEl = document.getElementById('scenDesc');
  if (nameEl) nameEl.value = `${d.name} — ${new Date().toLocaleDateString()}`;
  if (descEl) descEl.value = d.crisis || '';

  // Pre-set conflict location from the choropleth GeoJSON centroid
  // so the pin modal opens centered on the selected country
  if (worldMapState.geojsonLayer) {
    worldMapState.geojsonLayer.eachLayer(layer => {
      const props = layer.feature?.properties;
      const countryName = (d.name || '').toLowerCase().trim();
      const featureName = (props?.name || '').toLowerCase().trim();
      if (featureName && countryName && (featureName === countryName || featureName.includes(countryName) || countryName.includes(featureName))) {
        try {
          const bounds = layer.getBounds();
          const center = bounds.getCenter();
          // Store as pending pre-center for the pin modal to consume
          state._pendingConflictPin = { lat: +center.lat.toFixed(5), lng: +center.lng.toFixed(5) };
        } catch(e) { /* geometry may not support getBounds */ }
      }
    });
  }

  updateAll();
  document.querySelector('[href="#paneBuilder"]').click();
  showToast(`Scenario built from ${d.name} (Level ${lvl})`);
}

// ═══════════════════════════════════════════════════════════
// SNAPSHOT MODE — static fallback when /api/ is unavailable (GitHub Pages)
// ═══════════════════════════════════════════════════════════

let snapshotBannerShown = false;

function showSnapshotBanner() {
  if (snapshotBannerShown) return;
  snapshotBannerShown = true;
  const banner = document.createElement('div');
  banner.style.cssText = 'background:#eff6ff;border:1px solid #93c5fd;border-left:4px solid #3b82f6;border-radius:6px;padding:.5rem 1rem;margin:.5rem 1rem;font-size:.75rem;color:#1e40af;text-align:center';
  banner.textContent = '📸 Historical case data loaded from static snapshot (backend unavailable)';
  document.querySelector('.app-header')?.insertAdjacentElement('afterend', banner);
}

// Maps a live API path to its pre-computed snapshot/ equivalent for GitHub Pages
// deployments with no backend. Falls back on any fetch failure or non-OK response.
async function fetchWithSnapshotFallback(apiUrl, snapshotUrl) {
  try {
    const r = await fetch(apiUrl);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    showSnapshotBanner();
    return fetch(snapshotUrl).then(r => r.json());
  }
}

// ═══════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════

async function init() {
  initCharts();
  try {
    state.historicalCases = await fetchWithSnapshotFallback('/api/historical-cases', 'snapshot/index.json');
    populateCompareDropdown();
    renderHistTable('');
  } catch(e) {
    console.error('Failed to load historical cases', e);
  }
  updateAll();
  document.getElementById('remainAbs').value = state.population;
  updateRemainPopLabel();

  reinitTooltips();

  document.getElementById('tabMap').addEventListener('shown.bs.tab', () => {
    initWorldMap()
      .then(() => { setTimeout(() => worldMapState.lmap && worldMapState.lmap.invalidateSize(), 150); })
      .catch(e => console.error('Map init failed:', e));
  });

  // Force chart resize after first paint using requestAnimationFrame
  // rAF fires after the browser has painted, ensuring canvas has real dimensions
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      // Double rAF ensures we're after the second paint (layout + paint settled)
      if (state.charts.costBar) { state.charts.costBar.resize(); state.charts.costBar.update('none'); }
      if (state.charts.fin) { state.charts.fin.resize(); state.charts.fin.update('none'); }
      if (state.charts.human) { state.charts.human.resize(); state.charts.human.update('none'); }
      if (state.charts.radar) state.charts.radar?.resize?.();
    });
  });

  document.querySelector('[data-bs-target="#tabScenario"], [href="#tabScenario"]')
    ?.addEventListener('shown.bs.tab', () => {
      if (state.charts.costBar) { state.charts.costBar.resize(); state.charts.costBar.update('none'); }
    }, { once: true });
}

document.addEventListener('DOMContentLoaded', init);

// ── Map View — origin pin guidance message ────────────────────────────────────
document.getElementById('worldSearch').addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); searchWorldMap(); }
});

document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
  tab.addEventListener('shown.bs.tab', () => {
    if (state.charts.costBar) {
      state.charts.costBar.resize();
      state.charts.costBar.update('none');
    }
    if (state.charts.fin) state.charts.fin.resize();
    if (state.charts.human) state.charts.human.resize();
    if (state.charts.radar) state.charts.radar.resize();
    if (state.charts.stayBar) state.charts.stayBar?.resize?.();
  });
});
