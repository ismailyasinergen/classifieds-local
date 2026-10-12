'use strict';
const fs=require('node:fs'),path=require('node:path');
const p=require('../../ops/phase14-operations/inspect.cjs');
function main(){
 const files=p.verifySources(),acceptance=JSON.parse(p.read(p.developer,'rebuild/docs/phase14/adoption/adoption-20261012-storefront-v4/final-acceptance-resume.json'));
 const previous=JSON.parse(p.read(p.developer,'rebuild/docs/phase14/adoption/adoption-20261012-storefront-v4/baseline.json'));
 const runtime=p.runtimeNow();p.compareRuntime(runtime,acceptance.checks.runtime);
 const volumeNames=[...new Set(runtime.flatMap(r=>r.volumes))].sort();
 const volumes=p.command('docker',['volume','inspect','--format','{"name":{{json .Name}},"createdAt":{{json .CreatedAt}},"driver":{{json .Driver}},"scope":{{json .Scope}}}',...volumeNames]).split(/\r?\n/).map(JSON.parse);
 const protectedFiles={};for(const [name,root]of [['developer',p.developer],['original',p.original]])protectedFiles[name]=previous.protectedMetadata[name].map(f=>p.fingerprint(root,f.path));
 const result={atUTC:new Date().toISOString(),manifest:p.manifest,image:p.image,sourcePaths:files.length,overlayHash:p.overlayHash,runtime,containerIds:runtime.map(r=>r.id),networkIds:[...new Set(runtime.flatMap(r=>r.networkIds))].sort(),volumeNames,volumes,git:p.gitNow(),protected:protectedFiles,privateEnvByteEqualityVerified:false};
 fs.writeFileSync(path.join(p.docs,'baseline.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({pass:true,sourcesEachRoot:files.length,containers:runtime.length,protectedPaths:Object.values(protectedFiles).reduce((n,a)=>n+a.length,0),privateEnvByteEqualityVerified:false}));
}
try{main();}catch{console.error(JSON.stringify({pass:false,category:'baseline_unavailable'}));process.exitCode=1;}
