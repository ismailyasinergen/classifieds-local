/* Read-only ORIGINAL source/runtime and persistent identity check. */
const fs=require('node:fs'), path=require('node:path'), crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
function ensure(value){if(!value)throw new Error('Protection check failed');}
function read(file){return fs.readFileSync(path.join(root,file));}
function hash(value){return crypto.createHash('sha256').update(value).digest('hex');}
function run(){
  const before=JSON.parse(read('rebuild/docs/phase6/preflight-20261010.json'));
  const result=spawnSync(process.execPath,['rebuild/docs/phase5/adoption-checks.cjs','runtime'],{cwd:root,encoding:'utf8',windowsHide:true});
  ensure(result.status===0); const runtime=JSON.parse(result.stdout).runtime;
  for(const row of runtime){
    const dev=row.project==='classifieds-rebuild-dev', key=dev?'developer':'original';
    ensure(row.state==='running' && row.sourceMatches);
    if(!dev || ['db','redis'].includes(row.service)) ensure(row.id===before[key+'Containers'][row.service]);
    if(!dev && ['web','worker','scheduler'].includes(row.service)) ensure(row.image===before.originalImage);
    ensure(row.networkIds.length===1 && row.networkIds[0]===before.networkIds[key]);
    ensure(row.volumes.every(value=>before.volumeNames[key].includes(value)));
    if(row.service==='web') ensure(row.ports.length===1 && row.ports[0].host==='127.0.0.1' && row.ports[0].port===(dev?'8089':'8088'));
  }
  const definition=JSON.parse(read('rebuild/docs/phase5/task-C-candidate-manifest.json'));
  for(const part of [definition.base,...definition.overlays]) ensure(hash(read(part.path))===part.sha256);
  const map=new Map(read(definition.base.path).toString('utf8').trim().split(/\r?\n/).map(line=>[line.slice(66),line.slice(0,64)]));
  for(const overlay of definition.overlays) for(const file of JSON.parse(read(overlay.path)).files) map.set(file.path,file[overlay.fileHashField]);
  for(const [file,value] of Object.entries(definition.overrides)) map.set(file,value);
  ensure(hash([...map.keys()].sort().map(file=>map.get(file)+'  '+file+'\n').join(''))===definition.materializedSha256);
  for(const [file,value] of map) ensure(hash(fs.readFileSync(path.join('C:/Users/ismai/Desktop/classifieds_local',file)))===value);
  return {atUTC:new Date().toISOString(),pass:true,originalPaths:map.size,persistentIdsPreserved:true,originalAdoption:false,runtime};
}
module.exports={run};
if(require.main===module){try{const result=run();console.log(JSON.stringify(result));}catch{console.log('{"pass":false,"kind":"protection_check_failed"}');process.exitCode=1;}}
