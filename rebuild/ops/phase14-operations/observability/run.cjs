'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
async function main(){
 const args=process.argv.slice(2);
 if(args.length&&!(args.length===2&&args[0]==='--environment'&&['developer','original'].includes(args[1])))throw Error('input_refused');
 const digest=require('../gate.cjs').verifyAcceptance();
 const {parseArgs,collect,inspect,validateRuntime,measure,summary}=require('./core.cjs');
 const {verifySources,developer}=require('../inspect.cjs');
 const {guardDirectory}=require('../../recovery/guards.cjs');
 const environment=parseArgs(args),runId=crypto.randomBytes(12).toString('hex');
 verifySources();
 const report={runId,operationsSha256:digest,...await collect(environment)};
 report.sections.protection=await measure(()=>{verifySources();validateRuntime(inspect(environment),environment);require('../gate.cjs').verifyAcceptance();return {sourceFilesPerRoot:319,runtimeIdentityPreserved:true};});
 const dir=path.join(developer,'rebuild/docs/phase15/observations');fs.mkdirSync(dir,{recursive:true});guardDirectory(dir,developer);
 fs.writeFileSync(path.join(dir,runId+'.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
 const text=summary(report);fs.writeFileSync(path.join(dir,runId+'.md'),text,{flag:'wx'});console.log(text);
 if(Object.values(report.sections).some(s=>s.status==='unavailable'))process.exitCode=2;
}
if(require.main===module)main().catch(e=>{console.log(JSON.stringify({status:'unavailable',error:['input_refused','acceptance_unavailable'].includes(e.message)?e.message:'observation_failed'}));process.exitCode=1;});
module.exports={main};
