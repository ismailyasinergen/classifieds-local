'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {command,developer,image}=require('../inspect.cjs');
const {privateRun}=require('../capture.cjs');
const {runBinaryPipeline}=require('../safe-process.cjs');
async function main() {
 const run=crypto.randomBytes(8).toString('hex'),root=path.join(developer,'rebuild/docs/phase7',`task6-public-media-${run}`);
 fs.mkdirSync(root);fs.mkdirSync(path.join(root,'originals'));
 const key='a'.repeat(32),name=`originals/${key}.bin`;
 fs.writeFileSync(path.join(root,name),Buffer.from([0,255,10]),{flag:'wx'});
 const id=command('docker',['create','--name',`classifieds-rebuild-recovery-${run}-media-probe`,'--label',`phase7.run=${run}`,
  '--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--mount',`type=bind,source=${root},target=/media,readonly`,
  '--mount',`type=bind,source=${path.resolve(__dirname,'..')},target=/ops,readonly`,image,'sleep','120']);
 const result={run,id,pass:false,checks:0};
 try {
  command('docker',['start',id]);
  const mounts=JSON.parse(command('docker',['inspect','--format','{{json .Mounts}}',id]));assert(mounts.length===2&&mounts.every(m=>!m.RW));result.checks++;
  const spec=(mode,data)=>({command:'docker',args:['exec','-i',id,'python','-B','/ops/original_media.py',mode],input:Buffer.from(JSON.stringify(data))});
  const assets=[{key,original:name,source_bytes:3,state:'pending',derivative:''}];
  const entries=JSON.parse(privateRun(spec('inventory',assets)));assert.equal(entries.length,1);assert.equal(entries[0].bytes,3);result.checks++;
  result.stream=await runBinaryPipeline(spec('stream',entries),{command:process.execPath,args:['-e','process.stdin.resume();']},{maxBytes:65536,timeoutMs:30000});result.checks++;
  assert.throws(()=>privateRun(spec('inventory',[{...assets[0],key:'b'.repeat(32),original:'originals/'+'b'.repeat(32)+'.bin'}])),/^Error: capture_process_failed$/);result.checks++;
  assert.throws(()=>privateRun(spec('inventory',[{...assets[0],state:'ready',derivative:'derivatives/'+key+'.jpg'}])),/^Error: capture_process_failed$/);result.checks++;
  privateRun({command:'docker',args:['exec',id,'python','-B','-c',"import errno\ntry:\n open('/media/probe','wb')\nexcept OSError as e:\n assert e.errno==errno.EROFS\nelse:\n raise ValueError('write_allowed')"]});result.checks++;
  result.pass=true;
 } catch {result.category='media_probe_failed';process.exitCode=1;}
 finally {
  assert.equal(command('docker',['inspect','--format','{{index .Config.Labels "phase7.run"}}',id]),run);
  command('docker',['stop','--time','5',id]);command('docker',['rm',id]);result.cleanup='removed_exact_container';
 }
 result.exit=process.exitCode||0;fs.writeFileSync(path.join(developer,'rebuild/docs/phase7',`task6-media-${run}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
}
main().catch(()=>{console.log('{"pass":false,"category":"media_probe_setup_or_cleanup_failed"}');process.exitCode=1;});
