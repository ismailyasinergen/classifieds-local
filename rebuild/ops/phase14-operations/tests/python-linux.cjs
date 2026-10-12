'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const {createRuntime,stopOwnedRuntime,validateOwned}=require('../runtime.cjs'),{docs,inspectBaseline}=require('../inspect.cjs'),{failure,failureOutput,persist}=require('../lifecycle.cjs');
const result={run:crypto.randomBytes(8).toString('hex'),pass:false,syntheticOnly:true};let target,primary;
try{inspectBaseline();target=createRuntime('synthetic-source');validateOwned(target);
 const r=cp.spawnSync('docker',['exec','-e','PYTHONPATH=/ops:/ops/tests',target.services.web,'python','-B','-m','unittest','discover','-s','/ops/tests','-p','test_*.py'],{encoding:'utf8',timeout:120000,maxBuffer:65536,windowsHide:true});
 result.failures=[...String(r.stderr).matchAll(/^(?:FAIL|ERROR): ([a-zA-Z0-9_]+) \(([a-zA-Z0-9_.]+)\)/gm)].map(m=>({test:m[1],class:m[2]}));result.failureTypes=[...new Set([...String(r.stderr).matchAll(/^(AssertionError|ValueError|TypeError|AttributeError|PermissionError|FileNotFoundError|ImportError|ModuleNotFoundError|OSError):/gm)].map(m=>m[1]))];
 result.nativeExit=r.status;const match=String(r.stderr).match(/Ran (\d+) tests/);result.tests=match?Number(match[1]):null;result.pass=r.status===0&&result.tests>0;if(!result.pass)throw Error('operation_failed');
}catch(e){primary=failure(e,'operation_failed');result.category=primary.message;result.resources=primary.resources;}
finally{if(target)try{result.cleanup=stopOwnedRuntime(target);}catch(e){primary ||= failure(e,'cleanup_blocked');result.resources=e.resources;result.pass=false;}result.persistence=persist(fs,path.join(docs,'python-linux-'+result.run+'.json'),result,true);if(result.persistence!=='written')primary ||= Error('receipt_write_failed');}
console.log(JSON.stringify(primary?failureOutput(Object.assign(primary,{receipt:result,resources:result.resources})):result));if(primary)process.exitCode=1;
