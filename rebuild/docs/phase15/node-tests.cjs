'use strict';
const fs=require('node:fs'),cp=require('node:child_process'),path=require('node:path');
const at=new Date(),file=path.join(__dirname,'node-tests-'+at.toISOString().replaceAll(/[:.]/g,'-')+'.json');
const args=['--test','--test-reporter=tap','rebuild/ops/phase14-operations/tests/*.test.cjs','rebuild/ops/phase14-operations/observability/tests/*.test.cjs','rebuild/ops/phase14-operations/media-audit/tests/*.test.cjs','rebuild/ops/recovery/tests/health-observer.test.cjs'];
const r=cp.spawnSync(process.execPath,args,{encoding:'utf8',windowsHide:true,timeout:120000,maxBuffer:4*1024*1024});
const count=k=>{const m=r.stdout?.match(new RegExp('^# '+k+' (\\d+)$','m'));return m?Number(m[1]):null;};
const result={startedAt:at.toISOString(),finishedAt:new Date().toISOString(),nativeExit:r.status,tests:count('tests'),passed:count('pass'),failed:count('fail'),skipped:count('skipped'),durationMs:Date.now()-at.getTime(),failureNames:(r.stdout?.match(/^not ok .*$/gm)||[]),command:[process.execPath,...args]};
fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));process.exitCode=r.status===0&&result.tests>0?0:1;
