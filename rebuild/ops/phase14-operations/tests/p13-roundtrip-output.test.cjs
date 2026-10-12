'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),{failureOutput}=require('../lifecycle.cjs');
for(const fault of ['receipt_write_failed','cleanup_blocked','restore_component_failed','outer_receipt_failed'])test('actual synthetic upper CLI preserves child failure: '+fault,async()=>{
 const category=fault==='outer_receipt_failed'?'restore_component_failed':fault;
 const resources={run:'a'.repeat(16),role:'synthetic-target',known:['b'.repeat(64)],removed:[],retained:['b'.repeat(64)],unknown:false,status:'cleanup_blocked'};
 const child={pass:false,category,resources,persistence:'write_failed',lockCleanup:'cleanup_blocked',payload:'PRIVATE_CANARY'};
 let childStarted=false,cleanup=0;const module={exports:{}};
 vm.runInNewContext(fs.readFileSync(path.join(root,'tests/synthetic-roundtrip.cjs'),'utf8'),{module,__dirname:path.join(root,'tests'),process,console:{log(){}},require:n=>{
  if(n==='node:fs')return {writeFileSync(){if(childStarted&&fault==='outer_receipt_failed')throw Error('PRIVATE_CANARY');}};
  if(n==='node:child_process')return {spawnSync(){childStarted=true;return {status:1,stdout:JSON.stringify(child)};}};
  if(n==='../runtime.cjs')return {createRuntime:()=>({run:'c'.repeat(16),services:{web:'d'.repeat(64)}}),stopOwnedRuntime(){cleanup++;return {status:'removed'};},validateOwned(){},inspectSource:()=>({})};
  if(n==='../inspect.cjs')return {docs:'synthetic-docs',inspectBaseline(){}};
  if(n==='../capture.cjs')return {privateRun:()=>'{"pass":true}',captureBundle:async()=>({bundleId:'e'.repeat(64)})};
  if(n.endsWith('repository.cjs'))return {prepareRepository:()=>({})};
  return require(n.startsWith('.')?path.resolve(root,'tests',n):n);
 }});
 let error;try{await module.exports.main();}catch(e){error=e;}
 const out=failureOutput(error);assert.equal(out.category,category);assert.equal(out.resources.retained[0],resources.retained[0]);
 assert.equal(out.childFailure.persistence,'write_failed');assert.equal(out.childFailure.lockCleanup,'cleanup_blocked');
 assert.equal(out.persistence,fault==='outer_receipt_failed'?'write_failed':'written');assert.equal(cleanup,1);
 assert(!JSON.stringify(out).includes('PRIVATE_CANARY'));assert(!JSON.stringify(error.receipt).includes('PRIVATE_CANARY'));
});
