'use strict';
const {spawn,execFileSync}=require('node:child_process');
const path=require('node:path');
const {requireSafe}=require('../recovery/guards.cjs');
const {verifySources,developer,manifest,image}=require('./inspect.cjs');
const {backupComponent,commitBundle}=require('../recovery/repository.cjs');
const {acquireLock,releaseLocks}=require('./lock.cjs');
const {mergeLifecycle,failure}=require('./lifecycle.cjs');
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
  return {command:'docker',args:['exec','-i',source.appId,'python','/ops/source_export.py',mode],input,...(mode==='snapshot'?{snapshotBinding:{run:source.run,attempt:require('node:crypto').randomBytes(16).toString('hex'),containerId:source.appId}}:{})};
}
function privateRun(spec,maxBuffer=32*1024*1024) {
  try{return execFileSync(spec.command,spec.args,{input:spec.input,windowsHide:true,stdio:['pipe','pipe','pipe'],timeout:300000,maxBuffer});}
  catch {throw new Error('capture_process_failed');}
}
async function startSourceSnapshot(source) {
  const s=sourceCommand(source,'snapshot');
  return startSnapshotCommand(s);
}
const {startSnapshotCommand}=require('./snapshot.cjs');
function echo(bytes){return {command:process.execPath,args:['-e','process.stdin.pipe(process.stdout);'],input:Buffer.from(bytes)};}
async function captureBundleUnlocked(source,repo,inspectSource,onSnapshot) {
  const files=verifySources();
  requireSafe(source.role==='synthetic-source','original_export_gate_closed');
  const initial=inspectSource(source);
  assertSourceBinding(source,initial);
  requireSafe(initial.image===image&&initial.manifest===manifest,'capture_source_refused');
  const snapshot=await startSourceSnapshot(source),context={run:source.run,sourceKind:'synthetic'},receipts=[],outcome={};
  try {
    snapshot.catalog.deployment=require('./deployment.cjs').deployment();
    const before={...initial,keySha256:snapshot.catalog.keySha256,snapshotAlive:true};
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
    outcome.snapshotCleanup=await snapshot.close();
    const archive=await require('./owned-helper.cjs').backupArchive(repo,files,context);receipts.push(archive.component);mergeLifecycle(outcome,archive);
    receipts.push(await backupComponent(repo,'application-image.tar',{command:'docker',args:['image','save',image]},context));
    verifySources();
    const final={...inspectSource(source),keySha256:privateRun(sourceCommand(source,'key-identity'),1024).toString(),snapshotAlive:true};
    assertStable(before,final);
    const bundle={format:'classifieds-recovery-v1',complete:true,...context,keyId:repo.repoId,image,manifest,snapshotAt:snapshot.catalog.snapshotAt,components:receipts};
    const bundleId=await commitBundle(repo,bundle);
    return {bundleId,run:source.run,sourceKind:'synthetic',snapshotAt:bundle.snapshotAt,components:receipts,...outcome};
  } catch(e){mergeLifecycle(outcome,e);outcome.snapshotCleanup=await snapshot.abort();throw Object.assign(failure(e,'capture_failed'),outcome,{helperState:outcome.snapshotCleanup.status==='unverified'?'retained_unverified':undefined});}
}
async function captureBundle(source,repo,inspectSource,onSnapshot=()=>{}) {
  const release=acquireLock(path.join(repo.path,'phase7.bundle.lock'));
  let primary;
  try {return await captureBundleUnlocked(structuredClone(source),repo,inspectSource,onSnapshot);}catch(error){primary=error;throw error;}finally{releaseLocks([release],primary);}
}
module.exports={assertStable,assertSourceBinding,startSourceSnapshot,startSnapshotCommand,privateRun,captureBundle};
