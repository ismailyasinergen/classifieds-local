'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {docker,format}=require('../transport.cjs'),{guardReader}=require('../contract.cjs');
const run=crypto.randomBytes(12).toString('hex'),name='phase9-test-'+run,ops=path.resolve(__dirname,'..');
const image='sha256:23e5fe716cd2f2e73c189f035eb3df345ca155c1cd31c78bfdbd0c06839a1839';
const result={run,pass:false,tests:0,cleanup:[],liveDataAccess:false},owned=[];let volume;
const check=ok=>{assert(ok);result.tests++;};
const metadata=id=>JSON.parse(docker(['inspect','--format',format,id]));
function guard(item){const m=metadata(item.id);assert.equal(m.id,item.id);assert.equal(m.run,run);assert.equal(m.image,image);assert.equal(m.network,'none');assert(m.readonly&&!m.privileged);assert.deepEqual(m.capDrop,['ALL']);assert.deepEqual(m.security,['no-new-privileges']);assert.equal(m.mounts.length,2);assert(m.mounts.some(x=>x.Type==='volume'&&x.Name===volume&&x.Destination==='/media'&&x.RW===item.writable));assert(m.mounts.some(x=>x.Type==='bind'&&x.Destination==='/ops'&&!x.RW));return m;}
function create(suffix,user,writable,command){const id=docker(['create','--pull','never','--name',name+'-'+suffix,'--label','phase9.run='+run,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user',user,'--mount','type=volume,source='+volume+',target=/media'+(writable?'':',readonly'),'--mount','type=bind,source='+ops+',target=/ops,readonly',image,...command]);const item={id,writable};owned.push(item);guard(item);return item;}
async function main(){try{
 volume=docker(['volume','create','--label','phase9.run='+run,name]);
 const v=JSON.parse(docker(['volume','inspect','--format','{"name":{{json .Name}},"label":{{json (index .Labels "phase9.run")}}}',volume]));assert.equal(v.name,name);assert.equal(v.label,run);
 const setup="import os,json,hashlib\nos.mkdir('/media/originals',0o700);os.mkdir('/media/derivatives',0o700)\nfor p in ['/media/originals/'+('a'*32)+'.bin','/media/derivatives/'+('a'*32)+'.jpg']:\n with open(p,'wb') as f:f.write(b'SYNTHETIC_ONLY')\nprint(json.dumps({'created':True}))";
 const writer=create('setup','0:0',true,['python','-B','-c',setup]);check(JSON.parse(docker(['start','-a',writer.id])).created===true);
 const denial="import os,json\ntry:\n list(os.scandir('/media/originals'));ok=False\nexcept PermissionError:ok=True\nprint(json.dumps({'denied':ok}))";
 const nonroot=create('nonroot','1000:1000',false,['python','-B','-c',denial]);check(JSON.parse(docker(['start','-a',nonroot.id])).denied===true);
 const owner=create('owner','0:0',false,['python','-B','-c','import signal,sys,time; signal.signal(signal.SIGTERM,lambda *_:sys.exit(0)); time.sleep(90)']);guardReader(metadata(owner.id),{id:owner.id,run,image,volume,environment:'developer'});check(true);docker(['start',owner.id]);
 check(JSON.parse(docker(['exec',owner.id,'python','-B','/ops/preflight.py'])).metadataAccessVerified===true);
 const first=JSON.parse(docker(['exec',owner.id,'python','-B','/ops/helper.py','scan']));check(first.ok&&Object.keys(first.data.files).length===2);
 const readonly="import os,json,hashlib,errno\np='/media/originals/'+('a'*32)+'.bin'\nbefore=hashlib.sha256(open(p,'rb').read()).hexdigest();results=[]\nfor kind in ['create','modify','delete']:\n try:\n  if kind=='delete':os.unlink(p)\n  else:\n   with open('/media/originals/new' if kind=='create' else p,'wb') as f:f.write(b'bad')\n  results.append(False)\n except OSError as e:results.append(e.errno==errno.EROFS)\nprint(json.dumps({'denied':results,'unchanged':before==hashlib.sha256(open(p,'rb').read()).hexdigest()}))";
 const ro=JSON.parse(docker(['exec',owner.id,'python','-B','-c',readonly]));for(const ok of ro.denied)check(ok);check(ro.unchanged);
 const second=JSON.parse(docker(['exec',owner.id,'python','-B','/ops/helper.py','scan']));check(JSON.stringify(first)===JSON.stringify(second));
 const assets=[{id:1,key:'a'.repeat(32),original:'originals/'+('a'.repeat(32))+'.bin',derivative:'derivatives/'+('a'.repeat(32))+'.jpg',source_bytes:14,state:'ready',links:2,retained:true}];
 const compared=JSON.parse(docker(['exec','-i',owner.id,'python','-B','/ops/helper.py','compare'],{input:JSON.stringify([assets,assets,first.data,second.data])}));
 check(compared.ok&&compared.data.observationComplete&&compared.data.scannedFiles===2&&compared.data.multiRevisionAssets===1&&compared.data.missingOriginals===0&&compared.data.originalSizeMismatches===0);
 const refused=JSON.parse(docker(['exec','-i',owner.id,'python','-B','/ops/helper.py','compare'],{input:JSON.stringify([{PRIVATE_CANARY:'secret'}])}));check(refused.ok===false&&refused.error==='invalid_response'&&!JSON.stringify(refused).includes('PRIVATE_CANARY'));
 const remove=create('missing-setup','0:0',true,['python','-B','-c',"import os\nos.unlink('/media/derivatives/'+('a'*32)+'.jpg');os.rmdir('/media/derivatives')"]);
 docker(['start','-a',remove.id]);
 const preflight=()=>JSON.parse(docker(['exec',owner.id,'python','-B','/ops/preflight.py']));
 const missing=preflight();check(missing.metadataAccessVerified&&missing.directories.derivatives==='absent');
 const scan=()=>JSON.parse(docker(['exec',owner.id,'python','-B','/ops/helper.py','scan'])).data;
 const before=scan();check(before.directories.derivatives.state==='absent');
 const order=[];
 check(await require('./entry-pipeline.cjs')({verify(){guardReader(metadata(owner.id),{id:owner.id,run,image,volume,environment:'developer'});},open(){return preflight().directories;},snapshot(){order.push('DB');return assets;},scan(){order.push('FS');return scan();},compare(data){return require('../contract.cjs').output(JSON.parse(docker(['exec','-i',owner.id,'python','-B','/ops/helper.py','compare'],{input:JSON.stringify(data)})).data);},close(){return 'test_helper_retained_for_exact_cleanup';}}));
 check(JSON.stringify(order)===JSON.stringify(['DB','FS','DB','FS']));
 check(JSON.stringify(before)===JSON.stringify(scan()));
 const fixtureSetup=create('fixture-setup','0:0',true,['python','-B','-c',"import os\nos.mkdir('/media/search-fixtures',0o700);os.mkdir('/media/search-fixtures/'+('b'*16),0o700)\np='/media/search-fixtures/'+('b'*16)+'/car.jpg'\nwith open(p,'wb') as f:f.write(b'SYNTHETIC_ONLY')\nos.chmod(p,0o600)"]);
 docker(['start','-a',fixtureSetup.id]);
 const fixtureAssets=assets.map(a=>({...a,derivative:'search-fixtures/'+'b'.repeat(16)+'/car.jpg'}));
 const fixtureScan=()=>JSON.parse(docker(['exec',owner.id,'python','-B','/ops/helper.py','scan','developer'])).data;
 const fixtureBefore=fixtureScan();check(Object.keys(fixtureBefore.files).length===2);
 check(await require('./entry-pipeline.cjs')({verify(){guardReader(metadata(owner.id),{id:owner.id,run,image,volume,environment:'developer'});},open(){return preflight().directories;},snapshot(){return fixtureAssets;},scan:fixtureScan,compare(data){return require('../contract.cjs').output(JSON.parse(docker(['exec','-i',owner.id,'python','-B','/ops/helper.py','compare','developer'],{input:JSON.stringify(data)})).data,'developer');},close(){return 'test_helper_retained_for_exact_cleanup';}},true));
 check(JSON.stringify(fixtureBefore)===JSON.stringify(fixtureScan()));
 const fixtureRo=JSON.parse(docker(['exec',owner.id,'python','-B','-c',readonly.replace("/media/originals/'+('a'*32)+'.bin'","/media/search-fixtures/'+('b'*16)+'/car.jpg'").replace('/media/originals/new','/media/search-fixtures/new')]));
 check(fixtureRo.denied.every(Boolean)&&fixtureRo.unchanged);
 const originalScan=scan();check(originalScan.unsafe.includes('search-fixtures')&&!Object.keys(originalScan.files).some(p=>p.startsWith('search-fixtures/')));
 result.pass=true;
}catch{result.error='owner_os_failed';process.exitCode=1;}
finally{
 for(const item of owned.reverse())try{guard(item);require('../../graceful.cjs').gracefulStop(docker,item.id);docker(['rm',item.id]);result.cleanup.push({id:item.id,status:'removed_exact_owned'});}catch{result.cleanup.push({id:item.id,status:'cleanup_blocked'});result.pass=false;process.exitCode=1;}
 if(volume)try{const v=JSON.parse(docker(['volume','inspect','--format','{"name":{{json .Name}},"label":{{json (index .Labels "phase9.run")}}}',volume]));assert.equal(v.name,name);assert.equal(v.label,run);assert(result.cleanup.every(x=>x.status==='removed_exact_owned'));docker(['volume','rm',volume]);result.volumeRemoved=true;}catch{result.volumeRemoved=false;result.pass=false;process.exitCode=1;}
 fs.writeFileSync(path.resolve(__dirname,'../../../../docs/phase15/owner-os-'+run+'.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
}
}
main();
