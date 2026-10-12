/* Guarded, real MFA UI acceptance. Sensitive values never leave process memory. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const EXPECTED_ROOT = 'c:/users/ismai/.devspace/worktrees/classifieds_local-a7be577c';
const ORIGINAL_ROOT = 'c:/users/ismai/desktop/classifieds_local';
const BASE = 'http://localhost:8089';
const PROJECT = 'classifieds-rebuild-dev';
const MODES = ['desktop', 'mobile', 'nojs'];
const ROLES = MODES.flatMap(mode => ['staff', 'reviewer', 'seller'].map(role => mode + '-' + role));
const STAGES = new Set(['guard', 'create', 'staff', 'reviewer', 'seller', 'complete']);
const OPERATIONS = new Set(['guard', 'fixture', 'browser', 'navigation', 'form_submit', 'fill_code',
  'read_recovery', 'screenshot', 'assertion', 'supplementary_http']);
function ensure(condition) { if (!condition) throw new Error('Controlled acceptance condition failed.'); }
function normalize(value) {
  let result = String(value).replace(/\\/g, '/').toLowerCase().replace(/\/$/, '');
  result = result.replace(/^\/run\/desktop\/mnt\/host\/c\//, 'c:/').replace(/^\/host_mnt\/c\//, 'c:/');
  return result;
}
function validateRuntime(root, base, records) {
  ensure(normalize(root) === EXPECTED_ROOT && base === BASE && Array.isArray(records) && records.length === 6);
  const [web, db, redis, originalWeb, originalDB, originalRedis] = records;
  ensure(new Set(records.map(item => item.id)).size === 6);
  for (const [item, project, service] of [[web, PROJECT, 'web'], [db, PROJECT, 'db'], [redis, PROJECT, 'redis'],
    [originalWeb, 'classifieds-rebuild', 'web'], [originalDB, 'classifieds-rebuild', 'db'], [originalRedis, 'classifieds-rebuild', 'redis']]) {
    ensure(item.project === project && item.service === service && item.running === true && String(item.oneoff).toLowerCase() === 'false');
    ensure(Array.isArray(item.mounts) && item.networks && item.ports && typeof item.id === 'string');
  }
  for (const item of [web, db, redis]) {
    ensure(normalize(item.workingDirectory) === EXPECTED_ROOT + '/rebuild');
    const configs = item.configFiles.split(',').map(normalize).sort();
    ensure(JSON.stringify(configs) === JSON.stringify([EXPECTED_ROOT + '/rebuild/compose.dev.yaml', EXPECTED_ROOT + '/rebuild/compose.yaml'].sort()));
    ensure(JSON.stringify(Object.keys(item.networks)) === JSON.stringify([PROJECT + '_default']));
  }
  for (const [item, source, port] of [[web, EXPECTED_ROOT, '8089'], [originalWeb, ORIGINAL_ROOT, '8088']]) {
    const binding = item.ports['8000/tcp'];
    ensure(Array.isArray(binding) && binding.length === 1 && binding[0].HostIp === '127.0.0.1' && binding[0].HostPort === port);
    ensure(Object.entries(item.ports).every(([key, value]) => key === '8000/tcp' || value === null));
    const bind = item.mounts.filter(mount => mount.Destination === '/app');
    ensure(bind.length === 1 && bind[0].RW === false && normalize(bind[0].Source) === source + '/rebuild/backend');
  }
  for (const [item, destination, suffix] of [[web, '/var/lib/classifieds/media', 'rebuild_media'],
    [db, '/var/lib/postgresql/data', 'rebuild_postgres'], [redis, '/data', 'rebuild_redis']]) {
    const mounts = item.mounts.filter(mount => mount.Destination === destination);
    ensure(mounts.length === 1 && mounts[0].Name === PROJECT + '_' + suffix && mounts[0].Type === 'volume');
  }
  const devVolumes = new Set([web, db, redis].flatMap(item => item.mounts.map(mount => mount.Name).filter(Boolean)));
  const devNetworks = new Set([web, db, redis].flatMap(item => Object.values(item.networks).map(network => network.NetworkID)));
  ensure(!devNetworks.has(undefined));
  for (const item of [originalWeb, originalDB, originalRedis]) {
    ensure(!item.mounts.some(mount => mount.Name && devVolumes.has(mount.Name)));
    ensure(!Object.values(item.networks).some(network => devNetworks.has(network.NetworkID)));
  }
  for (const item of [db, redis, originalDB, originalRedis]) ensure(Object.values(item.ports).every(value => value === null));
  const address = db.networks[PROJECT + '_default'].IPAddress;
  ensure(typeof address === 'string' && /^(\d{1,3}\.){3}\d{1,3}$/.test(address) && address.split('.').every(value => Number(value) <= 255));
  return address;
}
function failureRecord(stage, operation, error) {
  return { stage: STAGES.has(stage) ? stage : 'unknown', operation: OPERATIONS.has(operation) ? operation : 'unknown',
    kind: error && error.name === 'TimeoutError' ? 'timeout' : 'verification_error' };
}
function forbiddenDiagnosis(body) {
  if (/CSRF/i.test(body)) {
    if (/cookie not set/i.test(body)) return 'csrf_cookie_missing';
    if (/Origin checking failed/i.test(body)) return 'csrf_origin';
    if (/token/i.test(body)) return 'csrf_token';
    return 'csrf_other';
  }
  return 'other_forbidden';
}
function screenshotAllowed(url, base, sensitiveElements) {
  try { const target = new URL(url); return target.origin === base && target.pathname === '/accounts/security/' &&
    !target.search && !target.hash && sensitiveElements === false; } catch { return false; }
}
function totp(secret, milliseconds = Date.now()) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const character of secret.replace(/=+$/, '')) { const value = alphabet.indexOf(character); ensure(value >= 0); bits += value.toString(2).padStart(5, '0'); }
  const bytes = []; for (let at = 0; at + 8 <= bits.length; at += 8) bytes.push(parseInt(bits.slice(at, at + 8), 2));
  const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(milliseconds / 30000)));
  const digest = crypto.createHmac('sha1', Buffer.from(bytes)).update(counter).digest();
  const offset = digest[digest.length - 1] & 15;
  return String((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, '0');
}
module.exports = { validateRuntime, failureRecord, forbiddenDiagnosis, screenshotAllowed, totp };

async function main() {
  const { chromium } = require('../.browser-test-tools/node_modules/playwright-core');
  const root = path.resolve(__dirname, '../..');
  const run = crypto.randomBytes(8).toString('hex');
  const artifactDir = path.join(root, 'rebuild/test-artifacts/mfa', run);
  const passwords = Object.fromEntries(ROLES.map(role => [role, crypto.randomBytes(32).toString('base64url')]));
  const emails = Object.fromEntries(ROLES.map(role => [role, 'mfa-' + run + '-' + role + '@browser.example.test']));
  const secrets = new Set([...Object.values(passwords), ...Object.values(emails)]);
  const checks = [], uiPosts = [], supplementaryHTTP = [], screenshots = [];
  const contexts = [], lastTotp = new Map(), loginTimes = [];
  const executablePath = 'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe';
  let stage = 'guard', operation = 'guard', mode = 'desktop', role = 'staff', lastCheck = '';
  let browser, dbAddress, receipt, initialState, finalState, createdArtifacts = false;
  let pageErrors = 0, requestFailures = 0, blockedExternalRequests = 0, asyncFailures = 0, navigations = 0, linkClicks = 0;
  const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
  function check(condition, label) { lastCheck = label; operation = 'assertion'; ensure(condition); checks.push(label); }
  function same(actual, expected, label) { check(JSON.stringify(actual) === JSON.stringify(expected), label); }
  function state(result, extra = {}) { return { result, run, stage, mode, assertions: checks.length, checks,
    contexts: contexts.length, navigations, linkClicks, uiPosts, supplementaryHTTP, screenshots,
    pageErrors, unexpectedRequestFailures: requestFailures, blockedExternalRequests, asyncFailures, ...extra }; }
  function persist(result, extra = {}) {
    if (createdArtifacts) fs.writeFileSync(path.join(artifactDir, 'summary.json'), JSON.stringify(state(result, extra), null, 2) + '\n');
  }
  function checkpoint(next) { stage = next; persist('RUNNING'); console.log(JSON.stringify({ run, mode, stage, assertions: checks.length })); }
  function docker(args, input) {
    const result = spawnSync('docker', args, { cwd: root, input, encoding: 'utf8', timeout: 60000, windowsHide: true, maxBuffer: 8 * 1024 * 1024 });
    ensure(result.status === 0 && !result.error); return result.stdout;
  }
  function guard() {
    operation = 'guard';
    // Project/service identity only. Config.Env is deliberately never requested.
    const projection = '{"id":{{json .Id}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},' +
      '"service":{{json (index .Config.Labels "com.docker.compose.service")}},"oneoff":{{json (index .Config.Labels "com.docker.compose.oneoff")}},' +
      '"workingDirectory":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}},' +
      '"configFiles":{{json (index .Config.Labels "com.docker.compose.project.config_files")}},"running":{{json .State.Running}},' +
      '"mounts":{{json .Mounts}},"networks":{{json .NetworkSettings.Networks}},"ports":{{json .NetworkSettings.Ports}}}';
    const names = [PROJECT + '-web-1', PROJECT + '-db-1', PROJECT + '-redis-1',
      'classifieds-rebuild-web-1', 'classifieds-rebuild-db-1', 'classifieds-rebuild-redis-1'];
    const records = docker(['inspect', '--format', projection, ...names]).trim().split(/\r?\n/).map(line => JSON.parse(line));
    dbAddress = validateRuntime(root, BASE, records);
    check(true, 'Exact developer runtime, source, loopback and disjoint persistent identities verified');
  }
  function fixture(action) {
    operation = 'fixture';
    const input = { action, run, db_address: dbAddress };
    if (action === 'create') input.passwords = passwords; else input.receipt = receipt;
    const result = JSON.parse(docker(['compose', '-f', 'rebuild/compose.yaml', '-f', 'rebuild/compose.dev.yaml',
      '-p', PROJECT, 'exec', '-T', 'web', 'python', 'manage.py', 'mfa_browser_fixture'], JSON.stringify(input)));
    if (action === 'create') { receipt = result.receipt; secrets.add(receipt); return result.state; }
    return result;
  }
  function local(route) {
    const target = new URL(route, BASE); ensure(target.origin === BASE && target.protocol === 'http:'); return target.href;
  }
  async function remember(page) {
    for (const cookie of await page.context().cookies()) secrets.add(cookie.value);
    for (const input of await page.locator('input[type=hidden]').all()) { const value = await input.inputValue(); if (value) secrets.add(value); }
  }
  async function privateHeaders(response) {
    const values = await response.allHeaders();
    check((values['cache-control'] || '').includes('private') && (values['cache-control'] || '').includes('no-store'), 'Security response is private/no-store');
    check(values['x-content-type-options'] === 'nosniff', 'Security response is nosniff');
    check(values['referrer-policy'] === 'same-origin', 'Security response suppresses cross-origin referrers and preserves CSRF');
  }
  async function makePage(actorRole, selectedMode = mode) {
    operation = 'browser';
    const context = await browser.newContext({ viewport: selectedMode === 'mobile' ? { width: 390, height: 844 } : { width: 1440, height: 1000 },
      locale: 'tr-TR', reducedMotion: 'reduce', javaScriptEnabled: selectedMode !== 'nojs', serviceWorkers: 'block', acceptDownloads: false });
    contexts.push(context);
    await context.route('**/*', async route => {
      try {
        const target = new URL(route.request().url());
        if (target.origin === BASE && target.protocol === 'http:') await route.continue();
        else { blockedExternalRequests += 1; await route.abort('blockedbyclient'); }
      } catch { asyncFailures += 1; }
    });
    const page = await context.newPage();
    page.setDefaultTimeout(12000); page.setDefaultNavigationTimeout(20000);
    page.on('pageerror', () => { pageErrors += 1; });
    page.on('requestfailed', request => { if (request.failure()?.errorText !== 'net::ERR_ABORTED') requestFailures += 1; });
    page.actorRole = actorRole;
    return page;
  }
  async function go(page, route, expectedStatus = 200) {
    operation = 'navigation';
    const response = await page.goto(local(route), { waitUntil: 'domcontentloaded' }); navigations += 1;
    check(response && response.status() === expectedStatus, 'Real navigation has expected status');
    check(new URL(page.url()).origin === BASE, 'Real navigation remains on developer origin');
    await remember(page); return response;
  }
  async function follow(page, label) {
    operation = 'navigation';
    const link = page.locator('main').getByRole('link', { name: label, exact: true });
    local(await link.getAttribute('href'));
    const [response] = await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded' }), link.click()]);
    linkClicks += 1; navigations += 1;
    check(response && response.status() === 200 && new URL(page.url()).origin === BASE, 'Real link navigation stays on developer origin');
    await remember(page); return response;
  }
  async function submit(page, button, action, keyboard = mode !== 'mobile') {
    operation = 'form_submit'; await remember(page);
    const [response] = await Promise.all([
      page.waitForResponse(value => value.request().method() === 'POST' && new URL(value.url()).origin === BASE && value.request().isNavigationRequest()),
      page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
      keyboard ? button.press('Enter') : button.click(),
    ]);
    const diagnosis = response.status() === 403 ? forbiddenDiagnosis(await response.text()) : 'not_forbidden';
    const sentOrigin = (await response.request().allHeaders()).origin;
    const originKind = sentOrigin === BASE ? 'same_origin' : sentOrigin === 'null' ? 'opaque_null' : sentOrigin === undefined ? 'absent' : 'other';
    uiPosts.push({ mode, role: page.actorRole, action, status: response.status(), diagnosis, originKind, input: keyboard ? 'keyboard Enter' : 'pointer click' });
    navigations += 1; check(new URL(page.url()).origin === BASE, 'Real form submission stays on developer origin');
    await remember(page); await privateHeaders(response); return response;
  }
  async function layout(page) {
    const metrics = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      unlabeled: [...document.querySelectorAll('main input:not([type=hidden]),main textarea,main select')].filter(element => !element.labels?.length).length }));
    check(!metrics.overflow, mode + ': no horizontal document overflow');
    check(metrics.unlabeled === 0, mode + ': visible form inputs have labels');
  }
  async function focusCode(page) {
    await page.getByLabel('Doğrulama kodu', { exact: true }).focus(); await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => ({ tag: document.activeElement.tagName,
      outline: getComputedStyle(document.activeElement).outlineStyle, width: getComputedStyle(document.activeElement).outlineWidth }));
    check(focused.tag === 'BUTTON' && focused.outline !== 'none' && parseFloat(focused.width) > 0, mode + ': keyboard submit focus is visible');
  }
  async function freshTotp(secret, minimumRemaining = 5) {
    while (Math.floor(Date.now() / 30000) === lastTotp.get(secret) || 30 - ((Date.now() / 1000) % 30) < minimumRemaining) await sleep(150);
    const step = Math.floor(Date.now() / 30000); const code = totp(secret); lastTotp.set(secret, step); secrets.add(code); return { code, step };
  }
  async function typeCode(page, code, action) {
    operation = 'fill_code'; secrets.add(code);
    await page.getByLabel('Doğrulama kodu', { exact: true }).fill(code);
    return submit(page, page.locator('main form button[type=submit]'), action);
  }
  async function readCodes(page) {
    operation = 'read_recovery';
    const codes = (await page.locator('ol.recovery-codes code').allTextContents()).map(value => value.trim());
    check(codes.length === 10 && codes.every(value => /^\d{8}$/.test(value)) && new Set(codes).size === 10, 'First UI view supplies ten distinct eight-digit recovery codes');
    codes.forEach(code => secrets.add(code)); await layout(page); return codes;
  }
  async function security(page, proven = true) {
    const response = await go(page, '/accounts/security/'); await privateHeaders(response);
    if (proven) check((await page.locator('main').innerText()).includes('İki adımlı doğrulama tamamlandı'), 'Security overview confirms real current-session proof');
    await layout(page); return response;
  }
  async function pair(page) {
    await security(page, false);
    await privateHeaders(await follow(page, 'Doğrulama uygulamasını eşleştir'));
    await layout(page);
    await page.getByText('Eşleştirme anahtarını göster', { exact: true }).click(); linkClicks += 1;
    const secret = (await page.locator('.mfa-secret').textContent()).replace(/\s/g, ''); secrets.add(secret);
    check(/^[A-Z2-7]+=*$/.test(secret) && secret.length >= 16, 'Manual enrollment key is available only in the synthetic UI');
    const token = await freshTotp(secret); await focusCode(page);
    const response = await typeCode(page, token.code, 'pair authenticator'); check(response.status() === 302, 'Genuine TOTP enrollment succeeds');
    if (await page.locator('ol.recovery-codes code').count() === 0) { await security(page); await privateHeaders(await follow(page, 'Kurtarma kodları')); }
    const codes = await readCodes(page); await security(page); return { secret, codes };
  }
  async function login(page, actorRole, next) {
    const now = Date.now(); while (loginTimes.length && now - loginTimes[0] > 60000) loginTimes.shift();
    if (loginTimes.length >= 24) await sleep(Math.max(0, 60100 - (Date.now() - loginTimes[0])));
    await privateHeaders(await go(page, '/accounts/login/?next=' + encodeURIComponent(next)));
    await page.locator('#id_login').fill(emails[actorRole]); await page.locator('#id_password').fill(passwords[actorRole]);
    const response = await submit(page, page.locator('main form button[type=submit]'), 'password login'); loginTimes.push(Date.now());
    check(response.status() === 302, 'Normal verified synthetic password step succeeds');
  }
  async function logout(page) {
    await privateHeaders(await go(page, '/accounts/logout/'));
    const response = await submit(page, page.locator('main form button[type=submit]'), 'logout'); check(response.status() === 302, 'Logout uses the ordinary CSRF form');
  }
  async function pending(page) {
    check(await page.getByLabel('Doğrulama kodu', { exact: true }).count() === 1 && await page.locator('.mfa-secret').count() === 0, 'Password step stops at a real second-factor challenge');
    await layout(page);
  }
  async function badCode(page, code, action) {
    const response = await typeCode(page, code, action); check(response.status() === 200, 'Invalid or reused factor is rejected without login');
    check((await page.locator('main').innerText()).includes('Doğrulama başarısız'), 'Rejected factor has a generic Turkish error'); await layout(page);
  }
  async function supplementalGet(page, route, action) {
    operation = 'supplementary_http';
    const response = await page.context().request.get(local(route), { maxRedirects: 0 });
    supplementaryHTTP.push({ mode, action, status: response.status(), transport: 'browser-context HTTP, not UI interaction' });
    return response;
  }
  async function capture(page, name) {
    await security(page); await remember(page); operation = 'screenshot';
    const sensitive = await page.locator('.mfa-qr,.mfa-secret,.recovery-codes,input[name=code],input[type=password],a[href^="otpauth:"]').count();
    check(screenshotAllowed(page.url(), BASE, sensitive !== 0), 'Screenshot is an explicitly allowed nonsensitive security overview');
    const text = await page.locator('body').innerText();
    check(![...secrets].some(value => value && text.includes(value)), 'No in-memory credential or factor appears in visible screenshot text');
    const file = path.join(artifactDir, name + '.png'); await page.screenshot({ path: file, fullPage: true });
    const bytes = fs.readFileSync(file);
    screenshots.push({ path: path.relative(root, file).replace(/\\/g, '/'), bytes: bytes.length,
      sha256: crypto.createHash('sha256').update(bytes).digest('hex'), viewport: page.viewportSize() }); persist('RUNNING');
  }
  async function staffJourney() {
    role = 'staff'; checkpoint('staff'); const actor = mode + '-staff'; const page = await makePage(actor);
    const anonAdmin = await supplementalGet(page, '/admin/', 'anonymous admin cannot bypass allauth');
    check(anonAdmin.status() === 302, 'Anonymous admin access does not authenticate');
    await login(page, actor, '/admin/');
    const { secret, codes } = await pair(page);
    await go(page, '/admin/'); check(new URL(page.url()).pathname === '/admin/', 'Paired staff reaches real Django admin');
    await logout(page); await login(page, actor, '/admin/'); await pending(page);
    const before = await supplementalGet(page, '/admin/', 'password-only pending login is not an authenticated admin session');
    check(before.status() === 302, 'Password-only pending stage has no admin access');
    const wrong = String((Number(totp(secret)) + 1) % 1000000).padStart(6, '0'); await badCode(page, wrong, 'wrong TOTP');
    const token = await freshTotp(secret, 15); await focusCode(page);
    check((await typeCode(page, token.code, 'valid TOTP login')).status() === 302, 'Valid TOTP finishes the actual login');
    await go(page, '/admin/');
    await logout(page); await login(page, actor, '/admin/'); await pending(page);
    check(Math.floor(Date.now() / 30000) === token.step, 'Deliberate TOTP replay remains inside the same time step');
    await badCode(page, token.code, 'same-step TOTP replay');
    check((await typeCode(page, codes[0], 'one-time recovery login')).status() === 302, 'Unused recovery code completes login');
    // Prove single-use independently, before regeneration invalidates the set.
    await logout(page); await login(page, actor, '/admin/'); await pending(page);
    await badCode(page, codes[0], 'consumed recovery replay before regeneration');
    check((await typeCode(page, codes[1], 'different unused recovery code')).status() === 302,
      'Another unused code in the same unchanged recovery set still works');
    await security(page); await privateHeaders(await follow(page, 'Yeni kurtarma kodları oluştur'));
    check((await submit(page, page.getByRole('button', { name: 'Yeni kodları oluştur', exact: true }), 'regenerate recovery codes')).status() === 302, 'Recent proof permits recovery regeneration');
    const replacementCodes = await readCodes(page);
    check(!replacementCodes.some(code => codes.includes(code)), 'Regeneration supplies a different recovery set');
    await security(page); await follow(page, 'Kurtarma kodları');
    check(await page.locator('ol.recovery-codes code').count() === 0, 'Recovery values cannot be viewed twice');
    await logout(page); await login(page, actor, '/admin/'); await pending(page);
    await badCode(page, codes[0], 'consumed recovery code replay');
    await badCode(page, codes[2], 'previously unused old recovery code after regeneration');
    check((await typeCode(page, replacementCodes[0], 'new recovery set login')).status() === 302, 'Regenerated recovery code works');
    await capture(page, mode + '-staff-security'); await page.context().close();
  }
  async function reviewerJourney() {
    role = 'reviewer'; checkpoint('reviewer'); const actor = mode + '-reviewer'; const page = await makePage(actor);
    await login(page, actor, '/inceleme/'); const { codes } = await pair(page);
    await privateHeaders(await go(page, '/inceleme/'));
    const target = page.locator('main').getByRole('link', { name: 'MFA kabul ' + run + ' ' + mode, exact: true });
    // Prior guarded runs are retained; the real DB-paginated queue may already
    // contain older submitted records. Locate this run through normal UI links.
    let queuePages = 1;
    while (await target.count() === 0) {
      check(queuePages < 100 && await page.locator('main').getByRole('link', { name: 'Sonraki', exact: true }).count() === 1,
        'Owned review target remains reachable through bounded real queue pagination');
      await privateHeaders(await follow(page, 'Sonraki')); queuePages += 1;
    }
    check(await target.count() === 1, 'Exactly one current-run review target found across the real queue');
    const reviewURL = local(await target.getAttribute('href'));
    check(/^\/inceleme\/\d+\/$/.test(new URL(reviewURL).pathname), 'Reviewer selects this run\'s real submitted revision');
    const admin = await supplementalGet(page, '/admin/', 'reviewer MFA does not grant staff permission');
    check(admin.status() === 302 || admin.status() === 403, 'A nonstaff reviewer still cannot enter admin');
    let other = await makePage(actor); await login(other, actor, '/inceleme/'); await pending(other);
    check((await typeCode(other, codes[0], 'second-device recovery login')).status() === 302, 'Second real session is bound to the old primary');
    await privateHeaders(await go(other, '/inceleme/'));
    // Preserve a genuinely authenticated session only in memory. Closing its
    // idle browser context avoids occupying local synchronous HTTP workers.
    const otherStorage = await other.context().storageState();
    otherStorage.cookies.forEach(cookie => secrets.add(cookie.value));
    await other.context().close();
    const stale = await page.context().newPage(); stale.actorRole = actor;
    stale.setDefaultTimeout(12000); stale.setDefaultNavigationTimeout(20000);
    stale.on('pageerror', () => { pageErrors += 1; });
    stale.on('requestfailed', request => { if (request.failure()?.errorText !== 'net::ERR_ABORTED') requestFailures += 1; });
    await go(stale, reviewURL); await layout(stale);
    await security(page); await privateHeaders(await follow(page, 'Cihazı değiştir'));
    check((await submit(page, page.getByRole('button', { name: 'Eski cihazı kaldır', exact: true }), 'remove old device')).status() === 302, 'Recent proof allows protected device removal');
    await security(page, false);
    check((await page.locator('main').innerText()).includes('Henüz eşleştirilmedi'), 'Removal immediately leaves mandatory account awaiting enrollment');
    const beforeDenial = fixture('inspect');
    await stale.locator('select[name=action]').selectOption('approve');
    await stale.locator('textarea[name=reason]').fill('Sentetik MFA eski form doğrulaması.');
    const denied = await submit(stale, stale.getByRole('button', { name: 'Kararı kaydet', exact: true }), 'stale moderation form without primary');
    check(denied.status() === 403, 'Previously opened review form cannot publish after device removal');
    same(fixture('inspect'), beforeDenial, 'Denied stale form changes no owned listing, revision, MFA or audit state');
    await stale.close();
    await pair(page);
    check(fixture('inspect').revisions[mode] === 'submitted', 'Re-enrollment never replays the suspended approval');
    other = await makePage(actor);
    await other.context().addCookies(otherStorage.cookies);
    const oldSession = await supplementalGet(other, '/inceleme/', 'replaced primary invalidates previous-session proof');
    check(oldSession.status() === 302 && (oldSession.headers()['location'] || '').includes('reauthenticate'), 'Other session must reauthenticate against the replacement primary');
    await other.context().close();
    await go(page, reviewURL); await page.locator('select[name=action]').selectOption('approve');
    await page.locator('textarea[name=reason]').fill('Sentetik MFA yeni cihaz ile onay.');
    check((await submit(page, page.getByRole('button', { name: 'Kararı kaydet', exact: true }), 'fresh reviewed approval after replacement')).status() === 302, 'Explicit fresh form publishes only after new pairing');
    check(fixture('inspect').revisions[mode] === 'approved', 'Exactly this mode\'s owned revision is approved');
    await capture(page, mode + '-reviewer-security'); await page.context().close();
  }
  async function sellerJourney() {
    role = 'seller'; checkpoint('seller'); const actor = mode + '-seller'; const page = await makePage(actor);
    await login(page, actor, '/ilanlarim/'); check(new URL(page.url()).pathname === '/ilanlarim/', 'Ordinary seller can use own dashboard without MFA');
    await security(page, false);
    check(!(await page.locator('main').innerText()).includes('iki adımlı doğrulama zorunludur'), 'Ordinary seller enrollment is optional');
    const { codes } = await pair(page); await logout(page); await login(page, actor, '/ilanlarim/'); await pending(page);
    check((await typeCode(page, codes[0], 'optional seller second-factor login')).status() === 302, 'Voluntary seller MFA also protects subsequent login');
    await go(page, '/ilanlarim/'); await capture(page, mode + '-seller-security'); await page.context().close();
  }
  try {
    const args = process.argv.slice(2); let selected = MODES;
    if (args.length) { ensure(args.length === 1 && /^--mode=(desktop|mobile|nojs)$/.test(args[0])); selected = [args[0].slice(7)]; }
    guard(); fs.mkdirSync(artifactDir, { recursive: true }); createdArtifacts = true; checkpoint('create');
    initialState = fixture('create');
    check(Object.values(initialState.roles).every(value => value.primary === 0 && value.recovery === 0 && value.events === 0), 'Fixture creates no MFA factors, fabricated proof or security events');
    operation = 'browser'; browser = await chromium.launch({ headless: true, executablePath });
    for (const selectedMode of selected) { mode = selectedMode; await staffJourney(); await reviewerJourney(); await sellerJourney(); }
    finalState = fixture('inspect');
    for (const selectedMode of selected) {
      for (const actor of ['staff', 'reviewer', 'seller']) {
        const values = finalState.roles[selectedMode + '-' + actor];
        check(values.primary === 1 && values.recovery === 1 && values.events >= 2, 'Selected synthetic account retains exactly one primary and recovery set');
      }
      check(finalState.revisions[selectedMode] === 'approved', 'Selected mode completed guarded explicit publication');
    }
    check(pageErrors === 0 && requestFailures === 0 && blockedExternalRequests === 0 && asyncFailures === 0, 'No page errors, unexpected request failures or external-origin contacts');
    checkpoint('complete'); persist('PASS', { selectedModes: selected, initialState, finalState, commandCompleted: true });
    console.log(JSON.stringify({ result: 'PASS', run, assertions: checks.length, contexts: contexts.length, uiPosts: uiPosts.length,
      supplementaryHTTP: supplementaryHTTP.length, screenshots: screenshots.length, commandCompleted: true }));
  } catch (error) {
    const failure = failureRecord(stage, operation, error);
    persist('FAIL', { failure, lastCheck, commandCompleted: false });
    console.log(JSON.stringify({ result: 'FAIL', run, assertions: checks.length, failure, lastCheck })); process.exitCode = 1;
  } finally { if (browser) await browser.close().catch(() => {}); }
}
if (require.main === module) main().catch(() => { console.log('{"result":"FAIL","kind":"runner_startup_error"}'); process.exitCode = 1; });
