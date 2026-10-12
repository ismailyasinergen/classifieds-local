'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {validateReviewPacket}=require('../task6-gate.cjs');
const valid=()=>({verdict:'PASS',scope:'phase7_integrated_operations',independent:true,reviewer:'/test/independent',coveredScopes:['original_adapter','owner_identity_media','health_lifecycle'],operationsSha256:'a'.repeat(64),syntheticAdapterPassed:true});
test('exact independent review and synthetic acceptance bind operations hash',()=>assert.equal(validateReviewPacket(valid(),'a'.repeat(64)),true));
for(const [key,value] of [['verdict','pending'],['scope','synthetic_only'],['independent',false],['operationsSha256','b'.repeat(64)],['syntheticAdapterPassed',false]])
 test('review gate refuses '+key,()=>assert.throws(()=>validateReviewPacket({...valid(),[key]:value},'a'.repeat(64)),/^Error: original_export_gate_closed$/));
