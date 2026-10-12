'use strict';
const fs=require('node:fs'), path=require('node:path'), crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {requireSafe,guardDirectory}=require('./guards.cjs');
const developer=path.resolve(__dirname,'../../..');
const original='C:/Users/ismai/Desktop/classifieds_local';
const manifest='591d1f543f8f8b555a2ece43964980d155ee5b78c9d50753c1cb9908abb81680';
const image='sha256:1c1b00332fe9b21b2d11b31e1d44942674962a77e002053a37e9c76b2f1b942e';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function command(cmd,args,cwd=developer) {
  try {return execFileSync(cmd,args,{cwd,encoding:'utf8',windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:60000,maxBuffer:16*1024*1024,env:{...process.env,GIT_PAGER:'cat',PAGER:'cat',GIT_OPTIONAL_LOCKS:'0'}}).trim();}
  catch {throw new Error('metadata_command_failed');}
}
function sourcePath(root,name) {
  requireSafe((name.startsWith('rebuild/')||name==='.github/workflows/rebuild-ci.yml')&&!name.split('/').includes('..'));
  const target=path.resolve(root,name); guardDirectory(path.dirname(target),root);
  requireSafe(fs.lstatSync(target).isFile()&&!fs.lstatSync(target).isSymbolicLink());return target;
}
function verifySources() {
  const file='rebuild/docs/phase6/mfa-stabilization/candidate-manifest';
  const map=JSON.parse(fs.readFileSync(path.join(developer,file+'.json')));
  const bytes=fs.readFileSync(path.join(developer,file+'.sha256'));
  requireSafe(hash(bytes)===manifest&&map.materializedSha256===manifest,'manifest_mismatch');
  requireSafe(map.files.length===273&&new Set(map.files.map(f=>f.path)).size===273);
  requireSafe(map.files.map(f=>f.sha256+'  '+f.path+'\n').join('')===bytes.toString());
  for(const root of [developer,original]) for(const f of map.files)
    requireSafe(hash(fs.readFileSync(sourcePath(root,f.path)))===f.sha256,'source_mismatch');
  for(const f of ['cli-adoption-report.md','release-state.json'])
    requireSafe(hash(fs.readFileSync(path.join(developer,'rebuild/docs/phase6',f)))===hash(fs.readFileSync(path.join(original,'rebuild/docs/phase6',f))),'acceptance_mismatch');
  const state=JSON.parse(fs.readFileSync(path.join(developer,'rebuild/docs/phase6/release-state.json')));
  requireSafe(state.originalAdoption===true&&state.candidateImage===image&&state.sourceManifest===manifest);
  for(const [f,h] of [['specs/2026-10-10-classifieds-backup-restore-design.md','f8d29add486525d9e71bdea7a7d0be7c1a866995a8998ccb0170de40c87428ba'],['plans/2026-10-10-classifieds-backup-restore.md','50e629d2c11262a6fcc790cc2fb194b21c21b8dd9db5f536e28d14959ddd69a2']])
    requireSafe(hash(fs.readFileSync(path.join(developer,'docs/superpowers',f)))===h,'plan_identity_mismatch');
  return map.files;
}
function isPrivateEnv(file) {return /(^|\/)\.env(?:$|\.)/.test(file)&&!file.endsWith('.example');}
function fingerprint(root,file) {
  const p=path.join(root,file);
  if(isPrivateEnv(file)) {
    const s=fs.lstatSync(p);
    return {path:file,protection:'metadata-only',size:s.size,mtimeMs:s.mtimeMs,ino:s.ino};
  }
  return {path:file,sha256:hash(fs.readFileSync(p))};
}
function protectedFiles(root) {
  const names=new Set(command('git',['ls-files','-c','-o','--exclude-standard','-z'],root).split('\0').filter(Boolean));
  for(const f of ['.env','rebuild/.env','.env.production','rebuild/.env.production'])if(fs.existsSync(path.join(root,f)))names.add(f);
  return [...names].sort().filter(f=>root!==developer||(!f.startsWith('rebuild/ops/recovery/')&&!f.startsWith('rebuild/docs/phase7/'))).map(f=>{
    const p=path.resolve(root,f); requireSafe(p.startsWith(path.resolve(root)+path.sep));
    requireSafe(!fs.lstatSync(p).isSymbolicLink());return fingerprint(root,f);
  });
}
function inspectBaseline() {
  verifySources();
  const runtime=JSON.parse(command(process.execPath,['rebuild/docs/phase5/adoption-checks.cjs','runtime']));
  requireSafe(runtime.pass&&runtime.runtime.length===10);
  for(const row of runtime.runtime) {
    requireSafe(row.state==='running'&&row.sourceMatches&&row.networkIds.length===1);
    requireSafe(row.ports.every(p=>p.host==='127.0.0.1'));
    if(row.project==='classifieds-rebuild'&&['web','worker','scheduler'].includes(row.service))requireSafe(row.image===image);
  }
  const git={},protectedMaps={};
  for(const [name,root] of [['developer',developer],['original',original]]) {
    git[name]={head:command('git',['rev-parse','HEAD'],root),branch:command('git',['rev-parse','--abbrev-ref','HEAD'],root),status:command('git',['status','--short'],root)};
    requireSafe(git[name].head==='3c0b949bef3636ab15780a4d8bf8a7e07f41a0ba');
    requireSafe(git[name].branch===(name==='developer'?'HEAD':'chatgpt/manual-v360'));
    protectedMaps[name]=protectedFiles(root);
  }
  const volumeNames=[...new Set(runtime.runtime.flatMap(r=>r.volumes))].sort();
  const format='{"name":{{json .Name}},"createdAt":{{json .CreatedAt}},"driver":{{json .Driver}},"scope":{{json .Scope}}}';
  const volumes=command('docker',['volume','inspect','--format',format,...volumeNames]).split(/\r?\n/).map(JSON.parse);
  requireSafe(volumes.length===10);
  return {atUTC:new Date().toISOString(),manifest,image,sourcePaths:273,runtime:runtime.runtime,git,protected:protectedMaps,
    containerIds:runtime.runtime.map(r=>r.id),volumeNames,volumes,networkIds:[...new Set(runtime.runtime.flatMap(r=>r.networkIds))]};
}
module.exports={inspectBaseline,verifySources,developer,original,manifest,image,hash,command,fingerprint,isPrivateEnv};
