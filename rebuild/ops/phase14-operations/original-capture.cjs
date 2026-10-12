'use strict';
const path=require('node:path');
const fs=require('node:fs');
const {verifyReview}=require('./gate.cjs');
const {verifySources,developer,image,manifest}=require('./inspect.cjs');
const {bindOriginal,createOriginalMediaReader}=require('./original-source.cjs');
const {startSnapshotCommand,privateRun,assertStable}=require('./capture.cjs');
const {requireSafe}=require('../recovery/guards.cjs');
const {acquireLock}=require('./lock.cjs');
const {backupArchive}=require('./owned-helper.cjs');
const {backupComponent,commitBundle}=require('../recovery/repository.cjs');
const {persist:writeReceipt,mustPersist,failure,mergeLifecycle}=require('./lifecycle.cjs');
async function captureOriginal(prepare,baseline) {
  verifyReview();const files=verifySources();
  let release,repo,snapshot,reader,recordFile,primary,fileCreated=false;
  const record={status:'capturing',components:[],cleanup:'not_started'};
  const persist=()=>{if(recordFile)mustPersist(fs,recordFile,record);};
  try {
    const source=bindOriginal(baseline),initial=source.inspect();
    Object.assign(record,{run:source.run,sourceKind:'original',source:initial});
    recordFile=path.join(developer,'rebuild/docs/phase15',`task6-capture-${source.run}.json`);
    mustPersist(fs,recordFile,record,true);fileCreated=true;
    reader=createOriginalMediaReader(source);
    repo=prepare();record.repoId=repo.repoId;
    release=acquireLock(path.join(repo.path,'phase7.bundle.lock'));persist();
    snapshot=await startSnapshotCommand(source.sourceCommand('snapshot'));
    const catalog=snapshot.catalog;
    catalog.deployment=require('./deployment.cjs').deployment();
    catalog.media=JSON.parse(privateRun(reader.command('inventory',catalog.assets)));delete catalog.assets;
    const before={...initial,keySha256:catalog.keySha256,snapshotAlive:true};
    record.snapshotAt=catalog.snapshotAt;persist();
    const receipts=record.components,context={run:source.run,sourceKind:'original'};
    async function component(kind,spec){const receipt=await backupComponent(repo,kind,spec,context);receipts.push(receipt);persist();}
    source.inspect();requireSafe(snapshot.isAlive(),'snapshot_lost');
    const dump={command:'docker',args:['exec','-e','PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=300000 -c lock_timeout=5000',source.dbId,
      'sh','-c','export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump --format=custom --no-owner --no-privileges --no-password --lock-wait-timeout=5s --snapshot="$1" -U "$POSTGRES_USER" -d "$POSTGRES_DB"','phase7',catalog.snapshot]};
    await component('database.dump',dump);
    source.inspect();requireSafe(snapshot.isAlive(),'snapshot_lost');
    await component('media.tar',reader.command('stream',catalog.media));
    await component('keys.json',source.sourceCommand('keys'));
    requireSafe(receipts.at(-1).sha256===before.keySha256,'capture_key_changed');
    const echo={command:process.execPath,args:['-e','process.stdin.pipe(process.stdout);'],input:Buffer.from(JSON.stringify(catalog))};
    await component('catalog.json',echo);
    assertStable(before,{...source.inspect(),keySha256:privateRun(source.sourceCommand('key-identity'),1024).toString(),snapshotAlive:snapshot.isAlive()});
    record.snapshotCleanup=await snapshot.close();snapshot=null;
    const archive=await backupArchive(repo,files,context);receipts.push(archive.component);mergeLifecycle(record,archive);persist();
    await component('application-image.tar',{command:'docker',args:['image','save',image]});
    verifySources();verifyReview();
    assertStable(before,{...source.inspect(),keySha256:privateRun(source.sourceCommand('key-identity'),1024).toString(),snapshotAlive:true});
    const bundle={format:'classifieds-recovery-v1',complete:true,...context,keyId:repo.repoId,image,manifest,snapshotAt:catalog.snapshotAt,components:receipts};
    const bundleId=await commitBundle(repo,bundle);
    Object.assign(record,{bundleId,status:'committed'});persist();
  } catch(error){primary=failure(error,'capture_failed');mergeLifecycle(record,error);record.resources=primary.resources;record.lockCleanup=primary.lockCleanup||'not_acquired';if(record.status!=='committed')record.status='failed';record.category=primary.message;}
  finally {
    try{if(snapshot){record.snapshotCleanup=await snapshot.abort();if(record.snapshotCleanup.status==='unverified'){record.helperState='retained_unverified';primary ||= Error('cleanup_blocked');}}}catch{record.snapshotCleanup={status:'unverified'};record.helperState='retained_unverified';primary ||= Error('cleanup_blocked');}
    try{if(reader){record.resources=reader.close();mergeLifecycle(record,{resources:record.resources},'mediaReader');}record.cleanup=reader?'removed':record.resources?.status||'not_created';}catch(error){record.cleanup='cleanup_blocked';record.resources=error.resources;mergeLifecycle(record,error,'mediaReader');primary ||= failure(error,'cleanup_blocked');}
    if(release)try{release();record.lockCleanup='released';}catch{record.lockCleanup='cleanup_blocked';primary ||= Error('lock_release_failed');}
    if(fileCreated){record.persistence=writeReceipt(fs,recordFile,record);if(record.persistence!=='written')primary ||= Error('receipt_write_failed');}
    else if(recordFile)record.persistence='write_failed';
  }
  if(primary)throw Object.assign(primary,{resources:record.resources,receipt:record,...require('./lifecycle.cjs').lifecycleFields(record)});
  if(record.cleanup==='cleanup_blocked')throw Object.assign(Error('cleanup_blocked'),{receipt:record});
  return record;
}
module.exports={captureOriginal};
