'use strict';

// ═══════════════════════════════════════════════════════════
// STATE — all data comes from the API; nothing here is a
// computed/business value. Cost layer only — no gatekeeper or
// pathway state, unlike the full RICS frontend (rics/static/app.js).
// ═══════════════════════════════════════════════════════════

const state = {
  vocabulary: null,
  cohorts: [],
  selectedCohortId: null,
  confMult: 0.70, // 1 - uncertaintyLevel
  charts: {},
};

function titleCase(id) {
  return id.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(' ');
}

function fmtUSD(v) {
  if (v == null || isNaN(v)) return '—';
  const abs = Math.abs(v);
  if (abs >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M';
  if (abs >= 1e3) return '$' + (v / 1e3).toFixed(1) + 'K';
  return '$' + Math.round(v).toLocaleString();
}

function fmtYears(v) {
  if (v == null || isNaN(v)) return '—';
  return v.toFixed(2);
}

// ═══════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════

async function init() {
  const [vocab, cohorts] = await Promise.all([
    fetch('/api/cohort-vocabulary').then(r => r.json()),
    fetch('/api/cohorts').then(r => r.json()),
  ]);

  state.vocabulary = vocab;
  state.cohorts = cohorts;

  populateCohortSelect();
  populateNewCohortModal();

  document.getElementById('cohortSelect').addEventListener('change', e => {
    state.selectedCohortId = e.target.value ? Number(e.target.value) : null;
    updateAll();
  });

  const uncSlider = document.getElementById('uncertaintySlider');
  uncSlider.addEventListener('input', () => {
    document.getElementById('uncReadout').textContent = uncSlider.value + '%';
  });
  uncSlider.addEventListener('change', () => {
    state.confMult = 1 - (Number(uncSlider.value) / 100);
    updateAll();
  });

  ['tentLifetimeInput', 'fundingShortfallInput', 'tbDocInput', 'tbSkillsInput',
   'tbTransportInput', 'tbStartupInput', 'tbOffsetInput'].forEach(id => {
    document.getElementById(id).addEventListener('change', updateAll);
  });

  document.getElementById('ncSubmitBtn').addEventListener('click', submitNewCohort);

  if (state.cohorts.length > 0) {
    state.selectedCohortId = state.cohorts[0].id;
    document.getElementById('cohortSelect').value = String(state.selectedCohortId);
  }
  updateAll();
}

document.addEventListener('DOMContentLoaded', init);

// ═══════════════════════════════════════════════════════════
// COHORT SELECT / EMPTY STATE (item 1)
// ═══════════════════════════════════════════════════════════

function populateCohortSelect() {
  const sel = document.getElementById('cohortSelect');
  const emptyNote = document.getElementById('cohortEmptyNote');
  sel.innerHTML = '';

  if (state.cohorts.length === 0) {
    emptyNote.style.display = 'block';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No cohorts yet';
    sel.appendChild(opt);
    return;
  }

  emptyNote.style.display = 'none';
  state.cohorts.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = `${titleCase(c.nationality)} · ${titleCase(c.vulnerability_category)} · n=${c.count} (${c.priority})`;
    sel.appendChild(opt);
  });
}

// ═══════════════════════════════════════════════════════════
// NEW COHORT MODAL
// ═══════════════════════════════════════════════════════════

function populateNewCohortModal() {
  const fill = (id, options) => {
    const sel = document.getElementById(id);
    sel.innerHTML = '';
    options.forEach(v => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = titleCase(v);
      sel.appendChild(opt);
    });
  };
  fill('ncNationality', state.vocabulary.nationalities);
  fill('ncVulnCategory', state.vocabulary.vulnerability_categories);
  fill('ncLegalStatus', state.vocabulary.legal_statuses);
  fill('ncPriority', Object.keys(state.vocabulary.priority_order));

  const floor = state.vocabulary.k_anonymity_floor;
  document.getElementById('ncCountFloorNote').textContent = `(minimum ${floor} — k-anonymity floor)`;
  const countInput = document.getElementById('ncCount');
  countInput.min = floor;
  countInput.value = floor;

  document.getElementById('ncSnapshotDate').value = new Date().toISOString().slice(0, 10);
}

