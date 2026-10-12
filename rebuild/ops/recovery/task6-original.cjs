'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {verifyReview}=require('./task6-gate.cjs');
const {inspectBaseline,developer}=require('./inspect.cjs');
const {requireSafe}=require('./guards.cjs');
const {prepareRepository}=require('./repository.cjs');
const {captureOriginal}=require('./original-capture.cjs');
const {acquireLock}=require('./safe-process.cjs');
const {startHealthObservation}=require('./health-observer.cjs');
async function main() {
  const operationsSha256=verifyReview(),dir=path.join(developer,'rebuild/docs/phase7');
  const release=acquireLock(path.join(dir,'operation.lock'));
  // The earlier metadata-only refusal remains immutable in task6-original-attempt.json.
  const file=path.join(dir,'task6-original-capture-owner.json');
  let observer;
  try {
    const before=JSON.parse(fs.readFileSync(path.join(dir,'task6-baseline.json'))),baseline=inspectBaseline();
    for(const key of ['runtime','git','volumes','networkIds','protected'])requireSafe(JSON.stringify(before[key])===JSON.stringify(baseline[key]),'task6_protection_drift');
    const result={status:'started',operationsSha256,startedAt:new Date().toISOString(),repoId:crypto.randomBytes(16).toString('hex'),health:[]};
    fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
    observer=startHealthObservation();
    try {
      const initial=await observer.ready;
      requireSafe(initial.length===2&&initial.every(r=>r.http===200&&r.category===null),'source_health_failed');
      const prepare=()=>prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId:result.repoId,create:true});
      Object.assign(result,await captureOriginal(prepare,baseline));result.status='committed';
    } catch(error){if(error.receipt)Object.assign(result,error.receipt);else result.status='failed';result.category=/^[a-z_]+$/.test(error.message)?error.message:'original_capture_failed';process.exitCode=1;}
    finally {
      result.healthObservation=await observer.stop();result.health=result.healthObservation.records;
      if(result.healthObservation.status!=='complete')process.exitCode=1;
      result.finishedAt=new Date().toISOString();fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');
    }
    console.log(JSON.stringify(result));return result;
  } finally {try{if(observer)await observer.stop();}finally{release();}}
}
module.exports={main};
