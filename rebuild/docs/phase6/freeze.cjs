/* Compose the approved MFA baseline with current explicitly scoped source. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../../..');
const hash=data=>crypto.createHash('sha256').update(data).digest('hex');
const read=file=>fs.readFileSync(path.join(root,file));
function ensure(value){if(!value)throw new Error('Source freeze verification failed');}
function baseline(){
  const definition=JSON.parse(read('rebuild/docs/phase5/task-C-candidate-manifest.json'));
  for(const part of [definition.base,...definition.overlays]) ensure(hash(read(part.path))===part.sha256);
  const map=new Map(read(definition.base.path).toString('utf8').trim().split(/\r?\n/).map(line=>[line.slice(66),line.slice(0,64)]));
  for(const overlay of definition.overlays) for(const file of JSON.parse(read(overlay.path)).files) map.set(file.path,file[overlay.fileHashField]);
  for(const [file,value] of Object.entries(definition.overrides)) map.set(file,value);
  ensure(hash(materialize(map))===definition.materializedSha256);
  return {map,definition};
}
function materialize(map){return [...map.keys()].sort().map(file=>map.get(file)+'  '+file+'\n').join('');}
function freeze(){
  ensure(root.toLowerCase().replace(/\\/g,'/')==='c:/users/ismai/.devspace/worktrees/classifieds_local-a7be577c');
  const {map:before,definition}=baseline(); const files=new Set(before.keys());
  function visit(relative){for(const entry of fs.readdirSync(path.join(root,relative),{withFileTypes:true})){
    if(entry.name==='__pycache__')continue;
    const file=relative+'/'+entry.name;
    if(entry.isDirectory())visit(file);
    else if(/\.(py|html|css|js|txt|json)$/.test(entry.name))files.add(file);
  }}
  visit('rebuild/backend');
  for(const file of ['rebuild/browser-tests/reports-appeals.cjs','rebuild/browser-tests/reports-appeals.test.cjs',
    'rebuild/docs/REPORTS_APPEALS_VERIFICATION.md','rebuild/README.md','rebuild/compose.yaml',
    'rebuild/docs/phase6/freeze.cjs','rebuild/docs/phase6/protection-check.cjs','rebuild/docs/phase6/verify-candidate.cjs'])files.add(file);
  const current=new Map([...files].map(file=>[file,hash(read(file))]));
  const text=materialize(current);
  const entries=[...current.keys()].sort().map(file=>({path:file,beforeSha256:before.get(file)||null,sha256:current.get(file),
    change:!before.has(file)?'added':before.get(file)===current.get(file)?'unchanged':'modified'}));
  const result={format:'classifieds-phase6-complete-sha256-v1',atUTC:new Date().toISOString(),
    baseline:definition.materializedSha256,materializedSha256:hash(text),sourcePaths:entries.length,
    backendPaths:entries.filter(row=>row.path.startsWith('rebuild/backend/')).length,
    added:entries.filter(row=>row.change==='added').length,modified:entries.filter(row=>row.change==='modified').length,
    originalAdoption:false,files:entries};
  fs.writeFileSync(path.join(__dirname,'candidate-manifest.sha256'),text);
  fs.writeFileSync(path.join(__dirname,'candidate-manifest.json'),JSON.stringify(result,null,2)+'\n');
  ensure(hash(read('rebuild/docs/phase6/candidate-manifest.sha256'))===result.materializedSha256);
  console.log(JSON.stringify({sourcePaths:result.sourcePaths,backendPaths:result.backendPaths,added:result.added,modified:result.modified,sha256:result.materializedSha256}));
}
module.exports={baseline,materialize};
if(require.main===module)freeze();
