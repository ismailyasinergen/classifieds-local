'use strict';
const {execFileSync}=require('node:child_process');
const {validateBundle,readComponent,checkRepository,assertSnapshotContext}=require('../recovery/repository.cjs');
const {verifyTargetIsolation}=require('./isolation.cjs');
const {validateOwned}=require('./runtime.cjs');
const {runBinaryPipeline}=require('../recovery/safe-process.cjs');
const {acquireLock,releaseLocks}=require('./lock.cjs');
const path=require('node:path');
const {requireSafe}=require('../recovery/guards.cjs');
function readPrivate(spec,maxBuffer=32*1024*1024) {
  try{return execFileSync(spec.command,spec.args,{env:spec.env,windowsHide:true,stdio:['ignore','pipe','pipe'],maxBuffer,timeout:300000});}
  catch{throw new Error('restore_component_failed');}
}
function targetCommand(target,service,args) {
  validateOwned(target);requireSafe(['synthetic-target','original-target'].includes(target.role),'restore_role_refused');
  return {command:'docker',args:['exec','-i',target.services[service],...args]};
}
async function restoreBundleUnlocked(repo,bundleId,target) {
  validateOwned(target);requireSafe(['synthetic-target','original-target'].includes(target.role),'restore_role_refused');
  const bundle=JSON.parse(readPrivate(readComponent(repo,bundleId,'bundle.json')));
  validateBundle(bundle);requireSafe(bundle.keyId===repo.repoId&&bundle.sourceKind===(target.role==='synthetic-target'?'synthetic':'original'),'restore_bundle_refused');
  requireSafe(bundle.image==='sha256:23e5fe716cd2f2e73c189f035eb3df345ca155c1cd31c78bfdbd0c06839a1839'&&bundle.manifest==='f69c9d336c5baec787e2b0113d3ec77fd536c97e1ed0e3769ebb46bfda4bac58','restore_identity_refused');
  assertSnapshotContext(repo,bundleId,'bundle.json',bundle.run,bundle.sourceKind);
  for(const c of bundle.components)assertSnapshotContext(repo,c.snapshotId,c.kind,bundle.run,bundle.sourceKind);
  const isolation=verifyTargetIsolation(target);
  try {
  checkRepository(repo);
  const empty=readPrivate(targetCommand(target,'db',['psql','-U','recovery','-d','recovery','-Atc',"SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"]),1024).toString().trim();
  requireSafe(empty==='0','restore_nonempty_refused');
  readPrivate(targetCommand(target,'web',['python','/ops/restore_runtime.py','missing-key-check']),1024);
  // Verify every encrypted component before the first plaintext target write.
  for(const c of bundle.components) {
    const checked=await runBinaryPipeline(readComponent(repo,c.snapshotId,c.kind),{command:process.execPath,args:['-e','process.stdin.resume();']},{maxBytes:c.bytes,timeoutMs:300000});
    requireSafe(checked.sha256===c.sha256&&checked.bytes===c.bytes,'restore_integrity_refused');
  }
  for(const kind of ['source.tar','application-image.tar','catalog.json','keys.json','media.tar','database.dump']) {
    const c=bundle.components.find(c=>c.kind===kind);
    const mode={'source.tar':'source','application-image.tar':'image','catalog.json':'catalog','keys.json':'keys','media.tar':'media'}[kind];
    const consumer=kind==='database.dump'?targetCommand(target,'db',['sh','-c','umask 077; set -C; cat > /tmp/recovery.dump']):targetCommand(target,'web',['python','/ops/restore_runtime.py',mode]);
    let checked;
    try {checked=await runBinaryPipeline(readComponent(repo,c.snapshotId,kind),consumer,{maxBytes:c.bytes,timeoutMs:300000});}
    catch {throw new Error('restore_'+(mode||'database')+'_failed');}
    requireSafe(checked.sha256===c.sha256&&checked.bytes===c.bytes,'restore_integrity_refused');
  }
  const dump=bundle.components.find(c=>c.kind==='database.dump');
  const hash=readPrivate(targetCommand(target,'db',['sha256sum','/tmp/recovery.dump']),1024).toString().split(' ')[0];
  requireSafe(hash===dump.sha256,'restore_dump_refused');
  readPrivate(targetCommand(target,'db',['pg_restore','--single-transaction','--exit-on-error','--no-owner','--no-privileges','-U','recovery','-d','recovery','/tmp/recovery.dump']));
  return {bundleId,run:target.run,restored:true,components:6,...require('./lifecycle.cjs').lifecycleFields(isolation)};
  } catch(e){throw Object.assign(require('./lifecycle.cjs').failure(e,'restore_failed'),require('./lifecycle.cjs').lifecycleFields(isolation));}
}
async function restoreBundle(repo,bundleId,target) {
  validateOwned(target);
  const release=acquireLock(path.join(repo.path,'phase7.bundle.lock'));
  let releaseTarget,primary;
  try {
    releaseTarget=acquireLock(path.resolve(__dirname,'../../docs/phase15',`operation-${target.run}.lock`));
    return await restoreBundleUnlocked(repo,bundleId,structuredClone(target));
  } catch(error){primary=error;throw error;}finally {releaseLocks([releaseTarget,release],primary);}
}
async function bootstrapImageFromBackup(repo,bundleId) {
  const release=acquireLock(path.join(repo.path,'phase7.bundle.lock'));
  let primary;
  try {
    const bundle=JSON.parse(readPrivate(readComponent(repo,bundleId,'bundle.json')));
    validateBundle(bundle);requireSafe(bundle.keyId===repo.repoId&&bundle.image==='sha256:23e5fe716cd2f2e73c189f035eb3df345ca155c1cd31c78bfdbd0c06839a1839');
    assertSnapshotContext(repo,bundleId,'bundle.json',bundle.run,bundle.sourceKind);
    const c=bundle.components.find(c=>c.kind==='application-image.tar');
    assertSnapshotContext(repo,c.snapshotId,c.kind,bundle.run,bundle.sourceKind);
    const checked=await runBinaryPipeline(readComponent(repo,c.snapshotId,c.kind),
      {command:'C:/Python314/python.exe',args:['-I',path.join(__dirname,'restore_runtime.py'),'image']},{maxBytes:c.bytes,timeoutMs:300000});
    requireSafe(checked.sha256===c.sha256&&checked.bytes===c.bytes,'restore_image_integrity_refused');
    const {command}=require('./inspect.cjs');
    const beforeIds=command('docker',['image','ls','--no-trunc','-q']);
    const existed=beforeIds.split(/\r?\n/).includes(bundle.image);
    const tagsBefore=existed?command('docker',['image','inspect','--format','{{json .RepoTags}}',bundle.image]):null;
    const loaded=await runBinaryPipeline(readComponent(repo,c.snapshotId,c.kind),{command:'docker',args:['image','load','--quiet']},{maxBytes:c.bytes,timeoutMs:300000});
    requireSafe(loaded.sha256===c.sha256&&loaded.bytes===c.bytes,'restore_image_load_refused');
    requireSafe(command('docker',['image','inspect','--format','{{.Id}}',bundle.image])===bundle.image,'restore_loaded_image_refused');
    if(existed)requireSafe(command('docker',['image','inspect','--format','{{json .RepoTags}}',bundle.image])===tagsBefore,'restore_image_tags_changed');
    return {image:bundle.image,archiveVerified:true,imageLoadExit:0,alreadyPresent:existed,tagsPreserved:true};
  } catch(error){primary=error;throw error;}finally {releaseLocks([release],primary);}
}
module.exports={restoreBundle,targetCommand,bootstrapImageFromBackup};
