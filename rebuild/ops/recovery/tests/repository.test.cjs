'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {validateBundle}=require('../repository.cjs');
const run='0123456789abcdef',hash='a'.repeat(64);
const kinds=['database.dump','media.tar','keys.json','catalog.json','source.tar','application-image.tar'];
const good=()=>({complete:true,run,sourceKind:'synthetic',keyId:run,components:kinds.map((kind,n)=>({kind,run,sourceKind:'synthetic',snapshotId:String(n).repeat(64),bytes:10,sha256:hash,producerExit:0,consumerExit:0}))});
test('valid six exact components accepted',()=>assert.equal(validateBundle(good()),true));
for(const [name,mutate] of Object.entries({incomplete:b=>b.complete=false,missing:b=>b.components.pop(),mixed:b=>b.components[0].run='f'.repeat(16),
  origin:b=>b.components[0].sourceKind='original',duplicate:b=>b.components[0]=b.components[1],short:b=>b.components[0].snapshotId='abc',
  latest:b=>b.components[0].snapshotId='latest',producer:b=>b.components[0].producerExit=1,consumer:b=>b.components[0].consumerExit=1,
  empty:b=>b.components[0].bytes=0,sha:b=>b.components[0].sha256='invalid',oversize:b=>b.components[0].bytes=536870913}))
  test('bundle refuses '+name,()=>{const b=good();mutate(b);assert.throws(()=>validateBundle(b));});
