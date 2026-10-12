'use strict';
const {safeResources}=require('../lifecycle.cjs');
const {counts,category,directoryOutput}=require('./contract.cjs');
async function observe(adapter){
 const startedAt=new Date().toISOString(),start=performance.now();let opened=false;
 let result={...Object.fromEntries(counts.map(k=>[k,null])),observationComplete:false,findingsPresent:null,reasons:null,directories:null,deletionAuthorized:false,candidateMeaning:'unreferenced_at_observation',error:null};
 try{
  await adapter.verify();opened=true;const directories=await adapter.open();if(directories)result.directories=directoryOutput(directories);
  const a=await adapter.snapshot(),s=await adapter.scan(),b=await adapter.snapshot(),t=await adapter.scan();
  result={...await adapter.compare([a,b,s,t]),error:null};await adapter.verify();
 }catch(e){result.observationComplete=false;result.error=category(e);result.resources=safeResources(e.resources);if(e.ownershipReleased)opened=false;if(e.directories)try{result.directories=directoryOutput(e.directories);}catch{}}
 finally{if(opened)try{result.cleanup=await adapter.close()||'removed_exact_owned';result.resources=safeResources(adapter.resources?.())||result.resources;}catch(e){result.observationComplete=false;result.cleanup='cleanup_blocked';result.resources=safeResources(e.resources)||result.resources;}else result.cleanup=result.resources?.status||'not_created';}
 return {...result,startedAt,endedAt:new Date().toISOString(),durationMs:performance.now()-start};
}
module.exports={observe};
