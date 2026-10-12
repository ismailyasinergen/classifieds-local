/* Local synthetic end-to-end proof. No credentials, authentication URLs, browser storage or raw errors leave this process. */
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const zlib = require('zlib');
const assert = require('assert/strict');
const { spawnSync } = require('child_process');
const { chromium } = require('../.browser-test-tools/node_modules/playwright-core');
const base = 'http://127.0.0.1:8088';
const run = crypto.randomBytes(8).toString('hex');
const passwords = {seller:crypto.randomBytes(32).toString('base64url'), reviewer:crypto.randomBytes(32).toString('base64url'),staff:crypto.randomBytes(32).toString('base64url')};
const emails = Object.fromEntries(['seller','reviewer','staff'].map(role=>[role,`task5-${run}-${role}@browser.example.test`]));
const secrets = [...Object.values(passwords),...Object.values(emails)];
const artifactDir = path.resolve('rebuild/test-artifacts/task-5');
let stage = 'launch';
let browser;
const pageErrors = [];
const networkFailures = [];
const screenshots = [];
let assertions = 0;
function safe(value) {
  let text = String(value);
  for (const secret of secrets) if(secret) text=text.split(secret).join('[secret]');
  return text.replace(/https?:\/\/[^\s"'<>]+/g,'[url]').replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi,'[email]').slice(0,1600);
}
function check(condition, message){assert.ok(condition,message);assertions++;}
function checkpoint(name){stage=name;console.log(JSON.stringify({checkpoint:name}));}
function fixture(action, role='seller') {
  const input = {action,role,run};
  if(action==='reviewer') input.password=passwords[role];
  const result = spawnSync('docker',['compose','-f','rebuild/compose.yaml','-p','classifieds-rebuild','exec','-T','web','python','manage.py','browser_fixture'],{input:JSON.stringify(input),encoding:'utf8',timeout:30000,windowsHide:true});
  if(result.status!==0) throw new Error('Synthetic fixture operation failed');
  const output=JSON.parse(result.stdout);
  if(output.url){secrets.push(output.url);secrets.push(output.url.split('/').filter(Boolean).at(-1));}
  return output;
}
function listen(page) {
  page.setDefaultTimeout(15000);
  page.on('pageerror',error=>pageErrors.push(safe(error.message)));
  page.on('requestfailed',request=>networkFailures.push({url:safe(request.url()),error:safe(request.failure()?.errorText)}));
}
async function visible(page,text){await page.getByText(text,{exact:false}).first().waitFor({state:'visible'});assertions++;}
async function goto(page,url){const r=await page.goto(base+url);check(r.status()<400,'Page must load');return r;}
async function clickNav(page,locator){await Promise.all([page.waitForURL(url=>!url.href.startsWith('about:')),locator.click()]);await page.waitForLoadState('domcontentloaded');}
async function postClick(page,locator,expected=302){
  const [response]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'),locator.click()]);
  check(response.status()===expected,'POST result '+expected+'; actual '+response.status());
  if(expected===302)await page.waitForLoadState('domcontentloaded');
  return response;
}
async function screenshot(page,name){
  check(!page.url().includes('/accounts/'),'Screenshots are product pages only');
  const file=path.join(artifactDir,name+'.png');
  await page.screenshot({path:file,fullPage:true});
  screenshots.push({path:path.relative(process.cwd(),file).replace(/\\/g,'/'),viewport:page.viewportSize()});
}
async function layout(page) {
  const metrics=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
    unlabeled:[...document.querySelectorAll('main input:not([type=hidden]):not([type=submit]),main select,main textarea')].filter(input=>!input.labels?.length&&!input.getAttribute('aria-label')).length}));
  check(metrics.scroll<=metrics.client,'No document horizontal overflow');
  check(metrics.unlabeled===0,'All actual fields have labels');
}
async function focus(page) {
  await page.keyboard.press('Tab');
  const focused=await page.evaluate(()=>({tag:document.activeElement.tagName,outline:getComputedStyle(document.activeElement).outlineStyle,width:getComputedStyle(document.activeElement).outlineWidth}));
  check(focused.tag!=='BODY','Keyboard reaches a control');
  check(focused.outline!=='none'&&focused.width!=='0px','Visible keyboard focus');
}
async function login(page,role) {
  await goto(page,'/accounts/login/');
  await page.locator('#id_login').fill(emails[role]);
  await page.locator('#id_password').fill(passwords[role]);
  await postClick(page,page.locator('main form button[type=submit]'));
  await page.waitForURL(base+'/');
}
async function details(page,title,price='245000') {
  await page.getByLabel('İlan başlığı').fill(title);
  await page.getByLabel('Açıklama').fill('Düzenli bakımlı, temiz kullanılmış yerel test ilanı. Bilgiler ve fotoğraflar bu tarayıcı yolculuğunda eklendi.');
  await page.getByLabel('Fiyat').fill(price);
  await page.getByLabel('Para birimi').fill('TRY');
  await page.getByLabel('Konum').fill('İstanbul · Kadıköy');
  await page.getByLabel('Model yılı').fill('2022');
  await page.getByLabel('Kilometre').fill('38000');
}
function crc32(buffer){let crc=0xffffffff;for(const byte of buffer){crc^=byte;for(let i=0;i<8;i++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}return(crc^0xffffffff)>>>0;}
function chunk(type,data){const typeBuffer=Buffer.from(type);const length=Buffer.alloc(4);length.writeUInt32BE(data.length);const crc=Buffer.alloc(4);crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer,data])));return Buffer.concat([length,typeBuffer,data,crc]);}
function png(variant=0){
  const width=720,height=440;
  const raw=Buffer.alloc((width*3+1)*height);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    let color=y>330?[195,205,195]:[229,238,226];
    if(y>295&&y<330)color=[165,183,161];
    // Synthetic test photograph: a simple car graphic, generated only in memory.
    if((x>120&&x<600&&y>220&&y<310)||(x>240&&x<480&&y>145&&y<250))color=variant?[179,104,65]:[49,111,99];
    if(x>260&&x<365&&y>160&&y<220)color=[178,210,213];
    if(x>385&&x<465&&y>160&&y<220)color=[178,210,213];
    if(((x-230)**2+(y-305)**2<35**2)||((x-520)**2+(y-305)**2<35**2))color=[34,46,48];
    if(((x-230)**2+(y-305)**2<17**2)||((x-520)**2+(y-305)**2<17**2))color=[203,211,206];
    const offset=y*(width*3+1)+1+x*3;
    raw[offset]=color[0];raw[offset+1]=color[1];raw[offset+2]=color[2];
  }
  const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(width);ihdr.writeUInt32BE(height,4);ihdr[8]=8;ihdr[9]=2;
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',ihdr),chunk('IDAT',zlib.deflateSync(raw)),chunk('IEND',Buffer.alloc(0))]);
}
async function upload(page,variant=0) {
  await page.getByLabel('Fotoğraf seçin').setInputFiles({name:'local-test.png',mimeType:'image/png',buffer:png(variant)});
  await postClick(page,page.getByRole('button',{name:'Fotoğraf yükle',exact:true}));
  await page.locator('#photo-status .status.ready').first().waitFor({timeout:90000});
  const images=page.locator('#photo-status img');check(await images.count()>0,'Processed image rendered');
  check(await images.first().evaluate(image=>image.complete&&image.naturalWidth>0),'Private inline derivative loaded');
}
async function review(page,id,action,reason,expected=302) {
  await goto(page,`/inceleme/${id}/`);
  await page.getByLabel('İnceleme kararı').selectOption(action);
  await page.getByLabel('Karar gerekçesi').fill(reason);
  if(reason==='')await page.locator('main form').evaluate(form=>form.noValidate=true);
  await postClick(page,page.getByRole('button',{name:'Kararı kaydet',exact:true}),expected);
}
async function visitorAbsent(context,url,status=404) {
  const response=await context.request.get(base+url,{maxRedirects:0});
  check(response.status()===status,'Unauthorized public/private relation denied');
}
async function auditPresentation(){
  const b=await chromium.launch({headless:true,executablePath:'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe'});
  try{
    const context=await b.newContext({locale:'tr-TR'});
    const page=await context.newPage();listen(page);
    const results=[];
    for(const width of [390,1440]){
      await page.setViewportSize({width,height:width===390?844:1000});
      for(const route of ['/','/accounts/login/']){
        await goto(page,route);await layout(page);
        const contrasts=await page.evaluate(()=>{
          const rgb=color=>color.match(/[0-9.]+/g).slice(0,3).map(Number);
          const luminance=color=>rgb(color).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
          const ratio=(a,b)=>{const la=luminance(a),lb=luminance(b);return(Math.max(la,lb)+.05)/(Math.min(la,lb)+.05)};
          const backdrop=element=>{for(let e=element;e;e=e.parentElement){const color=getComputedStyle(e).backgroundColor;if(color!=='rgba(0, 0, 0, 0)'&&color!=='transparent')return color;}return'rgb(255, 255, 255)'};
          const text=[...document.querySelectorAll('h1,h2,h3,.eyebrow,.muted,.hero p,.hero-note>span:last-child,.site-header nav>a,.button,.account-shell p,.account-shell label,.site-footer span,.site-footer p')].filter(e=>e.getClientRects().length&&e.innerText.trim()).map(e=>{
            const style=getComputedStyle(e),size=parseFloat(style.fontSize),weight=parseInt(style.fontWeight);
            return {selector:e.tagName+'.'+e.className,ratio:Number(ratio(style.color,backdrop(e)).toFixed(2)),minimum:size>=24||(size>=18.66&&weight>=700)?3:4.5};
          });
          const borders=[...document.querySelectorAll('main input:not([type=hidden]),main select,main textarea')].filter(e=>e.getClientRects().length).map(e=>({id:e.id,ratio:Number(ratio(getComputedStyle(e).borderTopColor,backdrop(e)).toFixed(2))}));
          return{text,borders};
        });
        check(contrasts.text.every(item=>item.ratio>=item.minimum),'Rendered text contrast passes at '+width);
        check(contrasts.borders.every(item=>item.ratio>=3),'Visible input boundary contrast passes at '+width+'; measured '+JSON.stringify(contrasts.borders));
        results.push({width,route,minTextContrast:Math.min(...contrasts.text.map(item=>item.ratio)),minInputBorderContrast:contrasts.borders.length?Math.min(...contrasts.borders.map(item=>item.ratio)):null});
      }
    }
    console.log(JSON.stringify({presentationAudit:'PASS',assertions,results}));
  }catch(error){console.log(JSON.stringify({presentationAudit:'FAIL',error:safe(error.message)}));process.exitCode=1;}
  finally{await b.close();}
}
if(process.argv.includes('--audit')){auditPresentation();}else {
(async()=>{
  fs.mkdirSync(artifactDir,{recursive:true});
  browser=await chromium.launch({headless:true,executablePath:'C:\\Users\\ismai\\AppData\\Local\\ms-playwright\\chromium_headless_shell-1243\\chrome-headless-shell-win64\\chrome-headless-shell.exe'});
  console.log(JSON.stringify({driver:require('../.browser-test-tools/node_modules/playwright-core/package.json').version,browser:browser.version(),mobile:{width:390,height:844},desktop:{width:1440,height:1000}}));
  const sellerContext=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,locale:'tr-TR'});
  const reviewerContext=await browser.newContext({viewport:{width:1440,height:1000},locale:'tr-TR'});
  const visitorContext=await browser.newContext({viewport:{width:1440,height:1000},locale:'tr-TR'});
  const seller=await sellerContext.newPage(),reviewer=await reviewerContext.newPage(),visitor=await visitorContext.newPage();
  for(const page of[seller,reviewer,visitor])listen(page);
  checkpoint('public-root-static-and-signup');
  await goto(visitor,'/');await visible(visitor,'Yayımdaki ilanlar');await layout(visitor);
  check((await visitorContext.request.get(base+'/static/app.css')).status()===200,'CSS served');
  check((await visitorContext.request.get(base+'/static/vendor/htmx-2.0.11.min.js')).status()===200,'HTMX served');
  await goto(seller,'/accounts/signup/');await layout(seller);await focus(seller);
  await seller.locator('#id_email').fill(emails.seller);
  await seller.locator('#id_password1').fill(passwords.seller);
  await seller.locator('#id_password2').fill(passwords.seller);
  await postClick(seller,seller.locator('main form button[type=submit]'));
  await seller.waitForURL(/\/accounts\/confirm-email\/$/);
  await goto(seller,'/ilan-ver/');
  check(seller.url().includes('/accounts/login/'),'Mandatory verification blocks signed-in draft creation');
  const confirmation=fixture('confirm').url;
  await goto(seller,confirmation);
  await postClick(seller,seller.locator('main form button[type=submit]'));
  await login(seller,'seller');
  fixture('reviewer','reviewer');fixture('reviewer','staff');
  await login(reviewer,'reviewer');
  const staffContext=await browser.newContext({viewport:{width:390,height:844},locale:'tr-TR'});
  const staff=await staffContext.newPage();listen(staff);await login(staff,'staff');
  check((await staff.goto(base+'/inceleme/')).status()===403,'Staff alone has no reviewer authority');
  await staffContext.close();
  checkpoint('category-photo-and-details');
  await goto(seller,'/ilan-ver/');await layout(seller);
  await seller.getByLabel('İlan kategorisi').selectOption({label:'Vasıta › Otomobil'});
  await postClick(seller,seller.getByRole('button',{name:'Taslak oluştur ve devam et'}));
  const first=fixture('inspect').listings.at(-1);
  const listingId=first.id;let revisionId=first.revisions.at(-1).id;
  await upload(seller);
  await seller.reload();await visible(seller,'Hazır');await layout(seller);
  const oldAsset=fixture('inspect').listings.at(-1).revisions.at(-1).images[0].asset_id;
  await seller.getByRole('link',{name:'Detaylara devam et'}).click();
  await seller.getByLabel('Model yılı').fill('1800');
  await postClick(seller,seller.getByRole('button',{name:'Kaydet ve önizle'}),200);
  check(await seller.locator('.errorlist').count()>0,'Invalid details show visible errors');
  await details(seller,'Kadıköy’de temiz, bakımlı otomobil');
  await screenshot(seller,'mobile-details');
  await layout(seller);await focus(seller);
  await postClick(seller,seller.getByRole('button',{name:'Kaydet ve önizle'}));
  await visible(seller,'Özel önizleme');await layout(seller);
  await screenshot(seller,'mobile-preview');
  await postClick(seller,seller.getByRole('button',{name:'İncelemeye gönder'}));
  await visible(seller,'İlanın incelemede');
  await visitorAbsent(visitorContext,`/ilanlar/${listingId}/`);
  await visitorAbsent(visitorContext,`/ilanlar/${listingId}/fotograflar/${revisionId}/${oldAsset}/`);
  checkpoint('reject-revise-and-approve');
  await goto(reviewer,'/inceleme/');
  await visible(reviewer,'Kadıköy’de temiz, bakımlı otomobil');
  await review(reviewer,revisionId,'reject','',200);
  check(await reviewer.locator('.errorlist').count()>0,'Missing reason rejected');
  await reviewer.getByLabel('Karar gerekçesi').fill('Başlığı ve açıklamayı daha açık yazın.');
  await postClick(reviewer,reviewer.getByRole('button',{name:'Kararı kaydet'}));
  await goto(seller,'/ilanlarim/');await visible(seller,'Başlığı ve açıklamayı daha açık yazın.');
  await postClick(seller,seller.getByRole('button',{name:'Yeni taslak oluştur'}).first());
  const revised=fixture('inspect').listings.find(item=>item.id===listingId).revisions.at(-1);
  revisionId=revised.id;check(revised.images[0].asset_id===oldAsset,'Ready photo copied from rejected version');
  await seller.getByRole('link',{name:'Detaylara devam et'}).click();
  await details(seller,'Kadıköy’de 2022 model bakımlı otomobil');
  await postClick(seller,seller.getByRole('button',{name:'Kaydet ve önizle'}));
  await postClick(seller,seller.getByRole('button',{name:'İncelemeye gönder'}));
  await goto(reviewer,`/inceleme/${revisionId}/`);await layout(reviewer);
  await screenshot(reviewer,'desktop-review');
  await reviewer.getByLabel('Karar gerekçesi').fill('İlan bilgileri açık ve uygun.');
  await postClick(reviewer,reviewer.getByRole('button',{name:'Kararı kaydet'}));
  const publicRevision=revisionId;
  await goto(visitor,`/ilanlar/${listingId}/`);
  await visible(visitor,'Kadıköy’de 2022 model bakımlı otomobil');
  check(!(await visitor.locator('main').innerText()).includes(emails.seller),'Private email absent publicly');
  check(await visitor.locator('.public-gallery img').first().evaluate(image=>image.complete&&image.naturalWidth>0),'Approved image visible');
  await layout(visitor);await screenshot(visitor,'desktop-public-detail');
  await goto(visitor,'/');await screenshot(visitor,'desktop-listings');
  await visitor.setViewportSize({width:390,height:844});await goto(visitor,`/ilanlar/${listingId}/`);
  await layout(visitor);await screenshot(visitor,'mobile-public-detail');
  await visitorAbsent(visitorContext,`/taslaklar/${publicRevision}/onizleme/`,302);
  await visitorAbsent(visitorContext,`/private-media/${oldAsset}/original/`,403);
  checkpoint('pending-edit-preserves-old-public-content-photo-and-stale-edit');
  await goto(seller,'/ilanlarim/');
  await postClick(seller,seller.getByRole('button',{name:'Yeni taslak oluştur'}).first());
  revisionId=fixture('inspect').listings.find(item=>item.id===listingId).revisions.at(-1).id;
  await upload(seller,1);
  await postClick(seller,seller.getByRole('button',{name:'Fotoğraf 1 kaldır',exact:true}));
  const draft=fixture('inspect').listings.find(item=>item.id===listingId).revisions.at(-1);
  check(draft.images.length===1&&draft.images[0].asset_id!==oldAsset,'Only copied draft relation removed');
  const newAsset=draft.images[0].asset_id;
  await seller.getByRole('link',{name:'Detaylara devam et'}).click();
  const stale=await sellerContext.newPage();listen(stale);await goto(stale,`/taslaklar/${revisionId}/duzenle/?step=details`);
  const staleVersion=await stale.locator('input[name=edit_version]').inputValue();
  await details(seller,'Yeni düzenleme · daha uygun fiyat','235000');
  await postClick(seller,seller.getByRole('button',{name:'Kaydet ve önizle'}));
  await details(stale,'Eski ekrandan üzerine yazma','230000');
  await postClick(stale,stale.getByRole('button',{name:'Kaydet ve önizle'}),409);
  await visible(stale,'Taslak değişti');check(await stale.locator('input[name=edit_version]').inputValue()===staleVersion,'Stale version preserved');
  await layout(stale);await stale.close();
  await postClick(seller,seller.getByRole('button',{name:'İncelemeye gönder'}));
  await visible(seller,'İlan yayında');await visible(seller,'Düzenlemen incelemede');await layout(seller);
  await screenshot(seller,'mobile-dashboard-pending');
  await goto(visitor,`/ilanlar/${listingId}/`);await visible(visitor,'Kadıköy’de 2022 model bakımlı otomobil');
  check(!(await visitor.locator('main').innerText()).includes('Yeni düzenleme'),'Pending title hidden');
  check((await visitorContext.request.get(base+`/ilanlar/${listingId}/fotograflar/${publicRevision}/${oldAsset}/`)).status()===200,'Approved old photo survives unlink');
  await visitorAbsent(visitorContext,`/ilanlar/${listingId}/fotograflar/${revisionId}/${newAsset}/`);
  checkpoint('stale-review-replay-and-new-publication');
  await goto(reviewer,`/inceleme/${revisionId}/`);
  await reviewer.getByLabel('Karar gerekçesi').fill('Eski inceleme ekranı.');
  await postClick(seller,seller.getByRole('button',{name:'İncelemeyi geri çek'}).first());
  await postClick(reviewer,reviewer.getByRole('button',{name:'Kararı kaydet'}),409);
  await visible(reviewer,'güncelliğini yitirdi');
  await postClick(seller,seller.getByRole('button',{name:'Yeni taslak oluştur'}).first());
  revisionId=fixture('inspect').listings.find(item=>item.id===listingId).revisions.at(-1).id;
  await seller.getByRole('link',{name:'Özel önizlemeyi aç'}).click();
  await postClick(seller,seller.getByRole('button',{name:'İncelemeye gönder'}));
  await review(reviewer,revisionId,'approve','Güncel bilgiler uygun.');
  await review(reviewer,revisionId,'approve','Aynı güncel sürüm tekrar onay.',302);
  await review(reviewer,publicRevision,'approve','Eski sürümü geri getirme denemesi.',409);
  check(fixture('inspect').listings.find(item=>item.id===listingId).public_revision_id===revisionId,'Old replay did not restore pointer');
  await visitorAbsent(visitorContext,`/ilanlar/${listingId}/fotograflar/${publicRevision}/${oldAsset}/`);
  await goto(visitor,`/ilanlar/${listingId}/`);await visible(visitor,'Yeni düzenleme · daha uygun fiyat');
  checkpoint('no-javascript-form-navigation-and-auth-pages');
  const noJSContext=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844},locale:'tr-TR'});
  const noJS=await noJSContext.newPage();listen(noJS);await login(noJS,'seller');
  await goto(noJS,'/ilan-ver/');await noJS.getByLabel('İlan kategorisi').selectOption({label:'Vasıta › Otomobil'});
  await postClick(noJS,noJS.getByRole('button',{name:'Taslak oluştur ve devam et'}));
  await noJS.getByRole('link',{name:'Detaylara devam et'}).click();
  await noJS.getByLabel('İlan başlığı').fill('JavaScript olmadan kayıtlı taslak');
  await postClick(noJS,noJS.getByRole('button',{name:'Kaydet ve önizle'}));
  await visible(noJS,'JavaScript olmadan kayıtlı taslak');await layout(noJS);
  await noJSContext.close();
  const auth=await visitorContext.newPage();listen(auth);
  for(const url of ['/accounts/login/','/accounts/signup/','/accounts/password/reset/']){await goto(auth,url);await layout(auth);await visible(auth,'Classifieds');}
  check(pageErrors.length===0,'No browser page errors');
  // Document navigation may cancel an in-flight status poll; retain only other failed requests.
  const significantFailures=networkFailures.filter(item=>!item.error.includes('ERR_ABORTED'));
  check(significantFailures.length===0,'No unexpected failed network requests');
  console.log(JSON.stringify({result:'PASS',assertions,pageErrors:pageErrors.length,unexpectedRequestFailures:significantFailures.length,screenshots}));
})().catch(error=>{
  console.log(JSON.stringify({result:'FAIL',stage,error:safe(error.message),pageErrors,networkFailures}));
  process.exitCode=1;
}).finally(async()=>{if(browser)await browser.close();});

}
