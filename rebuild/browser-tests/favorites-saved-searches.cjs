/* Real HTML forms on the exact developer runtime. No credentials or raw diagnostics leave memory. */
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const { chromium } = require('../.browser-test-tools/node_modules/playwright-core');
const root = path.resolve(__dirname, '../..'), project = 'classifieds-rebuild-dev', base = 'http://localhost:8089';
const run = crypto.randomBytes(8).toString('hex');
const modes = ['desktop', 'mobile', 'nojs'];
const passwords = Object.fromEntries(modes.map(mode => [mode, crypto.randomBytes(32).toString('base64url')]));
const emails = Object.fromEntries(modes.map(mode => [mode, `favorites-${run}-${mode}@browser.example.test`]));
const output = path.join(root, 'rebuild/test-artifacts/favorites-saved-searches', run);
const checks = [], posts = [], screenshots = [];
let stage = 'guard', browser, browserErrors = 0;
function check(value, label) { assert.ok(value, label); checks.push(label); }
function docker(args, input) {
  const result = spawnSync('docker', args, { cwd: root, input, encoding: 'utf8', timeout: 60000, windowsHide: true });
  if (result.status !== 0) throw new Error('developer_command_failed');
  return result.stdout;
}
function inspect(name) {
  return JSON.parse(docker(['inspect', '--format', '{"id":{{json .Id}},"image":{{json .Image}},"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}},"networks":{{json .NetworkSettings.Networks}},"ports":{{json .NetworkSettings.Ports}},"running":{{json .State.Running}}}', name]));
}
function guard() {
  check(root.toLowerCase().replaceAll('\\', '/') === 'c:/users/ismai/.devspace/worktrees/classifieds_local-a7be577c', 'exact developer root');
  const baseline = JSON.parse(fs.readFileSync(path.join(root, 'rebuild/docs/phase10/baseline.json')));
  const candidate = JSON.parse(fs.readFileSync(path.join(root, 'rebuild/docs/phase10/candidate-image.json')));
  const rows = {};
  for (const service of ['web', 'db', 'redis']) {
    const row = rows[service] = inspect(`${project}-${service}-1`);
    check(row.labels['com.docker.compose.project'] === project && row.labels['com.docker.compose.service'] === service && row.running, 'exact running developer ' + service);
    check(Object.keys(row.networks).length === 1 && !!row.networks[project + '_default'], 'isolated developer network ' + service);
    if (service !== 'web') check(row.id === baseline.runtime.find(x => x.project === project && x.service === service).id, 'persistent container preserved ' + service);
  }
  check(rows.web.image === candidate.imageId, 'reviewed developer candidate image');
  check(rows.web.mounts.some(x => x.Type === 'bind' && x.Destination === '/app' && x.RW === false && x.Source.toLowerCase().replaceAll('\\', '/').replace(/^\/run\/desktop\/mnt\/host\/c\//, 'c:/') === root.toLowerCase().replaceAll('\\', '/') + '/rebuild/backend'), 'readonly exact app source');
  check(rows.web.mounts.some(x => x.Destination === '/var/lib/classifieds/media' && x.Name === project + '_rebuild_media'), 'exact developer media volume');
  check(rows.db.mounts.some(x => x.Destination === '/var/lib/postgresql/data' && x.Name === project + '_rebuild_postgres'), 'exact developer database volume');
  check(rows.redis.mounts.some(x => x.Destination === '/data' && x.Name === project + '_rebuild_redis'), 'exact developer redis volume');
  check(JSON.stringify(rows.web.ports['8000/tcp']) === JSON.stringify([{HostIp:'127.0.0.1',HostPort:'8089'}]), 'only loopback8089');
  return rows.db.networks[project + '_default'].IPAddress;
}
function persist(result) {
  fs.writeFileSync(path.join(output, 'summary.json'), JSON.stringify({run,result,stage,assertions:checks.length,checks,
    realHtmlPosts:posts.length,posts,screenshots,browserErrors,originalAdoption:false},null,2)+'\n');
}
async function goto(page, route) {
  const response = await page.goto(base + route, {waitUntil:'domcontentloaded'});
  check(response.status() === 200, stage + ': GET200');
  return response;
}
async function submit(page, button, mode, action) {
  const post = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).origin === base);
  await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}), button.press('Enter')]);
  const response = await post;
  check(response.status() === 302, mode + ': ' + action + ' POST302');
  check(new URL(page.url()).origin === base, mode + ': local redirect');
  posts.push({mode,action,status:response.status(),input:'keyboard Enter'});
}
async function layout(page, label) {
  const state = await page.evaluate(() => ({overflow:document.documentElement.scrollWidth > innerWidth,
    unlabeled:[...document.querySelectorAll('main input:not([type=hidden]),main select,main textarea')].filter(x=>!x.labels?.length).length}));
  check(!state.overflow, label + ': no horizontal overflow');
  check(state.unlabeled === 0, label + ': labelled controls');
  const html = await page.content();
  check(!Object.values(emails).some(x=>html.includes(x)) && !Object.values(passwords).some(x=>html.includes(x)), label + ': no identity or password rendered');
}
async function screenshot(page, mode) {
  check(!page.url().includes('/accounts/'), 'no authentication screenshot');
  const file = path.join(output, mode + '.png');
  await page.screenshot({path:file,fullPage:false});
  screenshots.push({path:path.relative(root,file).replaceAll('\\','/'),sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')});
}
(async()=>{
  fs.mkdirSync(output,{recursive:true});
  const address = guard();
  stage='fixture';
  const data = JSON.parse(docker(['compose','-f','rebuild/compose.yaml','-f','rebuild/compose.dev.yaml','-p',project,'exec','-T','web','python','manage.py','favorites_browser_fixture'], JSON.stringify({run,passwords,db_address:address})));
  check(data.createdUsers===4 && data.createdListings===13,'fresh reserved synthetic records');
  browser = await chromium.launch({headless:true,executablePath:'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe'});
  for (const mode of modes) {
    stage=mode;
    const context=await browser.newContext({viewport:{width:mode==='mobile'?390:1440,height:900},javaScriptEnabled:mode!=='nojs'});
    const page=await context.newPage(); page.setDefaultTimeout(12000); page.on('pageerror',()=>browserErrors++);
    await goto(page,'/accounts/login/?next=/favorilerim/');
    await page.locator('#id_login').fill(emails[mode]); await page.locator('#id_password').fill(passwords[mode]);
    await submit(page,page.locator('main form button[type=submit]'),mode,'login');
    check(new URL(page.url()).pathname==='/favorilerim/',mode+': real allauth login');
    check(await page.getByRole('heading',{name:'İlan şu anda kullanılamıyor'}).count()===1,mode+': closed listing placeholder');
    check(!(await page.locator('main').innerText()).includes('Sentetik favori 00'),mode+': closed title hidden');
    await goto(page,`/ilanlar/${data.listing}/`);
    await submit(page,page.getByRole('button',{name:'Favorilere ekle',exact:true}),mode,'favorite add');
    check(await page.getByRole('button',{name:'Favorilerden kaldır',exact:true}).count()===1,mode+': explicit remove action');
    let response=await goto(page,'/favorilerim/');
    check((await response.allHeaders())['cache-control'].includes('no-store'),mode+': private favorites');
    check(await page.locator('main article').count()===12,mode+': twelve favorite rows');
    await page.getByRole('link',{name:'Sonraki',exact:true}).click();
    check(await page.locator('main article').count()===1,mode+': favorite second page');
    await goto(page,`/ilanlar/${data.listing}/`);
    await submit(page,page.getByRole('button',{name:'Favorilerden kaldır',exact:true}),mode,'favorite remove');
    await goto(page,'/?'+new URLSearchParams({category:String(data.category),q:'Sentetik favori',currency:'TRY',price_min:'1234.50',page:'2'}));
    await layout(page,mode+' search');
    await page.getByLabel('Arama adı:',{exact:true}).fill('Şişli <b>arama</b>');
    await page.getByLabel('Arama adı:',{exact:true}).press('Tab');
    const focused=await page.evaluate(()=>({tag:document.activeElement.tagName,outline:getComputedStyle(document.activeElement).outlineStyle}));
    check(focused.tag==='BUTTON' && focused.outline!=='none',mode+': visible keyboard focus');
    await submit(page,page.getByRole('button',{name:'Aramayı kaydet',exact:true}),mode,'save search');
    check(await page.locator('main article').count()===12,mode+': twelve saved searches');
    check(await page.getByRole('link',{name:'Sonraki',exact:true}).count()===1,mode+': search pagination');
    check(await page.locator('main article b').count()===0,mode+': search name escaped');
    check((await page.locator('main').innerText()).includes('otomatik bildirim veya e-posta göndermez'),mode+': no notification promise');
    await layout(page,mode+' saved searches'); await screenshot(page,mode);
    await page.locator('main article').first().getByRole('link',{name:'Aramayı aç',exact:true}).click();
    const query=new URL(page.url()).searchParams;
    check(!query.has('page') && query.get('q')==='Sentetik favori' && query.get('price_min')==='1234.50',mode+': canonical first-page reopen');
    await page.getByLabel('Arama adı:',{exact:true}).fill('Different name');
    await submit(page,page.getByRole('button',{name:'Aramayı kaydet',exact:true}),mode,'duplicate save');
    check(await page.getByRole('heading',{name:'Şişli <b>arama</b>',exact:true}).count()===1,mode+': duplicate retains name');
    await page.locator('main article').first().getByRole('link',{name:'Adını değiştir',exact:true}).click();
    await page.getByLabel('Arama adı:',{exact:true}).fill('Yeni ad');
    await submit(page,page.getByRole('button',{name:'Kaydet',exact:true}),mode,'rename');
    check(await page.getByRole('heading',{name:'Yeni ad',exact:true}).count()===1,mode+': rename visible');
    await submit(page,page.locator('main article').first().getByRole('button',{name:'Aramayı sil',exact:true}),mode,'delete search');
    check(await page.getByRole('heading',{name:'Yeni ad',exact:true}).count()===0,mode+': deleted search absent');
    await context.close(); persist('RUNNING');
  }
  check(browserErrors===0,'no browser page errors'); stage='complete'; persist('PASS');
  console.log(JSON.stringify({result:'PASS',run,assertions:checks.length,realHtmlPosts:posts.length,screenshots:screenshots.length}));
})().catch(()=>{persist('FAIL');console.error(JSON.stringify({result:'FAIL',stage,assertions:checks.length,error:'browser_acceptance_failed_raw_diagnostic_withheld'}));process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
