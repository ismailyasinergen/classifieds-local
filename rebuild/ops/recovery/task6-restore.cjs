'use strict';
// This entry imports no live source adapter; its only data inputs are backup references.
const fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const {verifyReview}=require('./task6-gate.cjs');
const {prepareRepository}=require('./repository.cjs');
const {bootstrapImageFromBackup,restoreBundle,targetCommand}=require('./restore.cjs');
const {createRuntime,stopOwnedRuntime}=require('./runtime.cjs');
const {requireSafe}=require('./guards.cjs');
function checked(spec,maxBuffer=32768) {
  try{return execFileSync(spec.command,spec.args,{windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:120000,maxBuffer});}
  catch{throw Error('target_check_failed');}
}
async function main(repoId,bundleId) {
  verifyReview();requireSafe(/^[a-f0-9]{32}$/.test(repoId)&&/^[a-f0-9]{64}$/.test(bundleId),'restore_reference_refused');
  const repo=prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId,create:false});
  const bootstrap=await bootstrapImageFromBackup(repo,bundleId);
  const target=createRuntime('original-target'),result={repoId,bundleId,run:target.run,bootstrap,status:'restoring',startedAt:new Date().toISOString()};
  const file=path.resolve(__dirname,'../../docs/phase7',`task6-restore-${target.run}.json`);
  fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  try {
    Object.assign(result,await restoreBundle(repo,bundleId,target));
    result.verification=JSON.parse(checked(targetCommand(target,'web',['python','-B','/ops/verify_original.py',target.run])));
    requireSafe(result.verification.pass===true,'original_restore_verification_failed');
    result.checks=[];
    for(const args of [['python','-m','pip','check'],['python','manage.py','check'],['python','manage.py','makemigrations','--check','--dry-run'],['python','manage.py','migrate','--check']]) {
      checked(targetCommand(target,'web',args));result.checks.push({command:args.join(' '),exit:0});
    }
    result.status='verified';
  } catch(error){result.status='failed';result.category=/^[a-z_]+$/.test(error.message)?error.message:'restore_failed';process.exitCode=1;}
  finally {
    try{result.cleanup=stopOwnedRuntime(target);}catch{result.cleanup={status:'cleanup_blocked'};process.exitCode=1;}
    result.finishedAt=new Date().toISOString();fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');
  }
  console.log(JSON.stringify(result));return result;
}
module.exports={main};