async function submitNewCohort() {
  const errEl = document.getElementById('ncError');
  errEl.style.display = 'none';

  const body = {
    snapshot_date: document.getElementById('ncSnapshotDate').value,
    nationality: document.getElementById('ncNationality').value,
    vulnerability_category: document.getElementById('ncVulnCategory').value,
    legal_status: document.getElementById('ncLegalStatus').value,
    count: Number(document.getElementById('ncCount').value),
    priority: document.getElementById('ncPriority').value,
    source: document.getElementById('ncSource').value || null,
    tag: document.getElementById('ncTag').value,
  };

  const res = await fetch('/api/cohorts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    errEl.textContent = detail && detail.detail ? JSON.stringify(detail.detail) : `Request failed (${res.status})`;
    errEl.style.display = 'block';
    return;
  }

  const created = await res.json();
  state.cohorts = await fetch('/api/cohorts').then(r => r.json());
  populateCohortSelect();
  state.selectedCohortId = created.id;
  document.getElementById('cohortSelect').value = String(created.id);

  const modalEl = document.getElementById('newCohortModal');
  bootstrap.Modal.getInstance(modalEl)?.hide();

  updateAll();
}

// ═══════════════════════════════════════════════════════════
// MAIN COST CALCULATION (items 2 + 3) — all math server-side,
// this file only renders what /api/calculate/breakeven returns.
// ═══════════════════════════════════════════════════════════

function currentCohort() {
  return state.cohorts.find(c => c.id === state.selectedCohortId) || null;
}

async function updateAll() {
  const cohort = currentCohort();
  const tentLifetime = parseFloat(document.getElementById('tentLifetimeInput').value);

  if (!cohort || !tentLifetime || tentLifetime <= 0) {
    clearMetricCards();
    document.getElementById('chartEmptyState').style.display = 'block';
    if (state.charts.breakeven) { state.charts.breakeven.destroy(); state.charts.breakeven = null; }
    return;
  }
  document.getElementById('chartEmptyState').style.display = 'none';

  const body = {
    trajectory_a: {
      cohort_count: cohort.count,
      conf_mult: state.confMult,
      tent_lifetime_years_override: tentLifetime,
      funding_shortfall_pct: (Number(document.getElementById('fundingShortfallInput').value) || 0) / 100,
    },
    trajectory_b: {
      conf_mult: state.confMult,
      documentation_usd: Number(document.getElementById('tbDocInput').value) || 0,
      skills_credentialing_usd: Number(document.getElementById('tbSkillsInput').value) || 0,
      transport_usd: Number(document.getElementById('tbTransportInput').value) || 0,
      startup_capital_usd: Number(document.getElementById('tbStartupInput').value) || 0,
      host_coinvestment_offset_usd: Number(document.getElementById('tbOffsetInput').value) || 0,
    },
  };

  const res = await fetch('/api/calculate/breakeven', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    clearMetricCards();
    return;
  }
  const data = await res.json();
  renderMetricCards(data);
  renderBreakevenChart(data);
}

function clearMetricCards() {
  ['mcTrajectoryA', 'mcTrajectoryB', 'mcBreakeven', 'mcBandWidth'].forEach(id => {
    document.getElementById(id).textContent = '—';
  });
  document.getElementById('mcTrajectoryAFlag').style.display = 'none';
  document.getElementById('mcTrajectoryBFlag').style.display = 'none';
  document.getElementById('mcBreakevenSub').textContent = ' ';
}

