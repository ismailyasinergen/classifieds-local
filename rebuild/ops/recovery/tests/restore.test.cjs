'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),Module=require('node:module');
const {acquireLock}=require('../safe-process.cjs');
const inspect=require('../inspect.cjs');
const baseline=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../../docs/phase7/runtime-baseline.json')));
const run='e193ba284af109ac',project=`classifieds-rebuild-recovery-${run}-synthetic-target`;
const refs={web:inspect.image,db:'postgres:17.11-bookworm@sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826',redis:'redis:7.4.11-bookworm@sha256:4fa24486b8bcca8eec45ee0eb166edc674795e53a2b53d1a9ef263eecebaac85'};
function fixture(change=()=>{}) {
  const ids={web:'a'.repeat(64),db:'b'.repeat(64),redis:'c'.repeat(64)},networkId='d'.repeat(64);
  const target={run,role:'synthetic-target',project,services:ids,networkId,images:{web:inspect.image,db:'db-image',redis:'redis-image'}};
  const metadata={},security={};let writes=0,repositoryReads=0;
  for(const [service,id] of Object.entries(ids)) {
    const dirs={web:['/run','/tmp','/var/lib/classifieds/media'],db:['/tmp','/var/lib/postgresql/data','/var/run/postgresql'],redis:['/data']}[service];
    metadata[id]={id,image:target.images[service],labels:{'com.docker.compose.project':project,'com.docker.compose.service':service},
      readonly:true,privileged:false,capAdd:[],ports:{},networks:{default:{NetworkID:networkId}},
      mounts:dirs.map(Destination=>({Type:'tmpfs',Destination}))};
    security[id]={imageRef:refs[service],capDrop:['ALL'],securityOpt:['no-new-privileges:true'],tmpfs:Object.fromEntries(dirs.map(d=>[d,'rw']))};
  }
  metadata[ids.web].mounts.push({Type:'bind',Destination:'/ops',RW:false,Source:path.resolve(__dirname,'..')});
  change({target,metadata,security});
  const load=Module._load;
  const runtimeFile=require.resolve('../runtime.cjs'),restoreFile=require.resolve('../restore.cjs');
  delete require.cache[runtimeFile];delete require.cache[restoreFile];
  Module._load=function(request,parent,...rest) {
    if(request==='./inspect.cjs'&&parent.filename===runtimeFile)return {...inspect,command(_cmd,args){
      if(args[0]==='inspect'){const id=args.at(-1);return JSON.stringify(args[2].includes('imageRef')?security[id]:metadata[id]);}
      if(args[0]==='network'&&args[1]==='inspect')return JSON.stringify({Internal:true,Labels:{'com.docker.compose.project':project},Containers:Object.fromEntries(Object.values(ids).map(id=>[id,{}]))});
      writes++;throw new Error('unexpected_write');
    }};
    if(request==='./repository.cjs'&&parent.filename===restoreFile)return {readComponent(){repositoryReads++;throw new Error('unexpected_repository_read');}};
    return load.call(this,request,parent,...rest);
  };
  let runtime,restore;
  try {runtime=require('../runtime.cjs');restore=require('../restore.cjs');}finally{Module._load=load;delete require.cache[runtimeFile];delete require.cache[restoreFile];}
  return {target,runtime,restore,counts:()=>({writes,repositoryReads})};
}
test('production validateOwned accepts complete constrained metadata',()=>assert.equal(fixture().runtime.validateOwned(fixture().target),true));
for(const [name,change] of Object.entries({
  live:x=>{x.target.services.db=baseline.containerIds[0];},
  foreign:x=>{x.target.project='classifieds-rebuild-dev';},
  dbImage:x=>{x.security[x.target.services.db].imageRef='postgres:latest';},
  redisImage:x=>{x.security[x.target.services.redis].imageRef='redis:latest';},
  capability:x=>{x.security[x.target.services.web].capDrop=[];},
  privilegePolicy:x=>{x.security[x.target.services.web].securityOpt=[];},
  missingTmpfs:x=>{delete x.security[x.target.services.db].tmpfs['/var/lib/postgresql/data'];},
  sourceBind:x=>{x.metadata[x.target.services.web].mounts[0]={Type:'bind',Destination:'/app',Source:'C:/live',RW:true};},
  publishedPort:x=>{x.metadata[x.target.services.web].ports={8000:[8088]};},
}))test('actual restore refuses '+name+' before repository or SQL writes',async()=>{
  const f=fixture(change);await assert.rejects(f.restore.restoreBundle({},'a'.repeat(64),f.target));
  assert.deepEqual(f.counts(),{writes:0,repositoryReads:0});
});
test('actual restore refuses occupied target lock before reading components',async()=>{
  const f=fixture(),dir=fs.mkdtempSync(path.join(os.tmpdir(),'phase7-lock-'));
  const unlock=acquireLock(path.resolve(__dirname,'../../../docs/phase7',`operation-${run}.lock`));
  try {await assert.rejects(f.restore.restoreBundle({path:dir},'a'.repeat(64),f.target),/^Error: run_locked$/);assert.deepEqual(f.counts(),{writes:0,repositoryReads:0});}
  finally {unlock();fs.rmdirSync(dir);}
});
const {validateSnapshotContext}=require('../repository.cjs');
test('snapshot context requires actual tags and exact single file tree',()=>{
  const metadata={tags:[run,'synthetic'],paths:['windows-stdin-provenance']},nodes=[{type:'file',path:'/database.dump'}];
  assert.equal(validateSnapshotContext(metadata,nodes,'database.dump',run,'synthetic'),true);
  for(const m of [{...metadata,tags:['other','synthetic']},{...metadata,tags:[run,'original']}])assert.throws(()=>validateSnapshotContext(m,nodes,'database.dump',run,'synthetic'));
  for(const n of [[],[...nodes,...nodes],[{type:'dir',path:'/database.dump'}],[{type:'file',path:'/keys.json'}]])assert.throws(()=>validateSnapshotContext(metadata,n,'database.dump',run,'synthetic'));
});
