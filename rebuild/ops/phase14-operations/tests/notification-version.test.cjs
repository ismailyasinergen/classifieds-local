'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
test('new profile accepts exact Phase14 adopted state',()=>{
 const state=require('../../../docs/phase14/adoption-state.json');
 assert.equal(require('../inspect.cjs').validateRelease(state),true);
});
