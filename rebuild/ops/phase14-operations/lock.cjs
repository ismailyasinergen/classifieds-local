'use strict';
const fs=require('node:fs');
function acquireLock(file){
 let fd;try{fd=fs.openSync(file,'wx');}catch{throw Error('run_locked');}
 let identity,closed=false,released=false;
 const release=()=>{
  if(released)return;
  try{
   if(!closed){fs.closeSync(fd);closed=true;}
   const current=fs.lstatSync(file);
   if(!identity||!current.isFile()||current.isSymbolicLink()||current.ino!==identity.ino||current.dev!==identity.dev)throw Error();
   fs.unlinkSync(file);released=true;
  }catch{throw Object.assign(Error('lock_release_failed'),{lockCleanup:'cleanup_blocked'});}
 };
 try{identity=fs.fstatSync(fd);fs.writeFileSync(fd,JSON.stringify({pid:process.pid}));}
 catch{const error=Error('receipt_write_failed');try{release();error.lockCleanup='released';}catch{error.lockCleanup='cleanup_blocked';}throw error;}
 return release;
}
function releaseLocks(releases,primary){let blocked=false;for(const release of releases)if(release)try{release();}catch{blocked=true;}if(blocked)throw Object.assign(primary||Error('lock_release_failed'),{lockCleanup:'cleanup_blocked'});}
module.exports={acquireLock,releaseLocks};
