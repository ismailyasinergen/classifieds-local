/* Synthetic, anonymous search acceptance on the isolated developer application only. */
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const assert = require('assert/strict');
const { spawnSync } = require('child_process');
const { chromium } = require('../.browser-test-tools/node_modules/playwright-core');
const root = path.resolve(__dirname, '../..');
const base = 'http://localhost:8089';
const run = crypto.randomBytes(8).toString('hex');
const artifactDir = path.join(root, 'rebuild', 'test-artifacts', 'search', run);
const executablePath = 'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe';
const screenshots = [];
const pageErrors = [];
const failedRequests = [];
let assertions = 0;
let stage = 'fixture';
let browser;
let diagnosticPage;
function check(condition, message) { assert.ok(condition, message); assertions++; }
function fixture() {
  const result = spawnSync('docker', ['compose', '-f', 'rebuild/compose.yaml', '-f', 'rebuild/compose.dev.yaml',
    '-p', 'classifieds-rebuild-dev', 'exec', '-T', 'web', 'python', 'manage.py', 'search_browser_fixture'],
    { cwd: root, input: JSON.stringify({ run }), encoding: 'utf8', timeout: 60000, windowsHide: true });
  if (result.status !== 0) throw new Error('Guarded synthetic fixture failed: ' + result.stderr.slice(-1000));
  return JSON.parse(result.stdout);
}
function listen(page) {
  page.setDefaultTimeout(30000);
  page.setDefaultNavigationTimeout(45000);
  page.on('pageerror', error => pageErrors.push(error.message.slice(0, 300)));
  page.on('requestfailed', request => failedRequests.push(request.failure()?.errorText));
}
async function goto(page, params = {}) {
  const response = await page.goto(base + '/?' + new URLSearchParams(params), { waitUntil: 'domcontentloaded' });
  check(response.status() === 200, 'GET search returns 200');
}
async function submit(page, button = 'Ara', keyboard = false) {
  console.log(JSON.stringify({ checkpoint: stage + ':' + button, before: new URL(page.url()).pathname + new URL(page.url()).search }));
  await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
    keyboard ? page.getByRole('button', { name: button, exact: true }).press('Enter') :
      page.getByRole('button', { name: button, exact: true }).click()]);
  check(new URL(page.url()).origin === base, 'Search stays on developer origin');
}
async function layout(page) {
  const metrics = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    unlabeled: [...document.querySelectorAll('main input:not([type=hidden]), main select')]
      .filter(input => !input.labels?.length).length,
    columns: getComputedStyle(document.querySelector('.search-common-grid')).gridTemplateColumns.split(' ').length
  }));
  check(!metrics.overflow, 'No horizontal overflow');
  check(metrics.unlabeled === 0, 'Every visible search control has an associated label');
  if (page.viewportSize().width === 390) check(metrics.columns === 1, '390px search fields use one column');
}
async function focus(page) {
  await page.getByLabel('Anahtar kelime', { exact: true }).focus();
  await page.keyboard.press('Tab');
  const outline = await page.evaluate(() => ({ tag: document.activeElement.tagName,
    style: getComputedStyle(document.activeElement).outlineStyle,
    width: getComputedStyle(document.activeElement).outlineWidth }));
  check(outline.tag !== 'BODY', 'Keyboard moves to a control');
  check(outline.style !== 'none' && outline.width !== '0px', 'Keyboard focus is visible');
}
async function cards(page) { return page.locator('.listing-card').evaluateAll(items => items.map(item => item.dataset.listingId)); }
async function capture(page, name, locator) {
  check(page.url().startsWith(base + '/?') && !page.url().includes('/accounts/'), 'Synthetic product screenshot only');
  const file = path.join(artifactDir, name + '.png');
  if (locator) await locator.evaluate(element => element.scrollIntoView({ block: 'start' }));
  await page.screenshot({ path: file, fullPage: false });
  const bytes = fs.readFileSync(file);
  screenshots.push({ path: path.relative(root, file).replace(/\\/g, '/'), bytes: bytes.length,
    sha256: crypto.createHash('sha256').update(bytes).digest('hex'), viewport: page.viewportSize() });
}
(async () => {
  fs.mkdirSync(artifactDir, { recursive: true });
  const data = fixture();
  check(data.count === 25 && new Set(data.order).size === 25, '25 fresh synthetic tied rows');
  stage = 'launch';
  browser = await chromium.launch({ headless: true, executablePath });
  const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'tr-TR', reducedMotion: 'reduce' });
  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'tr-TR',
    isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
  const noJSContext = await browser.newContext({ viewport: { width: 390, height: 844 },
    javaScriptEnabled: false, locale: 'tr-TR' });
  const desktop = await desktopContext.newPage(), mobile = await mobileContext.newPage(), noJS = await noJSContext.newPage();
  for (const page of [desktop, mobile, noJS]) listen(page);
  const params = { category: String(data.category), q: 'BMW X5', location: 'sisli',
    currency: 'try', price_min: '245000', price_max: '245000', sort: 'price_asc' };
  stage = 'desktop-fields-and-filters';
  await goto(desktop, params);
  await layout(desktop); await focus(desktop);
  for (const label of ['Anahtar kelime', 'Kategori', 'Kategori kapsamı', 'Konum', 'Para birimi',
    'En az fiyat', 'En çok fiyat', 'Sıralama', 'Model yılı — en az', 'Model yılı — en çok',
    'Motor hacmi — en az', 'Motor hacmi — en çok', 'Elektrikli', 'Renk', 'Donanım']) {
    check(await desktop.getByLabel(label, { exact: true }).count() === 1, 'Turkish field label: ' + label);
  }
  check(await desktop.locator('input[name="a.internal.eq"]').count() === 0, 'Explicit false filter hidden');
  check(await desktop.getByLabel('Renk', { exact: true }).locator('option[value="Mavi"]').count() === 1,
    'Compatible older option represented');
  await desktop.getByLabel('Elektrikli', { exact: true }).selectOption('false');
  await desktop.getByLabel('Motor hacmi — en az', { exact: true }).fill('2.00');
  await desktop.getByLabel('Model yılı — en az', { exact: true }).fill('2022');
  await submit(desktop);
  check((await cards(desktop)).join() === data.order.slice(0, 12).join(), 'First page stable UUID ties');
  const next = desktop.getByRole('link', { name: 'Sonraki', exact: true });
  const canonical = new URL(await next.getAttribute('href'), base);
  check(canonical.searchParams.getAll('page').join() === '2', 'Exactly one page parameter');
  check(canonical.searchParams.get('currency') === 'TRY', 'Currency is canonical');
  check(canonical.searchParams.get('a.area.min') === '2', 'Decimal criterion canonical');
  check(canonical.searchParams.get('a.electric.eq') === 'false', 'False survives pagination');
  check(canonical.searchParams.has('schemas'), 'Frozen schema refs survive pagination');
  const firstIds = await cards(desktop);
  const image = desktop.locator('.listing-card img').first();
  await image.scrollIntoViewIfNeeded();
  await image.waitFor({ state: 'visible' });
  await desktop.waitForFunction(() => { const item = document.querySelector('.listing-card img'); return item?.complete && item.naturalWidth > 0; });
  check(await image.evaluate(item => item.complete && item.naturalWidth > 0), 'Current public derivative loaded');
  await desktop.locator('#search-results').scrollIntoViewIfNeeded();
  await capture(desktop, 'desktop-results', desktop.locator('#search-results'));
  await next.click(); await desktop.waitForLoadState('domcontentloaded');
  const secondIds = await cards(desktop);
  check(secondIds.join() === data.order.slice(12, 24).join(), 'Second page stable UUID ties');
  check(!secondIds.some(id => firstIds.includes(id)), 'Pages do not overlap');
  await desktop.goBack({ waitUntil: 'domcontentloaded' });
  check((await cards(desktop)).join() === firstIds.join(), 'Back restores criteria and first page');
  await desktop.getByLabel('Anahtar kelime', { exact: true }).fill('BMW');
  await submit(desktop);
  check(!new URL(desktop.url()).searchParams.has('page'), 'New search resets page');
  stage = 'numeric-equality-replay';
  await goto(desktop, { ...params, schema: String(data.source.id), schema_version: String(data.source.version),
    'a.area.eq': '2.00' });
  check(await desktop.getByLabel('Motor hacmi — tam değer', { exact: true }).inputValue() === '2',
    'Canonical numeric equality reopens as its own control');
  check(await desktop.locator('[name="a.area.min"], [name="a.area.max"]').count() === 0,
    'Numeric equality does not render conflicting range controls');
  await submit(desktop);
  check((await cards(desktop)).join() === data.order.slice(0, 12).join(),
    'Numeric equality survives a new native GET submit');
  await desktopContext.close();

  stage = 'mobile-results-and-category-reset';
  const mobileParams = Object.fromEntries(canonical.searchParams);
  delete mobileParams.page;
  await goto(mobile, mobileParams);
  await layout(mobile); await focus(mobile);
  await mobile.locator('.search-panel').scrollIntoViewIfNeeded();
  await capture(mobile, 'mobile-filters', mobile.locator('.search-panel'));
  await mobile.locator('#search-results').evaluate(element => element.scrollIntoView({ block: 'start' }));
  await mobile.waitForFunction(() => { const item = document.querySelector('.listing-card img'); return item?.complete && item.naturalWidth > 0; });
  await capture(mobile, 'mobile-results', mobile.locator('#search-results'));
  await mobile.getByLabel('Kategori', { exact: true }).selectOption(String(data.other));
  await submit(mobile);
  check(await mobile.locator('#search-errors').count() === 1, 'Stale category identity is visible error');
  check(await mobile.locator('#search-results').count() === 0, 'Invalid criteria have no fake results');
  await submit(mobile, 'Kategoriyi uygula');
  check(await mobile.getByLabel('Alan — en az', { exact: true }).count() === 1, 'Explicit category apply loads new controls');
  const resetURL = new URL(mobile.url());
  check(![...resetURL.searchParams.keys()].some(key => key.startsWith('a.') || ['schema', 'schema_version', 'schemas', 'page'].includes(key)),
    'Category apply clears old attributes, identities and page');
  check(resetURL.searchParams.get('q') === 'BMW X5' && resetURL.searchParams.get('currency') === 'TRY',
    'Category apply retains common criteria');
  check(await mobile.getByText('Bu ölçütlerle ilan bulunamadı.', { exact: true }).count() === 1,
    'Legitimate empty search is distinct');
  await mobileContext.close();

  stage = 'no-javascript';
  diagnosticPage = noJS;
  await goto(noJS, { category: String(data.category) });
  await layout(noJS);
  await noJS.getByLabel('Anahtar kelime', { exact: true }).fill('BMW X5');
  await noJS.getByLabel('Para birimi', { exact: true }).fill('TRY');
  await noJS.getByLabel('Sıralama', { exact: true }).selectOption('price_asc');
  await noJS.getByLabel('Elektrikli', { exact: true }).selectOption('false');
  await submit(noJS, 'Ara', true);
  check((await cards(noJS)).join() === data.order.slice(0, 12).join(), 'No-JS GET search succeeds');
  await noJS.getByRole('link', { name: 'Sonraki', exact: true }).click();
  check((await cards(noJS)).join() === data.order.slice(12, 24).join(), 'No-JS canonical pagination succeeds');
  await noJS.getByLabel('Kategori', { exact: true }).selectOption(String(data.parent));
  await noJS.getByLabel('Kategori kapsamı', { exact: true }).selectOption('tree');
  await submit(noJS, 'Kategoriyi uygula', true);
  check(await noJS.locator('[name^="a."]').count() === 0, 'Tree has no named attribute controls');
  check((await cards(noJS)).length === 12, 'No-JS tree category apply succeeds');
  await noJS.getByLabel('Para birimi', { exact: true }).fill('');
  await submit(noJS, 'Ara', true);
  check(await noJS.locator('#id_currency').getAttribute('aria-invalid') === 'true', 'No-JS price/sort dependency linked error');
  check(await noJS.locator('#search-results').count() === 0, 'No-JS error has no fake results');
  await noJS.getByRole('link', { name: 'Filtreleri temizle', exact: true }).first().click();
  check(new URL(noJS.url()).search === '', 'Reset returns unfiltered root');
  check(await noJS.locator('[name^="a."]').count() === 0, 'Unselected root has no named attributes');
  check(pageErrors.length === 0, 'No browser page errors');
  check(failedRequests.filter(item => !item?.includes('ERR_ABORTED')).length === 0, 'No unexpected network failures');
  const result = { result: 'PASS', run, assertions, driver: require('../.browser-test-tools/node_modules/playwright-core/package.json').version,
    browser: browser.version(), javaScriptDisabled: true, tiedRows: 25, pageErrors: pageErrors.length,
    unexpectedRequestFailures: failedRequests.filter(item => !item?.includes('ERR_ABORTED')).length, screenshots };
  fs.writeFileSync(path.join(artifactDir, 'summary.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
})().catch(async error => {
  if (diagnosticPage) try { console.log(JSON.stringify({ diagnostic: await diagnosticPage.evaluate(() => ({ url: location.pathname + location.search, forms: [...document.forms].map(form => ({ action: form.getAttribute('action'), noValidate: form.noValidate, invalid: [...form.elements].filter(e => e.validity && !e.validity.valid).map(e => e.name), buttons: [...form.querySelectorAll('button')].map(e => ({ text: e.textContent, disabled: e.disabled })) })) })) })); } catch (diagnosticError) { console.log(JSON.stringify({ diagnostic: 'Unavailable during navigation' })); }
  console.log(JSON.stringify({ result: 'FAIL', run, stage, assertions, error: error.message.slice(0, 1600) }));
  process.exitCode = 1;
}).finally(async () => { if (browser) await browser.close(); });
