const test=require('node:test'),assert=require('node:assert/strict');
const p=require('../inspect.cjs'),g=require('../gate.cjs');
const state=require('../../../docs/phase14/adoption-state.json');
test('accepted Phase14 release source verifier accepts both exact roots',()=>assert.equal(p.verifySources().length,319));
for(const [name,value] of [['image','sha256:'+'0'.repeat(64)],['productManifestSha256','0'.repeat(64)],['originalAdoption',false],['sourcePathsEachRoot',273]])test('reject mixed release '+name,()=>assert.throws(()=>p.validateRelease({...state,[name]:value}),/release_identity_refused/));
const review={verdict:'PASS',independent:true,scope:'phase14_integrated_operations_v3',operationsSha256:'a'.repeat(64),productManifest:p.manifest,image:p.image,reviewer:'test-only-independent',coveredScopes:g.scopes,ownerIdentityProfile:'original-owner-0:0-capless'};
test('review field contract accepts complete test-only packet',()=>assert(g.validateReviewPacket(review,'a'.repeat(64))));
for(const [name,value] of [['scope','health_observation_only'],['independent',false],['verdict','review_pending'],['ownerIdentityProfile','nonroot'],['coveredScopes',[]],['operationsSha256','b'.repeat(64)]])test('reject review '+name,()=>assert.throws(()=>g.validateReviewPacket({...review,[name]:value},'a'.repeat(64)),/acceptance_unavailable/));
test('unnamed reviewer cannot supply acceptance',()=>assert.throws(()=>g.validateReviewPacket({...review,reviewer:''},'a'.repeat(64)),/acceptance_unavailable/));
