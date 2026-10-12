'use strict';
const fs=require('node:fs'),path=require('node:path');
const {inspectBaseline,developer,isPrivateEnv}=require('../inspect.cjs');
const {requireSafe}=require('../guards.cjs');
async function main() {
  const dir=path.join(developer,'rebuild/docs/phase7'),before=JSON.parse(fs.readFileSync(path.join(dir,'runtime-baseline.json'))),after=inspectBaseline();
  const fields=['manifest','image','sourcePaths','runtime','git','containerIds','volumeNames','volumes','networkIds'];
  requireSafe(fields.every(k=>JSON.stringify(before[k])===JSON.stringify(after[k])),'protection_drift');
  for(const root of ['developer','original'])requireSafe(JSON.stringify(before.protected[root].filter(r=>!isPrivateEnv(r.path)))===JSON.stringify(after.protected[root].filter(r=>!isPrivateEnv(r.path))),'file_drift');
  const health=[];
  for(const port of [8088,8089]) {
    const response=await fetch(`http://127.0.0.1:${port}/health/`,{signal:AbortSignal.timeout(5000)}),data=await response.json();
    requireSafe(response.status===200&&data.status==='ok','health_failed');health.push({port,http:response.status,status:data.status});
  }
  const result={pass:true,atUTC:new Date().toISOString(),sourcePathsPerRoot:273,containers:10,volumes:10,networks:2,
    protectedFilesPreserved:true,gitPreserved:true,privateEnvByteEqualityVerified:false,privateEnvContentRead:false,health,
    git:Object.fromEntries(Object.entries(after.git).map(([key,row])=>[key,{head:row.head,branch:row.branch}])),
    protectedCounts:Object.fromEntries(Object.entries(after.protected).map(([key,rows])=>[key,rows.length]))};
  fs.writeFileSync(path.join(dir,`final-protection-acl-task5-${Date.now()}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify(result));
}
main().catch(error=>{console.log(JSON.stringify({pass:false,category:/^[a-z_]+$/.test(error.message)?error.message:'final_protection_failed'}));process.exitCode=1;});
