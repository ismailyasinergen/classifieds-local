'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {validateOwned,inspectSource}=require('../runtime.cjs');
const {captureBundle}=require('../capture.cjs');
const {prepareRepository}=require('../repository.cjs');
const {command,developer}=require('../inspect.cjs');
const {requireSafe}=require('../guards.cjs');
async function main() {
  const run=process.argv[2];requireSafe(/^[a-f0-9]{16}$/.test(run));
  const receipt=JSON.parse(fs.readFileSync(path.join(developer,'rebuild/docs/phase7',`runtime-${run}.json`)));
  validateOwned(receipt);requireSafe(receipt.role==='synthetic-source');
  const source={...receipt,...inspectSource(receipt)};
  const existing=process.argv[3];requireSafe(existing===undefined||/^[a-f0-9]{32}$/.test(existing));
  const repo=prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId:existing||crypto.randomBytes(16).toString('hex'),create:existing===undefined});
  const file=path.join(developer,'rebuild/docs/phase7',`capture-${run}-${repo.repoId}-${Date.now()}.json`);
  const result={run,repoId:repo.repoId,status:'capturing',atUTC:new Date().toISOString()};
  fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  try {
    Object.assign(result,await captureBundle(source,repo,inspectSource,()=>{
      validateOwned(receipt);
      command('docker',['exec',receipt.services.web,'python','-c',"import django; django.setup(); from accounts.models import User; assert User.objects.filter(first_name='after-snapshot').count()==0; User.objects.filter(email='owner@example.test').update(first_name='after-snapshot')"]);
      result.concurrentMutation=true;
    }));result.status='committed';
  } catch(error) {result.status='failed';result.category=/^[a-z_]+$/.test(error.message)?error.message:'capture_failed';process.exitCode=1;}
  fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}
main().catch(()=>{console.log('{"pass":false,"category":"capture_setup_failed"}');process.exitCode=1;});
