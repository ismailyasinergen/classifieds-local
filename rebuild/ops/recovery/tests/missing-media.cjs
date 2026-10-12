'use strict';
const fs=require('node:fs'),path=require('node:path');
const {validateOwned,inspectSource}=require('../runtime.cjs');
const {prepareRepository,snapshotCount}=require('../repository.cjs');
const {captureBundle}=require('../capture.cjs');
const {command,developer}=require('../inspect.cjs');
const {requireSafe}=require('../guards.cjs');
async function main() {
  const run='c8cd76a7025cd583',repoId='76836c56abe8d4d86f4a2f24a20ba4da';
  const receipt=JSON.parse(fs.readFileSync(path.join(developer,'rebuild/docs/phase7',`runtime-${run}.json`)));
  validateOwned(receipt);requireSafe(receipt.role==='synthetic-source');
  const source={...receipt,...inspectSource(receipt)};
  const repo=prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId,create:false});
  const before=snapshotCount(repo);let moved=false;
  const result={run,pass:false,applicationRefused:false,cleanupRestored:false};
  try {
    requireSafe(JSON.parse(command('docker',['exec',receipt.services.web,'python','/ops/synthetic_fixture.py',run,'hold-media'])).mediaMoved);
    moved=true;
    try {await captureBundle(source,repo,inspectSource);}
    catch(error){requireSafe(error.message==='snapshot_lost');result.applicationRefused=true;}
    requireSafe(result.applicationRefused&&snapshotCount(repo)===before);result.noSnapshotOrBundleCreated=true;
  } finally {
    if(moved){validateOwned(receipt);requireSafe(JSON.parse(command('docker',['exec',receipt.services.web,'python','/ops/synthetic_fixture.py',run,'return-media'])).mediaMoved);result.cleanupRestored=true;}
    result.pass=result.applicationRefused&&result.cleanupRestored&&result.noSnapshotOrBundleCreated;
    fs.writeFileSync(path.join(developer,'rebuild/docs/phase7',`missing-media-${Date.now()}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
    console.log(JSON.stringify(result));
  }
}
main().catch(()=>{console.log('{"pass":false,"category":"missing_media_probe_failed"}');process.exitCode=1;});
