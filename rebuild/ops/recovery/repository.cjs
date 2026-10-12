'use strict';
const {requireSafe}=require('./guards.cjs');
const limits={'database.dump':512*1024*1024,'media.tar':512*1024*1024,'keys.json':32*1024*1024,
  'catalog.json':32*1024*1024,'source.tar':512*1024*1024,'application-image.tar':4*1024*1024*1024};
function validateBundle(bundle) {
  const check=ok=>requireSafe(ok,'bundle_refused');
  check(bundle.complete===true&&/^[a-f0-9]{16}$/.test(bundle.run));
  check(['synthetic','original'].includes(bundle.sourceKind)&&/^[a-f0-9]{16,32}$/.test(bundle.keyId));
  check(Array.isArray(bundle.components)&&bundle.components.length===6);
  check(new Set(bundle.components.map(c=>c.kind)).size===6);
  check(new Set(bundle.components.map(c=>c.snapshotId)).size===6);
  for(const c of bundle.components) {
    check(Object.hasOwn(limits,c.kind)&&c.run===bundle.run&&c.sourceKind===bundle.sourceKind);
    check(/^[a-f0-9]{64}$/.test(c.snapshotId)&&/^[a-f0-9]{64}$/.test(c.sha256));
    check(c.producerExit===0&&c.consumerExit===0);
    check(Number.isSafeInteger(c.bytes)&&c.bytes>0&&c.bytes<=limits[c.kind]);
  }
  return true;
}
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {guardDirectory}=require('./guards.cjs');
const {runBinaryPipeline,acquireLock}=require('./safe-process.cjs');
const privateHandles=new WeakMap();
function helper(mode,repoId) {
  try {
    return execFileSync('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
      ['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','RemoteSigned','-File',path.join(__dirname,'key-store.ps1'),'-Mode',mode,'-RepoId',repoId],
      {windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:15000,maxBuffer:32768});
  } catch {throw new Error('repository_key_or_acl_refused');}
}
function specification(repo,args) {
  const secret=privateHandles.get(repo);requireSafe(secret,'repository_handle_refused');
  const env={}; for(const key of ['SystemRoot','TEMP','TMP','PATH','USERPROFILE','LOCALAPPDATA'])if(process.env[key])env[key]=process.env[key];
  env.RESTIC_PASSWORD=secret.password;
  return {command:secret.executable,args:['--no-cache','--repo',repo.path,...args],env};
}
function restic(repo,args) {
  const s=specification(repo,args);
  try{return execFileSync(s.command,s.args,{env:s.env,windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:120000,maxBuffer:8*1024*1024});}
  catch {throw new Error('repository_command_failed');}
}
function prepareRepository({root,repoId,create}) {
  requireSafe(/^[a-f0-9]{32}$/.test(repoId),'repository_id_refused');
  const expected=path.resolve('C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories');
  requireSafe(path.resolve(root)===expected,'repository_path_refused');
  const target=guardDirectory(path.join(root,repoId),expected);
  const keyFile=path.resolve(expected,'../keys',repoId+'.dpapi');
  const exists=fs.existsSync(target),keyExists=fs.existsSync(keyFile);
  requireSafe(create?(!exists&&!keyExists):(exists&&keyExists),'repository_state_refused');
  const lock=JSON.parse(fs.readFileSync(path.join(__dirname,'tool-lock.json')));
  requireSafe(crypto.createHash('sha256').update(fs.readFileSync(lock.executable)).digest('hex')===lock.executableSha256,'repository_tool_refused');
  const key=helper(create?'Create':'Read',repoId);
  requireSafe(key.length===32,'repository_key_refused');
  const repo=Object.freeze({path:target,repoId});
  privateHandles.set(repo,{password:key.toString('base64'),executable:lock.executable});key.fill(0);
  helper(create?'CreateRepository':'CheckRepository',repoId);
  if(create)restic(repo,['init','--json']);else restic(repo,['cat','config']);
  return repo;
}
async function storeStream(repo,kind,producer,{run,sourceKind}) {
  requireSafe((Object.hasOwn(limits,kind)||kind==='bundle.json')&&/^[a-f0-9]{16}$/.test(run)&&['synthetic','original'].includes(sourceKind),'component_refused');
  const release=acquireLock(path.join(repo.path,'phase7.operation.lock'));
  const tag='phase7-'+crypto.randomBytes(16).toString('hex');
  try {
    const receipt=await runBinaryPipeline(producer,specification(repo,['backup','--stdin','--stdin-filename',kind,'--tag',tag,'--tag',run,'--tag',sourceKind,'--json']),{maxBytes:limits[kind]||32*1024*1024,timeoutMs:300000});
    requireSafe(receipt.bytes>0,'component_empty');
    const rows=JSON.parse(restic(repo,['snapshots','--json','--tag',tag]));
    requireSafe(rows.length===1&&/^[a-f0-9]{64}$/.test(rows[0].id),'component_snapshot_refused');
    return {kind,run,sourceKind,snapshotId:rows[0].id,...receipt};
  } finally {release();}
}
async function backupComponent(repo,kind,producer,context) {
  requireSafe(Object.hasOwn(limits,kind),'component_refused');
  return storeStream(repo,kind,producer,context);
}
function readComponent(repo,snapshotId,kind) {
  requireSafe(/^[a-f0-9]{64}$/.test(snapshotId)&&(Object.hasOwn(limits,kind)||kind==='bundle.json'),'component_refused');
  return specification(repo,['dump',snapshotId,'/'+kind]);
}
function checkRepository(repo){restic(repo,['check','--read-data']);}
function snapshotCount(repo){return JSON.parse(restic(repo,['snapshots','--json'])).length;}
function assertSnapshotContext(repo,snapshotId,kind,run,sourceKind) {
  requireSafe(/^[a-f0-9]{64}$/.test(snapshotId),'component_refused');
  const metadata=JSON.parse(restic(repo,['cat','snapshot',snapshotId]));
  const nodes=restic(repo,['ls','--json',snapshotId]).toString().trim().split(/\r?\n/).map(line=>JSON.parse(line)).filter(row=>row.struct_type==='node');
  return validateSnapshotContext(metadata,nodes,kind,run,sourceKind);
}
function validateSnapshotContext(metadata,nodes,kind,run,sourceKind) {
  requireSafe(metadata.tags?.includes(run)&&metadata.tags?.includes(sourceKind)&&metadata.paths?.length===1,'bundle_snapshot_context_refused');
  requireSafe(nodes.length===1&&nodes[0].type==='file'&&nodes[0].path==='/'+kind,'bundle_snapshot_path_refused');
  return true;
}
async function commitBundle(repo,bundle) {
  validateBundle(bundle);
  requireSafe(bundle.keyId===repo.repoId,'bundle_key_refused');
  for(const c of bundle.components) {
    const metadata=JSON.parse(restic(repo,['cat','snapshot',c.snapshotId]));
    requireSafe(metadata.tags.includes(bundle.run)&&metadata.tags.includes(bundle.sourceKind),'bundle_snapshot_context_refused');
    const checked=await runBinaryPipeline(readComponent(repo,c.snapshotId,c.kind),{command:process.execPath,args:['-e','process.stdin.resume();']},{maxBytes:limits[c.kind],timeoutMs:300000});
    requireSafe(checked.sha256===c.sha256&&checked.bytes===c.bytes,'component_integrity_refused');
  }
  const bytes=Buffer.from(JSON.stringify(bundle));
  requireSafe(bytes.length<=32*1024*1024,'bundle_oversize');
  // Bundle contains receipts only; key/catalog payloads are never command arguments.
  const producer={command:process.execPath,args:['-e','process.stdout.write(Buffer.from(process.argv[1],"base64"));',bytes.toString('base64')]};
  const result=await storeStream(repo,'bundle.json',producer,bundle);
  checkRepository(repo);return result.snapshotId;
}
module.exports={validateBundle,prepareRepository,backupComponent,readComponent,checkRepository,commitBundle,assertSnapshotContext,validateSnapshotContext,snapshotCount};
