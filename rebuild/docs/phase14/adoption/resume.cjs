'use strict';
const cp=require('node:child_process');
const O='C:/Users/ismai/Desktop/classifieds_local',D='C:/Users/ismai/.devspace/worktrees/classifieds_local-a7be577c';
function gitRead(root,check,spawn=cp.spawnSync){
 const operations={identity:['rev-parse','--show-toplevel','HEAD'],branch:['branch','--show-current'],status:['status','--short']};
 if(![O,D].includes(root)||!Object.hasOwn(operations,check))throw Error('git_request_refused');
 const args=['--no-optional-locks',...(root===O?['-c','safe.directory=','-c','safe.directory='+O]:[]),'-C',root,...operations[check]];
 const r=spawn('git',args,{encoding:'utf8',windowsHide:true,timeout:10000,maxBuffer:2*1024*1024});
 if(r.status!==0){const e=Error('git_check_failed');e.code='git_check_failed';e.detail={check,nativeExit:r.status,category:/dubious ownership/.test(r.stderr||'')?'dubious_ownership':r.error?'process_failure':'git_nonzero'};throw e;}
 return {value:r.stdout.trim(),nativeExit:r.status};
}
function classifyState({preparation,state,reportPresent,active}){
 if(active)throw Error('state_refused');
 if(state){if(state.status==='completed'&&state.originalAdoption===true&&reportPresent)return 'verify_completed';throw Error('state_refused');}
 if(preparation?.status==='blocked_before_cutover'&&preparation.cutoverStarted===false&&preparation.originalAdoption===false&&reportPresent)return 'revalidate_before_cutover';
 throw Error('state_refused');
}
module.exports={gitRead,classifyState};
