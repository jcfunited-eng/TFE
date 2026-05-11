/* ════════════════════════════════════════════════════════
   DSF-AI Frontend — plain JS, no framework
   ════════════════════════════════════════════════════════ */

const API = 'https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com';
const FREE_ANALYSIS_KEY = 'dsf_ai_free_used';

let selectedFile = null;
let lastReport = null;
let clerkReady = false;

// ── Clerk Auth ─────────────────────────────────────────
async function initClerk() {
  // Show sign-in link immediately
  showSignInFallback();

  // If Clerk already loaded, use it; otherwise wait for event
  if (window.Clerk) {
    clerkReady = true;
  } else {
    await new Promise(resolve => {
      window.addEventListener('clerk-loaded', resolve, { once: true });
      // Timeout after 10s
      setTimeout(resolve, 10000);
    });
  }

  try {
    const clerk = window.Clerk;
    if (!clerk) {
      console.log('Clerk not available');
      return;
    }
    clerkReady = true;

    // Update UI immediately and on every auth state change
    updateAuthUI();
    clerk.addListener(() => updateAuthUI());

    // Also retry after a short delay — session restore after
    // OAuth redirect can take a moment
    setTimeout(() => updateAuthUI(), 1000);
    setTimeout(() => updateAuthUI(), 3000);
  } catch (e) {
    console.log('Clerk init error:', e.message);
    showSignInFallback();
  }
}

function updateAuthUI() {
  const userBtnEl = document.getElementById('user-button');
  const clerk = window.Clerk;
  if (!clerk) return;

  if (clerk.user) {
    // Show user info + account link + sign out
    const name = clerk.user.firstName || clerk.user.emailAddresses?.[0]?.emailAddress || 'Account';
    const img = clerk.user.imageUrl;
    userBtnEl.innerHTML = `
      <span class="user-info">
        ${img ? `<img src="${img}" class="user-avatar" alt="">` : ''}
        <span class="user-name">${name}</span>
        <a href="#" id="account-link" class="nav-auth" style="margin-left:0.5rem;font-size:0.8rem;">Account</a>
        <a href="#" id="sign-out-link" class="nav-auth" style="margin-left:0.5rem;font-size:0.8rem;">Sign Out</a>
      </span>`;

    // Account link — go to account page
    const accountLink = document.getElementById('account-link');
    if (accountLink) {
      accountLink.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.href = '/static/account.html';
      });
    }

    const signOutLink = document.getElementById('sign-out-link');
    if (signOutLink) {
      signOutLink.addEventListener('click', async (e) => {
        e.preventDefault();
        await clerk.signOut();
        location.reload();
      });
    }

    // Auto-fetch credits on login
    fetchCredits(clerk.user.id);
  } else {
    showSignInFallback();
  }
}

function showSignInFallback() {
  const userBtnEl = document.getElementById('user-button');
  userBtnEl.innerHTML = '<a href="#" id="sign-in-link" class="nav-auth">Sign In</a>';
  const link = document.getElementById('sign-in-link');
  if (link) {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      doSignIn();
    });
  }
}

async function fetchCredits(userId) {
  try {
    const resp = await fetch(`${API}/api/v1/check-access`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    const data = await resp.json();
    // Update the account link with credit count
    const accountLink = document.getElementById('account-link');
    if (accountLink && data.credits !== undefined) {
      const creditsText = data.credits === -1 ? 'Unlimited' : `${data.credits} credits`;
      accountLink.textContent = creditsText;
    }
  } catch (e) {
    console.log('Failed to fetch credits:', e.message);
  }
}

async function showAccountInfo(userId) {
  try {
    const resp = await fetch(`${API}/api/v1/check-access`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    const data = await resp.json();
    const credits = data.credits === -1 ? 'Unlimited' : data.credits;
    const used = data.analyses_used || 0;
    const tier = data.reason === 'subscription' ? ' (Subscription)' : '';
    alert(`Account Summary\n\nAnalyses used: ${used}\nCredits remaining: ${credits}${tier}\n\nPurchase more credits in the Pricing section.`);
  } catch (e) {
    alert('Unable to load account info. Please try again.');
  }
}

function doSignIn() {
  if (clerkReady && window.Clerk) {
    // Try modal first
    try {
      window.Clerk.openSignIn({
        redirectUrl: window.location.href,
        afterSignInUrl: window.location.href,
      });
    } catch (err) {
      // Fallback: redirect to Clerk's hosted sign-in
      console.log('Modal failed, using redirect:', err.message);
      window.Clerk.redirectToSignIn({ redirectUrl: window.location.href });
    }
  } else {
    alert('Authentication is loading. Please try again in a moment.');
  }
}

function isLoggedIn() {
  return clerkReady && window.Clerk && window.Clerk.user;
}

function hasFreeAnalysis() {
  return !localStorage.getItem(FREE_ANALYSIS_KEY);
}

function markFreeUsed() {
  localStorage.setItem(FREE_ANALYSIS_KEY, 'true');
}

async function requireAuth() {
  // First analysis is free
  if (hasFreeAnalysis()) return true;

  // After that, must be logged in
  if (isLoggedIn()) return true;

  // Prompt sign-in
  if (clerkReady && window.Clerk) {
    doSignIn();
    return false;
  }

  // Clerk not loaded — allow anyway (graceful degradation)
  return true;
}

// Initialize Clerk when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initClerk();
  checkPaymentReturn();
});

