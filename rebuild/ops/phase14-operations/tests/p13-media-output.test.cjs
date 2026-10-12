'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../media-audit');
test('media summary source contains valid UTF-8 Turkish labels',()=>{const text=fs.readFileSync(path.join(root,'run.cjs'),'utf8');assert(text.includes('Gözlenen asset'));assert(text.includes('Dosya içeriği okunmadı'));assert(!text.includes('GÃ'));});
for(const phase of ['mkdir','json','markdown'])test('real media CLI persistence failure retains primary and removed IDs: '+phase,async()=>{
 const resources={run:'a'.repeat(24),role:'media-reader',known:['b'.repeat(64)],removed:['b'.repeat(64)],retained:[],unknown:false,status:'removed'};
 const report={error:'unsafe_entry',observationComplete:false,resources,cleanup:'removed_exact_owned',durationMs:1};
 const module={exports:{}};
 vm.runInNewContext(fs.readFileSync(path.join(root,'run.cjs'),'utf8'),{module,__dirname:root,process:{argv:['node','test'],exitCode:0},console:{log(){}},require:n=>n==='node:fs'?{mkdirSync(){if(phase==='mkdir')throw Error('PRIVATE_CANARY');},writeFileSync(f){if(phase==='json'&&f.endsWith('.json')||phase==='markdown'&&f.endsWith('.md'))throw Error('PRIVATE_CANARY');}}:n==='../gate.cjs'?{verifyAcceptance:()=>''}:n==='../inspect.cjs'?{developer:'synthetic'}:n==='../../recovery/guards.cjs'?{guardDirectory(){}}:n==='./observe.cjs'?{observe:async()=>report}:n==='./transport.cjs'?{makeAdapter(){}}:require(n.startsWith('.')?path.resolve(root,n):n)});
 let error;try{await module.exports.main();}catch(e){error=e;}
 const out=require('../lifecycle.cjs').failureOutput(error);assert.equal(out.category,'unsafe_entry');assert.equal(out.persistence,'write_failed');assert.equal(out.resources.removed[0],resources.removed[0]);assert(!JSON.stringify(out).includes('PRIVATE_CANARY'));
});
