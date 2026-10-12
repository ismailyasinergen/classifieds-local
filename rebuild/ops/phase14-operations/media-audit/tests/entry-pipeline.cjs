'use strict';
// Test-only acceptance and transport boundary; real entry, lifecycle and output contract.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
module.exports=async function pipeline(adapter, fixture=false){
 const files=new Map(),module={exports:{}},process={argv:['node','run.cjs'],exitCode:0};
 const mocks={'node:fs':{mkdirSync(){},writeFileSync(p,b,o){assert.equal(o.flag,'wx');assert(!files.has(p));files.set(p,b);}},
 './contract.cjs':require('../contract.cjs'),'./observe.cjs':require('../observe.cjs'),
 '../gate.cjs':{verifyAcceptance:()=> 'test_only_not_real_acceptance'},'./transport.cjs':{makeAdapter:()=>adapter},
 '../inspect.cjs':{developer:'/synthetic'},'../../recovery/guards.cjs':{guardDirectory(){}}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../run.cjs'),'utf8'),{require:n=>mocks[n]||require(n.startsWith('.')?path.resolve(__dirname,'..',n):n),module,process,console:{log(){}},__dirname:path.resolve(__dirname,'..')});
 await module.exports.main();
 const json=JSON.parse([...files.values()][0]),summary=[...files.values()][1];
 assert.equal(process.exitCode,0);assert.equal(json.observationComplete,true);assert.equal(json.findingsPresent,!fixture);
 assert.equal(json.directories.derivatives,'absent');assert.equal(json.missingReadyDerivatives,fixture?0:1);
 if(fixture){assert.equal(json.fixtureLayoutEnabled,true);assert.equal(json.reasons.fixtureDerivativeReferences,1);assert(summary.includes('Neden fixtureDerivativeReferences: 1'));assert(!summary.includes('bbbbbbbbbbbbbbbb'));}
 assert(summary.includes('Dizin derivatives: absent'));assert(!JSON.stringify([...files.values()]).includes('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'));
 return true;
};