function checkPaymentReturn() {
  const params = new URLSearchParams(window.location.search);
  const payment = params.get('payment');
  if (payment === 'success') {
    const tier = params.get('tier') || 'per_analysis';
    const msg = tier === 'per_analysis'
      ? 'Payment successful! You have 1 analysis credit.'
      : `Subscription activated! You have unlimited analyses.`;
    // Show a success banner
    const banner = document.createElement('div');
    banner.className = 'payment-success-banner';
    banner.textContent = msg;
    document.body.insertBefore(banner, document.body.firstChild);
    // Clean URL
    window.history.replaceState({}, '', '/');
  } else if (payment === 'cancelled') {
    window.history.replaceState({}, '', '/');
  }
}

// ── CSV Upload ─────────────────────────────────────────
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('csv-file');
const analyzeBtn = document.getElementById('analyze-btn');
const statusEl = document.getElementById('analyze-status');

dropzone.addEventListener('click', (e) => {
  // Don't trigger file picker if clicking on the context input or other interactive elements
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'LABEL') return;
  fileInput.click();
});

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
  // Show filename in the dropzone
  const fileNameEl = document.getElementById('file-name');
  fileNameEl.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  fileNameEl.hidden = false;
  statusEl.textContent = '';
  statusEl.className = 'status';
  analyzeBtn.disabled = false;
}

analyzeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  // Check if user has access — server is the single source of truth
  const userId = (clerkReady && window.Clerk && window.Clerk.user)
    ? window.Clerk.user.id : 'anonymous';

  // If not logged in and localStorage says free is used, require login first
  if (userId === 'anonymous' && !hasFreeAnalysis()) {
    doSignIn();
    return;
  }

  try {
    const accessResp = await fetch(`${API}/api/v1/check-access`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    const access = await accessResp.json();

    if (!access.allowed) {
      // Need to pay
      const remaining = access.credits || 0;
      const used = access.analyses_used || 0;
      statusEl.innerHTML = `You've used ${used} analyses and have ${remaining} credits remaining. <a href="#pricing" style="color:var(--accent)">Purchase more</a> or subscribe for unlimited access.`;
      statusEl.className = 'status error';
      return;
    }
  } catch (e) {
    // If access check fails and user is logged in, allow (graceful degradation)
    // If anonymous, check localStorage
    if (userId === 'anonymous' && !hasFreeAnalysis()) {
      statusEl.textContent = 'Please sign in to continue analyzing.';
      statusEl.className = 'status error';
      return;
    }
    console.log('Access check failed, allowing:', e.message);
  }

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
    markFreeUsed();
    statusEl.textContent = '';

    // Record usage in backend
    const recUserId = (clerkReady && window.Clerk && window.Clerk.user)
      ? window.Clerk.user.id : 'anonymous';
    fetch(`${API}/api/v1/record-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: recUserId }),
    }).catch(() => {});
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
      `<li>At <strong>${t.stimulus_value}</strong> (uncertainty: ${t.uncertainty || t.uncertainty_at_transition})</li>`
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

    let listHtml = '<div class="regime-list">';
    r.regime_map.forEach(seg => {
      listHtml += `<div class="regime-row"><span class="regime-dot regime-${seg.regime}"></span><strong>${seg.regime}</strong><span class="regime-range">${seg.start} — ${seg.end}</span></div>`;
    });
    listHtml += '</div>';

    regEl.innerHTML = barHtml + listHtml;
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
  const segs = r.structural_segments || '';
  document.getElementById('result-segments').textContent = segs ? `${segs} structural segments` : '';
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

  // Cluster screener is always free — no auth gate

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
  document.getElementById('cluster-dband').textContent = '';
  document.getElementById('cluster-disruption').textContent =
    r.shell_model_intact ? 'Standard shell model applies' : 'Modified shell structure';

  // Viability warning
  const warnEl = document.getElementById('cluster-warning');
  if (r.viable_at_operating_temp === false && r.viability_warning) {
    warnEl.textContent = r.viability_warning;
    warnEl.hidden = false;
  } else if (r.coherence_temperature_K) {
    warnEl.textContent = `Coherent up to ${r.coherence_temperature_K}K — viable at ${r.temperature_K}K.`;
    warnEl.hidden = false;
    warnEl.className = 'cluster-viable';
  } else {
    warnEl.hidden = true;
  }
}

// ── Stripe Checkout ────────────────────────────────────
document.querySelectorAll('.buy-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const tier = btn.dataset.tier;

    if (tier === 'industry') {
      window.location.href = 'mailto:support@dsf-ai.com?subject=DSF-AI Industry Plan Inquiry';
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Loading...';

    try {
      const checkoutUserId = (clerkReady && window.Clerk && window.Clerk.user)
        ? window.Clerk.user.id : 'anonymous';
      const resp = await fetch(`${API}/api/v1/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier, user_id: checkoutUserId }),
      });

      if (!resp.ok) throw new Error('Checkout failed');

      const data = await resp.json();
      window.location.href = data.checkout_url;
    } catch (e) {
      alert(`Payment error: ${e.message}`);
      btn.disabled = false;
      btn.textContent = tier === 'academic' ? 'Subscribe' : 'Buy Analysis';
    }
  });
});
