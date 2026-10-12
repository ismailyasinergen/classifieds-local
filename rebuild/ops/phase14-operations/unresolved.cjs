'use strict';
const fs=require('node:fs'),path=require('node:path'),{docs}=require('./inspect.cjs');
function unresolved(record){
 const bad=r=>r&&(r.unknown===true||r.status==='cleanup_blocked'||r.capacityExceeded===true||(r.retained||[]).length>0);
 return record?.snapshotCleanup?.status==='unverified'||record?.helperState==='retained_unverified'||bad(record?.resources)||Object.values(record?.resourceGroups||{}).some(bad)||(record?.phase&&record?.attempt&&record.phase!=='closed');
}
function assertNoUnresolved(){
 for(const n of fs.readdirSync(docs).filter(n=>/^(helper-[a-f0-9]{32}|synthetic-[a-f0-9]{16}|task6-capture-[a-f0-9]{16}|original-capture-v[23])\.json$/.test(n))){
  const p=path.join(docs,n);if(fs.lstatSync(p).isSymbolicLink())throw Error('cleanup_blocked');let r;try{r=JSON.parse(fs.readFileSync(p));}catch{throw Error('cleanup_blocked');}if(unresolved(r))throw Error('cleanup_blocked');
 }
}
module.exports={assertNoUnresolved,unresolved};
