'use strict';
const {sourceAlias}=require('../inspect.cjs');
const path=require('node:path');
const counts=['scannedAssets','scannedFiles','missingOriginals','missingReadyDerivatives','emptyReadyDerivatives','originalSizeMismatches','unlinkedButRetainedAssets','unreferencedCandidates','temporaryOrInflight','unreadableOrUnstable','unexpectedEntries','multiRevisionAssets','evidenceRetainedAssets','observedFileBytes'];
function requireSafe(ok,category){if(!ok)throw Error(category);}
function environment(args){if(args.length===0)return 'developer';requireSafe(args.length===2&&args[0]==='--environment'&&['developer','original'].includes(args[1]),'input_refused');return args[1];}
const normalize=s=>s.replaceAll('\\','/').toLowerCase().replace('/run/desktop/mnt/host/c/','c:/').replace('/host_mnt/c/','c:/');
function guardReader(m,r){
 requireSafe(['developer','original'].includes(r.environment)&&/^[a-f0-9]{24}$/.test(r.run)&&/^[a-f0-9]{64}$/.test(r.id)&&m.id===r.id&&m.image===r.image&&m.run===r.run&&m.user==='0:0'&&m.network==='none'&&m.readonly===true&&m.privileged===false&&!(m.capAdd||[]).length&&JSON.stringify(m.capDrop)==='["ALL"]'&&JSON.stringify(m.security)==='["no-new-privileges"]'&&m.pid===''&&m.userns===''&&m.ipc==='private'&&!Object.keys(m.ports||{}).length&&m.mounts?.length===2&&
 m.mounts.filter(x=>x.Type==='volume'&&x.Name===r.volume&&x.Destination==='/media'&&!x.RW).length===1&&m.mounts.filter(x=>x.Type==='bind'&&x.Destination==='/ops'&&!x.RW&&sourceAlias(x.Source,__dirname)).length===1,'identity_mismatch');return true;
}
const reasonCounts=['canonicalDerivativeReferences','fixtureDerivativeReferences','invalidOriginalReferences','invalidDerivativeReferences','unknownFilesystemEntries','unsafeFilesystemObjects','accessDenied','ioErrors','unstableFilesystemEntries','unmeasuredDerivativeReferences'];
function directoryOutput(data){requireSafe(data&&[ ['root','originals','derivatives'].sort().join(), ['root','originals','derivatives','searchFixtures'].sort().join() ].includes(Object.keys(data).sort().join())&&Object.values(data).every(v=>['present','absent','unreadable','unsafe','unstable'].includes(v))&&data.root!=='absent','invalid_response');return data;}
function output(data,environment='original'){
 requireSafe(data?.fixtureLayoutEnabled===(environment==='developer')&&['developer','original'].includes(environment),'invalid_response');
 requireSafe(('searchFixtures' in data.directories)===(environment==='developer'),'invalid_response');
 requireSafe(data.reasons&&Object.keys(data.reasons).sort().join()===[...reasonCounts].sort().join()&&reasonCounts.every(k=>Number.isSafeInteger(data.reasons[k])&&data.reasons[k]>=0),'invalid_response');
 directoryOutput(data?.directories);
 requireSafe(data.observationComplete!==true||Object.values(data.directories).every(v=>['present','absent'].includes(v)),'invalid_response');
 requireSafe(data&&JSON.stringify(Object.keys(data).sort())===JSON.stringify([...counts,'reasons','fixtureLayoutEnabled','directories','observationComplete','findingsPresent','deletionAuthorized','candidateMeaning'].sort())&&typeof data.observationComplete==='boolean'&&typeof data.findingsPresent==='boolean'&&data.deletionAuthorized===false&&data.candidateMeaning==='unreferenced_at_observation'&&counts.every(k=>Number.isSafeInteger(data[k])&&data[k]>=0||data.observationComplete===false&&data[k]===null&&['missingOriginals','missingReadyDerivatives','originalSizeMismatches','unreferencedCandidates'].includes(k)),'invalid_response');return data;
}
const errors=['input_refused','acceptance_unavailable','identity_mismatch','source_mismatch','limit_exceeded','timeout','access_denied','query_failed','unsafe_entry','unstable','invalid_response','command_failed','reader_preflight_refused','cleanup_blocked'];
function category(error){return errors.includes(error?.message)?error.message:'command_failed';}
module.exports={environment,guardReader,output,counts,requireSafe,normalize,category,errors,directoryOutput,reasonCounts};
