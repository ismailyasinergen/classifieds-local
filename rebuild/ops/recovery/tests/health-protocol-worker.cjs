'use strict';
// Deliberately malformed IPC from a test-owned child; no HTTP or filesystem access.
const mode=process.argv[2];let count=0;
process.on('message',m=>{
 if(m.type==='start'){
  for(let i=1;i<=(mode==='duplicate_initial'?2:1);i++){
   const start=performance.now(),record={id:i,target:m.config.targets[0].label,phase:'initial',startedAt:mode==='timestamp'?'October 11, 2026 (private-body-canary)':new Date().toISOString(),startedMonoMs:start,scheduleLagMs:0};
   process.send({type:'started',record:mode==='private_field'?{...record,secret:'private-body-canary'}:record});
   if(mode!=='record_loss')process.send({type:'sample',record:{...record,http:mode==='contradiction'?503:200,category:null,endedAt:new Date().toISOString(),endedMonoMs:start+1,durationMs:1,skippedSlots:0,timingCategory:'on_time'}});
   count++;
  }
  if(mode==='record_loss'){process.send({type:'done',started:count,completed:count,reason:'stop'});process.disconnect();}
 }
 if(m.type==='stop'&&mode!=='ignore_stop'){process.send({type:'done',started:count,completed:count,reason:'stop'},()=>process.disconnect());}
});
