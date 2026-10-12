/* Guarded developer-only acceptance. Secrets stay in memory; no raw diagnostics. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { validateRuntime, failureRecord, forbiddenDiagnosis, totp, screenshotAllowed: mfaScreenshot } = require('./mfa.cjs');
const BASE = 'http://localhost:8089';
const PROJECT = 'classifieds-rebuild-dev';
const MODES = ['desktop', 'mobile', 'nojs'];
const ROLES = MODES.flatMap(mode => ['sender', 'recipient', 'report-reviewer', 'appeal-reviewer'].map(role => mode + '-' + role));
function ensure(value) { if (!value) throw new Error('Controlled case acceptance failure'); }
function local(route) {
  const target = new URL(route, BASE);
  ensure(target.origin === BASE && target.protocol === 'http:' && !target.username && !target.password);
  return target.href;
}
function screenshotAllowed(url, base, sensitive) {
  if (mfaScreenshot(url, base, sensitive)) return true;
  try { const target = new URL(url); return base === BASE && target.origin === BASE && !target.search && !target.hash &&
    /^\/inceleme\/kararlarim\/[a-f0-9-]{36}\/$/.test(target.pathname) && sensitive === false; } catch { return false; }
}
function sourceIdentity(root) {
  const files = ['rebuild/requirements.lock', 'rebuild/browser-tests/reports-appeals.cjs'];
  function visit(relative) {
    for(const entry of fs.readdirSync(path.join(root,relative),{withFileTypes:true})) {
      if(entry.name === '__pycache__') continue;
      const file=relative+'/'+entry.name;
      if(entry.isDirectory()) visit(file);
      else if(/\.(py|html|css|js|txt|json)$/.test(entry.name)) files.push(file);
    }
  }
  visit('rebuild/backend');
  const map=files.sort().map(file=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex')+'  '+file+'\n').join('');
  return {paths:files.length,sha256:crypto.createHash('sha256').update(map).digest('hex')};
}
module.exports = { validateRuntime, failureRecord, forbiddenDiagnosis, screenshotAllowed, local };

async function main() {
  const { chromium } = require('../.browser-test-tools/node_modules/playwright-core');
  const root = path.resolve(__dirname, '../..');
  const run = crypto.randomBytes(8).toString('hex');
  const artifact = path.join(root, 'rebuild/test-artifacts/reports-appeals', run);
  const passwords = Object.fromEntries(ROLES.map(role => [role, crypto.randomBytes(32).toString('base64url')]));
  const emails = Object.fromEntries(ROLES.map(role => [role, `case-${run}-${role}@browser.example.test`]));
  const canary = 'report-private-' + crypto.randomBytes(12).toString('hex');
  const secrets = new Set([...Object.values(passwords), ...Object.values(emails), canary]);
  const checks = [], uiPosts = [], screenshots = [], supplementaryHTTP = [];
  let browser, receipt, dbAddress, targets, sources, mode = 'desktop', stage = 'guard', operation = 'guard', lastCheck = '';
  let ready = false, pageErrors = 0, requestFailures = 0, blockedExternalRequests = 0, asyncFailures = 0;
  let phaseAction = 'guard';
  let contexts = 0, links = 0, navigations = 0;
  function check(value, label) { lastCheck = label; operation = 'assertion'; ensure(value); checks.push(mode + ': ' + label); }
  function persist(result, extra = {}) {
    if (ready) fs.writeFileSync(path.join(artifact, 'summary.json'), JSON.stringify({ result, run, mode, stage,
      assertions: checks.length, checks, uiPosts, screenshots, supplementaryHTTP, contexts, links, navigations,
      pageErrors, requestFailures, blockedExternalRequests, asyncFailures, sources, phaseAction, ...extra }, null, 2) + '\n');
  }
  function docker(args, input) {
    const result = spawnSync('docker', args, { cwd: root, input, encoding: 'utf8', windowsHide: true, timeout: 60000, maxBuffer: 8*1024*1024 });
    ensure(result.status === 0 && !result.error); return result.stdout;
  }
  function guard() {
    operation = 'guard';
    const projection = '{"id":{{json .Id}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},' +
      '"service":{{json (index .Config.Labels "com.docker.compose.service")}},"oneoff":{{json (index .Config.Labels "com.docker.compose.oneoff")}},' +
      '"workingDirectory":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}},' +
      '"configFiles":{{json (index .Config.Labels "com.docker.compose.project.config_files")}},"running":{{json .State.Running}},' +
      '"mounts":{{json .Mounts}},"networks":{{json .NetworkSettings.Networks}},"ports":{{json .NetworkSettings.Ports}}}';
    const names = [PROJECT+'-web-1', PROJECT+'-db-1', PROJECT+'-redis-1',
      'classifieds-rebuild-web-1', 'classifieds-rebuild-db-1', 'classifieds-rebuild-redis-1'];
    const records = docker(['inspect', '--format', projection, ...names]).trim().split(/\r?\n/).map(JSON.parse);
    dbAddress = validateRuntime(root, BASE, records);
    check(true, 'Exact developer bind, origin, compose and separate persistent identities');
  }
  function fixture(action) {
    operation = 'fixture';
    const input = { action, run, db_address: dbAddress, ...(action === 'create' ? { passwords } : { receipt }) };
    const result = JSON.parse(docker(['compose','-f','rebuild/compose.yaml','-f','rebuild/compose.dev.yaml','-p',PROJECT,
      'exec','-T','web','python','manage.py','reports_appeals_browser_fixture'], JSON.stringify(input)));
    if (action === 'create') { receipt = result.receipt; secrets.add(receipt); return result.state; }
    return result;
  }
  async function remember(page) {
    for (const cookie of await page.context().cookies()) secrets.add(cookie.value);
    for (const field of await page.locator('input[type=hidden]').all()) { const value = await field.inputValue(); if(value) secrets.add(value); }
  }
  async function makePage(role, storageState) {
    const context = await browser.newContext({ viewport: mode === 'mobile' ? { width:390, height:844 } : { width:1440, height:1000 },
      locale:'tr-TR', javaScriptEnabled:mode !== 'nojs', reducedMotion:'reduce', serviceWorkers:'block', acceptDownloads:false,
      ...(storageState ? {storageState} : {}) });
    contexts += 1;
    await context.route('**/*', async route => {
      try { local(route.request().url()); await route.continue(); }
      catch { blockedExternalRequests += 1; await route.abort('blockedbyclient').catch(() => { asyncFailures += 1; }); }
    });
    const page = await context.newPage(); page.actorRole = mode + '-' + role;
    page.setDefaultTimeout(15000); page.setDefaultNavigationTimeout(20000);
    page.on('pageerror', () => { pageErrors += 1; });
    page.on('requestfailed', request => { if(request.failure()?.errorText !== 'net::ERR_ABORTED') requestFailures += 1; });
    return page;
  }
  async function suspend(page) {
    await remember(page);
    const state = await page.context().storageState();
    await page.context().close();
    return state;
  }
  async function go(page, route, status = 200) {
    operation = 'navigation';
    await page.bringToFront();
    const response = await page.goto(local(route), { waitUntil:'domcontentloaded' }); navigations += 1;
    check(response && response.status() === status, 'Navigation status ' + status);
    local(page.url()); await remember(page); return response;
  }
  async function follow(page, locator) {
    local(await locator.getAttribute('href'));
    const [response] = await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}), locator.click()]);
    links += 1; navigations += 1; local(page.url()); check(response.status() === 200, 'Bounded link navigation succeeds');
    await remember(page);
  }
  async function submit(page, label, status = 302) {
    operation = 'form_submit'; await remember(page);
    await page.bringToFront();
    const button = typeof label === 'string' ? page.getByRole('button', {name:label,exact:true}) : label;
    if(mode !== 'mobile') {
      await button.focus();
      await page.keyboard.press('Tab');
      await page.keyboard.press('Shift+Tab');
      const focus = await button.evaluate(el => ({active:el === document.activeElement,
        style:getComputedStyle(el).outlineStyle,width:parseFloat(getComputedStyle(el).outlineWidth)}));
      check(focus.active && focus.style !== 'none' && focus.width > 0, 'Keyboard submit has visible focus');
    }
    const [response] = await Promise.all([
      page.waitForResponse(value => value.request().method() === 'POST' && value.request().isNavigationRequest() && new URL(value.url()).origin === BASE),
      page.waitForNavigation({waitUntil:'domcontentloaded'}), mode === 'mobile' ? button.click() : button.press('Enter')]);
    uiPosts.push({ mode, role:page.actorRole.split('-').slice(1).join('-'), status:response.status(), input:mode === 'mobile'?'pointer':'keyboard' });
    if(uiPosts.length % 10 === 0) console.log(JSON.stringify({run,mode,uiPosts:uiPosts.length,assertions:checks.length}));
    check(response.status() === status, 'Real CSRF form POST status ' + status); local(page.url()); await remember(page);
    persist('RUNNING'); return response;
  }
  async function layout(page) {
    const state = await page.evaluate(() => ({ overflow:document.documentElement.scrollWidth > innerWidth + 1,
      unlabelled:[...document.querySelectorAll('main input:not([type=hidden]),main select,main textarea')]
        .filter(el => !el.labels?.length && !el.getAttribute('aria-label')).length }));
    check(!state.overflow, 'No horizontal overflow'); check(state.unlabelled === 0, 'Visible form fields have labels');
  }
  async function login(page) {
    phaseAction='login';
    await go(page, '/accounts/login/?next=/accounts/security/');
    await page.locator('#id_login').fill(emails[page.actorRole]); await page.locator('#id_password').fill(passwords[page.actorRole]);
    await submit(page, page.locator('main form button[type=submit]'));
  }
  async function enroll(page) {
    phaseAction='enroll';
    await go(page, '/accounts/security/');
    await follow(page, page.getByRole('link', {name:'Doğrulama uygulamasını eşleştir',exact:true}));
    await page.getByText('Eşleştirme anahtarını göster',{exact:true}).click();
    const secret = (await page.locator('.mfa-secret').textContent()).replace(/\s/g,''); secrets.add(secret);
    ensure(/^[A-Z2-7]+=*$/.test(secret));
    while (30 - ((Date.now()/1000)%30) < 5) await new Promise(resolve => setTimeout(resolve,150));
    const code = totp(secret); secrets.add(code);
    await page.getByLabel('Doğrulama kodu',{exact:true}).fill(code);
    await submit(page, page.locator('main form button[type=submit]'));
    for(const value of await page.locator('ol.recovery-codes code').allTextContents()) secrets.add(value.trim());
    await go(page, '/accounts/security/');
    check((await page.locator('main').innerText()).includes('İki adımlı doğrulama tamamlandı'), 'Normal UI TOTP creates genuine proof');
  }
  function id(page) { const match = new URL(page.url()).pathname.match(/\/([a-f0-9-]{36})\/$/); ensure(match); return match[1]; }
  async function report(page, route, text = canary, status = 302) {
    phaseAction='report';
    await go(page, route); await layout(page);
    const token = await page.locator('[name=client_token]').inputValue();
    await page.getByLabel('Bildirim nedeni').selectOption('other'); await page.getByLabel(/^Açıklama:?$/).fill(text);
    const response = await submit(page,'Bildirim gönder',status);
    if(status === 429) {
      check(Number((await response.allHeaders())['retry-after']) > 0, 'Report quota has positive Retry-After');
      check(await page.locator('[name=client_token]').inputValue() === token && await page.getByLabel(/^Açıklama:?$/).inputValue() === text, '429 preserves report token and text');
      return null;
    }
    return id(page);
  }
  async function queued(page, route, target) {
    await go(page, route);
    for(let at=0; at<100; at++) {
      const exact = page.locator('main a[href="'+target+'"]');
      if(await exact.count()) { await follow(page,exact); return; }
      const next = page.getByRole('link',{name:'Sonraki sayfa',exact:true});
      ensure(await next.count() === 1); await follow(page,next);
    }
    ensure(false);
  }
  async function decide(page, reportId, action) {
    phaseAction='report_decision';
    await queued(page,'/inceleme/bildirimler/',`/inceleme/bildirimler/${reportId}/`);
    await page.getByLabel(/^Karar:?$/).selectOption(action);
    await page.getByLabel(/^Kullanıcıya gösterilecek gerekçe:?$/).fill('Sentetik kabul kararı');
    if(action === 'restrict_messaging') {
      const end = new Date(Date.now()+86400000);
      const localDate = new Date(end.getTime()-end.getTimezoneOffset()*60000).toISOString().slice(0,16);
      await page.getByLabel('Kısıt bitiş zamanı').fill(localDate);
    }
    await submit(page,'Kararı kaydet');
  }
  async function subjectDecision(page, text) {
    await go(page,'/inceleme/kararlarim/');
    await follow(page,page.locator('main .case-list a').filter({hasText:text}).first());
    check(!(await page.locator('main').innerText()).includes(canary), 'Subject never sees reporter private explanation');
    return new URL(page.url()).pathname;
  }
  async function appeal(page, decisionPath, status = 302) {
    phaseAction='appeal';
    await go(page,decisionPath+'itiraz/'); await layout(page);
    const token = await page.locator('[name=client_token]').inputValue();
    await page.getByLabel(/^Açıklama:?$/).fill('Sentetik itiraz açıklaması');
    const response = await submit(page,'İtiraz gönder',status);
    if(status === 429) {
      check(Number((await response.allHeaders())['retry-after']) > 0 && await page.locator('[name=client_token]').inputValue() === token,
        '429 appeal quota preserves token and retry'); return null;
    }
    return id(page);
  }
  async function resolve(page, appealId, outcome) {
    phaseAction='appeal_decision';
    await queued(page,'/inceleme/itirazlar/',`/inceleme/itirazlar/${appealId}/`);
    await page.getByLabel(/^İtiraz kararı:?$/).selectOption(outcome);
    await page.getByLabel(/^Kullanıcıya gösterilecek gerekçe:?$/).fill('Sentetik bağımsız inceleme');
    await submit(page,'İtiraz kararını kaydet');
  }
  async function capture(page, name) {
    await remember(page); await layout(page);
    const sensitive = await page.locator('.mfa-qr,.mfa-secret,.recovery-codes,input[name=code],input[type=password],a[href^="otpauth:"]').count();
    const body = await page.locator('body').innerText();
    check(screenshotAllowed(page.url(),BASE,sensitive !== 0) && ![...secrets].some(value => value && body.includes(value)), 'Screenshot passes explicit route and secret canary guard');
    const file = path.join(artifact,name+'.png'); await page.screenshot({path:file,fullPage:true});
    const bytes = fs.readFileSync(file); screenshots.push({path:path.relative(root,file).replace(/\\/g,'/'),sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length});
  }
  async function journey() {
    stage = 'reviewer'; console.log(JSON.stringify({run,mode,stage}));
    const target = targets[mode];
    // Sync Gunicorn workers can be occupied by idle browser sockets. Keep one
    // live context; genuine role-specific session cookies remain only in memory.
    let sender=await makePage('sender'); await login(sender);
    await go(sender,`/inceleme/bildir/ilan/${target.stale}/`,409);
    const main = await report(sender,`/inceleme/bildir/ilan/${target.main}/`);
    const duplicate = await report(sender,`/inceleme/bildir/ilan/${target.main}/`,'Farklı sentetik açıklama');
    check(main === duplicate && (await sender.locator('main').innerText()).includes('yeni açıklama kaydedilmedi'), 'Duplicate preserves original report');
    const noAction=await report(sender,`/inceleme/bildir/ilan/${target.no_action}/`);
    let senderState=await suspend(sender);
    let recipient=await makePage('recipient'); await login(recipient);
    const reports=[];
    const count=mode==='desktop'?20:3;
    for(const message of target.messages.slice(0,count)) reports.push(await report(recipient,`/inceleme/bildir/mesaj/${message}/`));
    if(mode==='desktop') await report(recipient,`/inceleme/bildir/mesaj/${target.messages[20]}/`,canary,429);
    await go(recipient,`/mesajlar/${target.conversation}/`); await submit(recipient,'Karşı tarafı engelle');
    let recipientState=await suspend(recipient);
    let reviewer=await makePage('report-reviewer'); await login(reviewer); await enroll(reviewer);
    await decide(reviewer,noAction,'no_action'); await decide(reviewer,main,'hide_listing');
    const sanctions=mode==='desktop'?11:3;
    for(const value of reports.slice(0,sanctions)) await decide(reviewer,value,'restrict_messaging');
    let reviewerState=await suspend(reviewer);
    recipient=await makePage('recipient',recipientState);
    const decision=await subjectDecision(recipient,'main');
    const listingAppeal=await appeal(recipient,decision);
    recipientState=await suspend(recipient);
    reviewer=await makePage('report-reviewer',reviewerState);
    await go(reviewer,`/inceleme/itirazlar/${listingAppeal}/`,403);
    await reviewer.context().close();
    let second=await makePage('appeal-reviewer'); await login(second); await enroll(second);
    await resolve(second,listingAppeal,'revoke');
    let secondState=await suspend(second);
    recipient=await makePage('recipient',recipientState);
    await go(recipient,decision); check((await recipient.locator('main').innerText()).includes('Yaptırım geri alındı'), 'Independent appeal revokes listing sanction');
    await capture(recipient,mode+'-decision');
    recipientState=await suspend(recipient);
    sender=await makePage('sender',senderState);
    await go(sender,'/inceleme/kararlarim/');
    const paths=await sender.locator('main .case-list a').evaluateAll(elements=>elements.map(el=>el.getAttribute('href')));
    check(paths.length===sanctions, 'Subject sees only own message sanctions');
    const appeals=[];
    for(const route of paths.slice(0,mode==='desktop'?10:3)) appeals.push(await appeal(sender,route));
    if(mode==='desktop') await appeal(sender,paths[10],429);
    senderState=await suspend(sender);
    second=await makePage('appeal-reviewer',secondState);
    await resolve(second,appeals[0],'uphold');
    const before=fixture('inspect'); await resolve(second,appeals[1],'revoke'); const after=fixture('inspect');
    check(after.counts.active_messaging_restrictions===before.counts.active_messaging_restrictions-1 && after.counts.blocks===before.counts.blocks,
      'Revoke affects exactly one restriction and preserves UserBlock');
    await second.context().close();
    sender=await makePage('sender',senderState);
    await go(sender,paths[0]); check((await sender.locator('main').innerText()).includes('Yaptırım etkin'), 'Upheld restriction remains active');
    await go(sender,paths[1]); check((await sender.locator('main').innerText()).includes('Yaptırım geri alındı'), 'Only selected message restriction revoked');
    await sender.context().close();
    recipient=await makePage('recipient',recipientState);
    await go(recipient,`/mesajlar/${target.conversation}/`); check(await recipient.getByRole('button',{name:'Engeli kaldır',exact:true}).count()===1,'Existing block remains visible');
    await recipient.context().close();
    persist('RUNNING');
  }
  try {
    ensure(process.argv.length===2); guard(); sources=sourceIdentity(root); fs.mkdirSync(artifact,{recursive:true}); ready=true;
    stage='create'; const initial=fixture('create'); targets=initial.targets;
    check(initial.factors===0 && initial.counts.reports===0 && initial.counts.decisions===0,'Fixture did not fabricate MFA or cases');
    browser=await chromium.launch({headless:true,executablePath:'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe'});
    for(const selected of MODES){mode=selected;await journey();}
    const final=fixture('inspect'); guard();
    check(pageErrors===0 && requestFailures===0 && blockedExternalRequests===0 && asyncFailures===0,'No browser or external-origin errors');
    check(final.factors===12,'Six UI reviewers each have primary and recovery factors');
    check(JSON.stringify(sources)===JSON.stringify(sourceIdentity(root)),'Browser-tested source identity stayed unchanged');
    stage='complete'; persist('PASS',{counts:final.counts,commandCompleted:true});
    console.log(JSON.stringify({result:'PASS',run,assertions:checks.length,uiPosts:uiPosts.length,screenshots:screenshots.length}));
  } catch(error) {
    const failure=failureRecord(stage,operation,error); persist('FAIL',{failure,lastCheck,commandCompleted:false});
    console.log(JSON.stringify({result:'FAIL',run,failure,lastCheck})); process.exitCode=1;
  } finally {if(browser) await browser.close().catch(()=>{});}
}
if(require.main===module) main().catch(()=>{console.log('{"result":"FAIL","kind":"runner_startup_error"}');process.exitCode=1;});
