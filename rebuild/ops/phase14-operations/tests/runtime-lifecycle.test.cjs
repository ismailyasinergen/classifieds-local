'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),image=require('../inspect.cjs').image;
function fixture(options={}){
 const net='9'.repeat(64),ids={web:'1'.repeat(64),db:'2'.repeat(64),redis:'3'.repeat(64)},images={web:image,db:'sha256:'+'4'.repeat(64),redis:'sha256:'+'5'.repeat(64)};
 let attempt,project,role,run,netExists=false,composeCalls=0,receiptWrites=0;const containers=new Map(),removed=[],stopped=[],writes=[];
 const labels=service=>({'com.docker.compose.project':project,'com.docker.compose.service':service,'phase15.run':run,'phase15.role':role,'phase15.attempt':options.foreign?'foreign':attempt});
 function meta(id){const s=containers.get(id);if(!s)throw Error('not_found');return {id,image:images[s],labels:labels(s),mounts:[],ports:{},networks:{default:{NetworkID:net}},privileged:false,capAdd:[],readonly:!options.invalid,state:stopped.includes(id)?'exited':'running'};}
 function command(c,a){
  if(a[0]==='ps')return [...containers.keys()].join('\n');
  if(a[0]==='image')return images[a.at(-1)===image?'web':a.at(-1).startsWith('postgres')?'db':'redis'];
  if(a[0]==='network'&&a[1]==='ls')return netExists?net:'';
  if(a[0]==='network'&&a[1]==='inspect')return JSON.stringify({Id:net,Internal:true,Labels:{...labels(),'com.docker.compose.network':'default'},Containers:Object.fromEntries([...containers.keys()].map(id=>[id,{}]))});
  if(a[0]==='network'&&a[1]==='rm'){assert(netExists);assert.equal(containers.size,0);netExists=false;removed.push(net);return '';}
  if(a[0]==='inspect'){if(a[2].includes('IN_APP_NOTIFICATIONS_ENABLED'))return 'disabled';if(a[2]==='{{json .State.Status}}')return JSON.stringify(stopped.includes(a.at(-1))?'exited':'running');const id=a.at(-1),s=containers.get(id);if(options.metadataFailure&&!options.metadataFailed){options.metadataFailed=true;throw Error('metadata_failed');}if(a[2].includes('imageRef'))return JSON.stringify({imageRef:s==='web'?image:s==='db'?'postgres:17.11-bookworm@sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826':'redis:7.4.11-bookworm@sha256:4fa24486b8bcca8eec45ee0eb166edc674795e53a2b53d1a9ef263eecebaac85',capDrop:['ALL'],securityOpt:['no-new-privileges:true'],tmpfs:Object.fromEntries(({web:['/var/lib/classifieds/media','/run','/tmp'],db:['/var/lib/postgresql/data','/var/run/postgresql','/tmp'],redis:['/data']}[s]||[]).map(x=>[x,'']))});return JSON.stringify(meta(id));}
  if(a[0]==='kill'){assert.equal(a[2],'SIGTERM');if(options.stopFail===a.at(-1))throw Error('secret_canary');stopped.push(a.at(-1));return '';}
  if(a[0]==='rm'){containers.delete(a.at(-1));removed.push(a.at(-1));return '';}
  throw Error('unexpected_command');
 }
 const mockFs={readFileSync:()=>JSON.stringify({containerIds:options.baseline?[ids.db]:[],networkIds:[]}),writeFileSync(file){writes.push(file);if(file.includes('runtime-')&&++receiptWrites===options.failWrite)throw Error('secret_canary');if(file.includes('cleanup-')&&options.cleanupReceiptFail)throw Error('secret_canary');}};
 const cp={execFileSync(c,a,o){composeCalls++;project=a[a.indexOf('-p')+1];run=o.env.RECOVERY_RUN;role=o.env.RECOVERY_ROLE;attempt=o.env.RECOVERY_ATTEMPT;netExists=true;for(const s of options.services||['db','redis','web'])containers.set(ids[s],s);if(options.startFail)throw Error('secret_canary');}};
 const sourceRoot=process.env.P11_TEST_V1==='1'?path.resolve(root,'../../docs/phase15/before-v1/rebuild/ops/phase14-operations'):root;
 const module={exports:{}};vm.runInNewContext(fs.readFileSync(path.join(sourceRoot,'runtime.cjs'),'utf8'),{require:n=>n==='node:fs'?mockFs:n==='node:child_process'?cp:n==='./inspect.cjs'?{...require('../inspect.cjs'),command}:require(n.startsWith('.')?path.resolve(root,n):n),module,__dirname:root,process:{env:{}},Buffer});
 return {api:module.exports,stats:()=>({composeCalls,containers:containers.size,netExists,removed,stopped,writes}),ids};
}
function failed(f){let e;try{f.api.createRuntime('synthetic-target');}catch(x){e=x;}assert(e);assert(!JSON.stringify(e).includes('secret_canary'));return e;}
test('runtime preparation receipt failure creates no external resources',()=>{const f=fixture({failWrite:1});const e=failed(f);assert.equal(f.stats().composeCalls,0);assert.equal(e.message,'receipt_write_failed');});
for(const services of [[],['db'],['db','redis']])test('partial Compose cleanup '+services.join('+'),()=>{const f=fixture({services,startFail:true});const e=failed(f);assert.equal(e.message,'runtime_start_failed');assert.equal(f.stats().containers,0);assert.equal(f.stats().netExists,false);assert.equal(e.resources.retained.length,0);});
for(const failWrite of [2,3])test('runtime postcreate receipt failure '+failWrite,()=>{const f=fixture({failWrite});const e=failed(f);assert.equal(e.message,'receipt_write_failed');assert.equal(f.stats().containers,0);assert.equal(f.stats().netExists,false);});
test('runtime validation refuses unsafe container and retains it without deletion',()=>{const f=fixture({invalid:true});const e=failed(f);assert.equal(e.resources.status,'cleanup_blocked');assert.equal(f.stats().removed.length,0);});
test('metadata error is not empty-resource success',()=>{const f=fixture({metadataFailure:true});const e=failed(f);assert.equal(e.resources.unknown,true);});
test('cleanup failure preserves primary and evaluates other containers',()=>{const f=fixture({startFail:true,stopFail:'2'.repeat(64)});const e=failed(f);assert.equal(e.message,'runtime_start_failed');assert.equal(f.stats().containers,1);assert.equal(f.stats().removed.length,2);assert(e.resources.retained.includes('2'.repeat(64)));});
test('cleanup persistence failure preserves removed state and does not remove twice',()=>{const f=fixture({cleanupReceiptFail:true});const r=f.api.createRuntime('synthetic-target');let e;try{f.api.stopOwnedRuntime(r);}catch(x){e=x;}assert.equal(e.message,'receipt_write_failed');assert.equal(e.resources.retained.length,0);assert.equal(e.resources.removed.length,4);assert.equal(e.resources.persistence,'write_failed');const count=f.stats().removed.length;assert.throws(()=>f.api.stopOwnedRuntime(r));assert.equal(f.stats().removed.length,count);});
test('successful repeated cleanup uses in-memory completion and no second Docker removal',()=>{const f=fixture();const r=f.api.createRuntime('synthetic-target');f.api.stopOwnedRuntime(r);f.api.stopOwnedRuntime(r);assert.equal(f.stats().removed.length,4);});
test('foreign creation identity is retained with zero removal',()=>{const f=fixture({foreign:true,startFail:true});failed(f);assert.equal(f.stats().removed.length,0);});
test('baseline candidate is not stopped or deleted',()=>{const f=fixture({baseline:true,startFail:true,services:['db']});failed(f);assert.equal(f.stats().stopped.length,0);assert.equal(f.stats().removed.length,0);});
test('fabricated receipt confers no cleanup ownership',()=>{const f=fixture();assert.throws(()=>f.api.stopOwnedRuntime({run:'a'.repeat(16),services:{db:f.ids.db}}));assert.equal(f.stats().removed.length,0);});
