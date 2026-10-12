'use strict';
const fs=require('node:fs'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {validateOwned}=require('../runtime.cjs');
const {requireSafe}=require('../guards.cjs');
try {
  const run=process.argv[2];requireSafe(/^[a-f0-9]{16}$/.test(run));
  const dir=path.resolve(__dirname,'../../../docs/phase7');
  const target=JSON.parse(fs.readFileSync(path.join(dir,`runtime-${run}.json`)));
  validateOwned(target);requireSafe(target.role==='synthetic-target');
  const r=spawnSync('docker',['exec',target.services.web,'python','/ops/verify_restore.py',run],{windowsHide:true,encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:60000,maxBuffer:32768});
  const result={...JSON.parse(r.stdout),exit:r.status,run};
  fs.writeFileSync(path.join(dir,`verify-${run}-${Date.now()}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify(result));process.exitCode=r.status;
} catch {console.log('{"pass":false,"category":"verification_process_failed"}');process.exitCode=1;}
