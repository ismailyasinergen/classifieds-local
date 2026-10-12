'use strict';
const path=require('node:path');
const fs=require('node:fs');
const {verifyReview}=require('./task6-gate.cjs');
const {verifySources,developer,image,manifest}=require('./inspect.cjs');
const {bindOriginal,createOriginalMediaReader}=require('./original-source.cjs');
const {startSnapshotCommand,privateRun,assertStable}=require('./capture.cjs');
const {requireSafe}=require('./guards.cjs');
const {acquireLock}=require('./safe-process.cjs');
const {backupComponent,commitBundle}=require('./repository.cjs');
async function captureOriginal(prepare,baseline) {
  verifyReview();const files=verifySources();
  let release=()=>{},repo,snapshot,reader,recordFile,primary;
  const record={status:'capturing',components:[],cleanup:'not_started'};
  const persist=()=>{if(recordFile)fs.writeFileSync(recordFile,JSON.stringify(record,null,2)+'\n');};
  try {
    const source=bindOriginal(baseline),initial=source.inspect();
    Object.assign(record,{run:source.run,sourceKind:'original',source:initial});
    recordFile=path.join(developer,'rebuild/docs/phase7',`task6-capture-${source.run}.json`);
    fs.writeFileSync(recordFile,JSON.stringify(record,null,2)+'\n',{flag:'wx'});
    reader=createOriginalMediaReader(source);
    repo=prepare();record.repoId=repo.repoId;
    release=acquireLock(path.join(repo.path,'phase7.bundle.lock'));persist();
    snapshot=await startSnapshotCommand(source.sourceCommand('snapshot'));
    const catalog=snapshot.catalog;
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
    await snapshot.close();snapshot=null;
    const archive={command:'docker',args:['run','--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
      '--mount',`type=bind,source=${__dirname},target=/ops,readonly`,'--mount',`type=bind,source=${developer},target=/source,readonly`,
      '-i',image,'python','-B','/ops/archive_io.py'],input:Buffer.from(JSON.stringify(files))};
    await component('source.tar',archive);
    await component('application-image.tar',{command:'docker',args:['image','save',image]});
    verifySources();verifyReview();
    assertStable(before,{...source.inspect(),keySha256:privateRun(source.sourceCommand('key-identity'),1024).toString(),snapshotAlive:true});
    const bundle={format:'classifieds-recovery-v1',complete:true,...context,keyId:repo.repoId,image,manifest,snapshotAt:catalog.snapshotAt,components:receipts};
    const bundleId=await commitBundle(repo,bundle);
    Object.assign(record,{bundleId,status:'committed'});persist();
  } catch(error){primary=error;if(error.mediaReader)record.retainedMediaReader=error.mediaReader;record.status='failed';record.category=/^[a-z_]+$/.test(error.message)?error.message:'capture_failed';}
  finally {
    snapshot?.abort();
    try{reader?.close();record.cleanup=reader?'removed':record.retainedMediaReader?record.retainedMediaReader.cleanup:'not_created';}catch{record.cleanup='cleanup_blocked';}
    try{persist();}finally{release();}
  }
  if(primary)throw Object.assign(primary,{receipt:record});
  if(record.cleanup==='cleanup_blocked')throw Object.assign(Error('cleanup_blocked'),{receipt:record});
  return record;
}
module.exports={captureOriginal};
