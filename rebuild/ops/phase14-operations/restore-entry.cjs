'use strict';
// This entry imports no live source adapter; its only data inputs are backup references.
const {mergeLifecycle,lifecycleFields}=require('./lifecycle.cjs');
const fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const {verifyReview}=require('./gate.cjs');
const {prepareRepository}=require('../recovery/repository.cjs');
const {bootstrapImageFromBackup,restoreBundle,targetCommand}=require('./restore.cjs');
const {createRuntime,stopOwnedRuntime}=require('./runtime.cjs');
const {requireSafe}=require('../recovery/guards.cjs');
const {persist,mustPersist,failure}=require('./lifecycle.cjs');
function validateVerification(v){
 const exact=(o,keys)=>o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).sort().join()===keys.split(' ').sort().join();
 const ok=value=>requireSafe(value,'original_restore_verification_failed'),count=n=>Number.isSafeInteger(n)&&n>=0;
 ok(exact(v,'pass checks tables rows catalogSha256 mediaFiles mediaCoverage mfa keyBindingVerified realAccountAuthenticationPerformed favorites savedSearches favoritesCoverage savedSearchesCoverage notifications storefronts'));
 ok(v.pass===true&&v.keyBindingVerified===true&&v.realAccountAuthenticationPerformed===false&&/^[a-f0-9]{64}$/.test(v.catalogSha256));
 for(const k of ['checks','tables','rows','mediaFiles','favorites','savedSearches'])ok(count(v[k]));
 for(const k of ['favorites','savedSearches'])ok(v[k+'Coverage']===(v[k]?'aggregate_verified':'empty'));
 ok(v.mediaCoverage===(v.mediaFiles?'verified':'unavailable'));
 ok(exact(v.mfa,'primary recovery coverage')&&count(v.mfa.primary)&&count(v.mfa.recovery)&&v.mfa.coverage===(v.mfa.primary+v.mfa.recovery?'verified':'unavailable'));
 const n=v.notifications;ok(exact(n,'tables consumption enabledSearches disabledSearches readDeliveries archivedDeliveries nullSearchMatches publicationBoundaryVerified deploymentOverlayBytesVerified runtimeConsumerDisabled quarantineVerified realUserOperationPerformed restoredConsumerExecuted'));
 ok(exact(n.tables,'events_publicationboundary events_eventconsumption notifications_savedsearch notifications_notificationdelivery notifications_notificationmatch'));
 for(const t of Object.values(n.tables))ok(exact(t,'count coverage')&&count(t.count)&&t.coverage===(t.count?'aggregate_verified':'empty'));
 ok(exact(n.consumption,'pending retry completed skipped failed')&&Object.values(n.consumption).every(count));
 for(const k of ['enabledSearches','disabledSearches','readDeliveries','archivedDeliveries','nullSearchMatches'])ok(count(n[k]));
 for(const k of ['publicationBoundaryVerified','deploymentOverlayBytesVerified','runtimeConsumerDisabled','quarantineVerified'])ok(n[k]===true);
 ok(n.realUserOperationPerformed===false&&n.restoredConsumerExecuted===false);
 const st=v.storefronts;ok(exact(st,'count published unpublished neverPublished withdrawn draftDiffersFromPublic minEditVersion maxEditVersion coverage schemaVerified snapshotValuesVerified uuidNoSequenceVerified behaviorTestPerformed realUserOperationPerformed'));
 for(const k of ['count','published','unpublished','neverPublished','withdrawn','draftDiffersFromPublic'])ok(count(st[k]));
 ok(st.published+st.unpublished===st.count&&st.neverPublished+st.withdrawn===st.unpublished&&st.draftDiffersFromPublic<=st.count&&st.coverage===(st.count?'aggregate_verified':'empty'));
 ok(st.count?(Number.isSafeInteger(st.minEditVersion)&&Number.isSafeInteger(st.maxEditVersion)&&st.minEditVersion>=1&&st.maxEditVersion>=st.minEditVersion):(st.minEditVersion===null&&st.maxEditVersion===null));
 for(const k of ['schemaVerified','snapshotValuesVerified','uuidNoSequenceVerified'])ok(st[k]===true);
 ok(st.behaviorTestPerformed===false&&st.realUserOperationPerformed===false);return v;
}
function checked(spec,maxBuffer=32768) {
  try{return execFileSync(spec.command,spec.args,{windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:120000,maxBuffer});}
  catch{throw Error('target_check_failed');}
}
async function main(repoId,bundleId) {
  verifyReview();requireSafe(/^[a-f0-9]{32}$/.test(repoId)&&/^[a-f0-9]{64}$/.test(bundleId),'restore_reference_refused');
  const repo=prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId,create:false});
  const bootstrap=await bootstrapImageFromBackup(repo,bundleId);
  let target,file,primary,fileCreated=false;
  const result={repoId,bundleId,bootstrap,status:'restoring',startedAt:new Date().toISOString()};
  try {
    target=createRuntime('original-target');result.run=target.run;
    file=path.resolve(__dirname,'../../docs/phase15',`task6-restore-${target.run}.json`);
    mustPersist(fs,file,result,true);fileCreated=true;
    Object.assign(result,await restoreBundle(repo,bundleId,target));
    result.verification=validateVerification(JSON.parse(checked(targetCommand(target,'web',['python','-B','/ops/verify_original.py',target.run]))));
    requireSafe(result.verification.pass===true,'original_restore_verification_failed');
    result.checks=[];
    for(const args of [['python','-m','pip','check'],['python','manage.py','check'],['python','manage.py','makemigrations','--check','--dry-run'],['python','manage.py','migrate','--check']]) {
      checked(targetCommand(target,'web',args));result.checks.push({command:args.join(' '),exit:0});
    }
    result.status='verified';
  } catch(error){primary=failure(error,'restore_failed');mergeLifecycle(result,primary);result.status='failed';result.category=primary.message;result.resources=primary.resources;}
  finally {
    if(target)try{result.cleanup=stopOwnedRuntime(target);result.resources=result.cleanup.resources;mergeLifecycle(result,result.cleanup,'restoreRuntime');}catch(error){result.cleanup={status:'cleanup_blocked'};result.resources=error.resources;mergeLifecycle(result,error,'restoreRuntime');primary ||= failure(error,'cleanup_blocked');}
    result.finishedAt=new Date().toISOString();
    if(fileCreated){result.persistence=persist(fs,file,result);if(result.persistence!=='written')primary ||= Error('receipt_write_failed');}
    else if(file)result.persistence='write_failed';
  }
  if(primary)throw Object.assign(primary,{resources:result.resources,receipt:result,...lifecycleFields(result)});
  console.log(JSON.stringify(result));return result;
}
module.exports={main,validateVerification};
