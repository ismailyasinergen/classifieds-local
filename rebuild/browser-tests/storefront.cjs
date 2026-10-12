'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');
const {chromium}=require('../.browser-test-tools/node_modules/playwright-core');
const root=path.resolve(__dirname,'../..'),base='http://localhost:8089',project='classifieds-rebuild-dev';
const run=crypto.randomBytes(8).toString('hex'),modes=['desktop','mobile','nojs'];
const passwords=Object.fromEntries(modes.map(m=>[m,crypto.randomBytes(32).toString('base64url')]));
const emails=Object.fromEntries(modes.map(m=>[m,`storefront-${run}-${m}@browser.example.test`]));
const out=path.join(root,'rebuild/test-artifacts/storefront',run),checks=[],posts=[],screenshots=[];
let stage='guard',browser,address,errors=0;
const startedAt=new Date().toISOString();
function check(value,name){assert.ok(value,name);checks.push(name);}
function docker(args,input){const r=spawnSync('docker',args,{cwd:root,input,encoding:'utf8',timeout:60000,maxBuffer:4*1024*1024,windowsHide:true});if(r.status!==0)throw Error('developer_command_failed');return r.stdout;}
const compose=['compose','-f','rebuild/compose.yaml','-f','rebuild/compose.dev.yaml','-p',project];
function guard(){
 const baseline=JSON.parse(fs.readFileSync(path.join(root,'rebuild/docs/phase14/baseline.json'))),candidate=JSON.parse(fs.readFileSync(path.join(root,'rebuild/docs/phase14/candidate-image-v4.json')));
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
async function go(page,url){const r=await page.goto(base+url,{waitUntil:'domcontentloaded'});check(r.status()===200,stage+' GET200');return r;}
async function submit(page,button,label){const post=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).origin===base);await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),button.press('Enter')]);const r=await post;check(r.status()===302,label+' POST302');posts.push({action:label,status:r.status()});}
async function login(page,mode){await go(page,'/accounts/login/?next=/vitrinim/');await page.locator('#id_login').fill(emails[mode]);await page.locator('#id_password').fill(passwords[mode]);await submit(page,page.locator('main form button[type=submit]'),'login '+mode);}
async function layout(page,label){const state=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,unlabelled:[...document.querySelectorAll('main input:not([type=hidden]),main select,main textarea')].filter(e=>!e.labels?.length).length}));check(!state.overflow,label+' no overflow');if(await page.locator('.search-common-grid').count()){const n=await page.locator('.search-common-grid').evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length);check(n===(page.viewportSize().width<700?1:4),label+' responsive grid');}check(!state.unlabelled,label+' labels');const html=await page.content();check(!Object.values(emails).some(v=>html.includes(v))&&!Object.values(passwords).some(v=>html.includes(v)),label+' no credentials rendered');}
function persist(result,extra={}){fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify({run,result,stage,startedAt,finishedAt:new Date().toISOString(),assertions:checks.length,checks,realHtmlPosts:posts.length,posts,screenshots,browserErrors:errors,originalAdoption:false,...extra},null,2)+'\n',{flag:'wx'});}
(async()=>{
 fs.mkdirSync(out,{recursive:true});guard();stage='fixture';const fixture=JSON.parse(docker([...compose,'exec','-T','web','python','manage.py','storefront_browser_fixture'],JSON.stringify({run,passwords,db_address:address})));check(fixture.createdUsers===3&&fixture.createdListings===42,'fresh synthetic scope');
 browser=await chromium.launch({headless:true,executablePath:'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe'});
 const visitorContext=await browser.newContext(),visitor=await visitorContext.newPage();visitor.setDefaultTimeout(12000);
 for(const mode of modes){
  stage=mode;const context=await browser.newContext({viewport:{width:mode==='mobile'?390:1440,height:900},javaScriptEnabled:mode!=='nojs'}),page=await context.newPage();page.setDefaultTimeout(12000);page.on('pageerror',()=>errors++);
  await login(page,mode);await go(page,'/vitrinim/');check(await page.getByRole('button',{name:'Vitrin oluştur',exact:true}).count()===1,'optional initial '+mode);
  await page.getByLabel('Vitrin adı:',{exact:true}).fill('Sentetik '+mode+' vitrini');await page.getByLabel('Tanıtım metni:',{exact:true}).fill('İlk taslak tanıtımı');await submit(page,page.getByRole('button',{name:'Vitrin oluştur',exact:true}),'create '+mode);
  await page.getByLabel('Tanıtım metni:',{exact:true}).fill('Yayımlanacak tanıtım');await submit(page,page.getByRole('button',{name:'Taslağı kaydet',exact:true}),'save draft '+mode);
  await page.getByRole('link',{name:'Özel önizleme',exact:true}).click();check((await page.locator('main').innerText()).includes('Yayımlanacak tanıtım'),'preview draft '+mode);check(await page.locator('.listing-card').count()===12,'preview public paginated '+mode);check(!(await page.locator('main').innerText()).includes('Gizli vitrin canary'),'preview hidden excluded '+mode);
  await go(page,'/vitrinim/');await submit(page,page.getByRole('button',{name:'Vitrini yayımla',exact:true}),'publish '+mode);stage=mode+' public-link';const publicUrl=await page.getByRole('link',{name:'Public vitrini aç',exact:true}).getAttribute('href');
  stage=mode+' anonymous-public';let response=await go(visitor,publicUrl);check((await response.allHeaders())['cache-control'].includes('no-store'),'public private cache '+mode);check(await visitor.locator('.listing-card').count()===12,'public page twelve '+mode);let text=await visitor.locator('main').innerText();check(!text.includes('Gizli vitrin canary')&&!modes.filter(m=>m!==mode).some(m=>text.includes('Sentetik '+m+' ilan')),'seller isolation '+mode);check(await visitor.getByRole('button',{name:'Aramayı kaydet',exact:true}).count()===0,'no scoped saved search '+mode);
  stage=mode+' public-layout';await go(page,publicUrl);await layout(page,mode+' public');await page.getByRole('link',{name:'Sonraki',exact:true}).click();check(new URL(page.url()).pathname===publicUrl,'pagination retains scope '+mode);check(await page.locator('.listing-card').count()===1,'second page one '+mode);
  await page.locator('#id_q').fill('ilan 00');await Promise.all([page.waitForNavigation({waitUntil:'domcontentloaded'}),page.getByRole('button',{name:'Ara',exact:true}).press('Enter')]);check(new URL(page.url()).pathname===publicUrl,'filter retains scope '+mode);check(await page.locator('.listing-card').count()===1,'filtered public result '+mode);await layout(page,mode+' filtered');
  const file=path.join(out,mode+'.png');await page.screenshot({path:file,fullPage:false});screenshots.push({mode,sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')});
  await go(page,'/vitrinim/');await page.getByLabel('Tanıtım metni:',{exact:true}).fill('Yeni özel taslak');await submit(page,page.getByRole('button',{name:'Taslağı kaydet',exact:true}),'independent draft '+mode);await go(visitor,publicUrl);check((await visitor.locator('main').innerText()).includes('Yayımlanacak tanıtım')&&!(await visitor.locator('main').innerText()).includes('Yeni özel taslak'),'published snapshot preserved '+mode);
  await submit(page,page.getByRole('button',{name:'Yayını güncelle',exact:true}),'update publication '+mode);await go(visitor,publicUrl);check((await visitor.locator('main').innerText()).includes('Yeni özel taslak'),'explicit update visible '+mode);await layout(page,mode+' management');
  await submit(page,page.getByRole('button',{name:'Yayından kaldır',exact:true}),'unpublish '+mode);response=await visitor.goto(base+publicUrl);check(response.status()===404,'removed public 404 '+mode);await context.close();
 }
 check(errors===0,'no browser errors');persist('PASS',{fixture});console.log(JSON.stringify({run,result:'PASS',assertions:checks.length,realHtmlPosts:posts.length}));
})().catch(error=>{const category=error.name==='TimeoutError'?'browser_timeout':error.code==='ERR_ASSERTION'?'browser_assertion_failed':'browser_operation_failed';persist('FAIL',{category});console.log(JSON.stringify({run,result:'FAIL',stage,assertions:checks.length,realHtmlPosts:posts.length,category}));process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
