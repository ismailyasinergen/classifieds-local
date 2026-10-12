'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {observe}=require('../media-audit/observe.cjs');
const resources={run:'a'.repeat(16),role:'media-reader',known:['b'.repeat(64)],removed:[],retained:['b'.repeat(64)],unknown:false,status:'cleanup_blocked',persistence:'not_attempted'};
test('observe preserves primary scan error and exact retained reader',async()=>{
 const result=await observe({verify(){},open(){},snapshot(){return [];},scan(){throw Error('unsafe_entry');},close(){throw Object.assign(Error('PRIVATE_CANARY'),{resources});}});
 assert.equal(result.error,'unsafe_entry');assert.equal(result.resources.retained[0],resources.retained[0]);assert(!JSON.stringify(result).includes('PRIVATE_CANARY'));
});
test('constructor failure ownership is retained without caller double cleanup',async()=>{
 let closes=0;
 const result=await observe({verify(){},open(){throw Object.assign(Error('command_failed'),{resources,ownershipReleased:true});},close(){closes++;}});
 assert.equal(closes,0);assert.equal(result.resources.status,'cleanup_blocked');
});
