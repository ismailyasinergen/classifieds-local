'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const {chromium}=require('../.browser-test-tools/node_modules/playwright-core');
const {totp}=require('./mfa.cjs');
const root=path.resolve(__dirname,'../..'),base='http://localhost:8089',project='classifieds-rebuild-dev';
const run=crypto.randomBytes(8).toString('hex'),modes=['desktop','mobile','nojs'];
const passwords=Object.fromEntries([...modes,'reviewer'].map(m=>[m,crypto.randomBytes(32).toString('base64url')]));
const emails=Object.fromEntries([...modes,'reviewer'].map(m=>[m,`notifications-${run}-${m}@browser.example.test`]));
const out=path.join(root,'rebuild/test-artifacts/in-app-notifications',run),checks=[],posts=[],screenshots=[];
let stage='guard',browser,fixture,address,errors=0;
const startedAt=new Date().toISOString();
function check(value,name){assert.ok(value,name);checks.push(name);}
function docker(args,input){const r=spawnSync('docker',args,{cwd:root,input,encoding:'utf8',timeout:60000,maxBuffer:4*1024*1024,windowsHide:true});if(r.status!==0)throw Error('developer_command_failed');return r.stdout;}
const compose=['compose','-f','rebuild/compose.yaml','-f','rebuild/compose.dev.yaml','-p',project];
function guard(){
 const baseline=JSON.parse(fs.readFileSync(path.join(root,'rebuild/docs/phase12/baseline.json'))),candidate=JSON.parse(fs.readFileSync(path.join(root,'rebuild/docs/phase12/candidate-image-v2.json')));
 for(const service of ['web','worker','scheduler','db','redis']){
  const row=JSON.parse(docker(['inspect','--format','{"id":{{json .Id}},"image":{{json .Image}},"labels":{{json .Config.Labels}},"mounts":{{json .Mounts}},"networks":{{json .NetworkSettings.Networks}},"ports":{{json .NetworkSettings.Ports}},"running":{{json .State.Running}}}',`${project}-${service}-1`]));
  check(row.running&&row.labels['com.docker.compose.project']===project&&row.labels['com.docker.compose.service']===service,'exact developer '+service);
  check(Object.keys(row.networks).length===1&&row.networks[project+'_default'],'single developer network '+service);
  if(['db','redis'].includes(service))check(row.id===baseline.runtime.find(r=>r.project===project&&r.service===service).id,'persistent '+service+' unchanged');
  else check(row.image===candidate.imageId,'candidate image '+service);
  if(service==='db')address=row.networks[project+'_default'].IPAddress;
  if(service==='web'){
   check(row.mounts.some(m=>m.Type==='bind'&&m.Destination==='/app'&&!m.RW&&m.Source.toLowerCase().replaceAll('\\','/').replace(/^\/run\/desktop\/mnt\/host\/c\//,'c:/')===root.toLowerCase().replaceAll('\\','/')+'/rebuild/backend'),'exact readonly source');
   check(row.mounts.some(m=>m.Name===project+'_rebuild_media'&&m.Destination==='/var/lib/classifieds/media'),'developer media');
   check(JSON.stringify(row.ports['8000/tcp'])===JSON.stringify([{HostIp:'127.0.0.1',HostPort:'8089'}]),'loopback8089');
  }
 }
}
function fixtureCall(action){return JSON.parse(docker([...compose,'exec','-T','web','python','manage.py','notifications_browser_fixture'],JSON.stringify({action,run,db_address:address,...(action==='create'?{passwords}:{receipt:fixture.receipt})})));}
async function go(page,url){const r=await page.goto(base+url,{waitUntil:'domcontentloaded'});check(r.status()===200,stage+' GET200');return r;}
async function submit(page,button,label){const post=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).origin===base);await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),button.press('Enter')]);const r=await post;check(r.status()===302,label+' POST302');posts.push({action:label,status:r.status()});}
async function login(page,role){await go(page,'/accounts/login/?next=/accounts/security/');await page.locator('#id_login').fill(emails[role]);await page.locator('#id_password').fill(passwords[role]);await submit(page,page.locator('main form button[type=submit]'),'login '+role);}
async function approve(page,id){await go(page,`/inceleme/${id}/`);await page.locator('#id_action').selectOption('approve');await page.locator('#id_reason').fill('Sentetik geliştirici kabulü uygun.');await submit(page,page.getByRole('button',{name:'Kararı kaydet'}),'normal review approval');}
async function waitCompleted(count){const deadline=Date.now()+75000;while(Date.now()<deadline){const state=fixtureCall('inspect');check(state.failed===0,'no fixture consumer retry/failure');if(state.completed>=count)return state;await new Promise(r=>setTimeout(r,2000));}throw Error('bounded_worker_wait_expired');}
async function layout(page,label){const state=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,unlabelled:[...document.querySelectorAll('main input:not([type=hidden]),main select,main textarea')].filter(e=>!e.labels?.length).length}));check(!state.overflow,label+' no overflow');check(!state.unlabelled,label+' labels');const html=await page.content();check(!Object.values(emails).some(v=>html.includes(v))&&!Object.values(passwords).some(v=>html.includes(v)),label+' no credentials rendered');}
function persist(result,extra={}){fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify({run,result,stage,startedAt,finishedAt:new Date().toISOString(),assertions:checks.length,checks,realHtmlPosts:posts.length,posts,screenshots,browserErrors:errors,originalAdoption:false,...extra},null,2)+'\n');}
(async()=>{
 fs.mkdirSync(out,{recursive:true});guard();stage='fixture';fixture=fixtureCall('create');check(fixture.createdUsers===5&&fixture.createdListings===6,'fresh synthetic scope');
 browser=await chromium.launch({headless:true,executablePath:'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe'});
 const reviewerContext=await browser.newContext(),reviewer=await reviewerContext.newPage();reviewer.setDefaultTimeout(12000);
 stage='reviewer MFA';await login(reviewer,'reviewer');await reviewer.getByRole('link',{name:'Doğrulama uygulamasını eşleştir',exact:true}).click();await reviewer.getByText('Eşleştirme anahtarını göster',{exact:true}).click();const secret=(await reviewer.locator('.mfa-secret').textContent()).replace(/\s/g,'');
 const remaining=30-((Date.now()/1000)%30);if(remaining<5)await new Promise(r=>setTimeout(r,(remaining+1)*1000));
 await reviewer.getByLabel('Doğrulama kodu',{exact:true}).fill(totp(secret));await submit(reviewer,reviewer.locator('main form button[type=submit]'),'synthetic MFA enrollment');
 for(const [index,mode] of modes.entries()){
  stage=mode;const context=await browser.newContext({viewport:{width:mode==='mobile'?390:1440,height:900},javaScriptEnabled:mode!=='nojs'}),page=await context.newPage();page.setDefaultTimeout(12000);page.on('pageerror',()=>errors++);
  await login(page,mode);await go(page,`/?category=${fixture.category}&q=${mode}`);await page.getByLabel('Arama adı:',{exact:true}).fill('Yeni ilan aramam');await submit(page,page.getByRole('button',{name:'Aramayı kaydet',exact:true}),'save search '+mode);
  check(await page.getByRole('button',{name:'Uygulama içi bildirimleri aç'}).count()===1,'default disabled '+mode);await submit(page,page.getByRole('button',{name:'Uygulama içi bildirimleri aç'}),'enable '+mode);await layout(page,mode);
  await approve(reviewer,fixture.revisions[mode][0]);let state=await waitCompleted(index*2+1);check(state.deliveries===index+1,'beat worker first publication '+mode);
  const response=await go(page,'/bildirimlerim/');check((await response.allHeaders())['cache-control'].includes('no-store'),'private inbox '+mode);check(await page.locator('main article').count()===1,'one delivery '+mode);check((await page.locator('main').innerText()).includes('Sentetik bildirim '+mode+' 0'),'current public content '+mode);await layout(page,mode);
  const file=path.join(out,mode+'.png');await page.screenshot({path:file,fullPage:false});screenshots.push({mode,sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')});
  await submit(page,page.getByRole('button',{name:'Okundu işaretle'}),'read '+mode);check(!(await page.locator('nav').innerText()).includes('okunmamış'),'unread cleared '+mode);await submit(page,page.getByRole('button',{name:'Arşivle'}),'archive '+mode);check(await page.locator('main article').count()===0,'archive hidden '+mode);
  await go(page,'/kayitli-aramalarim/');await submit(page,page.getByRole('button',{name:'Bildirimleri durdur'}),'disable '+mode);await approve(reviewer,fixture.revisions[mode][1]);state=await waitCompleted(index*2+2);check(state.deliveries===index+1&&state.archived===index+1,'disabled period no delivery '+mode);await context.close();
 }
 const logs=docker([...compose,'logs','--since',startedAt,'--no-log-prefix','scheduler','worker']);
 const dispatches=(logs.match(/Scheduler: Sending due task consume-in-app-notifications/g)||[]).length,workerReceives=(logs.match(/Task notifications\.tasks\.consume_in_app_notifications\[[a-f0-9-]+\] received/g)||[]).length,workerFinishes=(logs.match(/in_app_consumer_completed chunks=\d+/g)||[]).length;
 check(dispatches>0&&workerReceives>0&&workerFinishes>0,'actual beat dispatch and worker completion');check(errors===0,'no browser errors');persist('PASS',{scheduler:{dispatches,workerReceives,workerFinishes,manualTaskDispatch:false},fixture:fixtureCall('inspect')});console.log(JSON.stringify({run,result:'PASS',assertions:checks.length,realHtmlPosts:posts.length,dispatches,workerReceives,workerFinishes}));
})().catch(()=>{persist('FAIL',{category:'browser_acceptance_failed'});console.log(JSON.stringify({run,result:'FAIL',stage,assertions:checks.length,realHtmlPosts:posts.length,category:'browser_acceptance_failed'}));process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
