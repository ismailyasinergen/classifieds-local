'use strict';
const {mergeLifecycle,lifecycleFields}=require('./lifecycle.cjs');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {verifyReview}=require('./gate.cjs');
const {inspectBaseline,compareRuntime,developer}=require('./inspect.cjs');
const {requireSafe}=require('../recovery/guards.cjs');
const {prepareRepository}=require('../recovery/repository.cjs');
const {captureOriginal}=require('./original-capture.cjs');
const {acquireLock}=require('./lock.cjs');
const {startHealthObservation}=require('../recovery/health-observer.cjs');
const {persist,mustPersist,failure}=require('./lifecycle.cjs');
function validatePreconditions(before,current){
  for(const key of ['runtime','git','volumes','networkIds','protected'])try{
    if(key==='runtime'){
      compareRuntime(current.runtime,before.runtime);
      // Mounts use the existing exact multiset/security contract; retain every other field and array order.
      const rest=rows=>rows.map(({mounts,...row})=>row);
      requireSafe(JSON.stringify(rest(before.runtime))===JSON.stringify(rest(current.runtime)),'task6_protection_drift');
    }else requireSafe(JSON.stringify(before[key])===JSON.stringify(current[key]),'task6_protection_drift');
  }catch{throw Object.assign(Error('task6_protection_drift'),{preflight:{stage:'preflight',failedCheck:key}});}
  return current;
}
function inspectPreconditions(){
  let before,current;
  try{before=JSON.parse(fs.readFileSync(path.join(developer,'rebuild/docs/phase15/baseline.json')));current=inspectBaseline();}
  catch{throw Object.assign(Error('task6_protection_drift'),{preflight:{stage:'preflight',failedCheck:'source_runtime_metadata'}});}
  return validatePreconditions(before,current);
}
async function main() {
  require('./unresolved.cjs').assertNoUnresolved();
  const operationsSha256=verifyReview(),dir=path.join(developer,'rebuild/docs/phase15');
  const release=acquireLock(path.join(dir,'operation.lock'));
  const file=path.join(dir,'original-capture-v3.json');
  let observer,primary,fileCreated=false,writeAttempted=false;
  const result={status:'started',operationsSha256,startedAt:new Date().toISOString(),repoId:crypto.randomBytes(16).toString('hex'),health:[],activity:{repository:'not_run',capture:'not_run',health:'not_run'}};
  try {
    const baseline=inspectPreconditions();
    writeAttempted=true;mustPersist(fs,file,result,true);fileCreated=true;
    result.activity.health='attempted';
    observer=startHealthObservation();
      const initial=await observer.ready;
      requireSafe(initial.length===2&&initial.every(r=>r.http===200&&r.category===null),'source_health_failed');
      const prepare=()=>{result.activity.repository='attempted';return prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId:result.repoId,create:true});};
      result.activity.capture='attempted';
      Object.assign(result,await captureOriginal(prepare,baseline));result.status='committed';
  } catch(error){primary=failure(error,'capture_failed');mergeLifecycle(result,primary);if(error.preflight)result.preflight=primary.preflight;if(error.receipt)Object.assign(result,error.receipt);else result.status='failed';result.category=primary.message;result.resources=primary.resources||result.resources;}
  finally {
    if(observer)try{result.healthObservation=await observer.stop();result.health=result.healthObservation.records;if(result.healthObservation.status!=='complete')primary ||= Error('health_observation_failed');}catch{result.healthStatus='unavailable';primary ||= Error('health_observation_failed');}
    try{release();result.operationLockCleanup='released';}catch{result.operationLockCleanup='cleanup_blocked';primary ||= Error('lock_release_failed');}
    result.finishedAt=new Date().toISOString();
    result.persistence='written';
    if(fileCreated||!writeAttempted)result.persistence=persist(fs,file,result,!fileCreated);else result.persistence='write_failed';
    if(result.persistence!=='written')primary ||= Error('receipt_write_failed');
  }
  if(primary)throw Object.assign(primary,{resources:result.resources,receipt:result,...lifecycleFields(result)});
  console.log(JSON.stringify(result));return result;
}
module.exports={main,validatePreconditions,inspectPreconditions};
