'use strict';
const fs=require('node:fs'),path=require('node:path');
const {createRuntime}=require('../runtime.cjs');
const {prepareRepository}=require('../repository.cjs');
const {restoreBundle,bootstrapImageFromBackup}=require('../restore.cjs');
const {requireSafe}=require('../guards.cjs');
async function main() {
  const [repoId,bundleId]=process.argv.slice(2);requireSafe(/^[a-f0-9]{32}$/.test(repoId)&&/^[a-f0-9]{64}$/.test(bundleId));
  const repo=prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId,create:false});
  const bootstrap=await bootstrapImageFromBackup(repo,bundleId);
  const target=createRuntime('synthetic-target');
  const file=path.resolve(__dirname,'../../../docs/phase7',`restore-${target.run}.json`);
  const result={run:target.run,repoId,bundleId,status:'restoring',bootstrap,startedAt:new Date().toISOString()};
  fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  try {Object.assign(result,await restoreBundle(repo,bundleId,target));result.status='restored_not_verified';}
  catch(error){result.status='failed';result.category=/^[a-z_]+$/.test(error.message)?error.message:'restore_failed';process.exitCode=1;}
  result.finishedAt=new Date().toISOString();fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}
main().catch(error=>{console.log(JSON.stringify({pass:false,category:/^[a-z_]+$/.test(error.message)?error.message:'restore_setup_failed'}));process.exitCode=1;});
