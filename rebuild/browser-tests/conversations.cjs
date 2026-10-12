/* Real UI acceptance on the guarded developer project; credentials stay in memory. */
const path = require('path'), fs = require('fs'), crypto = require('crypto');
const assert = require('assert/strict');
const { spawnSync } = require('child_process');
const { chromium } = require('../.browser-test-tools/node_modules/playwright-core');
const root = path.resolve(__dirname, '../..'), base = 'http://localhost:8089';
const project = 'classifieds-rebuild-dev';
const run = crypto.randomBytes(8).toString('hex');
const artifactDir = path.join(root, 'rebuild/test-artifacts/conversations', run);
const passwords = Object.fromEntries(['buyer', 'seller', 'newcomer'].map(role => [role, crypto.randomBytes(32).toString('base64url')]));
const emails = Object.fromEntries(Object.keys(passwords).map(role => [role, 'conversations-' + run + '-' + role + '@browser.example.test']));
const secrets = [...Object.values(passwords), ...Object.values(emails)];
const executablePath = 'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe';
const checks = [], screenshots = [], pageErrors = [], failures = [];
let stage = 'guard', browser, dbAddress, threadPath, data;
const safe = value => secrets.reduce((result, secret) => result.split(secret).join('[redacted]'), String(value));
function summary(result, extra = {}) {
  return { result, run, stage, assertions: checks.length, checks, screenshots,
    pageErrors: pageErrors.map(safe), unexpectedRequestFailures: failures.filter(x => !x.includes('ERR_ABORTED')).map(safe), ...extra };
}
function persist(result, extra = {}) {
  fs.writeFileSync(path.join(artifactDir, 'summary.json'), JSON.stringify(summary(result, extra), null, 2) + '\n');
}
function checkpoint(name) { stage = name; persist('RUNNING'); console.log(JSON.stringify({ run, stage, assertions: checks.length })); }
function check(condition, message) { assert.ok(condition, message); checks.push(message); }
function docker(args, input) {
  const result = spawnSync('docker', args, { cwd: root, input, encoding: 'utf8', timeout: 45000, windowsHide: true });
  if (result.status !== 0) throw new Error('Developer operation failed: ' + safe(result.stderr).slice(-800));
  return result.stdout;
}
function guard() {
  check(new URL(base).hostname === 'localhost' && new URL(base).port === '8089', 'Developer8089 origin fixed');
  const containers = JSON.parse(docker(['inspect', project + '-web-1', project + '-db-1']));
  const [web, db] = containers;
  for (const container of containers) check(container.Config.Labels['com.docker.compose.project'] === project, 'Verified developer Compose label');
  check(web.Config.Labels['com.docker.compose.service'] === 'web' && db.Config.Labels['com.docker.compose.service'] === 'db', 'Verified exact web and DB services');
  const ports = web.NetworkSettings.Ports['8000/tcp'];
  check(ports.length === 1 && ports[0].HostIp === '127.0.0.1' && ports[0].HostPort === '8089', 'Only developer8089 web binding');
  check(web.Mounts.some(x => x.Destination === '/app' && x.RW === false &&
    x.Source.toLowerCase().replace(/\\/g, '/').endsWith('/.devspace/worktrees/classifieds_local-a7be577c/rebuild/backend')), 'Developer source bind read-only and exact worktree');
  check(web.Mounts.some(x => x.Destination === '/var/lib/classifieds/media' && x.Name === project + '_rebuild_media'), 'Developer media volume');
  check(db.Mounts.some(x => x.Destination === '/var/lib/postgresql/data' && x.Name === project + '_rebuild_postgres'), 'Developer PostgreSQL volume');
  const network = Object.keys(db.NetworkSettings.Networks).find(key => key === project + '_default');
  check(!!network && !!web.NetworkSettings.Networks[network], 'Web and DB share exact developer network');
  dbAddress = db.NetworkSettings.Networks[network].IPAddress;
  check(/^\d+\.\d+\.\d+\.\d+$/.test(dbAddress), 'Developer DB IP independently resolved');
}
function fixture(action) {
  const input = { run, action, db_address: dbAddress };
  if (action === 'create') input.passwords = passwords;
  return JSON.parse(docker(['compose', '-f', 'rebuild/compose.yaml', '-f', 'rebuild/compose.dev.yaml',
    '-p', project, 'exec', '-T', 'web', 'python', 'manage.py', 'conversations_browser_fixture'], JSON.stringify(input)));
}
function listen(page) {
  page.setDefaultTimeout(12000); page.setDefaultNavigationTimeout(20000);
  page.on('pageerror', error => pageErrors.push(safe(error.message).slice(0, 400)));
  page.on('requestfailed', request => failures.push(safe(request.failure()?.errorText || 'unknown')));
}
async function goto(page, route, status = 200) {
  const response = await page.goto(base + route, { waitUntil: 'domcontentloaded' });
  check(response.status() === status, 'HTTP ' + status + ' on synthetic product route');
  return response;
}
async function submit(page, button, keyboard = false) {
  const control = typeof button === 'string' ? page.getByRole('button', { name: button, exact: true }) : button;
  await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded' }), keyboard ? control.press('Enter') : control.click()]);
  check(new URL(page.url()).origin === base, 'POST stays on developer origin');
}
async function login(page, role) {
  await goto(page, '/accounts/login/?next=/mesajlar/');
  await page.locator('#id_login').fill(emails[role]);
  await page.locator('#id_password').fill(passwords[role]);
  await submit(page, page.locator('main form button[type=submit]'));
  check(new URL(page.url()).pathname === '/mesajlar/', 'Verified synthetic normal allauth login return');
}
async function privacy(page) {
  const html = await page.content();
  check(!Object.values(emails).some(email => html.includes(email)), 'No private account email rendered');
  check(!html.includes('<script>synthetic-xss</script>'), 'Message XSS stays escaped');
}
async function layout(page) {
  const metrics = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    unlabeled: [...document.querySelectorAll('main input:not([type=hidden]), main textarea, main select')]
      .filter(element => !element.labels?.length).length
  }));
  check(!metrics.overflow, 'No horizontal overflow at ' + page.viewportSize().width + 'px');
  check(metrics.unlabeled === 0, 'Every visible message control is labeled');
}
async function focus(page) {
  await page.getByLabel('Mesajın', { exact: true }).focus();
  await page.keyboard.press('Tab');
  const metrics = await page.evaluate(() => ({ tag: document.activeElement.tagName,
    outline: getComputedStyle(document.activeElement).outlineStyle, width: getComputedStyle(document.activeElement).outlineWidth }));
  check(metrics.tag === 'BUTTON' && metrics.outline !== 'none' && metrics.width !== '0px', 'Keyboard composer-to-send focus is visible');
}
async function capture(page, name, locator) {
  check(!new URL(page.url()).pathname.startsWith('/accounts/'), 'Screenshot is synthetic product UI');
  if (locator) await locator.scrollIntoViewIfNeeded();
  const file = path.join(artifactDir, name + '.png');
  await page.screenshot({ path: file, fullPage: false });
  const bytes = fs.readFileSync(file);
  screenshots.push({ path: path.relative(root, file).replace(/\\/g, '/'), bytes: bytes.length,
    sha256: crypto.createHash('sha256').update(bytes).digest('hex'), viewport: page.viewportSize() });
  persist('RUNNING');
  console.log(JSON.stringify({ run, screenshot: screenshots[screenshots.length - 1] }));
}
async function send(page, body, keyboard = false) {
  await page.getByLabel('Mesajın', { exact: true }).fill(body);
  await submit(page, 'Gönder', keyboard);
}
async function openThread(page) { await goto(page, threadPath); await privacy(page); }
(async () => {
  fs.mkdirSync(artifactDir, { recursive: true }); persist('RUNNING');
  guard(); data = fixture('create');
  check(data.guard.debug && data.guard.database_verified && data.guard.site === 'localhost:8089', 'Inner DEBUG/Site/DB/mount guard passed');
  check(data.threads === 13, '13 fresh synthetic inbox fixtures');
  checkpoint('launch');
  browser = await chromium.launch({ headless: true, executablePath });
  const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'tr-TR', reducedMotion: 'reduce' });
  const sellerContext = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'tr-TR', reducedMotion: 'reduce' });
  const buyer = await desktopContext.newPage(), seller = await sellerContext.newPage();
  [buyer, seller].forEach(listen);
  checkpoint('normal-login-and-first-send');
  await login(buyer, 'buyer'); await login(seller, 'seller');
  await goto(buyer, '/ilanlar/' + data.listing + '/');
  await buyer.getByRole('link', { name: 'Mesaj gönder', exact: true }).click();
  check(await buyer.getByLabel('Mesajın').getAttribute('maxlength') === null, 'No UTF16 maxlength blocks astral Unicode');
  await send(buyer, '<script>synthetic-xss</script>\nİlk soru', true);
  threadPath = new URL(buyer.url()).pathname;
  check(/^\/mesajlar\/[a-f0-9-]+\/$/.test(threadPath), 'First send PRG reaches persisted UUID conversation');
  await layout(buyer); await privacy(buyer); await focus(buyer);
  await capture(buyer, 'desktop-conversation', buyer.locator('#conversation-history'));
  await goto(seller, '/mesajlar/');
  const threadRow = seller.locator('.conversation-row').filter({ has: seller.getByRole('link', { name: 'Sentetik görüşme 00', exact: true }) });
  check(await threadRow.locator('[data-unread]').count() === 1, 'Seller sees incoming unread inbox badge');
  await privacy(seller);
  await threadRow.getByRole('link', { name: 'Sentetik görüşme 00', exact: true }).click();
  checkpoint('automatic-poll-composer-preservation');
  await buyer.getByLabel('Mesajın').fill('Yazılmakta olan taslak');
  await send(seller, 'Satıcı otomatik yenileme yanıtı');
  await buyer.locator('.message-body').filter({ hasText: 'Satıcı otomatik yenileme yanıtı' }).waitFor({ timeout: 20000 });
  check(await buyer.getByLabel('Mesajın').inputValue() === 'Yazılmakta olan taslak', '15s automatic history refresh preserves composer');
  check(fixture('inspect').buyer_read === 0, 'Automatic refresh performs no read mutation');
  checkpoint('explicit-read-after-later-insertion');
  const displayed = Number(await buyer.locator('input[name=through_message_id]').inputValue());
  await buyer.getByRole('button', { name: 'Okundu olarak işaretle', exact: true }).focus();
  await send(seller, 'Sonradan gelen okunmamış');
  // Focus in history suppresses the next real 15s poll.
  await buyer.waitForTimeout(16000);
  check(Number(await buyer.locator('input[name=through_message_id]').inputValue()) === displayed, 'History focus guard preserves displayed watermark');
  await submit(buyer, 'Okundu olarak işaretle', true);
  const readState = fixture('inspect');
  check(readState.buyer_read === readState.last_sequence - 1 && readState.buyer_unread, 'Explicit displayed read keeps later incoming unread');
  await goto(buyer, '/mesajlar/');
  const buyerRow = buyer.locator('.conversation-row').filter({ has: buyer.getByRole('link', { name: 'Sentetik görüşme 00', exact: true }) });
  check(await buyerRow.locator('[data-unread]').count() === 1, 'Later incoming remains unread in UI');
  checkpoint('personal-archive-and-directional-block');
  await openThread(buyer); await submit(buyer, 'Arşivle');
  await buyer.getByRole('link', { name: 'Arşiv', exact: true }).click();
  check(await buyer.getByRole('link', { name: 'Sentetik görüşme 00', exact: true }).count() === 1, 'Personal archived thread visible');
  await buyer.getByRole('link', { name: 'Sentetik görüşme 00', exact: true }).click();
  await submit(buyer, 'Arşivden çıkar');
  await submit(buyer, 'Karşı tarafı engelle');
  check(await buyer.getByRole('button', { name: 'Gönder', exact: true }).isDisabled(), 'Buyer block disables composer');
  await openThread(seller);
  check(await seller.getByRole('button', { name: 'Gönder', exact: true }).isDisabled(), 'Either-direction block disables seller composer');
  await submit(seller, 'Karşı tarafı engelle');
  await submit(buyer, 'Engeli kaldır');
  check(await buyer.getByRole('button', { name: 'Gönder', exact: true }).isDisabled(), 'Removing own block leaves peer block effective');
  await submit(seller, 'Engeli kaldır');
  await openThread(buyer);
  check(await buyer.getByRole('button', { name: 'Gönder', exact: true }).isEnabled(), 'Both owned blocks removed restores sending');
  checkpoint('validation-and-astral-unicode');
  const status400 = buyer.waitForResponse(response => response.url().endsWith('/gonder/') && response.request().method() === 'POST');
  await send(buyer, 'x'.repeat(4001));
  check((await status400).status() === 400, 'Oversized UI message returns bound400');
  check((await buyer.getByLabel('Mesajın').inputValue()).length === 4001, 'Bound invalid text retained');
  await send(buyer, '😀'.repeat(4000));
  check(await buyer.locator('.message-body').last().innerText() === '😀'.repeat(4000), '4000 astral Unicode characters accepted through browser');
  await privacy(buyer); await layout(buyer);
  checkpoint('sql-history-and-inbox-pagination');
  fixture('paginate');
  await openThread(buyer);
  check(await buyer.locator('.message-bubble').count() === 30, 'Newest history bounded to30 rows');
  const newestSequences = await buyer.locator('.message-bubble').evaluateAll(rows => rows.map(row => Number(row.dataset.sequence)));
  check(newestSequences.every((value, index) => index === 0 || value === newestSequences[index - 1] + 1), 'Newest group displayed chronologically');
  await buyer.getByRole('link', { name: 'Daha eski mesajlar', exact: true }).click();
  check(await buyer.locator('#conversation-history').getAttribute('hx-trigger') === null, 'Older history has no automatic polling');
  check(await buyer.locator('.message-bubble').count() > 0 && await buyer.locator('.message-bubble').count() < 30, 'Older group paginated separately');
  await buyer.getByRole('link', { name: 'Daha yeni mesajlar', exact: true }).click();
  await goto(buyer, '/mesajlar/');
  check(await buyer.locator('.conversation-row').count() === 12, 'Inbox SQL first page12');
  await buyer.getByRole('link', { name: 'Sonraki', exact: true }).click();
  check(await buyer.locator('.conversation-row').count() === 2, 'Inbox second page2 from14 fresh threads');
  checkpoint('contact-preference-and-closed-listing');
  await goto(seller, '/ilanlar/' + data.listing + '/');
  await submit(seller, 'Yeni görüşmeleri kapat');
  check(await seller.getByRole('button', { name: 'Yeni görüşmeleri aç', exact: true }).count() === 1, 'Owner contact preference closes new contact');
  await openThread(buyer); await send(buyer, 'Kapalı iletişim tercihi mevcut yanıtı engellemez');
  fixture('close');
  await openThread(seller);
  check(await seller.getByText('İlan artık yayında değil.', { exact: true }).count() === 1, 'Closed listing history shows safe unavailable label');
  await send(seller, 'Kapalı ilan mevcut yanıtı engellemez');
  const newcomerContext = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'tr-TR' });
  const newcomer = await newcomerContext.newPage(); listen(newcomer); await login(newcomer, 'newcomer');
  await goto(newcomer, '/mesajlar/ilan/' + data.listing + '/', 403);
  check(await newcomer.getByLabel('Mesajın').count() === 0, 'Closed listing prevents different new initiator');
  await newcomerContext.close();
  await desktopContext.close(); await sellerContext.close();
  checkpoint('mobile-layout-and-keyboard');
  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'tr-TR', reducedMotion: 'reduce' });
  const mobile = await mobileContext.newPage(); listen(mobile);
  await login(mobile, 'buyer'); await openThread(mobile); await layout(mobile); await focus(mobile);
  await mobile.getByLabel('Mesajın').fill('Mobil klavye yanıtı');
  await capture(mobile, 'mobile-composer', mobile.locator('.conversation-composer'));
  await submit(mobile, 'Gönder', true);
  check(await mobile.locator('.message-body').last().innerText() === 'Mobil klavye yanıtı', 'Mobile keyboard normal POST succeeds');
  await capture(mobile, 'mobile-conversation', mobile.locator('#conversation-history'));
  await mobileContext.close();
  checkpoint('no-javascript-native-pointer');
  const noJSContext = await browser.newContext({ viewport: { width: 390, height: 844 }, javaScriptEnabled: false, locale: 'tr-TR', reducedMotion: 'reduce' });
  const noJS = await noJSContext.newPage(); listen(noJS);
  await login(noJS, 'seller'); await openThread(noJS); await layout(noJS);
  await send(noJS, 'JavaScript olmadan normal gönderim');
  check(await noJS.locator('.message-body').last().innerText() === 'JavaScript olmadan normal gönderim', 'NoJS pointer send persists message');
  await noJS.getByRole('link', { name: 'Mesajları yenile', exact: true }).click();
  check(await noJS.locator('.message-body').last().innerText() === 'JavaScript olmadan normal gönderim', 'NoJS GET refresh preserves history');
  await submit(noJS, 'Okundu olarak işaretle');
  await noJS.getByRole('link', { name: 'Daha eski mesajlar', exact: true }).click();
  check(await noJS.locator('#conversation-history').getAttribute('hx-trigger') === null, 'NoJS older navigation works');
  await privacy(noJS); await capture(noJS, 'nojs-history', noJS.locator('#conversation-history'));
  check(pageErrors.length === 0, 'No unexpected browser page errors');
  check(failures.filter(x => !x.includes('ERR_ABORTED')).length === 0, 'No unexpected request failures');
  checkpoint('complete');
  persist('PASS', { driver: require('../.browser-test-tools/node_modules/playwright-core/package.json').version,
    browser: browser.version(), javaScriptDisabled: true, fixtureGuard: data.guard });
  console.log(JSON.stringify(summary('PASS', { driver: require('../.browser-test-tools/node_modules/playwright-core/package.json').version, browser: browser.version() })));
})().catch(error => {
  persist('FAIL', { error: safe(error.message).slice(0, 1600) });
  console.log(JSON.stringify({ result: 'FAIL', run, stage, assertions: checks.length, error: safe(error.message).slice(0, 1600) }));
  process.exitCode = 1;
}).finally(async () => { if (browser) await browser.close(); });
