'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {createRuntime,metadata,stopOwnedRuntime,validateOwned}=require('../runtime.cjs');
const {memoryCommand}=require('../original-source.cjs');
const {startSnapshotCommand,privateRun}=require('../capture.cjs');
const {hash,developer}=require('../inspect.cjs');
const {runBinaryPipeline}=require('../safe-process.cjs');
async function main() {
 const source=createRuntime('synthetic-source'),result={run:source.run,checks:0,pass:false,scope:'new_task6_transport_synthetic_only'};
 let snapshot;
 const spec=args=>({command:'docker',args:['exec','-i',source.services.web,...args]});
 try {
  validateOwned(source);
  privateRun(spec(['python','/ops/synthetic_fixture.py',source.run]));result.checks++;
  const dbIp=Object.values(metadata(source.services.db).networks)[0].IPAddress,context={dbIp,dbBinding:hash(Buffer.from('recovery\nrecovery'))};
  assert.throws(()=>privateRun(memoryCommand(source.services.web,'keys',{...context,dbBinding:'0'.repeat(64)})),/^Error: capture_process_failed$/);result.checks++;
  assert.throws(()=>privateRun(memoryCommand(source.services.web,'keys',{...context,dbIp:'192.0.2.1'})),/^Error: capture_process_failed$/);result.checks++;
  const originalKeys=privateRun(spec(['python','/ops/source_export.py','keys'])),transported=privateRun(memoryCommand(source.services.web,'keys',context));
  assert.deepEqual(transported,originalKeys);result.checks++;const keySha=hash(transported);transported.fill(0);originalKeys.fill(0);
  snapshot=await startSnapshotCommand(memoryCommand(source.services.web,'snapshot',context));
  assert.equal(snapshot.catalog.keySha256,keySha);assert.equal(Object.keys(snapshot.catalog.tables).length,36);assert.equal(snapshot.catalog.assets.length,2);result.checks+=3;
  const dump={command:'docker',args:['exec','-e','PGOPTIONS=-c default_transaction_read_only=on',source.services.db,'sh','-c',
    'export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump --format=custom --no-owner --no-privileges --no-password --snapshot="$1" -U "$POSTGRES_USER" -d "$POSTGRES_DB"','phase7',snapshot.catalog.snapshot]};
  result.dump=await runBinaryPipeline(dump,{command:process.execPath,args:['-e','process.stdin.resume();']},{maxBytes:512*1024*1024,timeoutMs:300000});result.checks++;
  assert(snapshot.isAlive());await snapshot.close();snapshot=null;result.checks++;
  await assert.rejects(runBinaryPipeline(dump,{command:process.execPath,args:['-e','process.stdin.resume();']},{maxBytes:512*1024*1024,timeoutMs:300000}),/^Error: pipeline_failed$/);result.checks++;
  result.pass=true;
 } catch(error){result.category=/^[a-z_]+$/.test(error.message)?error.message:'synthetic_transport_assertion_failed';process.exitCode=1;}
 finally {snapshot?.abort();try{result.cleanup=stopOwnedRuntime(source);}catch{result.cleanup={status:'cleanup_blocked'};result.pass=false;process.exitCode=1;}}
 result.exit=process.exitCode||0;fs.writeFileSync(path.join(developer,'rebuild/docs/phase7',`task6-synthetic-${source.run}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
}
main().catch(()=>{console.log('{"pass":false,"category":"synthetic_transport_setup_failed"}');process.exitCode=1;});
