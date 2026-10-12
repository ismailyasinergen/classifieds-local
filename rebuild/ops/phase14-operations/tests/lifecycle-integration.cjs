'use strict';
// Fault injection exists only in this synthetic runner. Production constructors are executed unchanged.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),cp=require('node:child_process'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),profile=require('../inspect.cjs'),run=crypto.randomBytes(8).toString('hex');
const result={run,syntheticOnly:true,pass:false,checks:0,cases:[]};
const docker=a=>profile.command('docker',a);
function api(mode){
 const real={...cp,execFileSync(command,args,options){
  if(command==='docker'&&args[0]==='compose'){
   if(mode==='network-only'){
    const e=options.env,project=args[args.indexOf('-p')+1];
    docker(['network','create','--internal','--label',`com.docker.compose.project=${project}`,'--label','com.docker.compose.network=default','--label',`phase15.run=${e.RECOVERY_RUN}`,'--label',`phase15.role=${e.RECOVERY_ROLE}`,'--label',`phase15.attempt=${e.RECOVERY_ATTEMPT}`,project+'_default']);
   }else cp.execFileSync(command,mode==='partial-db'?args.concat('db'):args,options);
   if(mode!=='cleanup-receipt')throw Error('synthetic_start_failure');
   return Buffer.alloc(0);
  }return cp.execFileSync(command,args,options);
 }};
 const mockFs={...fs,writeFileSync(file,...args){if(mode==='cleanup-receipt'&&path.basename(file).startsWith('cleanup-'))throw Error('synthetic_receipt_failure');return fs.writeFileSync(file,...args);}};
 const module={exports:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'runtime.cjs'),'utf8'),{require:n=>n==='node:child_process'?real:n==='node:fs'?mockFs:require(n.startsWith('.')?path.resolve(root,n):n),module,__dirname:root,process,Buffer});return module.exports;
}
try{
 profile.inspectBaseline();
 for(const mode of ['network-only','partial-db','cleanup-receipt']){
  const runtime=api(mode);let error;
  try{const target=runtime.createRuntime('synthetic-target');runtime.stopOwnedRuntime(target);}catch(e){error=e;}
  assert(error?.resources);assert.equal(error.message,mode==='cleanup-receipt'?'receipt_write_failed':'runtime_start_failed');result.checks+=2;
  const resources=error.resources;assert.equal(resources.retained.length,0);assert.equal(resources.status,'removed');result.checks+=2;
  const containers=docker(['ps','-aq','--no-trunc']).split(/\r?\n/),networks=docker(['network','ls','-q','--no-trunc']).split(/\r?\n/);
  for(const id of resources.known){assert(!containers.includes(id)&&!networks.includes(id));result.checks++;}
  result.cases.push({mode,category:error.message,resources,metadataAbsenceVerified:true});
 }
 profile.inspectBaseline();result.pass=true;
}catch(error){result.category='lifecycle_integration_failed';if(error.resources)result.resources=error.resources;process.exitCode=1;}
fs.writeFileSync(path.join(profile.docs,`lifecycle-integration-${run}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
