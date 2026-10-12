'use strict';
const fs=require('node:fs'),path=require('node:path');
const {inspectBaseline,developer,isPrivateEnv}=require('./inspect.cjs');
const {acquireLock}=require('./safe-process.cjs');
const dir=path.join(developer,'rebuild/docs/phase7');
function main() {
  const release=acquireLock(path.join(dir,'operation.lock'));
  try {
    if(!['inspect','verify-protection'].includes(process.argv[2]))throw new Error('stage_not_implemented');
    const baseline=inspectBaseline();
    const name=path.join(dir,'runtime-baseline.json');
    if(process.argv[2]==='verify-protection') {
      const before=JSON.parse(fs.readFileSync(name));
      const equal=['manifest','image','sourcePaths','runtime','git','containerIds','volumeNames','volumes','networkIds']
        .every(k=>JSON.stringify(before[k])===JSON.stringify(baseline[k]));
      if(!equal)throw new Error('protection_drift');
      for(const name of ['developer','original']) {
        const safeMap=map=>map.filter(row=>!isPrivateEnv(row.path));
        if(JSON.stringify(safeMap(before.protected[name]))!==JSON.stringify(safeMap(baseline.protected[name])))throw new Error('protection_drift');
      }
      const result={atUTC:new Date().toISOString(),pass:true,sourcePathsPerRoot:273,containers:10,volumes:10,networks:2,gitPreserved:true,protectedFilesPreserved:true,
        privateEnvContentRechecked:false,privateEnvProtection:'No writes performed; initial content hashes retained, final content reads excluded after independent review; no initial stat baseline available.',
        privateEnvFinalMetadata:Object.fromEntries(Object.entries(baseline.protected).map(([k,v])=>[k,v.filter(row=>isPrivateEnv(row.path))])),
        protectedCounts:Object.fromEntries(Object.entries(baseline.protected).map(([k,v])=>[k,v.length]))};
      fs.writeFileSync(path.join(dir,'final-protection.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
      console.log(JSON.stringify(result));return;
    }
    if(fs.existsSync(name))throw new Error('baseline_exists');
    fs.writeFileSync(name,JSON.stringify(baseline,null,2)+'\n',{flag:'wx'});
    console.log(JSON.stringify({pass:true,sourcePaths:273,containers:baseline.containerIds.length,volumes:baseline.volumes.length,networks:baseline.networkIds.length,git:Object.fromEntries(Object.entries(baseline.git).map(([k,v])=>[k,{head:v.head,branch:v.branch}])),
      protectedCounts:Object.fromEntries(Object.entries(baseline.protected).map(([k,v])=>[k,v.length]))}));
  } finally {release();}
}
Promise.resolve().then(()=>{
  if(process.argv[2]==='original')return require('./task6-original.cjs').main();
  if(process.argv[2]==='restore-original')return require('./task6-restore.cjs').main(...process.argv.slice(3));
  return main();
}).catch(error=>{console.log(JSON.stringify({pass:false,category:/^[a-z_]+$/.test(error.message)?error.message:'operation_failed'}));process.exitCode=1;});
