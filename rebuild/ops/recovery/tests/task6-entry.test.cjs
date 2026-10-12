'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),Module=require('node:module');
test('ORIGINAL entry checks independent gate before repository or Docker',async()=>{
 let reads=0;const load=Module._load;Module._load=function(name,...args){
  if(name==='./task6-gate.cjs')return {verifyReview(){throw Error('original_export_gate_closed');}};
  if(name==='./repository.cjs')return {prepareRepository(){reads++;throw Error('private_read');}};
  return load.call(this,name,...args);
 };
 let main;try{const file=require.resolve('../task6-original.cjs');delete require.cache[file];main=require(file).main;}finally{Module._load=load;}
 await assert.rejects(main(),/^Error: original_export_gate_closed$/);assert.equal(reads,0);
});
