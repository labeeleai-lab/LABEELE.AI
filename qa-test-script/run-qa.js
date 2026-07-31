/**
 * Self-service QA script for the logged-in areas of labeele.ai
 * (dashboard, account, admin pages) that Claude cannot test directly,
 * since Claude never enters passwords or authenticates on your behalf.
 *
 * YOU run this yourself, on your own machine, with your own credentials.
 * Your password is only ever read from environment variables you set on
 * your own machine and typed into the real login form by Playwright's
 * browser automation - it is never sent anywhere else, logged, or seen
 * by Claude.
 *
 * SETUP (one time):
 *   cd qa-test-script
 *   npm install playwright
 *   npx playwright install chromium
 *
 * RUN:
 *   Windows PowerShell:
 *     $env:LABEELE_TEST_EMAIL="your-email@example.com"
 *     $env:LABEELE_TEST_PASSWORD="your-password"
 *     node run-qa.js
 *
 *   Bash:
 *     LABEELE_TEST_EMAIL="your-email@example.com" LABEELE_TEST_PASSWORD="your-password" node run-qa.js
 *
 * OUTPUT:
 *   Creates ./qa-output/ with screenshots of every page visited, a
 *   console-errors.json listing any browser console errors per page, and
 *   a summary.json with pass/fail per step. Share that folder back with
 *   Claude (or just the summary.json + console-errors.json) and it can be
 *   folded straight into the QA report - no credentials are in that output.
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.LABEELE_BASE_URL || 'https://www.labeele.ai';
const EMAIL = process.env.LABEELE_TEST_EMAIL;
const PASSWORD = process.env.LABEELE_TEST_PASSWORD;
const OUT_DIR = path.join(__dirname, 'qa-output');

if (!EMAIL || !PASSWORD) {
  console.error('Set LABEELE_TEST_EMAIL and LABEELE_TEST_PASSWORD environment variables first. See the comment at the top of this file for exact commands.');
  process.exit(1);
}

fs.mkdirSync(OUT_DIR, { recursive: true });

const summary = [];
const consoleErrorsByPage = {};

function record(step, status, detail) {
  summary.push({ step, status, detail: detail || '', timestamp: new Date().toISOString() });
  console.log(`[${status.toUpperCase()}] ${step}${detail ? ' - ' + detail : ''}`);
}

async function screenshot(page, name) {
  await page.screenshot({ path: path.join(OUT_DIR, `${name}.png`), fullPage: true });
}

function attachConsoleListener(page, label) {
  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  consoleErrorsByPage[label] = errors;
  return errors;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  try {
    // 1. Login
    attachConsoleListener(page, 'login');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await screenshot(page, '01-login-filled');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    const url = page.url();
    if (url.includes('/dashboard')) {
      record('Login', 'pass', `Redirected to ${url}`);
    } else {
      record('Login', 'fail', `Expected redirect to /dashboard, got ${url}`);
      await screenshot(page, '01-login-failed');
    }
    await screenshot(page, '02-post-login');

    // 2. Dashboard
    attachConsoleListener(page, 'dashboard');
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: 'networkidle' });
    await screenshot(page, '03-dashboard');
    record('Dashboard loads', 'pass', page.url());

    // Try asking DUKE (first agent button) a simple test question, if the form exists
    try {
      const textarea = await page.$('textarea');
      if (textarea) {
        await textarea.fill('This is an automated QA test question - please give a short reply.');
        await screenshot(page, '04-dashboard-query-filled');
        const sendButton = await page.$('button:has-text("Send")');
        if (sendButton) {
          await sendButton.click();
          await page.waitForTimeout(20000); // real generation can take a while
          await screenshot(page, '05-dashboard-query-result');
          record('Dashboard: submit a query', 'pass', 'Submitted - see 05-dashboard-query-result.png for the actual response');
        } else {
          record('Dashboard: submit a query', 'fail', 'Send button not found');
        }
      } else {
        record('Dashboard: submit a query', 'fail', 'Query textarea not found');
      }
    } catch (e) {
      record('Dashboard: submit a query', 'fail', String(e));
    }

    // 3. Account page
    attachConsoleListener(page, 'account');
    await page.goto(`${BASE_URL}/account`, { waitUntil: 'networkidle' });
    await screenshot(page, '06-account');
    record('Account page loads', page.url().includes('/account') ? 'pass' : 'fail', page.url());

    // 4. Admin (only works if this account is an admin - failure here just means it isn't, not a bug)
    attachConsoleListener(page, 'admin');
    await page.goto(`${BASE_URL}/admin`, { waitUntil: 'networkidle' });
    await screenshot(page, '07-admin-overview');
    if (page.url().includes('/admin')) {
      record('Admin overview loads', 'pass', page.url());

      for (const sub of ['training', 'personas', 'knowledge', 'annotate', 'code', 'team']) {
        try {
          await page.goto(`${BASE_URL}/admin/${sub}`, { waitUntil: 'networkidle' });
          await page.waitForTimeout(1500);
          await screenshot(page, `08-admin-${sub}`);
          record(`Admin: /admin/${sub}`, 'pass', page.url());
        } catch (e) {
          record(`Admin: /admin/${sub}`, 'fail', String(e));
        }
      }
    } else {
      record('Admin overview loads', 'info', `Redirected to ${page.url()} - this account is likely not an admin, which is expected behavior, not a bug`);
    }

    // 5. Logout
    attachConsoleListener(page, 'logout');
    try {
      const signOutButton = await page.$('button:has-text("Sign out")');
      if (signOutButton) {
        await signOutButton.click();
        await page.waitForTimeout(2000);
        await screenshot(page, '09-post-logout');
        record('Sign out', page.url().includes('/login') || page.url() === `${BASE_URL}/` ? 'pass' : 'fail', page.url());
      } else {
        record('Sign out', 'fail', 'Sign out button not found');
      }
    } catch (e) {
      record('Sign out', 'fail', String(e));
    }
  } catch (err) {
    record('Unhandled error during QA run', 'fail', String(err));
  } finally {
    await browser.close();
  }

  fs.writeFileSync(path.join(OUT_DIR, 'summary.json'), JSON.stringify(summary, null, 2));
  fs.writeFileSync(path.join(OUT_DIR, 'console-errors.json'), JSON.stringify(consoleErrorsByPage, null, 2));

  console.log(`\nDone. Results written to ${OUT_DIR}`);
  console.log('Share summary.json, console-errors.json, and the screenshots back with Claude to fold into the QA report.');
}

main();
