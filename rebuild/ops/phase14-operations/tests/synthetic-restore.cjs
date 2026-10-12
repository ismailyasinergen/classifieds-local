'use strict';
// No live source adapter or capture process state is imported here.
const {mergeLifecycle,lifecycleFields}=require('../lifecycle.cjs');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),cp=require('node:child_process');
const {createRuntime,stopOwnedRuntime}=require('../runtime.cjs');
const {prepareRepository}=require('../../recovery/repository.cjs');
const {restoreBundle,bootstrapImageFromBackup,targetCommand}=require('../restore.cjs');
const {docs}=require('../inspect.cjs');
const {failure,failureOutput,persist,mustPersist}=require('../lifecycle.cjs');
function safeOutcome(value){
 const out={pass:value?.pass===true,checks:Number.isSafeInteger(value?.checks)&&value.checks>=0?value.checks:0};
 const numbers=['tables','mediaFiles','mfaPrimaryFactors','favorites','savedSearches','storefronts'],booleans=['catalogOnly','consumerDisabled','deploymentBytesVerified','syntheticOnly','syntheticWritesOnly','partialContinued','duplicateDelivery','readArchivePreserved','retryStatePreserved','beatEvidence','draftPrivacyVerified','ownerScopeVerified'];
 if(value?.pass===true){assert(Object.keys(value).every(k=>['pass','checks','checkNames',...numbers,...booleans].includes(k)));for(const k of numbers)if(k in value){assert(Number.isSafeInteger(value[k])&&value[k]>=0);out[k]=value[k];}for(const k of booleans)if(k in value){assert.equal(typeof value[k],'boolean');out[k]=value[k];}}
 else out.category=['snapshot_catalog_mismatch','notification_restore_assertion','restore_verification_failed','feature_restore_verification_failed','synthetic_target_required'].includes(value?.category)?value.category:'verification_protocol_failed';
 return out;
}
async function main(repoId,bundleId){assert(/^[a-f0-9]{32}$/.test(repoId)&&/^[a-f0-9]{64}$/.test(bundleId));const result={repoId,bundleId,pass:false,checks:0,stage:'open_repository'};let target,file,primary,fileCreated=false;
 try{const repo=prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId,create:false});result.bootstrap=await bootstrapImageFromBackup(repo,bundleId);result.stage='create_target';target=createRuntime('synthetic-target');result.targetRun=target.run;file=path.join(docs,'synthetic-restore-'+target.run+'.json');mustPersist(fs,file,result,true);fileCreated=true;
 result.stage='restore';Object.assign(result,await restoreBundle(repo,bundleId,target));
 for(const name of ['verify_storefronts.py catalog','verify_notifications.py catalog','verify_restore.py','verify_features.py','verify_storefronts.py behavior','verify_notifications.py resume']){result.stage=name;const s=targetCommand(target,'web',['python','-B','/ops/'+name.split(' ')[0],target.run,...name.split(' ').slice(1)]),r=cp.spawnSync(s.command,s.args,{encoding:'utf8',windowsHide:true,timeout:120000,maxBuffer:65536});let value;try{value=safeOutcome(JSON.parse(r.stdout));}catch{throw Error('verification_protocol_failed');}result[name]={...value,nativeExit:r.status};assert.equal(r.status,0);assert.equal(value.pass,true);result.checks+=value.checks;}
 result.stage='complete';result.pass=true;
 }catch(error){primary=failure(error,'restore_failed');mergeLifecycle(result,primary);result.category=primary.message;result.resources=primary.resources;result.pass=false;}
 finally{
  if(target)try{result.cleanup=stopOwnedRuntime(target);result.resources=result.cleanup.resources;mergeLifecycle(result,result.cleanup,'restoreRuntime');}catch(error){result.cleanup={status:'cleanup_blocked'};result.resources=error.resources||result.resources;mergeLifecycle(result,error,'restoreRuntime');primary ||= failure(error,'cleanup_blocked');result.pass=false;}
  if(fileCreated){result.persistence='written';result.persistence=persist(fs,file,result);if(result.persistence!=='written'){primary ||= Error('receipt_write_failed');result.pass=false;}}
  else if(file)result.persistence='write_failed';
 }
 if(primary)throw Object.assign(primary,{resources:result.resources,receipt:result,...lifecycleFields(result)});
 console.log(JSON.stringify(result));return result;
}
function reportFailure(error){console.log(JSON.stringify(failureOutput(error)));process.exitCode=1;}
if(require.main===module)main(...process.argv.slice(2)).catch(reportFailure);
module.exports={main,reportFailure,safeOutcome};
