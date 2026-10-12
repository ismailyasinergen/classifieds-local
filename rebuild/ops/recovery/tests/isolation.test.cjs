'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {assertIsolation}=require('../isolation.cjs');
const names=['host8088','host8089','gateway8088','gateway8089','external443'];
const good=()=>names.map(name=>({name,resolved:true,connected:false,completed:true}));
test('complete actual deny evidence passes',()=>assert.equal(assertIsolation(good()),true));
for(const field of ['connected','resolved','completed'])test('isolation refuses '+field,()=>{
  const rows=good(); rows[0][field]=field==='connected';
  assert.throws(()=>assertIsolation(rows),/^Error: isolation_blocked$/);
});
test('missing probe evidence is refused',()=>assert.throws(()=>assertIsolation(good().slice(1))));
test('duplicate probe evidence is refused',()=>assert.throws(()=>assertIsolation([...good(),good()[0]])));
