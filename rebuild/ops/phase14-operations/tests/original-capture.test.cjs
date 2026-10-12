'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),Module=require('node:module');
const {image,manifest}=require('../inspect.cjs');
function harness(failure) {
 let committed=0,privateReads=0,closed=0,components=0,inspections=0,repositories=0,writes=0;
 const identity={appId:'a'.repeat(64),dbId:'b'.repeat(64),image,manifest};
 const catalog={snapshot:'00000001-00000001-1',keySha256:'c'.repeat(64),assets:[],snapshotAt:'2026-10-11T00:00:00Z'};
 const source={run:'a'.repeat(16),...identity,inspect(){inspections++;return {...identity,image:failure==='source'&&inspections>1?'changed':image};},sourceCommand(mode){privateReads++;return {mode};}};
 const overrides={
  './gate.cjs':{verifyReview(){if(failure==='review')throw Error('original_export_gate_closed');}},
  './inspect.cjs':{image,manifest,developer:process.cwd(),verifySources:()=>[]},
  'node:fs':{writeFileSync(){writes++;if(failure==='pipeline-final'&&writes===4)throw Error('secret_receipt_canary');}},
  './original-source.cjs':{bindOriginal(){if(failure==='identity')throw Error('original_identity_refused');return source;},createOriginalMediaReader(){if(failure==='preflight')throw Error('reader_preflight_refused');return {command(mode){if(failure==='media')throw Error('media_unavailable');return {mode};},close(){closed++;if(failure?.startsWith('cleanup'))throw Error('cleanup_blocked');return {run:source.run,role:'media-reader',known:['9'.repeat(64)],removed:['9'.repeat(64)],retained:[],unknown:false,status:'removed',persistence:'written'};}};}},
  './capture.cjs':{...require('../capture.cjs'),startSnapshotCommand:async()=>({catalog,isAlive:()=>failure!=='snapshot',close:async()=>({status:'closed',acknowledged:true}),abort:async()=>({run:source.run,attempt:'8'.repeat(32),containerId:identity.appId,status:failure==='snapshot-abort'?'unverified':'closed',acknowledged:failure!=='snapshot-abort',localClient:'exited',localExit:0})}),privateRun:s=>s.mode==='inventory'?Buffer.from('[]'):Buffer.from('c'.repeat(64))},
  '../recovery/repository.cjs':{backupComponent:async(repo,kind)=>{components++;if(['pipeline','cleanup-before','pipeline-final','snapshot-abort'].includes(failure))throw Error('pipeline_failed');return {kind,sha256:failure==='key'&&kind==='keys.json'?'bad':'c'.repeat(64)};},commitBundle:async()=>{committed++;return 'd'.repeat(64);}},
  './owned-helper.cjs':{backupArchive:async()=>{components++;if(failure==='archive-retained')throw Object.assign(Error('pipeline_failed'),{resourceGroups:{archive:{run:source.run,role:'archive',known:['f'.repeat(64)],removed:[],retained:['f'.repeat(64)],unknown:true,status:'cleanup_blocked',persistence:'written'}}});return {component:{kind:'source.tar',sha256:'c'.repeat(64)},resourceGroups:{archive:{run:source.run,role:'archive',known:['f'.repeat(64)],removed:['f'.repeat(64)],retained:[],unknown:false,status:'removed',persistence:'written'}}};}},
  './lock.cjs':{acquireLock:()=>()=>{}}
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
test('capture final receipt failure preserves primary pipeline category',async()=>{const h=harness('pipeline-final');await assert.rejects(h.run(),e=>e.message==='pipeline_failed'&&e.receipt.persistence==='write_failed');assert.equal(h.stats().closed,1);assert.equal(h.stats().committed,0);});

test('archive retained survives successful reader cleanup in receipt and CLI',async()=>{const h=harness('archive-retained');let e;try{await h.run();}catch(x){e=x;}const out=require('../lifecycle.cjs').failureOutput(e);assert.equal(e.message,'pipeline_failed');assert.equal(out.resourceGroups.archive.retained.length,1);assert.equal(out.resourceGroups.mediaReader.status,'removed');assert.equal(e.receipt.resourceGroups.archive.status,'cleanup_blocked');assert.equal(h.stats().committed,0);});
test('snapshot unverified survives successful reader cleanup in receipt and CLI',async()=>{const h=harness('snapshot-abort');let e;try{await h.run();}catch(x){e=x;}const out=require('../lifecycle.cjs').failureOutput(e);assert.equal(out.category,'pipeline_failed');assert.equal(out.snapshotCleanup.status,'unverified');assert.equal(out.helperState,'retained_unverified');assert.equal(out.resourceGroups.mediaReader.status,'removed');assert.equal(e.receipt.snapshotCleanup.status,'unverified');});
