'use strict';
const {mergeLifecycle,lifecycleFields}=require('../lifecycle.cjs');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict'),cp=require('node:child_process');
const {createRuntime,stopOwnedRuntime,validateOwned,inspectSource}=require('../runtime.cjs');
const {docs,inspectBaseline}=require('../inspect.cjs');
const {privateRun,captureBundle}=require('../capture.cjs');
const {prepareRepository}=require('../../recovery/repository.cjs');
const {failure,failureOutput,persist:save,mustPersist}=require('../lifecycle.cjs');
async function main(){
 require('../unresolved.cjs').assertNoUnresolved();
 inspectBaseline();const result={run:crypto.randomBytes(8).toString('hex'),pass:false,stage:'create_source',syntheticOnly:true,checks:0},file=path.join(docs,'synthetic-'+result.run+'.json');let source,primary,fileCreated=false;
 const persist=()=>mustPersist(fs,file,result);
 try{
  mustPersist(fs,file,result,true);fileCreated=true;
  source=createRuntime('synthetic-source');result.sourceRun=source.run;validateOwned(source);
  const execute=args=>{validateOwned(source);return privateRun({command:'docker',args:['exec','-i',source.services.web,...args]});};
  for(const args of [['python','-B','/ops/synthetic_fixture.py',source.run],['python','-B','/ops/synthetic_fixture.py',source.run,'augment'],['python','-B','/ops/feature_fixture.py',source.run],['python','-B','/ops/notification_fixture.py',source.run],['python','-B','/ops/storefront_fixture.py',source.run]]){result.stage=args[2]+(args[4]||'');persist();JSON.parse(execute(args));result.checks++;}
  result.stage='repository';result.repoId=crypto.randomBytes(16).toString('hex');persist();const repo=prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId:result.repoId,create:true});
  result.stage='capture';persist();Object.assign(result,await captureBundle({...source,...inspectSource(source)},repo,inspectSource,()=>{execute(['python','-B','-c',"import django; django.setup(); from accounts.models import User; User.objects.filter(email='owner@example.test').update(first_name='after-snapshot')"]);}));
  result.stage='stop_source_before_restore';const ownedSource=source;source=null;result.sourceCleanup=stopOwnedRuntime(ownedSource);mergeLifecycle(result,result.sourceCleanup,'sourceRuntime');persist();
  result.stage='separate_restore_process';persist();const r=cp.spawnSync(process.execPath,[path.join(__dirname,'synthetic-restore.cjs'),result.repoId,result.bundleId],{encoding:'utf8',windowsHide:true,timeout:900000,maxBuffer:65536});result.restoreNativeExit=r.status;
  try{result.restore=JSON.parse(r.stdout);}catch{throw Error('restore_protocol_invalid');}
  if(r.status!==0||result.restore.pass!==true){const child=result.restore;const error=failure(Error(child.category),'restore_failed',child.resources);result.childFailure=failureOutput(Object.assign(error,{receipt:child}));result.restore=result.childFailure;error.lockCleanup=result.childFailure.lockCleanup;throw error;}result.checks+=result.restore.checks;result.pass=true;result.stage='complete';
 }catch(e){primary=failure(e,'capture_failed');mergeLifecycle(result,primary);result.category=primary.message;result.resources=primary.resources;result.pass=false;}
 finally{if(source)try{result.sourceCleanup=stopOwnedRuntime(source);result.resources=result.sourceCleanup.resources;mergeLifecycle(result,result.sourceCleanup,'sourceRuntime');}catch(e){result.cleanup='cleanup_blocked';result.resources=e.resources||result.resources;mergeLifecycle(result,e,'sourceRuntime');primary ||= failure(e,'cleanup_blocked');result.pass=false;}result.finishedAt=new Date().toISOString();result.persistence='written';result.persistence=fileCreated?save(fs,file,result):'write_failed';if(result.persistence==='write_failed'){primary ||= Error('receipt_write_failed');result.pass=false;}}
 if(primary)throw Object.assign(primary,{resources:result.resources,receipt:result,...lifecycleFields(result)});console.log(JSON.stringify(result));return result;
}
if(require.main===module)main().catch(e=>{console.log(JSON.stringify(failureOutput(e)));process.exitCode=1;});
module.exports={main};
