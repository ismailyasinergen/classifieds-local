'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {hash}=require('../inspect.cjs');
const source=fs.readFileSync(path.join(__dirname,'../task6-gate.cjs'),'utf8');
const historical=['owner-os-3aab7ab4a8ee2363.json','task6-owner-execution-evidence.json','task6-synthetic-c41832728f4863fd.json','verify-bce537aa8fbeac06-1791668086486.json'];
function fixture() {
 const bytes=Buffer.from('public test operation'),digest=hash(Buffer.from(hash(bytes)+'  rebuild/ops/recovery/one.cjs\n'));
 const run={tests:1,passed:1,failed:0,skipped:0,exit:0};
 return {bytes,names:['one.cjs'],map:{files:[{path:'rebuild/ops/recovery/one.cjs',sha256:hash(bytes)}],materializedSha256:digest},
  review:{verdict:'PASS',scope:'phase7_integrated_operations',independent:true,reviewer:'/test/independent',syntheticAdapterPassed:true,
   coveredScopes:['original_adapter','owner_identity_media','health_lifecycle'],ownerIdentityProfile:'original-owner-0:0-capless',ownerOsRegressionPassed:true,operationsSha256:digest},
  evidence:{operationsSha256:digest,runs:{gate:{...run},health:{...run},node:{...run}},historicalEvidence:historical.map(name=>({name,sha256:hash(Buffer.from('{}'))}))}};
}
function verify(f) {
 const documents={'operations-manifest-final-integrated-v2.json':JSON.stringify(f.map),'final-operations-regressions-v2.json':JSON.stringify(f.evidence)};
 if(f.review){f.review.regressionsSha256=f.badEvidenceHash?'0'.repeat(64):hash(Buffer.from(documents['final-operations-regressions-v2.json']));documents['final-operations-review-v2.json']=JSON.stringify(f.review);}
 for(const name of historical)documents[name]='{}';
 const mockFs={readdirSync:()=>f.names,lstatSync:()=>({isSymbolicLink:()=>false,isFile:()=>true,isDirectory:()=>false}),readFileSync:p=>{
  const name=path.basename(p);if(name==='one.cjs')return f.bytes;
  assert(Object.hasOwn(documents,name),'unexpected or missing file '+name);return Buffer.from(documents[name]);
 }};
 const module={exports:{}};
 vm.runInNewContext(source,{require:n=>n==='node:fs'?mockFs:n==='./inspect.cjs'?{hash,developer:'/fixture'}:n==='./guards.cjs'?require('../guards.cjs'):require(n),module,__dirname:'/fixture/rebuild/ops/recovery',Buffer});
 return module.exports.verifyReview();
}
test('actual gate accepts only explicit integrated package',()=>{const f=fixture();assert.equal(verify(f),f.map.materializedSha256);});
const mutations={
 'missing review':f=>{f.review=null;},
 'health-only scope':f=>{f.review.scope='health_observation_only';},
 'old owner scope':f=>{f.review.scope='task6_original_adapter';},
 'missing integrated coverage':f=>{f.review.coveredScopes.pop();},
 'nonindependent review':f=>{f.review.independent=false;},
 'pending verdict':f=>{f.review.verdict='review_pending';},
 'old manifest':f=>{f.map.files[0].sha256='a'.repeat(64);},
 'changed single byte':f=>{f.bytes=Buffer.from('changed');},
 'unlisted operation':f=>{f.names.push('extra.cjs');},
 'unlisted unknown extension':f=>{f.names.push('extra.txt');},
 'unlisted executable bytecode':f=>{f.names.push('__pycache__/media_stream.cpython-314.pyc');},
 'wrong owner profile':f=>{f.review.ownerIdentityProfile='1000:1000';},
 'missing regression suite':f=>{delete f.evidence.runs.health;},
 'failed regression':f=>{f.evidence.runs.node.exit=1;},
 'skipped regression':f=>{f.evidence.runs.gate.skipped=1;},
 'old regression sources':f=>{f.evidence.operationsSha256='a'.repeat(64);},
 'tampered regression bytes':f=>{f.badEvidenceHash=true;},
 'missing owner OS evidence':f=>{f.evidence.historicalEvidence.shift();},
 'tampered historical evidence':f=>{f.evidence.historicalEvidence[0].sha256='a'.repeat(64);}
};
for(const [name,mutate] of Object.entries(mutations))test('actual gate refuses '+name,()=>{const f=fixture();mutate(f);assert.throws(()=>verify(f),/^Error: original_export_gate_closed$/);});