function renderMetricCards(data) {
  const [aPoint] = data.trajectory_a_per_person_year;
  document.getElementById('mcTrajectoryA').textContent = fmtUSD(aPoint);
  const aFlag = document.getElementById('mcTrajectoryAFlag');
  if (!data.funding_shortfall_calibrated) {
    aFlag.style.display = 'inline-block';
    aFlag.textContent = 'Funding-shortfall multiplier not yet calibrated (alpha unset)';
  } else {
    aFlag.style.display = 'none';
  }

  const [bPoint] = data.trajectory_b_per_person;
  document.getElementById('mcTrajectoryB').textContent = fmtUSD(bPoint);
  const bFlag = document.getElementById('mcTrajectoryBFlag');
  if (data.trajectory_b_uncosted_components.length > 0) {
    bFlag.style.display = 'inline-block';
    bFlag.textContent = 'Not yet costed: ' + data.trajectory_b_uncosted_components.join(', ');
  } else {
    bFlag.style.display = 'none';
  }

  const beEl = document.getElementById('mcBreakeven');
  const beSub = document.getElementById('mcBreakevenSub');
  const [bTotalPoint] = data.trajectory_b_upfront_total;
  if (bTotalPoint === 0) {
    beEl.textContent = '—';
    beSub.textContent = 'Trajectory B not yet costed — nothing to break even against';
  } else if (data.breakeven_year_point == null) {
    beEl.textContent = 'Never';
    beSub.textContent = 'Status quo does not exceed the inclusion pathway cost within any horizon';
  } else {
    beEl.textContent = fmtYears(data.breakeven_year_point);
    beSub.textContent = (data.breakeven_year_low != null && data.breakeven_year_high != null)
      ? `range ${fmtYears(data.breakeven_year_low)}–${fmtYears(data.breakeven_year_high)} years`
      : ' ';
  }

  document.getElementById('mcBandWidth').textContent =
    (bTotalPoint !== 0 && data.breakeven_year_band_width != null) ? fmtYears(data.breakeven_year_band_width) + ' yr' : '—';
}

function renderBreakevenChart(data) {
  const canvas = document.getElementById('breakevenChart');
  if (state.charts.breakeven) { state.charts.breakeven.destroy(); state.charts.breakeven = null; }

  const series = data.chart_series;
  const pts = key => series.map(s => ({ x: s.year, y: s[key] }));
  const beYear = data.breakeven_year_point;

  state.charts.breakeven = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'Trajectory B — low',
          data: pts('trajectory_b_low'),
          borderColor: 'rgba(37,99,235,.35)',
          borderWidth: 1,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Trajectory B — high (uncertainty band)',
          data: pts('trajectory_b_high'),
          borderColor: 'rgba(37,99,235,.35)',
          backgroundColor: 'rgba(37,99,235,.15)',
          borderWidth: 1,
          pointRadius: 0,
          fill: '-1',
        },
        {
          label: 'Trajectory B — point estimate',
          data: pts('trajectory_b_point'),
          borderColor: '#2563eb',
          borderDash: [4, 4],
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Trajectory A — status quo (cumulative)',
          data: pts('trajectory_a_cumulative'),
          borderColor: '#dc2626',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 10 }, boxWidth: 12 } },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: { label: ctx => ctx.dataset.label + ': ' + fmtUSD(ctx.parsed.y) },
        },
      },
      scales: {
        x: {
          type: 'linear',
          title: { display: true, text: 'Year', font: { size: 10 } },
          ticks: { font: { size: 9 }, stepSize: 1 },
          grid: { color: 'rgba(0,0,0,.04)' },
        },
        y: {
          ticks: { font: { size: 9 }, callback: v => fmtUSD(v) },
          grid: { color: 'rgba(0,0,0,.04)' },
        },
      },
    },
    plugins: [{
      id: 'beMarker',
      afterDraw(chart) {
        if (beYear == null) return;
        const { ctx, scales: { x, y } } = chart;
        const xPx = x.getPixelForValue(beYear);
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = '#16a34a';
        ctx.lineWidth = 1.5;
        ctx.moveTo(xPx, y.top);
        ctx.lineTo(xPx, y.bottom);
        ctx.stroke();
        ctx.fillStyle = '#16a34a';
        ctx.font = 'bold 9px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText('Year ' + beYear.toFixed(2), xPx, y.top + 10);
        ctx.restore();
      },
    }],
  });
}
