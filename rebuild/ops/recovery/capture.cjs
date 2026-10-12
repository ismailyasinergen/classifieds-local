'use strict';
const {spawn,execFileSync}=require('node:child_process');
const path=require('node:path');
const {requireSafe}=require('./guards.cjs');
const {verifySources,developer,manifest,image}=require('./inspect.cjs');
const {backupComponent,commitBundle}=require('./repository.cjs');
const {acquireLock}=require('./safe-process.cjs');
function assertSourceBinding(source,identity) {
  requireSafe(source.appId===identity.appId&&source.dbId===identity.dbId&&/^[a-f0-9]{16}$/.test(source.run),'source_alias_refused');
  return true;
}
function assertStable(before,after) {
  for(const key of ['appId','dbId','image','manifest','keySha256'])requireSafe(Boolean(before[key])&&before[key]===after[key],'capture_identity_changed');
  requireSafe(before.snapshotAlive===true&&after.snapshotAlive===true,'snapshot_lost');
  return true;
}
function sourceCommand(source,mode,input) {
  requireSafe(source.role==='synthetic-source'&&/^[a-f0-9]{64}$/.test(source.appId),'source_not_accepted');
  return {command:'docker',args:['exec','-i',source.appId,'python','/ops/source_export.py',mode],input};
}
function privateRun(spec,maxBuffer=32*1024*1024) {
  try{return execFileSync(spec.command,spec.args,{input:spec.input,windowsHide:true,stdio:['pipe','pipe','pipe'],timeout:300000,maxBuffer});}
  catch {throw new Error('capture_process_failed');}
}
async function startSourceSnapshot(source) {
  const s=sourceCommand(source,'snapshot');
  return startSnapshotCommand(s);
}
async function startSnapshotCommand(s) {
  const child=spawn(s.command,s.args,{windowsHide:true,stdio:['pipe','pipe','pipe']});child.stderr.resume();
  let alive=true;const done=new Promise(resolve=>{child.on('close',code=>{alive=false;resolve(code);});child.on('error',()=>{alive=false;resolve(-1);});});
  child.stdin.on('error',()=>{});
  const catalog=await new Promise((resolve,reject)=>{
    let chunks=[],bytes=0;
    const timer=setTimeout(()=>{child.stdin.destroy();child.kill();reject(new Error('snapshot_timeout'));},300000);
    const fail=()=>{clearTimeout(timer);reject(new Error('snapshot_lost'));};child.once('close',fail);child.once('error',fail);
    child.stdout.on('data',chunk=>{
      bytes+=chunk.length;if(bytes>32*1024*1024){child.stdin.destroy();child.kill();fail();return;}
      chunks.push(chunk);
      if(chunk.includes(10)) {
        clearTimeout(timer);child.off('close',fail);child.off('error',fail);
        try{resolve(JSON.parse(Buffer.concat(chunks)));}catch{child.stdin.destroy();reject(new Error('catalog_invalid'));}
      }
    });
  });
  requireSafe(/^[A-Fa-f0-9]+-[A-Fa-f0-9]+-[0-9]+$/.test(catalog.snapshot),'snapshot_invalid');
  return {catalog,isAlive:()=>alive,async close(){child.stdin.end('close\n');const code=await done;requireSafe(code===0,'snapshot_close_failed');},abort(){child.stdin.destroy();child.kill();}};
}
function echo(bytes){return {command:process.execPath,args:['-e','process.stdin.pipe(process.stdout);'],input:Buffer.from(bytes)};}
async function captureBundleUnlocked(source,repo,inspectSource,onSnapshot) {
  const files=verifySources();
  requireSafe(source.role==='synthetic-source','original_export_gate_closed');
  const initial=inspectSource(source);
  assertSourceBinding(source,initial);
  requireSafe(initial.image===image&&initial.manifest===manifest,'capture_source_refused');
  const snapshot=await startSourceSnapshot(source),context={run:source.run,sourceKind:'synthetic'},receipts=[];
  const before={...initial,keySha256:snapshot.catalog.keySha256,snapshotAlive:true};
  try {
    await onSnapshot();
    const dump={command:'docker',args:['exec','-e','PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=300000 -c lock_timeout=5000',source.dbId,
      'sh','-c','export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump --format=custom --no-owner --no-privileges --no-password --lock-wait-timeout=5s --snapshot="$1" -U "$POSTGRES_USER" -d "$POSTGRES_DB"','phase7',snapshot.catalog.snapshot]};
    receipts.push(await backupComponent(repo,'database.dump',dump,context));
    receipts.push(await backupComponent(repo,'media.tar',sourceCommand(source,'media',Buffer.from(JSON.stringify(snapshot.catalog.media))),context));
    receipts.push(await backupComponent(repo,'keys.json',sourceCommand(source,'keys'),context));
    requireSafe(receipts.at(-1).sha256===before.keySha256,'capture_key_changed');
    receipts.push(await backupComponent(repo,'catalog.json',echo(JSON.stringify(snapshot.catalog)),context));
    const after={...inspectSource(source),keySha256:privateRun(sourceCommand(source,'key-identity'),1024).toString(),snapshotAlive:snapshot.isAlive()};
    assertStable(before,after);
    await snapshot.close();
    const archive={command:'docker',args:['run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
      '--mount',`type=bind,source=${path.join(developer,'rebuild/ops/recovery')},target=/ops,readonly`,
      '--mount',`type=bind,source=${developer},target=/source,readonly`,'-i',image,'python','/ops/archive_io.py'],input:Buffer.from(JSON.stringify(files))};
    receipts.push(await backupComponent(repo,'source.tar',archive,context));
    receipts.push(await backupComponent(repo,'application-image.tar',{command:'docker',args:['image','save',image]},context));
    verifySources();
    const final={...inspectSource(source),keySha256:privateRun(sourceCommand(source,'key-identity'),1024).toString(),snapshotAlive:true};
    assertStable(before,final);
    const bundle={format:'classifieds-recovery-v1',complete:true,...context,keyId:repo.repoId,image,manifest,snapshotAt:snapshot.catalog.snapshotAt,components:receipts};
    const bundleId=await commitBundle(repo,bundle);
    return {bundleId,run:source.run,sourceKind:'synthetic',snapshotAt:bundle.snapshotAt,components:receipts};
  } catch(e){snapshot.abort();throw e;}
}
async function captureBundle(source,repo,inspectSource,onSnapshot=()=>{}) {
  const release=acquireLock(path.join(repo.path,'phase7.bundle.lock'));
  try {return await captureBundleUnlocked(structuredClone(source),repo,inspectSource,onSnapshot);}finally{release();}
}
module.exports={assertStable,assertSourceBinding,startSourceSnapshot,startSnapshotCommand,privateRun,captureBundle};
