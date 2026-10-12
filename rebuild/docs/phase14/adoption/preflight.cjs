'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const {readAllowed,hash,metadata}=require('./files.cjs');
const {gitRead,classifyState}=require('./resume.cjs');
const DEV='C:/Users/ismai/.devspace/worktrees/classifieds_local-a7be577c',ORIGINAL='C:/Users/ismai/Desktop/classifieds_local';
const MANIFEST='f69c9d336c5baec787e2b0113d3ec77fd536c97e1ed0e3769ebb46bfda4bac58',IMAGE='sha256:23e5fe716cd2f2e73c189f035eb3df345ca155c1cd31c78bfdbd0c06839a1839',OLD='sha256:f6525485baa46917fa3693be96090771ec5a341611ffd873a8887cdccef5365e';
const overlay='rebuild/compose.original-notifications.yaml',overlayHash='35afc2f08edc21d370d4000486c47b2e1607a9082d1a76cace940dd74aeb30d6';
function json(p){return JSON.parse(readAllowed(DEV,p,new Set([p])));}
function verify(){
 if(path.resolve(process.cwd()).toLowerCase()!==path.resolve(DEV).toLowerCase())throw Error('root_refused');
 const statePath='rebuild/docs/phase14/adoption-state.json',reportPath='rebuild/docs/phase14/cli-adoption-report.md';
 const active=[DEV,ORIGINAL].some(root=>metadata(root,'rebuild/docs/phase14/adoption.lock').state!=='absent');
 if(metadata(DEV,'rebuild/docs/phase14/adoption/adoption-20261012-storefront-v4/execution.jsonl').state==='present'&&metadata(DEV,statePath).state==='absent')throw Error('partial_state_requires_journal_resume');
 const states=[DEV,ORIGINAL].map(root=>metadata(root,statePath).state==='absent'?null:JSON.parse(readAllowed(root,statePath,new Set([statePath]))));
 if(JSON.stringify(states[0])!==JSON.stringify(states[1]))throw Error('state_refused');
 const continuation=classifyState({preparation:json('rebuild/docs/phase14/adoption/preparation-results.json'),state:states[0],reportPresent:metadata(DEV,reportPath).state==='present',active});
 const m=json('rebuild/docs/phase14/candidate-manifest-v4.json'),old=json('rebuild/docs/phase12/candidate-manifest-v2.json'),allow=new Set(m.files.map(f=>f.path));
 const flat=m.files.map(f=>f.sha256+'  '+f.path+'\n').join('');if(hash(flat)!==MANIFEST||allow.size!==319||m.files.length!==319)throw Error('manifest_refused');
 if(hash(readAllowed(DEV,'rebuild/docs/phase14/candidate-manifest-v4.sha256',new Set(['rebuild/docs/phase14/candidate-manifest-v4.sha256'])))!==MANIFEST)throw Error('flat_manifest_refused');
 const oldMap=new Map(old.files.map(f=>[f.path,f.sha256]));let added=0,modified=0,same=0;
 for(const f of m.files){if(hash(readAllowed(DEV,f.path,allow))!==f.sha256)throw Error('developer_source_mismatch');if((oldMap.get(f.path)||null)!==f.beforeSha256)throw Error('before_manifest_mismatch');const actual=metadata(ORIGINAL,f.path).state==='absent'?null:hash(readAllowed(ORIGINAL,f.path,allow));if(actual!==(continuation==='verify_completed'?f.sha256:f.beforeSha256))throw Error('original_source_mismatch');if(!f.beforeSha256)added++;else if(f.beforeSha256!==f.sha256)modified++;else same++;}
 for(const root of [DEV,ORIGINAL])if(hash(readAllowed(root,overlay,new Set([overlay])))!==overlayHash)throw Error('overlay_mismatch');
 const t=json('rebuild/docs/phase14/tests-v4.json');for(const e of t.evidence)if(hash(readAllowed(DEV,e.path,new Set([e.path])))!==e.sha256)throw Error('evidence_mismatch');
 const git=[DEV,ORIGINAL].map(root=>{const identity=gitRead(root,'identity'),branch=gitRead(root,'branch'),status=gitRead(root,'status');const [top,head]=identity.value.split(/\r?\n/);if(top!==root)throw Error('git_root_mismatch');return {root,head,branch:branch.value,status:status.value,nativeExits:[identity.nativeExit,branch.nativeExit,status.nativeExit]};});
 if(git.some(g=>g.head!=='3c0b949bef3636ab15780a4d8bf8a7e07f41a0ba')||git[0].branch!==''||git[1].branch!=='chatgpt/manual-v360')throw Error('git_identity_refused');
 return {atUTC:new Date().toISOString(),continuation,developerSources:319,originalSources:continuation==='verify_completed'?319:309,added,modified,same,manifest:MANIFEST,image:IMAGE,overlayHash,evidenceHashesVerified:t.evidence.length,git,privateEnvByteEqualityVerified:false};
}
if(require.main===module){try{const r=verify();console.log(JSON.stringify({...r,git:r.git.map(g=>({...g,statusEntries:g.status.split('\n').length,status:undefined}))}));}catch(e){console.log(JSON.stringify({error:e.message,detail:e.detail}));process.exitCode=1;}}
module.exports={verify,json,DEV,ORIGINAL,MANIFEST,IMAGE,OLD,overlay,overlayHash};
