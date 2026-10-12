'use strict';
// New isolated source only; no real source snapshot or private backup output.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {createRuntime,stopOwnedRuntime,inspectSource}=require('../runtime.cjs');
const {createHelper,resolveHost}=require('../owned-helper.cjs');
const {startSourceSnapshot,privateRun}=require('../capture.cjs');
const {runBinaryPipeline}=require('../../recovery/safe-process.cjs');
const {verifySources,command,docs}=require('../inspect.cjs');
const {failure,failureOutput,mergeLifecycle,persist}=require('../lifecycle.cjs');
async function main(){
 const run=crypto.randomBytes(8).toString('hex'),result={run,syntheticOnly:true,pass:false,checks:0,cases:[]};let source,helper,snapshot,primary;
 const check=(x)=>{assert(x);result.checks++;};
 try{
  const dns=resolveHost(run);check(dns.hosts.length>0);check(dns.resourceGroups.dns.status==='removed');result.cases.push({role:'dns',...require('../lifecycle.cjs').lifecycleFields(dns)});
  const files=verifySources();helper=createHelper('archive',run);
  const normal=await runBinaryPipeline(helper.producer(Buffer.from(JSON.stringify(files))),{command:process.execPath,args:['-e','process.stdin.resume();']},{maxBytes:8*1024*1024,timeoutMs:60000});helper.verifyExit();check(normal.producerExit===0&&normal.consumerExit===0&&normal.bytes>0);const archive=helper.close();helper=null;check(archive.resourceGroups.archive.status==='removed');result.cases.push({role:'archive',bytes:normal.bytes,producerExit:normal.producerExit,consumerExit:normal.consumerExit,...archive});
  helper=createHelper('archive',run);let expected;try{await runBinaryPipeline(helper.producer(Buffer.from(JSON.stringify(files))),{command:process.execPath,args:['-e','process.stdin.once("data",()=>process.exit(9));']},{maxBytes:8*1024*1024,timeoutMs:60000});}catch(e){expected=e.message;}check(expected==='pipeline_failed');const cancelled=helper.close();helper=null;check(cancelled.resourceGroups.archive.status==='removed');result.cases.push({role:'archive-consumer-failure',expectedCategory:expected,injectedConsumerExit:9,...cancelled});
  source=createRuntime('synthetic-source');const identity=inspectSource(source);
  privateRun({command:'docker',args:['exec','-i',identity.appId,'python','-B','/ops/synthetic_fixture.py',source.run]});
  snapshot=await startSourceSnapshot({...source,...identity});check(snapshot.catalog.format===3);const closed=await snapshot.close();check(closed.status==='closed'&&closed.acknowledged&&closed.localExit===0);result.cases.push({role:'snapshot-close',snapshotCleanup:closed});snapshot=null;
  snapshot=await startSourceSnapshot({...source,...identity});const aborted=await snapshot.abort();check(aborted.status==='closed'&&aborted.acknowledged&&aborted.localExit===0);result.cases.push({role:'snapshot-abort',snapshotCleanup:aborted});snapshot=null;
  result.pass=true;
 }catch(e){primary=failure(e,'operation_failed');result.category=primary.message;mergeLifecycle(result,e);}
 finally{
  if(snapshot)try{result.snapshotCleanup=await snapshot.abort();if(result.snapshotCleanup.status!=='closed')primary ||= Error('cleanup_blocked');}catch(e){primary ||= failure(e,'cleanup_blocked');mergeLifecycle(result,e);}
  if(helper)try{mergeLifecycle(result,helper.close());}catch(e){primary ||= failure(e,'cleanup_blocked');mergeLifecycle(result,e);}
  if(source)try{result.sourceCleanup=stopOwnedRuntime(source);mergeLifecycle(result,result.sourceCleanup,'sourceRuntime');}catch(e){primary ||= failure(e,'cleanup_blocked');mergeLifecycle(result,e,'sourceRuntime');}
  try{const current=command('docker',['ps','-aq','--no-trunc']).split(/\r?\n/),nets=command('docker',['network','ls','-q','--no-trunc']).split(/\r?\n/);const groups=[...result.cases.flatMap(c=>Object.values(c.resourceGroups||{})),...Object.values(result.resourceGroups||{})];check(groups.every(g=>g.known.every(id=>!current.includes(id)&&!nets.includes(id))));result.exactMetadataAbsenceVerified=true;}catch(e){primary ||= failure(e,'cleanup_blocked');}
  if(primary)result.pass=false;result.finishedAt=new Date().toISOString();result.persistence=persist(fs,path.join(docs,'v2-lifecycle-integration-'+run+'.json'),result,true);if(result.persistence!=='written')primary ||= Error('receipt_write_failed');
 }
 console.log(JSON.stringify(primary?failureOutput(Object.assign(primary,{receipt:result,...require('../lifecycle.cjs').lifecycleFields(result)})):result));if(primary)process.exitCode=1;
}
main();
