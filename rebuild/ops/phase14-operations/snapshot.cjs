'use strict';
const {spawn}=require('node:child_process');
const {safeSnapshot}=require('./lifecycle.cjs');
async function startSnapshotCommand(spec){
 const binding=spec.snapshotBinding;
 if(!binding||!/^[a-f0-9]{16}$/.test(binding.run)||!/^[a-f0-9]{32}$/.test(binding.attempt)||!/^[a-f0-9]{64}$/.test(binding.containerId))throw Error('snapshot_binding_refused');
 const state={...binding,status:'unverified',acknowledged:false,localClient:'unverified',localExit:null};
 let child,buffer=Buffer.alloc(0),catalogSettled=false,closed=false,started=false,closing,protocolError=false,initTimer;
 let resolveCatalog,rejectCatalog,resolveExit;const catalogPromise=new Promise((yes,no)=>{resolveCatalog=yes;rejectCatalog=no;});
 const done=new Promise(resolve=>{resolveExit=resolve;});
 const reject=code=>{if(!catalogSettled){catalogSettled=true;clearTimeout(initTimer);rejectCatalog(Error(code));}};
 const detach=()=>{for(const s of [child?.stdin,child?.stdout,child?.stderr])s?.destroy();child?.unref();};
 const cleanup=()=>{if(closing)return closing;closing=(async()=>{
  if(!started&&state.localClient==='not_started'){state.status='not_started';return safeSnapshot(state);}
  try{child.stdin.end('close:'+binding.attempt+'\n');}catch{}
  let timer;await Promise.race([done,new Promise(resolve=>{timer=setTimeout(resolve,5000);})]);clearTimeout(timer);
  if(state.acknowledged)state.status='closed';
  detach();return safeSnapshot(state);
 })();return closing;};
 const read=chunk=>{
  buffer=Buffer.concat([buffer,chunk]);const limit=catalogSettled?2048:32*1024*1024+1024;
  if(buffer.length>limit){buffer=Buffer.alloc(0);protocolError=true;reject('catalog_capacity');return;}
  let pos;while((pos=buffer.indexOf(10))>=0){const line=buffer.subarray(0,pos);buffer=buffer.subarray(pos+1);let frame;
   try{frame=JSON.parse(line);}catch{protocolError=true;reject('catalog_invalid');continue;}
   if(frame.run!==binding.run||frame.attempt!==binding.attempt){protocolError=true;reject('snapshot_binding_refused');continue;}
   if(frame.type==='snapshot_closed'&&frame.transactionClosed===true&&frame.connectionClosed===true){state.acknowledged=true;continue;}
   if(frame.type!=='catalog'||catalogSettled){protocolError=true;reject('catalog_invalid');continue;}
   if(!/^[A-Fa-f0-9]+-[A-Fa-f0-9]+-[0-9]+$/.test(frame.catalog?.snapshot)){protocolError=true;reject('snapshot_invalid');continue;}
   catalogSettled=true;clearTimeout(initTimer);resolveCatalog(frame.catalog);
  }
 };
 try{
  child=spawn(spec.command,[...spec.args,binding.run,binding.attempt],{windowsHide:true,stdio:['pipe','pipe','pipe']});
  child.stderr.resume();child.stdin.on('error',()=>{reject('snapshot_lost');});
  child.once('spawn',()=>{started=true;});
  child.once('error',()=>{if(!started){state.localClient='not_started';state.status='not_started';}reject('snapshot_spawn_failed');resolveExit();});
  child.once('close',code=>{closed=true;state.localClient='exited';state.localExit=code;reject('snapshot_lost');resolveExit();});
  child.stdout.on('data',read);initTimer=setTimeout(()=>reject('snapshot_timeout'),300000);
  const catalog=await catalogPromise;
  return {catalog,isAlive:()=>!closed&&!closing&&!protocolError,async close(){const result=await cleanup();if(result.status!=='closed'||result.localClient!=='exited'||result.localExit!==0||protocolError)throw Object.assign(Error(result.status==='closed'?'snapshot_close_failed':'snapshot_close_timeout'),{snapshotCleanup:result,helperState:result.status==='unverified'?'retained_unverified':undefined});return result;},async abort(){return cleanup();}};
 }catch(error){clearTimeout(initTimer);if(!child){state.localClient='not_started';state.status='not_started';}const result=await cleanup();throw Object.assign(Error(error.message),{snapshotCleanup:result,helperState:result.status==='unverified'?'retained_unverified':undefined});}
}
module.exports={startSnapshotCommand};
