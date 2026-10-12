'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {developer,command}=require('../inspect.cjs');
const {requireSafe}=require('../guards.cjs');
const docs=path.join(developer,'rebuild/docs/phase7'),ops=path.resolve(__dirname,'..');
const local='C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7';
requireSafe(command('docker',['ps','-aq','--filter','name=classifieds-rebuild-recovery-'])==='','owned_runtime_remaining');
const counts={keyEnvelopes:fs.readdirSync(path.join(local,'keys')).filter(n=>/^[a-f0-9]{32}\.dpapi$/.test(n)).length,
  repositoryDirectories:fs.readdirSync(path.join(local,'repositories'),{withFileTypes:true}).filter(d=>d.isDirectory()).length,
  retainedAclProbes:fs.readdirSync(local,{withFileTypes:true}).filter(d=>d.isDirectory()&&d.name.startsWith('acl-probe-')).length};
const file=path.join(docs,'release-state.json'),old=JSON.parse(fs.readFileSync(file));
const previous={...old};delete previous.previousStates;
const state={...old,status:'tasks_2_to_5_verified_original_not_started',completedStage:'reviewed',
  tasks:{...old.tasks,'2':'accepted_acl_dpapi_restic','3':'synthetic_capture_verified','4':'synthetic_restore_verified','5':'synthetic_acceptance_independent_pass','6':'not_started_original_adapter_unimplemented'},
  toolingTestsPassed:true,keyTestExecuted:true,keyTestCommandExit:0,keyTestChecks:11,blocker:null,
  tests:{nodeOperations:{tests:83,passed:83,exit:0,durationMs:1820.5405},python:{tests:17,passed:17,exit:0},django:{tests:556,passed:556,exit:0,durationSeconds:142.796},nodeProduct:{tests:9,passed:9,exit:0},syntheticRestore:{checks:66,exit:0},resticCanary:{checks:15,exit:0}},
  syntheticRestoreVerified:true,originalBackupVerified:false,originalRestoreVerified:false,keyRoundTripVerified:true,localRecoveryVerified:false,
  independentReview:'pass_tasks_3_5_synthetic_scope',originalAdapterReview:'not_implemented_not_reviewed',
  sourceRuntimePreserved:true,privateEnvByteEqualityVerified:false,offsiteVerified:false,independentKeyCustody:false,scheduledBackupsEnabled:false,liveTakeoverPerformed:false,
  ownedDockerResources:[],retainedStorage:counts,keyEnvelopes:{count:counts.keyEnvelopes,syntheticOnly:true},
  backupRepositories:[...new Set([...(old.backupRepositories||[]),'287e97aea84d8d40482f5f8eb3ab2af9','a4860d667e1eca477d457f178724f04e','76836c56abe8d4d86f4a2f24a20ba4da'])],
  negativeRepositoryCopies:[...new Set([...(old.negativeRepositoryCopies||[]),'50f71c3b050531d6427e1e8ad19e05b2'])],
  bundleIds:[...new Set([...(old.bundleIds||[]),'c956107d68de6b1d565671999cf53ba2db58e347f1f3662cfe104166c8d37c39','563c1068a0cf48e25f17c8ec829ebc994bab97d6e806b3f2415e55afef472e9f','2f98d8ac0dd25421ea31294a4cebc8cbbff3ccada80e5ec3ac24185402892db4'])],
  bundleContent:'Historical canaries plus two genuine synthetic DB/media/key/source/image bundles; no ORIGINAL data.',
  operationsManifest:'operations-manifest-acl-task5.json',nextTask:6,nextStep:'Implement and independently review the ORIGINAL read-only adapter before any real-data export; current adapter explicitly refuses non-synthetic sources.',
  previousStates:[...(old.previousStates||[]),previous],updatedAt:new Date().toISOString()};
fs.writeFileSync(file,JSON.stringify(state,null,2)+'\n');
const resumeFile=path.join(docs,'task-2-resume-state.json'),resume=JSON.parse(fs.readFileSync(resumeFile));
fs.writeFileSync(resumeFile,JSON.stringify({status:'task2_accepted',keyRoundTripVerified:true,checks:11,exit:0,
  acl:{setup:true,exactApplicationRefusal:'key_acl_refused',restored:true,removed:true},
  evidence:'task-2-report.md',continuedThroughTask:5,previousStates:[resume]},null,2)+'\n');
const rows=[];
function walk(dir) {for(const entry of fs.readdirSync(dir,{withFileTypes:true})) {
  if(entry.name==='__pycache__')continue;
  const p=path.join(dir,entry.name);requireSafe(!entry.isSymbolicLink());
  if(entry.isDirectory())walk(p);else if(entry.isFile())rows.push({path:path.relative(developer,p).replaceAll('\\','/'),sha256:crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')});
}}
walk(ops);rows.sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);
const materialized=rows.map(r=>r.sha256+'  '+r.path+'\n').join('');
const manifest={atUTC:new Date().toISOString(),files:rows,materializedSha256:crypto.createHash('sha256').update(materialized).digest('hex'),scope:'Operational code only; product273-file manifest unchanged; no keys/data included.'};
fs.writeFileSync(path.join(docs,'operations-manifest-acl-task5.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:state.status,counts,operationsFiles:rows.length,operationsManifestSha256:manifest.materializedSha256,ownedRuntimeRemaining:0}));
