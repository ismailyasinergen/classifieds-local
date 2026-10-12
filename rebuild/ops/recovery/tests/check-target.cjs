'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const {validateOwned}=require('../runtime.cjs');
const run='bce537aa8fbeac06',dir=path.resolve(__dirname,'../../../docs/phase7');
const target=JSON.parse(fs.readFileSync(path.join(dir,`runtime-${run}.json`)));
validateOwned(target);
const results=[];
for(const args of [['-m','pip','check'],['manage.py','check'],['manage.py','makemigrations','--check','--dry-run'],['manage.py','migrate','--check']]) {
  validateOwned(target);
  const result=spawnSync('docker',['exec',target.services.web,'python',...args],{windowsHide:true,stdio:['ignore','pipe','pipe'],timeout:60000,maxBuffer:32768});
  results.push({check:args.join(' '),exit:result.status});
  if(result.status!==0)break;
}
const result={run,pass:results.length===4&&results.every(r=>r.exit===0),results};
fs.writeFileSync(path.join(dir,`target-checks-${run}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(result));process.exitCode=result.pass?0:1;
