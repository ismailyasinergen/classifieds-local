'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {command,developer,image}=require('../inspect.cjs');
const {guardReader,readerFormat}=require('../original-source.cjs');
const {privateRun}=require('../capture.cjs');
const {runBinaryPipeline}=require('../safe-process.cjs');
async function main(){
 const run=crypto.randomBytes(8).toString('hex'),volume=`classifieds-rebuild-recovery-${run}-owner-fixture`,ops=path.resolve(__dirname,'..');
 const result={run,volume,checks:0,pass:false,containers:[]},file=path.join(developer,'rebuild/docs/phase7',`owner-os-${run}.json`);
 const save=()=>fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');
 fs.writeFileSync(file,JSON.stringify(result)+'\n',{flag:'wx'});
 const d=args=>command('docker',args);
 const base=['--label',`phase7.run=${run}`,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--user','0:0'];
 let created=false;
 try{
  d(['volume','create','--label',`phase7.run=${run}`,volume]);created=true;
  const setup=d(['create',...base,'--mount',`type=volume,source=${volume},target=/media`,image,'python','-B','-c',"import os\nos.mkdir('/media/originals',0o700);os.mkdir('/media/derivatives',0o700)\nopen('/media/originals/'+('a'*32)+'.bin','wb').write(bytes([0,255,10]))\nos.symlink('/etc/passwd','/media/originals/'+('b'*32)+'.bin')"]);
  result.containers.push(setup);save();d(['start','-a',setup]);assert.equal(d(['inspect','--format','{{.State.ExitCode}}',setup]),'0');result.fixtureSetup=true;
  const id=d(['create',...base,'--mount',`type=volume,source=${volume},target=/media,readonly`,'--mount',`type=bind,source=${ops},target=/ops,readonly`,image,'sleep','300']);
  result.containers.push(id);save();
  guardReader(JSON.parse(d(['inspect','--format',readerFormat,id])),{id,run,volume,profile:'original-owner'});result.checks++;
  d(['start',id]);
  d(['exec','--user','1000:1000',id,'python','-B','-c',"import errno\ntry:\n open('/media/originals/'+('a'*32)+'.bin','rb')\nexcept PermissionError as e:\n assert e.errno==errno.EACCES\nelse:\n raise AssertionError('nonroot_access_allowed')"]);result.checks++;
  d(['exec',id,'python','-B','/ops/reader_preflight.py','original-owner']);result.checks++;
  d(['exec',id,'python','-B','-c',"import errno,os,hashlib\np='/media/originals/'+('a'*32)+'.bin'\nbefore=open(p,'rb').read();assert before==bytes([0,255,10])\nfor action in [lambda:open('/media/new','wb'),lambda:open(p,'wb'),lambda:os.unlink(p)]:\n try: action()\n except OSError as e: assert e.errno==errno.EROFS\n else: raise AssertionError('write_allowed')\nassert open(p,'rb').read()==before and not os.path.exists('/media/new')"]);result.checks+=4;
  const spec=(mode,data)=>({command:'docker',args:['exec','-i',id,'python','-B','/ops/original_media.py',mode],input:Buffer.from(JSON.stringify(data))});
  const key='a'.repeat(32),asset={key,original:`originals/${key}.bin`,source_bytes:3,state:'pending',derivative:''};
  const entries=JSON.parse(privateRun(spec('inventory',[asset])));assert.equal(entries.length,1);result.checks++;
  result.pipeline=await runBinaryPipeline(spec('stream',entries),{command:process.execPath,args:['-e','process.stdin.resume()']},{maxBytes:65536,timeoutMs:30000});result.checks++;
  for(const bad of [{...asset,key:'c'.repeat(32),original:'originals/'+'c'.repeat(32)+'.bin'},{...asset,state:'ready',derivative:`derivatives/${key}.jpg`},{...asset,key:'b'.repeat(32),original:'originals/'+'b'.repeat(32)+'.bin'},{...asset,original:'../etc/passwd'}]){
   assert.throws(()=>privateRun(spec('inventory',[bad])),/^Error: capture_process_failed$/);result.checks++;
  }
  const changed=entries.map(e=>({...e,sha256:'0'.repeat(64)}));
  await assert.rejects(runBinaryPipeline(spec('stream',changed),{command:process.execPath,args:['-e','process.stdin.resume()']},{maxBytes:65536,timeoutMs:30000}));result.checks++;
  result.pass=true;
 }catch{result.category='owner_os_test_failed';process.exitCode=1;}
 finally{
  try{
   for(const id of result.containers.reverse()){
    assert.equal(d(['inspect','--format','{{index .Config.Labels "phase7.run"}}',id]),run);
    assert.equal(d(['inspect','--format','{{.Image}}',id]),image);
    d(['stop','--time','3',id]);d(['rm',id]);
   }
   if(created){assert.equal(d(['volume','inspect','--format','{{index .Labels "phase7.run"}}',volume]),run);d(['volume','rm',volume]);}
   result.cleanup='removed_exact_owned_fixture';
  }catch{result.cleanup='cleanup_blocked';process.exitCode=1;}
  result.exit=process.exitCode||0;save();console.log(JSON.stringify(result));
 }
}
main().catch(()=>{console.log('{"category":"owner_fixture_setup_failed"}');process.exitCode=1;});
