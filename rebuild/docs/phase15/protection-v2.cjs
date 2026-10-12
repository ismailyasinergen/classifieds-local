'use strict';
const fs=require('node:fs'),path=require('node:path'),p=require('../../ops/phase14-operations/inspect.cjs');
const startedAt=new Date().toISOString();
try{
 const b=p.inspectBaseline(),containers=p.command('docker',['ps','-aq','--no-trunc']).split(/\r?\n/),networks=p.command('docker',['network','ls','-q','--no-trunc']).split(/\r?\n/);
 const old=JSON.parse(p.read(p.developer,'rebuild/docs/phase13/operations-manifest-v2-r2.json'));
 for(const f of [...old.files,...old.dependencies])if(p.hash(p.read(p.developer,f.path))!==f.sha256)throw Error('historical_source_changed');
 const ids=new Set();for(const name of fs.readdirSync(p.docs).filter(n=>/^runtime-[a-f0-9]{16}\.json$/.test(n))){const r=JSON.parse(p.read(p.developer,'rebuild/docs/phase15/'+name));for(const id of [...Object.values(r.services||{}),r.networkId].filter(Boolean))ids.add(id);}
 for(const name of fs.readdirSync(p.docs).filter(n=>/^db-integration-[a-f0-9]{16}\.json$/.test(n))){const r=JSON.parse(p.read(p.developer,'rebuild/docs/phase15/'+name));for(const c of r.cleanup||[])ids.add(c.id);}
 for(const name of fs.readdirSync(p.docs).filter(n=>/^image-[a-f0-9]{16}\.json$/.test(n))){const r=JSON.parse(p.read(p.developer,'rebuild/docs/phase15/'+name));if(r.id)ids.add(r.id);}
 for(const name of fs.readdirSync(p.docs).filter(n=>/^helper-[a-f0-9]{32}\.json$/.test(n))){const r=JSON.parse(p.read(p.developer,'rebuild/docs/phase15/'+name));for(const id of r.resources?.known||[])ids.add(id);if(r.resources?.unknown||r.resources?.retained?.length||r.phase!=='closed')throw Error('helper_unresolved');}
 for(const id of ids)if(containers.includes(id)||networks.includes(id))throw Error('temporary_retained');
 if(fs.readdirSync(p.docs).some(n=>n.endsWith('.lock')))throw Error('lock_retained');
 const result={pass:true,startedAt,finishedAt:new Date().toISOString(),sourcesEachRoot:319,overlayHash:p.overlayHash,runtimeContainers:b.runtime.length,protectedPaths:Object.values(b.protected).reduce((n,r)=>n+r.length,0),historicalBoundFiles:old.files.length+old.dependencies.length,temporaryExactIdsAbsent:ids.size,gitPreserved:true,privateEnvByteEqualityVerified:false};
 fs.writeFileSync(path.join(p.docs,'protection-v2-'+Date.now()+'.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
}catch{console.log(JSON.stringify({pass:false,category:'protection_unavailable'}));process.exitCode=1;}
