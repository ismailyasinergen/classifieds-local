'use strict';
// Fault injection only after a real, new, non-running helper create; no live source process.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const profile=require('../inspect.cjs'),life=require('../lifecycle.cjs'),root=path.resolve(__dirname,'..');
const run=crypto.randomBytes(8).toString('hex'),result={run,syntheticOnly:true,pass:false,checks:0,cases:[]};
try{
 for(const role of ['archive','dns']){
  let createdId;const module={exports:{}};
  const command=(cmd,args)=>{const value=profile.command(cmd,args);if(cmd==='docker'&&args[0]==='create'){createdId=value;throw Error('command_failed');}return value;};
  vm.runInNewContext(fs.readFileSync(path.join(root,'owned-helper.cjs'),'utf8'),{module,Buffer,process,structuredClone,__dirname:root,require:n=>n==='./inspect.cjs'?{...profile,command}:require(n.startsWith('.')?path.resolve(root,n):n)});
  let e;try{module.exports.createHelper(role,run);}catch(x){e=x;}
  if(e?.message!=='command_failed'||e.resourceGroups?.[role]?.status!=='removed'||e.resourceGroups[role].unknown||e.resourceGroups[role].removed[0]!==createdId)throw e||Error('operation_failed');result.checks+=4;
  if(profile.command('docker',['ps','-aq','--no-trunc']).split(/\r?\n/).includes(createdId))throw Error('cleanup_blocked');result.checks++;
  result.cases.push({role,expectedPrimary:e.message,...life.lifecycleFields(e),exactMetadataAbsenceVerified:true});
 }result.pass=true;
}catch(e){result.category=life.failure(e,'operation_failed').message;life.mergeLifecycle(result,e);process.exitCode=1;}
result.persistence=life.persist(fs,path.join(profile.docs,'v2-discovery-integration-'+run+'.json'),result,true);if(result.persistence!=='written')process.exitCode=1;console.log(JSON.stringify(result));
