'use strict';
// Schema only, two fresh synthetic runtimes. No repository, keys or user fixture.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const {createRuntime,stopOwnedRuntime,validateOwned}=require('../runtime.cjs'),{inspectBaseline,docs,command}=require('../inspect.cjs'),{failure,failureOutput,persist}=require('../lifecycle.cjs');
const run=crypto.randomBytes(8).toString('hex'),result={run,syntheticOnly:true,schemaOnly:true,pass:false,cleanup:[]};let primary;const handles=[];
const exec=(h,role,args,input)=>{validateOwned(h);try{return cp.execFileSync('docker',['exec','-i',h.services[role],...args],{input,timeout:120000,maxBuffer:8*1024*1024,windowsHide:true,stdio:['pipe','pipe','pipe']});}catch(e){if(args.includes('/ops/tests/schema_semantics.py'))try{const v=JSON.parse(e.stdout);result.probeFailure={category:['cast_semantics_refused','constraint_insert_probe_failed','schema_probe_failed'].includes(v.category)?v.category:'invalid_response',sqlstate:/^[A-Z0-9]{5}$/.test(v.sqlstate)?v.sqlstate:null,errorType:['ValueError','SyntaxError','ProgrammingError','TypeError','CheckViolation','NotNullViolation'].includes(v.errorType)?v.errorType:'other'};}catch{}throw Error('operation_failed');}};
const query=`import django,json;django.setup()
from django.db import connection
with connection.cursor() as c:
 c.execute("SELECT current_setting('server_version'),current_setting('search_path'),current_setting('TimeZone'),current_setting('DateStyle'),current_setting('extra_float_digits'),current_setting('standard_conforming_strings')")
 settings=c.fetchone()
 c.execute("SELECT t.relname,c.conname,c.contype,pg_get_constraintdef(c.oid),c.convalidated,c.condeferrable,c.condeferred,c.conislocal,c.coninhcount,c.connoinherit FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public' ORDER BY t.relname,c.conname")
 rows=c.fetchall()
print(json.dumps({'settings':settings,'constraints':rows}))`;
try{
 inspectBaseline();const source=createRuntime('synthetic-source');handles.push(source);const target=createRuntime('synthetic-source');handles.push(target);
 exec(source,'web',['python','-B','-c',"import django,io;django.setup();from django.core.management import call_command;call_command('migrate',interactive=False,stdout=io.StringIO(),stderr=io.StringIO())"]);
 const before=JSON.parse(exec(source,'web',['python','-B','-c',query]));
 result.supportingInsertChecks=JSON.parse(exec(source,'web',['python','-B','/ops/tests/schema_semantics.py']));
 const dump=exec(source,'db',['pg_dump','--schema-only','--format=custom','--no-owner','--no-privileges','--no-password','--lock-wait-timeout=5s','-U','recovery','-d','recovery']);
 exec(target,'db',['pg_restore','--single-transaction','--exit-on-error','--no-owner','--no-privileges','-U','recovery','-d','recovery'],dump);
 const after=JSON.parse(exec(target,'web',['python','-B','-c',query]));
 result.settings={source:before.settings,target:after.settings};result.toolVersions={dump:exec(source,'db',['pg_dump','--version']).toString().trim(),restore:exec(target,'db',['pg_restore','--version']).toString().trim()};
 result.storefront={source:before.storefrontColumns,target:after.storefrontColumns,constraints:before.constraints.filter(r=>r[0]==='accounts_storefront')};
 result.constraintCounts={source:before.constraints.length,target:after.constraints.length};result.differences=[];
 const fields=['table','name','type','definition','validated','deferrable','deferred','islocal','inhcount','noinherit'];
 for(const a of before.constraints){const b=after.constraints.find(r=>r[0]===a[0]&&r[1]===a[1]);const differences={};for(let i=0;i<fields.length;i++)if(!b||a[i]!==b[i])differences[fields[i]]={source:a[i],target:b?.[i]??null};if(Object.keys(differences).length)result.differences.push({table:a[0],name:a[1],differences});}
 result.pass=true;
}catch(e){primary=failure(e,'operation_failed');result.category=primary.message;result.resources=primary.resources;}
finally{for(const h of handles.reverse())try{const cleanup=stopOwnedRuntime(h);const ids=command('docker',['ps','-aq','--no-trunc'])+'\n'+command('docker',['network','ls','-q','--no-trunc']);if(cleanup.resources.known.some(id=>ids.split(/\r?\n/).includes(id)))throw Object.assign(Error('cleanup_blocked'),{resources:cleanup.resources});result.cleanup.push({...cleanup,metadataAbsenceVerified:true});}catch(e){primary ||= failure(e,'cleanup_blocked');result.resources=e.resources;result.pass=false;}result.persistence=persist(fs,path.join(docs,'schema-roundtrip-'+run+'.json'),result,true);if(result.persistence==='write_failed')primary ||= Error('receipt_write_failed');}
if(primary){console.log(JSON.stringify(failureOutput(Object.assign(primary,{receipt:result,resources:result.resources}))));process.exitCode=1;}else console.log(JSON.stringify(result));
