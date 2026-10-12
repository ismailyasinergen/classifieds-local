'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),inspect=require('../inspect.cjs');
const copy=x=>JSON.parse(JSON.stringify(x));
function baseline(){return {runtime:Array.from({length:10},(_,i)=>({environment:i<5?'original':'developer',service:['web','worker','scheduler','db','redis'][i%5],id:String(i),image:'image',configHash:'config',flag:true,mounts:[{Type:'bind',Source:'C:/allowed/backend',Destination:'/app',RW:false,Propagation:'rprivate'},{Type:'volume',Name:'media',Source:'/vol/media',Destination:'/media',RW:false}],networks:{app:{NetworkID:'network'}},portBindings:{},state:'running'})),git:{head:'fixed'},volumes:[{name:'fixed'}],networkIds:['fixed'],protected:{original:[],developer:[]}};}
async function exercise(change=()=>{},options={}){
 const before=baseline(),current=copy(before);change(current);const frozen=JSON.stringify({before,current});
 const calls={capture:0,repository:0,health:0,released:0,writes:[]};
 const mocks={
  './gate.cjs':{verifyReview:()=>''},'./unresolved.cjs':{assertNoUnresolved(){}},
  './inspect.cjs':{...inspect,developer:'/synthetic',inspectBaseline:()=>current},
  'node:fs':{readFileSync:()=>Buffer.from(JSON.stringify(before)),writeFileSync:(file,bytes)=>{if(options.writeError)throw Error('SECRET_CANARY');calls.writes.push(JSON.parse(bytes));}},
  './lock.cjs':{acquireLock:()=>()=>{calls.released++;if(options.lockError)throw Error('SECRET_CANARY');}},
  '../recovery/repository.cjs':{prepareRepository:()=>{calls.repository++;return {};}},
  '../recovery/health-observer.cjs':{startHealthObservation:()=>{calls.health++;return {ready:Promise.resolve([{http:200,category:null},{http:200,category:null}]),stop:async()=>({status:'complete',records:[]})};}},
  './original-capture.cjs':{captureOriginal:async prepare=>{calls.capture++;prepare();return {status:'committed'};}}
 };
 const module={exports:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'capture-entry.cjs'),'utf8'),{require:n=>Object.hasOwn(mocks,n)?mocks[n]:require(n.startsWith('.')?path.resolve(root,n):n),module,Buffer,JSON,console:{log(){}}});
 let error,result;try{result=await module.exports.main();}catch(e){error=e;}
 assert.equal(JSON.stringify({before,current}),frozen,'comparison mutated input');
 return {calls,error,result,entry:module.exports};
}
test('actual entry reaches capture boundary with identical runtime',async()=>{const r=await exercise();assert.ifError(r.error);assert.equal(r.calls.capture,1);});
test('actual entry reaches capture boundary with mount order only changed',async()=>{const r=await exercise(x=>x.runtime[0].mounts.reverse());assert.ifError(r.error);assert.equal(r.calls.capture,1);});
const differences={missing:x=>x.runtime[0].mounts.pop(),extra:x=>x.runtime[0].mounts.push(copy(x.runtime[0].mounts[0])),duplicate:x=>x.runtime[0].mounts[1]=copy(x.runtime[0].mounts[0]),source:x=>x.runtime[0].mounts[0].Source='C:/other',volume:x=>x.runtime[0].mounts[1].Name='other',destination:x=>x.runtime[0].mounts[0].Destination='/other',writable:x=>x.runtime[0].mounts[0].RW=true,type:x=>x.runtime[0].mounts[0].Type='volume',propagation:x=>x.runtime[0].mounts[0].Propagation='shared',image:x=>x.runtime[0].image='other',container:x=>x.runtime[0].id='other',config:x=>x.runtime[0].configHash='other',network:x=>x.runtime[0].networks.app.NetworkID='other',port:x=>x.runtime[0].portBindings={port:'other'},flag:x=>x.runtime[0].flag=false,state:x=>x.runtime[0].state='other',git:x=>x.git.head='other',volumes:x=>x.volumes=[],networkIds:x=>x.networkIds=[],protected:x=>x.protected.original.push({path:'SECRET_CANARY'})};
for(const [name,change]of Object.entries(differences))test('actual entry refuses '+name+' before data and preserves safe preflight category',async()=>{
 const r=await exercise(change);assert.ok(r.error);assert.equal(r.calls.capture,0);assert.equal(r.calls.repository,0);assert.equal(r.calls.health,0);assert.equal(r.calls.released,1);
 const out=require('../lifecycle.cjs').failureOutput(r.error);assert.equal(out.category,'task6_protection_drift');assert.equal(out.preflight.stage,'preflight');assert.equal(out.preflight.failedCheck,['git','volumes','networkIds','protected'].includes(name)?name:'runtime');assert.equal(out.activity.repository,'not_run');assert.equal(out.persistence,'written');assert.ok(!JSON.stringify(out).includes('SECRET_CANARY'));
});
test('preflight primary survives receipt and lock failures together',async()=>{const r=await exercise(differences.image,{writeError:true,lockError:true});const out=require('../lifecycle.cjs').failureOutput(r.error);assert.equal(out.category,'task6_protection_drift');assert.equal(out.persistence,'write_failed');assert.equal(out.operationLockCleanup,'cleanup_blocked');assert.equal(r.calls.capture,0);});
test('shared precondition is real and readonly without main',async()=>{const r=await exercise();const a=baseline(),b=copy(a);b.runtime[1].mounts.reverse();assert.equal(r.entry.validatePreconditions(a,b),b);assert.equal(r.entry.inspectPreconditions().runtime.length,10);});
test('outer CLI preserves only allowed preflight and activity fields',()=>{let output;const module={exports:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'run.cjs'),'utf8'),{require:n=>require(path.resolve(root,n)),module,process:{exitCode:0},console:{log:x=>output=JSON.parse(x)}});module.exports.reportFailure(Object.assign(Error('task6_protection_drift'),{preflight:{stage:'preflight',failedCheck:'runtime',secret:'SECRET_CANARY'},receipt:{activity:{repository:'not_run',capture:'not_run',health:'not_run',payload:'SECRET_CANARY'},persistence:'write_failed',operationLockCleanup:'cleanup_blocked'}}));assert.equal(output.category,'task6_protection_drift');assert.equal(output.preflight.failedCheck,'runtime');assert.equal(output.activity.repository,'not_run');assert.equal(output.persistence,'write_failed');assert.ok(!JSON.stringify(output).includes('SECRET_CANARY'));});
module.exports={baseline,exercise};
