/* ════════════════════════════════════════════════════════
   DSF-AI Frontend — plain JS, no framework
   ════════════════════════════════════════════════════════ */

const API = 'https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com';

let selectedFile = null;
let lastReport = null;

// ── CSV Upload ─────────────────────────────────────────
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('csv-file');
const analyzeBtn = document.getElementById('analyze-btn');
const statusEl = document.getElementById('analyze-status');

dropzone.addEventListener('click', () => fileInput.click());

dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
  dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    selectFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    selectFile(fileInput.files[0]);
  }
});

function selectFile(file) {
  if (!file.name.endsWith('.csv')) {
    statusEl.textContent = 'Please select a .csv file.';
    statusEl.className = 'status error';
    return;
  }
  selectedFile = file;
  statusEl.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  statusEl.className = 'status';
  analyzeBtn.disabled = false;
}

analyzeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  analyzeBtn.disabled = true;
  statusEl.textContent = 'Analyzing...';
  statusEl.className = 'status';
  document.getElementById('analyze-results').hidden = true;

  const formData = new FormData();
  formData.append('file', selectedFile);

  const context = document.getElementById('context-input').value.trim();
  if (context) {
    formData.append('context', context);
  }

  try {
    const resp = await fetch(`${API}/api/v1/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!resp.ok) {
      let errMsg = 'Analysis failed';
      try { const err = await resp.json(); errMsg = err.detail || err.error || errMsg; } catch(_) {}
      throw new Error(errMsg);
    }

    const report = await resp.json();
    lastReport = report;
    displayReport(report);
    statusEl.textContent = '';
  } catch (e) {
    if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
      statusEl.textContent = 'CSV analysis is coming soon. Try the Cluster Screener below.';
    } else {
      statusEl.textContent = `Error: ${e.message}`;
    }
    statusEl.className = 'status error';
  }

  analyzeBtn.disabled = false;
});

function displayReport(r) {
  const el = document.getElementById('analyze-results');
  el.hidden = false;

  // Transitions
  const transEl = document.getElementById('result-transitions');
  if (r.transitions && r.transitions.length > 0) {
    transEl.innerHTML = '<ul>' + r.transitions.map(t =>
      `<li>At <strong>${t.stimulus_value}</strong> (uncertainty: ${t.uncertainty_at_transition})</li>`
    ).join('') + '</ul>';
  } else {
    transEl.textContent = 'No transitions detected.';
  }

  // Regime map
  const regEl = document.getElementById('result-regimes');
  if (r.regime_map && r.regime_map.length > 0) {
    const totalRange = r.stimulus_range[1] - r.stimulus_range[0];
    let barHtml = '<div class="regime-bar">';
    let legendHtml = '<div class="regime-legend">';
    const regimeSet = new Set();

    r.regime_map.forEach(seg => {
      const width = ((seg.end - seg.start) / totalRange * 100).toFixed(1);
      barHtml += `<div class="regime-segment regime-${seg.regime}" style="width:${width}%" title="${seg.regime}: ${seg.start} - ${seg.end}">${seg.regime.substring(0, 3)}</div>`;
      regimeSet.add(seg.regime);
    });

    barHtml += '</div>';
    regimeSet.forEach(regime => {
      legendHtml += `<span class="legend-${regime}">${regime}: `;
      const segs = r.regime_map.filter(s => s.regime === regime);
      legendHtml += segs.map(s => `${s.start}-${s.end}`).join(', ');
      legendHtml += '</span>';
    });
    legendHtml += '</div>';

    regEl.innerHTML = barHtml + legendHtml;
  } else {
    regEl.textContent = 'No regime data.';
  }

  // Precursor
  const precEl = document.getElementById('result-precursor');
  if (r.precursor_onset !== null) {
    precEl.innerHTML = `Structural changes begin at <strong>${r.precursor_onset}</strong>`;
    if (r.transitions && r.transitions.length > 0) {
      const firstTrans = r.transitions[0].stimulus_value;
      const lead = Math.abs(r.precursor_onset - firstTrans).toFixed(1);
      precEl.innerHTML += ` (${lead} units before the first transition)`;
    }
  } else {
    precEl.textContent = 'No precursors detected.';
  }

  // Uncertainty
  const uncEl = document.getElementById('result-uncertainty');
  if (r.uncertainty_peak) {
    uncEl.innerHTML = `Peak: <strong>${r.uncertainty_peak.value}</strong> at ${r.uncertainty_peak.location}`;
  }

  // Narrative
  const narEl = document.getElementById('result-narrative');
  const narText = document.getElementById('narrative-text');
  if (r.narrative) {
    narText.textContent = r.narrative;
    narEl.hidden = false;
  } else {
    narEl.hidden = true;
  }

  // Meta
  document.getElementById('result-points').textContent = `${r.data_points} data points`;
  document.getElementById('result-gates').textContent = `${r.n_gates} structural gates`;
  document.getElementById('result-time').textContent = r.compute_time_s ? `${r.compute_time_s}s` : '';
}

// Download JSON
document.getElementById('download-json').addEventListener('click', () => {
  if (!lastReport) return;
  const blob = new Blob([JSON.stringify(lastReport, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'dsf-ai-analysis.json';
  a.click();
  URL.revokeObjectURL(url);
});

// ── Cluster Screener ───────────────────────────────────
document.getElementById('cluster-btn').addEventListener('click', async () => {
  const element = document.getElementById('cluster-element').value;
  const N = parseInt(document.getElementById('cluster-size').value);
  const lattice = document.getElementById('cluster-lattice').value;
  const btn = document.getElementById('cluster-btn');

  btn.disabled = true;
  btn.textContent = 'Predicting...';

  try {
    const resp = await fetch(`${API}/api/v1/cluster`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ element, N_atoms: N, lattice, temperature_K: 300 }),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Prediction failed');
    }

    const r = await resp.json();
    displayCluster(r);
  } catch (e) {
    alert(`Error: ${e.message}`);
  }

  btn.disabled = false;
  btn.textContent = 'Predict';
});

function displayCluster(r) {
  document.getElementById('cluster-results').hidden = false;
  document.getElementById('cluster-title').textContent =
    `${r.element}${r.N_atoms} — ${r.geometry} cluster`;

  document.getElementById('prop-moment').textContent =
    r.magnetic_moment_uB !== null ? r.magnetic_moment_uB.toFixed(2) : '—';
  document.getElementById('prop-ea').textContent =
    r.electron_affinity_eV !== null ? r.electron_affinity_eV.toFixed(3) : '—';
  document.getElementById('prop-seebeck').textContent =
    r.seebeck_uV_K !== null ? (r.seebeck_uV_K > 0 ? '+' : '') + r.seebeck_uV_K.toFixed(1) : '—';
  document.getElementById('prop-gap').textContent =
    r.homo_lumo_gap_eV !== null ? r.homo_lumo_gap_eV.toFixed(4) : '—';

  document.getElementById('cluster-geometry').textContent = `Geometry: ${r.geometry}`;
  document.getElementById('cluster-dband').textContent =
    `d-band screening: ${r.d_band_screening.toFixed(3)}`;
  document.getElementById('cluster-disruption').textContent =
    r.disruption_active ? 'Superatom disrupted' : 'Superatom shell intact';
}
