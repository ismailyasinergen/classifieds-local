'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),Module=require('node:module');
const {image,manifest}=require('../inspect.cjs');
function harness(failure) {
 let committed=0,privateReads=0,closed=0,components=0,inspections=0,repositories=0;
 const identity={appId:'a'.repeat(64),dbId:'b'.repeat(64),image,manifest};
 const catalog={snapshot:'00000001-00000001-1',keySha256:'c'.repeat(64),assets:[],snapshotAt:'2026-10-11T00:00:00Z'};
 const source={run:'a'.repeat(16),...identity,inspect(){inspections++;return {...identity,image:failure==='source'&&inspections>1?'changed':image};},sourceCommand(mode){privateReads++;return {mode};}};
 const overrides={
  './task6-gate.cjs':{verifyReview(){if(failure==='review')throw Error('original_export_gate_closed');}},
  './inspect.cjs':{image,manifest,developer:process.cwd(),verifySources:()=>[]},
  'node:fs':{writeFileSync(){}},
  './original-source.cjs':{bindOriginal(){if(failure==='identity')throw Error('original_identity_refused');return source;},createOriginalMediaReader(){if(failure==='preflight')throw Error('reader_preflight_refused');return {command(mode){if(failure==='media')throw Error('media_unavailable');return {mode};},close(){closed++;if(failure?.startsWith('cleanup'))throw Error('cleanup_blocked');}};}},
  './capture.cjs':{...require('../capture.cjs'),startSnapshotCommand:async()=>({catalog,isAlive:()=>failure!=='snapshot',close:async()=>{},abort(){}}),privateRun:s=>s.mode==='inventory'?Buffer.from('[]'):Buffer.from('c'.repeat(64))},
  './repository.cjs':{backupComponent:async(repo,kind)=>{components++;if(failure==='pipeline'||failure==='cleanup-before')throw Error('pipeline_failed');return {kind,sha256:failure==='key'&&kind==='keys.json'?'bad':'c'.repeat(64)};},commitBundle:async()=>{committed++;return 'd'.repeat(64);}},
  './safe-process.cjs':{acquireLock:()=>()=>{}}
 };
 const original=Module._load;Module._load=function(name,...rest){return overrides[name]||original.call(this,name,...rest);};
 const filename=require.resolve('../original-capture.cjs');delete require.cache[filename];let fn;
 try{fn=require(filename).captureOriginal;}finally{Module._load=original;}
 return {run:()=>fn(()=>{repositories++;return {path:'unused',repoId:'e'.repeat(32)};},{}),stats:()=>({committed,privateReads,closed,components,repositories})};
}
test('reader preflight fails before repository creation or snapshot',async()=>{const h=harness('preflight');await assert.rejects(h.run(),/^Error: reader_preflight_refused$/);assert.equal(h.stats().repositories,0);assert.equal(h.stats().privateReads,0);assert.equal(h.stats().committed,0);});
test('reviewed bounded ORIGINAL capture commits six components',async()=>{const h=harness();const r=await h.run();assert.equal(r.sourceKind,'original');assert.equal(h.stats().committed,1);assert.equal(h.stats().components,6);assert.equal(h.stats().closed,1);});
for(const failure of ['review','identity','media','snapshot','pipeline','key','source'])test('original capture refuses '+failure+' without completion',async()=>{
 const h=harness(failure);const errors={review:'original_export_gate_closed',identity:'original_identity_refused',media:'media_unavailable',snapshot:'snapshot_lost',pipeline:'pipeline_failed',key:'capture_key_changed',source:'capture_identity_changed'};
 await assert.rejects(h.run(),new RegExp('^Error: '+errors[failure]+'$'));assert.equal(h.stats().committed,0);
 if(['review','identity'].includes(failure))assert.equal(h.stats().privateReads,0);
});
test('cleanup failure preserves primary pipeline error and partial receipt',async()=>{
 const h=harness('cleanup-before');await assert.rejects(h.run(),error=>error.message==='pipeline_failed'&&error.receipt.cleanup==='cleanup_blocked'&&error.receipt.status==='failed');
});
test('cleanup failure after commit preserves exact committed bundle',async()=>{
 const h=harness('cleanup-after');await assert.rejects(h.run(),error=>error.message==='cleanup_blocked'&&error.receipt.bundleId==='d'.repeat(64)&&error.receipt.status==='committed'&&error.receipt.components.length===6);
});
