/* Guarded pilot UI acceptance. Credentials, cookies, CSRF and client tokens stay in memory. */
const path = require('path'), fs = require('fs'), crypto = require('crypto');
const assert = require('assert/strict');
const { spawnSync } = require('child_process');
const { chromium } = require('../.browser-test-tools/node_modules/playwright-core');
const root = path.resolve(__dirname, '../..'), base = 'http://localhost:8089';
const project = 'classifieds-rebuild-dev', run = crypto.randomBytes(8).toString('hex');
const artifactDir = path.join(root, 'rebuild/test-artifacts/pilot-limits', run);
const roles = ['contact', 'message', 'creator', 'seller', 'reviewer'];
const passwords = Object.fromEntries(roles.map(role => [role, crypto.randomBytes(32).toString('base64url')]));
const emails = Object.fromEntries(roles.map(role => [role, 'pilot-' + run + '-' + role + '@browser.example.test']));
const secrets = [...Object.values(passwords), ...Object.values(emails)];
const executablePath = 'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe';
const checks = [], screenshots = [], pageErrors = [], failures = [], uiPosts = [], supplementalHTTP = [];
let stage = 'guard', operation = 'guard', browser, dbAddress, data, replay;
// Never persist raw Playwright locator diagnostics: hidden fields can appear in them.
const safe = value => secrets.reduce((result, secret) => secret ? result.split(secret).join('[redacted]') : result,
  String(value).replace(/value=(?:\\"|"|')([^"']+)(?:\\"|"|')/g, 'value="[redacted]"'));
function check(condition, message) { assert.ok(condition, message); checks.push(message); }
function equal(actual, expected, message) { assert.deepEqual(actual, expected, message); checks.push(message); }
function summary(result, extra = {}) {
  return { result, run, stage, assertions: checks.length, checks, uiPosts, supplementalHTTP, screenshots,
    pageErrors: pageErrors.map(safe), unexpectedRequestFailures: failures.filter(x => !x.includes('ERR_ABORTED')).map(safe), ...extra };
}
function persist(result, extra = {}) {
  fs.writeFileSync(path.join(artifactDir, 'summary.json'), JSON.stringify(summary(result, extra), null, 2) + '\n');
}
function checkpoint(name) { stage = name; persist('RUNNING'); console.log(JSON.stringify({ run, stage, assertions: checks.length })); }
function docker(args, input) {
  const result = spawnSync('docker', args, { cwd: root, input, encoding: 'utf8', timeout: 45000, windowsHide: true });
  if (result.status !== 0) throw new Error('Developer operation failed: ' + safe(result.stderr).slice(-800));
  return result.stdout;
}
function guard() {
  check(new URL(base).hostname === 'localhost' && new URL(base).port === '8089', 'Fixed developer8089 origin');
  check(root.toLowerCase().replace(/\\/g, '/').endsWith('/.devspace/worktrees/classifieds_local-a7be577c'), 'Exact detached developer root');
  const all = JSON.parse(docker(['inspect', project + '-web-1', project + '-db-1', project + '-redis-1',
    'classifieds-rebuild-db-1', 'classifieds-rebuild-redis-1']));
  const [web, db, redis, originalDB, originalRedis] = all;
  for (const container of [web, db, redis]) check(container.Config.Labels['com.docker.compose.project'] === project, 'Verified developer Compose label');
  for (const [container, service] of [[web, 'web'], [db, 'db'], [redis, 'redis']])
    check(container.Config.Labels['com.docker.compose.service'] === service, 'Verified exact developer service ' + service);
  const ports = web.NetworkSettings.Ports['8000/tcp'];
  check(ports.length === 1 && ports[0].HostIp === '127.0.0.1' && ports[0].HostPort === '8089', 'Only loopback8089 web binding');
  check(web.Mounts.some(x => x.Destination === '/app' && x.RW === false &&
    x.Source.toLowerCase().replace(/\\/g, '/').endsWith('/.devspace/worktrees/classifieds_local-a7be577c/rebuild/backend')), 'Read-only exact developer source bind');
  for (const [container, destination, volume] of [[web, '/var/lib/classifieds/media', 'rebuild_media'],
    [db, '/var/lib/postgresql/data', 'rebuild_postgres'], [redis, '/data', 'rebuild_redis']])
    check(container.Mounts.some(x => x.Destination === destination && x.Name === project + '_' + volume), 'Exact developer volume ' + volume);
  for (const [dev, original] of [[db, originalDB], [redis, originalRedis]]) {
    check(original.Config.Labels['com.docker.compose.project'] === 'classifieds-rebuild', 'Read-only original runtime identity established');
    check(dev.Id !== original.Id, 'Developer and original persistent services have distinct IDs');
    check(!dev.Mounts.some(d => d.Name && original.Mounts.some(o => o.Name === d.Name)), 'Developer and original persistent volumes disjoint');
    check(!Object.keys(dev.NetworkSettings.Networks).some(n => original.NetworkSettings.Networks[n]), 'Developer and original networks disjoint');
    check(Object.values(dev.NetworkSettings.Ports || {}).every(value => value === null), 'Developer persistent service exposes no host port');
  }
  const network = project + '_default';
  check(!!db.NetworkSettings.Networks[network] && !!redis.NetworkSettings.Networks[network] &&
    !!web.NetworkSettings.Networks[network], 'Exact shared developer network');
  dbAddress = db.NetworkSettings.Networks[network].IPAddress;
  check(/^\d+\.\d+\.\d+\.\d+$/.test(dbAddress), 'Developer DB IP independently resolved');
  const env = Object.fromEntries(web.Config.Env.map(x => { const at = x.indexOf('='); return [x.slice(0, at), x.slice(at + 1)]; }));
  equal(['PILOT_NEW_CONTACTS_PER_HOUR', 'PILOT_MESSAGES_PER_HOUR', 'PILOT_NEW_LISTINGS_PER_DAY'].map(k => env[k]),
    ['10', '120', '10'], 'Running developer application retains production defaults10/120/10');
}
function fixture(action) {
  const input = { run, action, db_address: dbAddress };
  if (action === 'create') input.passwords = passwords;
  return JSON.parse(docker(['compose', '-f', 'rebuild/compose.yaml', '-f', 'rebuild/compose.dev.yaml',
    '-p', project, 'exec', '-T', 'web', 'python', 'manage.py', 'pilot_limits_browser_fixture'], JSON.stringify(input)));
}
function listen(page) {
  page.setDefaultTimeout(12000); page.setDefaultNavigationTimeout(20000);
  page.on('pageerror', error => pageErrors.push({ kind: error.name || 'Error', diagnosis: 'Browser page error; raw diagnostic omitted.' }));
  page.on('requestfailed', request => failures.push(safe(request.failure()?.errorText || 'unknown')));
}
async function goto(page, route, status = 200) {
  check(route.startsWith('/') && !route.startsWith('//'), 'Guarded product-relative navigation');
  operation = route.startsWith('/accounts/') ? 'synthetic-login-navigation' : 'product-navigation';
  const response = await page.goto(base + route, { waitUntil: 'domcontentloaded' });
  check(response.status() === status, 'HTTP ' + status + ' on synthetic product route');
  await rememberSecrets(page);
  return response;
}
async function rememberSecrets(page) {
  for (const cookie of await page.context().cookies()) secrets.push(cookie.value);
  for (const input of await page.locator('input[name=csrfmiddlewaretoken], input[name=client_token]').all())
    secrets.push(await input.inputValue());
}
async function submit(page, control, mode, action, keyboard = false) {
  operation = 'ordinary-form-submit:' + mode + ':' + action;
  await rememberSecrets(page);
  const post = page.waitForResponse(response => response.request().method() === 'POST' && new URL(response.url()).origin === base);
  await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded' }), keyboard ? control.press('Enter') : control.click()]);
  const response = await post;
  check(new URL(page.url()).origin === base, 'Normal HTML POST stays on developer origin');
  uiPosts.push({ mode, action, input: keyboard ? 'keyboard Enter' : 'pointer click', status: response.status() });
  await rememberSecrets(page);
  return response;
}
async function login(page, role, mode) {
  await goto(page, '/accounts/login/?next=/mesajlar/');
  await page.locator('#id_login').fill(emails[role]); await page.locator('#id_password').fill(passwords[role]);
  await submit(page, page.locator('main form button[type=submit]'), mode, 'synthetic login');
  check(new URL(page.url()).pathname === '/mesajlar/', 'Normal verified synthetic allauth login');
}
async function headers(response, label) {
  const values = await response.allHeaders();
  check(/^[1-9]\d*$/.test(values['retry-after'] || ''), label + ': positive decimal Retry-After');
  check(values['cache-control'].includes('private') && values['cache-control'].includes('no-store'), label + ': private/no-store');
  check(values['x-content-type-options'] === 'nosniff', label + ': nosniff');
}
async function layout(page, label) {
  const metrics = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    unlabeled: [...document.querySelectorAll('main input:not([type=hidden]), main textarea, main select')]
      .filter(element => !element.labels?.length).length
  }));
  check(!metrics.overflow, label + ': no horizontal overflow at ' + page.viewportSize().width + 'px');
  check(metrics.unlabeled === 0, label + ': visible form controls labeled');
}
async function focus(page, field, label) {
  await field.focus(); await page.keyboard.press('Tab');
  const metrics = await page.evaluate(() => ({ tag: document.activeElement.tagName,
    outline: getComputedStyle(document.activeElement).outlineStyle, width: getComputedStyle(document.activeElement).outlineWidth }));
  check(metrics.tag === 'BUTTON' && metrics.outline !== 'none' && metrics.width !== '0px', label + ': visible keyboard submit focus');
}
async function privacy(page, label) {
  const html = await page.content();
  check(!Object.values(emails).some(email => html.includes(email)), label + ': no private email rendered');
  check(await page.locator('script').filter({ hasText: 'pilotInjected' }).count() === 0, label + ': retained message cannot create script');
}
async function capture(page, name, field) {
  check(!new URL(page.url()).pathname.startsWith('/accounts/'), 'Screenshot restricted to synthetic product UI');
  await field.scrollIntoViewIfNeeded();
  const file = path.join(artifactDir, name + '.png');
  await page.screenshot({ path: file, fullPage: false });
  const bytes = fs.readFileSync(file);
  screenshots.push({ path: path.relative(root, file).replace(/\\/g, '/'), bytes: bytes.length,
    sha256: crypto.createHash('sha256').update(bytes).digest('hex'), viewport: page.viewportSize() });
  persist('RUNNING');
}
const messages = { contact: 'Yeni görüşme sınırına ulaştınız.', message: 'Mesaj gönderme sınırına ulaştınız.',
  creator: 'Yeni ilan sınırına ulaştınız.' };
