'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fixture=require('./snapshot-fixture.cjs');
test('snapshot helper close is bounded when process does not answer',async()=>{const f=fixture(),p=f.start();f.catalog();const h=await p,c=h.close().catch(e=>e);f.tick(5000);const e=await c;assert.equal(e.message,'snapshot_close_timeout');assert.equal(e.helperState,'retained_unverified');});
