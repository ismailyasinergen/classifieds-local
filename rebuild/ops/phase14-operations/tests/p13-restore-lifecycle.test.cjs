'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),id='b'.repeat(64);
test('synthetic verification output drops raw failure data and rejects successful private fields',()=>{
 const {safeOutcome}=require('./synthetic-restore.cjs');
 assert(!JSON.stringify(safeOutcome({pass:false,category:'PRIVATE_CANARY',payload:'PRIVATE_CANARY'})).includes('PRIVATE_CANARY'));
 assert.throws(()=>safeOutcome({pass:true,checks:1,payload:'PRIVATE_CANARY'}));
 assert(!JSON.stringify(safeOutcome({pass:true,checks:1,checkNames:['PRIVATE_CANARY']})).includes('PRIVATE_CANARY'));
});
for(const fault of ['prepare','first-receipt','restore-and-cleanup','last-receipt','cleanup-receipt'])test('real synthetic restore lifecycle: '+fault,async()=>{
 let cleanup=0,writes=0,created=0;
 const resources={run:'a'.repeat(16),role:'synthetic-target',known:[id],removed:[],retained:[id],unknown:false,status:'cleanup_blocked'};
 const module={exports:{}},mockFs={...fs,writeFileSync(){writes++;if(fault==='first-receipt'||fault==='last-receipt'&&writes===2)throw Error('PRIVATE_CANARY');}};
 vm.runInNewContext(fs.readFileSync(path.join(root,'tests/synthetic-restore.cjs'),'utf8'),{module,__dirname:path.join(root,'tests'),process,console:{log(){}},require:n=>{
  if(n==='node:fs')return mockFs;
  if(n==='node:child_process')return {spawnSync:()=>({status:0,stdout:'{"pass":true,"checks":1}'})};
  if(n==='../inspect.cjs')return {docs:'synthetic-docs'};
  if(n.endsWith('repository.cjs'))return {prepareRepository(){if(fault==='prepare')throw Error('input_refused');return {};}};
  if(n==='../runtime.cjs')return {createRuntime(){created++;return {run:resources.run};},stopOwnedRuntime(){cleanup++;if(fault==='restore-and-cleanup')throw Object.assign(Error('cleanup_blocked'),{resources});resources.removed=[id];resources.retained=[];resources.status='removed';if(fault==='cleanup-receipt')throw Object.assign(Error('receipt_write_failed'),{resources:{...resources,persistence:'write_failed'}});return {status:'removed',resources};}};
  if(n==='../restore.cjs')return {bootstrapImageFromBackup:async()=>({}),restoreBundle:async()=>{if(fault==='restore-and-cleanup'||fault==='last-receipt')throw Error('restore_component_failed');return {};},targetCommand:()=>({command:'test',args:[]})};
  return require(n.startsWith('.')?path.resolve(root,'tests',n):n);
 }});
 let error;try{await module.exports.main('c'.repeat(32),'d'.repeat(64));}catch(e){error=e;}
 assert(error);const out=require('../lifecycle.cjs').failureOutput(error);
 assert.equal(cleanup,created);assert(!JSON.stringify(out).includes('PRIVATE_CANARY'));
 if(fault==='prepare')assert.equal(created,0);
 if(fault==='restore-and-cleanup'){assert.equal(out.category,'restore_component_failed');assert.equal(out.resources.retained[0],id);}
 if(fault==='last-receipt'){assert.equal(out.category,'restore_component_failed');assert.equal(out.resources.removed[0],id);assert.equal(out.persistence,'write_failed');}
 if(fault==='first-receipt'||fault==='cleanup-receipt'){assert.equal(out.category,'receipt_write_failed');assert.equal(out.resources.removed[0],id);}
});
