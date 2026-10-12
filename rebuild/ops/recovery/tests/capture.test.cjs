'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {assertStable}=require('../capture.cjs');
const good=()=>({appId:'a'.repeat(64),dbId:'b'.repeat(64),image:'sha256:'+'c'.repeat(64),manifest:'d'.repeat(64),keySha256:'e'.repeat(64),snapshotAlive:true});
for(const field of ['appId','dbId','image','manifest','keySha256','snapshotAlive'])
  test('capture refuses changed '+field,()=>{const before=good(),after=good();after[field]=field==='snapshotAlive'?false:'changed';assert.throws(()=>assertStable(before,after));});
test('capture accepts stable identity only',()=>assert.equal(assertStable(good(),good()),true));
for(const field of ['appId','dbId'])test('capture refuses inconsistent '+field+' alias before spawn',()=>{
  const identity=good(),source={...identity,run:'a'.repeat(16),[field]:'f'.repeat(64)};
  assert.throws(()=>require('../capture.cjs').assertSourceBinding(source,identity),/^Error: source_alias_refused$/);
});
