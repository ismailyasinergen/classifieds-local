'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
test('real restore output rejects unknown/private fields and preserves empty/populated coverage',()=>{
 const {validateVerification}=require('../restore-entry.cjs');
 assert.equal(typeof validateVerification,'function');
 for(const n of [0,2]){
  const value={pass:true,checks:3,tables:40,rows:n,catalogSha256:'a'.repeat(64),mediaFiles:0,mediaCoverage:'unavailable',mfa:{primary:0,recovery:0,coverage:'unavailable'},keyBindingVerified:true,realAccountAuthenticationPerformed:false,favorites:n,savedSearches:n,favoritesCoverage:n?'aggregate_verified':'empty',savedSearchesCoverage:n?'aggregate_verified':'empty',notifications:{tables:Object.fromEntries(['events_publicationboundary','events_eventconsumption','notifications_savedsearch','notifications_notificationdelivery','notifications_notificationmatch'].map(k=>[k,{count:n,coverage:n?'aggregate_verified':'empty'}])),consumption:{pending:n,retry:0,completed:0,skipped:0,failed:0},enabledSearches:n,disabledSearches:0,readDeliveries:0,archivedDeliveries:0,nullSearchMatches:0,publicationBoundaryVerified:true,deploymentOverlayBytesVerified:true,runtimeConsumerDisabled:true,quarantineVerified:true,realUserOperationPerformed:false,restoredConsumerExecuted:false}};
  value.storefronts={count:n,published:n,unpublished:0,neverPublished:0,withdrawn:0,draftDiffersFromPublic:0,minEditVersion:n?1:null,maxEditVersion:n?2:null,coverage:n?'aggregate_verified':'empty',schemaVerified:true,snapshotValuesVerified:true,uuidNoSequenceVerified:true,behaviorTestPerformed:false,realUserOperationPerformed:false};
  assert.deepEqual(validateVerification(value),value);
  for(const mutate of [v=>{delete v.storefronts;},v=>{v.storefronts.private='PRIVATE_CANARY';},v=>{v.storefronts.behaviorTestPerformed=true;},v=>{v.storefronts.snapshotValuesVerified=false;},v=>{v.storefronts.minEditVersion=0;}]){const bad=structuredClone(value);mutate(bad);assert.throws(()=>validateVerification(bad),e=>!e.message.includes('PRIVATE_CANARY'));}
  for(const mutate of [v=>{v.private='PRIVATE_CANARY';},v=>{v.notifications.tables.notifications_savedsearch.coverage='unknown';},v=>{v.notifications.restoredConsumerExecuted=true;},v=>{delete v.notifications;},v=>{v.notifications.consumption.pending=-1;}]){const bad=structuredClone(value);mutate(bad);assert.throws(()=>validateVerification(bad),e=>!e.message.includes('PRIVATE_CANARY'));}
 }
});