const body = '<script>window.pilotInjected=true</script>\nSentetik sınır & <b>korunan metin</b>';
async function deny(page, role, mode) {
  if (role === 'contact') {
    await goto(page, '/ilanlar/' + data.target_listing + '/');
    await page.getByRole('link', { name: 'Mesaj gönder', exact: true }).click();
  } else await goto(page, role === 'message' ? '/mesajlar/' + data.thread + '/' : '/ilan-ver/');
  checkpoint(mode + '-' + role + '-bound-form');
  const before = fixture('inspect');
  const field = role === 'creator' ? page.getByLabel('İlan kategorisi', { exact: false }) : page.getByLabel('Mesajın', { exact: true });
  let token;
  if (role === 'creator') await field.selectOption(String(data.category));
  else { await field.fill(body); token = await page.locator('input[name=client_token]').inputValue(); secrets.push(token); }
  const button = role === 'creator' ? page.locator('main form button[type=submit]') : page.getByRole('button', { name: 'Gönder', exact: true });
  check(await button.count() === 1, mode + ' ' + role + ': unique submit control');
  checkpoint(mode + '-' + role + '-submitting');
  const response = await submit(page, button, mode, role + ' quota denial', mode === 'desktop' && role !== 'creator');
  check(response.status() === 429, mode + ' ' + role + ': real UI HTTP429');
  await headers(response, mode + ' ' + role);
  check((await page.locator('main').innerText()).includes(messages[role]), mode + ' ' + role + ': Turkish action-specific wait message');
  if (role === 'creator') {
    check(await field.inputValue() === String(data.category), mode + ': selected category retained');
    check((await page.locator('main').innerText()).includes('Mevcut taslaklarınızı düzenlemeye devam edebilirsiniz.'), mode + ': existing-draft continuity explained');
  } else {
    check(await field.inputValue() === body, mode + ' ' + role + ': escaped message body retained exactly');
    check(await page.locator('input[name=client_token]').inputValue() === token, mode + ' ' + role + ': client token unchanged');
    check((await page.content()).includes('&lt;script&gt;window.pilotInjected=true&lt;/script&gt;'), mode + ' ' + role + ': source body HTML escaped');
  }
  equal(fixture('inspect'), before, mode + ' ' + role + ': denial creates no records or sequence/read/archive/draft changes');
  await privacy(page, mode + ' ' + role); await layout(page, mode + ' ' + role); await focus(page, field, mode + ' ' + role);
  await capture(page, mode + '-' + role + '-429', field);
}
(async () => {
  fs.mkdirSync(artifactDir, { recursive: true }); persist('RUNNING');
  guard(); data = fixture('create');
  check(data.guard.debug && data.guard.database_verified && data.guard.site === 'localhost:8089', 'Inner DEBUG/Site/DB/mount guard passed');
  equal(data.defaults, [10, 120, 10], 'Scoped construction override fully restored');
  check(data.counts.contact.contacts === 10 && data.counts.message.messages === 119 && data.counts.creator.listings === 10, 'Successful production-default actor histories ready');
  checkpoint('launch-and-last-slot');
  browser = await chromium.launch({ headless: true, executablePath });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'tr-TR', reducedMotion: 'reduce' });
  const message = await desktop.newPage(); listen(message); await login(message, 'message', 'desktop');
  await goto(message, '/mesajlar/' + data.thread + '/');
  const finalBody = 'Sentetik gerçek UI son mesaj hakkı';
  const finalToken = await message.locator('input[name=client_token]').inputValue(); secrets.push(finalToken);
  const csrf = await message.locator('.conversation-composer input[name=csrfmiddlewaretoken]').inputValue(); secrets.push(csrf);
  replay = { body: finalBody, client_token: finalToken, csrfmiddlewaretoken: csrf };
  await message.getByLabel('Mesajın', { exact: true }).fill(finalBody);
  const lastSlot = await submit(message, message.getByRole('button', { name: 'Gönder', exact: true }), 'desktop', 'last message slot', true);
  check(lastSlot.status() === 302, '120th message succeeds with real keyboard HTML PRG');
  check(fixture('inspect').counts.message.messages === 120, '120 successful Message rows persisted at real running default');
  await deny(message, 'message', 'desktop');
  checkpoint('exhausted-idempotent-replay-supplement');
  const beforeReplay = fixture('inspect');
  const replayResponse = await desktop.request.post(base + '/mesajlar/' + data.thread + '/gonder/', {
    form: replay, headers: { Referer: base + '/mesajlar/' + data.thread + '/' }, maxRedirects: 0 });
  supplementalHTTP.push({ action: 'same-body/token replay at120', status: replayResponse.status(), transport: 'browser context HTTP; not pointer/UI' });
  check(replayResponse.status() === 302, 'Supplemental browser HTTP: valid exhausted replay302');
  equal(fixture('inspect'), beforeReplay, 'Supplemental browser HTTP: replay no accounting or state changes');
  const desktopContact = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'tr-TR', reducedMotion: 'reduce' });
  const contact = await desktopContact.newPage(); listen(contact); await login(contact, 'contact', 'desktop'); await deny(contact, 'contact', 'desktop');
  await goto(contact, '/mesajlar/' + data.contact_thread + '/');
  await contact.getByLabel('Mesajın', { exact: true }).fill('Sentetik mevcut görüşmeye kapasitede yanıt');
  const existing = await submit(contact, contact.getByRole('button', { name: 'Gönder', exact: true }), 'desktop', 'existing thread at contact capacity', true);
  check(existing.status() === 302 && fixture('inspect').counts.contact.contacts === 10, 'Existing conversation reply succeeds without new contact at10');
  const desktopCreator = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'tr-TR', reducedMotion: 'reduce' });
  const creator = await desktopCreator.newPage(); listen(creator); await login(creator, 'creator', 'desktop'); await deny(creator, 'creator', 'desktop');
  // Continuity uses separate logged-in participants and draft owner.
  await goto(message, '/mesajlar/' + data.thread + '/');
  check(await message.locator('.message-bubble').count() === 30, 'Desktop history remains readable at120');
  await message.getByRole('link', { name: 'Daha eski mesajlar', exact: true }).click();
  check(await message.locator('.message-bubble').count() === 30, 'Desktop older history remains readable');
  await submit(message, message.getByRole('button', { name: 'Okundu olarak işaretle', exact: true }), 'desktop', 'explicit read at capacity', true);
  await submit(message, message.getByRole('button', { name: 'Arşivle', exact: true }), 'desktop', 'archive at capacity');
  await goto(message, '/mesajlar/' + data.thread + '/');
  await submit(message, message.getByRole('button', { name: 'Arşivden çıkar', exact: true }), 'desktop', 'unarchive at capacity');
  // Reuse continuity only with the correct owner; read history is tested on message pages above/below.
  async function draftContinuity(page, mode) {
    await goto(page, '/taslaklar/' + data.draft + '/duzenle/?step=details');
    const before = fixture('inspect'), title = 'Sentetik kapasitede düzenleme ' + mode;
    await page.getByLabel('İlan başlığı', { exact: false }).fill(title);
    const response = await submit(page, page.getByRole('button', { name: 'Kaydet ve çık', exact: true }), mode, 'existing draft edit', mode === 'desktop');
    check(response.status() === 302 && new URL(page.url()).pathname === '/ilanlarim/', mode + ': existing draft normal PRG at listing capacity');
    const after = fixture('inspect'); equal(after.counts, before.counts, mode + ': draft edit preserves identity counts');
    check(after.draft_state.version === before.draft_state.version + 1 && after.draft_state.title === title, mode + ': existing draft persisted once');
  }
  await draftContinuity(creator, 'desktop');
  // End completed desktop surfaces before the next independent viewport acceptance.
  await Promise.all([desktop.close(), desktopContact.close(), desktopCreator.close()]);
  for (const mode of ['mobile', 'nojs']) {
    checkpoint(mode + '-ordinary-form-acceptance');
    for (const role of ['contact', 'message', 'creator']) {
      const context = await browser.newContext({ viewport: mode === 'mobile' ? { width: 390, height: 844 } : { width: 1440, height: 1000 },
        locale: 'tr-TR', reducedMotion: 'reduce', javaScriptEnabled: mode !== 'nojs' });
      const page = await context.newPage(); listen(page); await login(page, role, mode); await deny(page, role, mode);
      if (role === 'message') {
        await goto(page, '/mesajlar/' + data.thread + '/');
        check(await page.locator('.message-bubble').count() === 30, mode + ': history readable at message capacity');
        await page.getByRole('link', { name: 'Daha eski mesajlar', exact: true }).click();
        check(await page.locator('.message-bubble').count() === 30, mode + ': older history readable at capacity');
      } else if (role === 'creator') await draftContinuity(page, mode);
      await context.close();
    }
  }
  check(uiPosts.filter(x => x.status === 429).length === 9, 'Nine actual429 UI POSTs: all3 actions x desktop/mobile/no-JS');
  check(pageErrors.length === 0, 'No browser page errors');
  check(failures.filter(x => !x.includes('ERR_ABORTED')).length === 0, 'No unexpected browser request failures');
  checkpoint('complete');
  persist('PASS', { defaults: [10, 120, 10], finalCounts: fixture('inspect').counts, browserContexts: 9, screenshotCount: screenshots.length });
  console.log(JSON.stringify(summary('PASS', { defaults: [10, 120, 10], browserContexts: 9, screenshotCount: screenshots.length })));
})().catch(cause => {
  // Detailed locator diagnostics may contain previously unseen masked tokens.
  const errorKind = cause.name || 'Error';
  const diagnostic = /page\.goto/.test(cause.message || '') ? 'Navigation timed out' :
    /locator\./.test(cause.message || '') ? 'Control operation failed' :
    /waitForResponse/.test(cause.message || '') ? 'POST response not observed' :
    /waitForNavigation/.test(cause.message || '') ? 'POST navigation not completed' : 'Acceptance assertion or operation failed';
  const error = { kind: errorKind, failedStage: stage, operation, diagnosis: diagnostic };
  persist('FAIL', { error });
  console.error(JSON.stringify(summary('FAIL', { error }))); process.exitCode = 1;
}).finally(async () => { if (browser) await browser.close(); });
