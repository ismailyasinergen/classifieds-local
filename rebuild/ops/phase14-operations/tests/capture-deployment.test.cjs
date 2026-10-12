'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),profile=require('../inspect.cjs');
for(const status of ['closed','unverified'])test('post-snapshot deployment refusal preserves '+status+' abort outcome',async()=>{
 let aborts=0,releases=0;const source={role:'synthetic-source',run:'a'.repeat(16),appId:'b'.repeat(64),dbId:'c'.repeat(64),image:profile.image,manifest:profile.manifest};
 const snapshot={catalog:{snapshot:'1-1-1'},abort:async()=>{aborts++;return {status,acknowledged:status==='closed',run:source.run,attempt:'d'.repeat(32),containerId:source.appId};}};
 const mocks={'./inspect.cjs':{...profile,verifySources:()=>[]},'./snapshot.cjs':{startSnapshotCommand:async()=>snapshot},'./deployment.cjs':{deployment(){throw Error('PRIVATE_CANARY');}},'./lock.cjs':{acquireLock:()=>()=>{releases++;},releaseLocks:releases=>releases.forEach(f=>f())}};
 const module={exports:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'capture.cjs'),'utf8'),{module,process,Buffer,structuredClone,__dirname:root,require:n=>mocks[n]||require(n.startsWith('.')?path.resolve(root,n):n)});
 let error;try{await module.exports.captureBundle(source,{path:'/synthetic-only'},()=>source);}catch(e){error=e;}
 assert.equal(aborts,1);assert.equal(releases,1);assert.equal(error.message,'capture_failed');assert.equal(error.snapshotCleanup.status,status);
 const out=require('../lifecycle.cjs').failureOutput(error);assert.equal(out.snapshotCleanup.status,status);assert(!JSON.stringify(out).includes('PRIVATE_CANARY'));
});
