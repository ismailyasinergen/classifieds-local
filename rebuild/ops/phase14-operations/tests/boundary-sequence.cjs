'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const {createRuntime,stopOwnedRuntime,validateOwned}=require('../runtime.cjs'),{docs,inspectBaseline}=require('../inspect.cjs'),{failure,failureOutput,persist}=require('../lifecycle.cjs');
const result={run:crypto.randomBytes(8).toString('hex'),pass:false,syntheticOnly:true};let target,primary;
try{inspectBaseline();target=createRuntime('synthetic-source');validateOwned(target);
 const code=`import django,io,json;django.setup()
from django.core.management import call_command
from django.db import connection,transaction
from events.boundaries import next_publication_boundary
call_command('migrate',interactive=False,stdout=io.StringIO(),stderr=io.StringIO())
with transaction.atomic():
 first=next_publication_boundary()
with connection.cursor() as c:
 c.execute('SELECT last_value,is_called FROM events_publicationboundary_id_seq');before=c.fetchone()
with transaction.atomic():
 second=next_publication_boundary()
with connection.cursor() as c:
 c.execute('SELECT last_value,is_called FROM events_publicationboundary_id_seq');after=c.fetchone()
 c.execute('SELECT count(*),min(id),max(id),max(value) FROM events_publicationboundary');row=c.fetchone()
print(json.dumps({'first':first,'second':second,'idSequenceBefore':before,'idSequenceAfter':after,'rowAggregate':row,'legacyNextSequenceCheck':after[0]+int(after[1])>row[2]}))`;
 result.measurement=JSON.parse(cp.execFileSync('docker',['exec',target.services.web,'python','-B','-c',code],{encoding:'utf8',timeout:120000,maxBuffer:65536,windowsHide:true,stdio:['ignore','pipe','pipe']}));result.pass=true;
}catch(e){primary=failure(e,'operation_failed');result.category=primary.message;result.resources=primary.resources;}
finally{if(target)try{result.cleanup=stopOwnedRuntime(target);}catch(e){primary ||= failure(e,'cleanup_blocked');result.resources=e.resources;result.pass=false;}result.persistence=persist(fs,path.join(docs,'boundary-sequence-'+result.run+'.json'),result,true);if(result.persistence!=='written')primary ||= Error('receipt_write_failed');}
console.log(JSON.stringify(primary?failureOutput(Object.assign(primary,{receipt:result,resources:result.resources})):result));if(primary)process.exitCode=1;
