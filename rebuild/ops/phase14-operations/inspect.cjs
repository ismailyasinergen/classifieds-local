'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {command}=require('../recovery/inspect.cjs');
const {readAllowed,metadata,classify,hash}=require('../../docs/phase14/adoption/files.cjs');
const {gitRead}=require('../../docs/phase14/adoption/resume.cjs');
const {inventory}=require('../../docs/phase14/adoption/runtime.cjs');
const developer=path.resolve(__dirname,'../../..'),original='C:/Users/ismai/Desktop/classifieds_local',docs=path.join(developer,'rebuild/docs/phase15');
const manifest='f69c9d336c5baec787e2b0113d3ec77fd536c97e1ed0e3769ebb46bfda4bac58',image='sha256:23e5fe716cd2f2e73c189f035eb3df345ca155c1cd31c78bfdbd0c06839a1839';
const overlay='rebuild/compose.original-notifications.yaml',overlayHash='35afc2f08edc21d370d4000486c47b2e1607a9082d1a76cace940dd74aeb30d6';
const check=(ok,code)=>{if(!ok)throw Error(code);};
const read=(root,p)=>readAllowed(root,p,new Set([p]));
const isPrivateEnv=p=>classify(p)==='private';
const fingerprint=(root,p)=>({path:p,protection:'metadata-only',...metadata(root,p)});
function validateRelease(s){check(s?.status==='completed'&&s.originalAdoption===true&&s.originalNotificationConsumerEnabled===true&&s.image===image&&s.productManifestSha256===manifest&&s.sourcePathsEachRoot===319&&s.overlayHash===overlayHash,'release_identity_refused');return true;}
function verifySources(){
 const prefix='rebuild/docs/phase14/candidate-manifest-v4',m=JSON.parse(read(developer,prefix+'.json')),bytes=read(developer,prefix+'.sha256');
 check(hash(bytes)===manifest&&m.materializedSha256===manifest&&m.files.length===319&&new Set(m.files.map(f=>f.path)).size===319&&m.files.map(f=>f.sha256+'  '+f.path+'\n').join('')===bytes.toString(),'manifest_mismatch');
 const allow=new Set(m.files.map(f=>f.path));for(const root of [developer,original])for(const f of m.files){check((f.path.startsWith('rebuild/')||f.path==='.github/workflows/rebuild-ci.yml')&&!isPrivateEnv(f.path),'source_path_refused');check(hash(readAllowed(root,f.path,allow))===f.sha256,'source_mismatch');}
 for(const root of [developer,original])check(hash(read(root,overlay))===overlayHash,'deployment_identity_refused');
 for(const p of ['rebuild/docs/phase14/cli-adoption-report.md','rebuild/docs/phase14/adoption-state.json'])check(hash(read(developer,p))===hash(read(original,p)),'acceptance_mismatch');
 validateRelease(JSON.parse(read(developer,'rebuild/docs/phase14/adoption-state.json')));return m.files;
}
function sourceAlias(value,expected){const slash=expected.replaceAll('\\','/');const aliases=[expected,slash,slash.replaceAll('/','\\')];if(/^[Cc]:\//.test(slash))aliases.push('/run/desktop/mnt/host/c/'+slash.slice(3));return aliases.includes(value);}
function compareMounts(now,before){
 check(now.length===before.length,'mount_changed');const order=xs=>[...xs].sort((a,b)=>a.Destination.localeCompare(b.Destination));
 for(const [i,a]of order(now).entries()){const b=order(before)[i];if(a.Type==='bind'&&b.Type==='bind'){const host=b.Source.startsWith('/run/desktop/mnt/host/c/')?'C:/'+b.Source.slice('/run/desktop/mnt/host/c/'.length):b.Source;check(sourceAlias(a.Source,host),'mount_changed');assert.deepEqual({...a,Source:host},{...b,Source:host});}else assert.deepEqual(a,b);}return true;
}
function runtimeNow(){const rows=inventory(image);return rows.map(r=>({...r,portBindings:r.ports,project:r.environment==='original'?'classifieds-rebuild':'classifieds-rebuild-dev',state:'running',sourceMatches:true,volumes:r.mounts.filter(m=>m.Type==='volume').map(m=>m.Name).sort(),networkIds:Object.values(r.networks).map(n=>n.NetworkID).sort(),ports:Object.values(r.ports||{}).flatMap(p=>p||[]).map(p=>({host:p.HostIp,port:p.HostPort})).sort((a,b)=>a.port.localeCompare(b.port))}));}
function compareRuntime(current,expected){check(current.length===10&&expected.length===10,'runtime_identity_refused');for(const old of expected){const rows=current.filter(r=>r.environment===old.environment&&r.service===old.service);check(rows.length===1,'runtime_identity_refused');const r=rows[0];for(const k of ['id','image','configHash','flag'])check(r[k]===old[k],'runtime_identity_refused');compareMounts(r.mounts,old.mounts);assert.deepEqual(r.portBindings||r.ports,old.portBindings||old.ports);assert.deepEqual(Object.values(r.networks).map(n=>n.NetworkID).sort(),Object.values(old.networks).map(n=>n.NetworkID).sort());}return true;}
function gitNow(){const out={};for(const [name,root]of [['developer',developer.replaceAll('\\','/')],['original',original]]){const identity=gitRead(root,'identity').value,branch=gitRead(root,'branch').value,status=gitRead(root,'status').value;check(identity.endsWith('3c0b949bef3636ab15780a4d8bf8a7e07f41a0ba')&&branch===(name==='developer'?'':'chatgpt/manual-v360'),'git_drift');out[name]={head:identity.split('\n').at(-1),branch:branch||'HEAD',status};}return out;}
function inspectBaseline(){verifySources();const expected=JSON.parse(read(developer,'rebuild/docs/phase15/baseline.json')),accepted=JSON.parse(read(developer,'rebuild/docs/phase14/adoption/adoption-20261012-storefront-v4/final-acceptance-resume.json'));const runtime=runtimeNow();compareRuntime(runtime,accepted.checks.runtime);compareRuntime(runtime,expected.runtime);const volumes=command('docker',['volume','inspect','--format','{"name":{{json .Name}},"createdAt":{{json .CreatedAt}},"driver":{{json .Driver}},"scope":{{json .Scope}}}',...expected.volumeNames]).split(/\r?\n/).map(JSON.parse);assert.deepEqual(volumes,expected.volumes);const git=gitNow();assert.deepEqual(git,expected.git);for(const [name,root]of [['developer',developer],['original',original]])for(const f of expected.protected[name])assert.deepEqual(fingerprint(root,f.path),f);return {...expected,atUTC:new Date().toISOString(),runtime,git};}
module.exports={developer,original,docs,manifest,image,overlay,overlayHash,hash,command,read,fingerprint,isPrivateEnv,validateRelease,verifySources,sourceAlias,compareMounts,runtimeNow,compareRuntime,gitNow,inspectBaseline};
