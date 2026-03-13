import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { chromium } from 'playwright';

function parseArgs(argv) {
  const args = {
    baseUrl: process.env.TFE_VALIDATION_BASE_URL || process.env.TFE_BASE_URL || 'https://taofinancialengine.com',
    outDir: '',
    username: process.env.TFE_VALIDATION_USERNAME || process.env.TFE_LOGIN_USERNAME || process.env.TFE_USERNAME || '',
    password: process.env.TFE_VALIDATION_PASSWORD || process.env.TFE_LOGIN_PASSWORD || process.env.TFE_PASSWORD || '',
    timeoutMs: 120000,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    const next = argv[i + 1];
    if (token === '--base-url' && next) {
      args.baseUrl = next.trim();
      i += 1;
      continue;
    }
    if (token === '--out-dir' && next) {
      args.outDir = next.trim();
      i += 1;
      continue;
    }
    if (token === '--username' && next) {
      args.username = next;
      i += 1;
      continue;
    }
    if (token === '--password' && next) {
      args.password = next;
      i += 1;
      continue;
    }
    if (token === '--timeout-ms' && next) {
      const n = Number(next);
      if (Number.isFinite(n) && n > 0) {
        args.timeoutMs = Math.floor(n);
      }
      i += 1;
      continue;
    }
    throw new Error(`Unknown or malformed argument: ${token}`);
  }

  if (!args.outDir) {
    throw new Error('Missing required --out-dir argument.');
  }

  return args;
}

function nowIso() {
  return new Date().toISOString();
}

async function writeJson(targetPath, payload) {
  await fs.mkdir(path.dirname(targetPath), { recursive: true });
  await fs.writeFile(targetPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}

function trimBody(body, limit = 5000) {
  if (body.length <= limit) return body;
  return `${body.slice(0, limit)}\n...[truncated]`;
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  const baseUrl = String(args.baseUrl).replace(/\/+$/, '');
  const outDir = path.resolve(args.outDir);

  await fs.mkdir(outDir, { recursive: true });

  const pages = [
    {
      key: 'recommendations',
      route: '/recommendations',
      apiRoute: '/api/recommendations/list?page=1&pageSize=5',
      requiresAuth: true,
    },
    {
      key: 'screener',
      route: '/screener',
      apiRoute: '/api/screener?page=1&pageSize=5',
      requiresAuth: true,
    },
    {
      key: 'watchlist',
      route: '/watchlist',
      apiRoute: '/api/watchlist',
      requiresAuth: true,
    },
    {
      key: 'portfolio',
      route: '/portfolio',
      apiRoute: '/api/portfolio',
      requiresAuth: true,
    },
    {
      key: 'admin_refresh_log',
      route: '/admin-console/refresh-log',
      apiRoute: '/api/admin/refresh/log',
      requiresAuth: true,
    },
    {
      key: 'home',
      route: '/',
      apiRoute: null,
      requiresAuth: false,
    },
  ];

  const summary = {
    generated_at_utc: nowIso(),
    base_url: baseUrl,
    out_dir: outDir,
    auth: {
      attempted: Boolean(args.username && args.password),
      signed_in: false,
      sign_in_status: null,
      sign_in_error: null,
      session_status: null,
      session_body_sample: null,
    },
    page_results: [],
    overall_pass: false,
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  page.setDefaultTimeout(args.timeoutMs);

  try {
    if (summary.auth.attempted) {
      const signInResp = await context.request.post(`${baseUrl}/api/auth/sign-in`, {
        data: {
          username: args.username,
          password: args.password,
        },
      });
      summary.auth.sign_in_status = signInResp.status();
      if (signInResp.ok()) {
        summary.auth.signed_in = true;
      } else {
        const text = await signInResp.text();
        summary.auth.sign_in_error = trimBody(text, 800);
      }
    }

    const sessionResp = await context.request.get(`${baseUrl}/api/auth/session`);
    summary.auth.session_status = sessionResp.status();
    summary.auth.session_body_sample = trimBody(await sessionResp.text(), 1200);

    for (const cfg of pages) {
      const result = {
        page: cfg.key,
        route: cfg.route,
        requires_auth: cfg.requiresAuth,
        page_url: `${baseUrl}${cfg.route}`,
        page_status: null,
        screenshot: `${cfg.key}.png`,
        api_route: cfg.apiRoute,
        api_status: null,
        api_response_file: cfg.apiRoute ? `${cfg.key}-api.json` : null,
        pass: false,
        fail_reasons: [],
      };

      const pageResp = await page.goto(result.page_url, {
        waitUntil: 'domcontentloaded',
        timeout: args.timeoutMs,
      });
      result.page_status = pageResp ? pageResp.status() : null;

      await page.waitForTimeout(2500);
      await page.screenshot({ path: path.join(outDir, result.screenshot), fullPage: true });

      if (cfg.apiRoute) {
        const apiResp = await context.request.get(`${baseUrl}${cfg.apiRoute}`);
        const apiBody = await apiResp.text();
        result.api_status = apiResp.status();
        await writeJson(path.join(outDir, result.api_response_file), {
          status: apiResp.status(),
          headers: apiResp.headers(),
          body: trimBody(apiBody, 20000),
        });
      }

      if (result.page_status !== 200) {
        result.fail_reasons.push(`page_status_${result.page_status}`);
      }
      if (cfg.apiRoute && result.api_status !== 200) {
        result.fail_reasons.push(`api_status_${result.api_status}`);
      }
      if (cfg.requiresAuth && !summary.auth.signed_in) {
        result.fail_reasons.push('not_authenticated');
      }

      result.pass = result.fail_reasons.length === 0;
      summary.page_results.push(result);
    }

    summary.overall_pass = summary.page_results.every((item) => item.pass);
  } finally {
    await browser.close();
  }

  await writeJson(path.join(outDir, 'summary.json'), summary);
  process.stdout.write(`${outDir}\n`);
  process.stdout.write(`${JSON.stringify({ overall_pass: summary.overall_pass }, null, 2)}\n`);
}

run().catch(async (error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`page_confidence_probe_error: ${message}\n`);
  process.exitCode = 1;
});
