/* Ephemeral read-only image probe: no bind, network, Django import or secrets. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'../../..');
const tag='classifieds-rebuild-dev-reports-appeals-candidate:phase6-final';
function ensure(value){if(!value)throw new Error('Candidate image verification failed');}
function docker(args){const result=spawnSync('docker',args,{cwd:root,encoding:'utf8',windowsHide:true,timeout:60000,maxBuffer:4*1024*1024});ensure(result.status===0&&!result.error);return result.stdout.trim();}
try{
  const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'candidate-manifest.json')));
  const material=fs.readFileSync(path.join(__dirname,'candidate-manifest.sha256'));
  ensure(crypto.createHash('sha256').update(material).digest('hex')===manifest.materializedSha256);
  const id=docker(['image','inspect','--format','{{.Id}}',tag]);
  const code="from pathlib import Path; import hashlib,json; files={str(p.relative_to('/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}; print(json.dumps(dict(files=files,lock=hashlib.sha256(Path('/tmp/requirements.lock').read_bytes()).hexdigest())))";
  const actual=JSON.parse(docker(['run','--rm','--read-only','--network','none','--name','classifieds-rebuild-dev-phase6-image-verify',
    '--label','com.docker.compose.project=classifieds-rebuild-dev','--entrypoint','python',id,'-c',code]));
  const expected=Object.fromEntries(manifest.files.filter(row=>row.path.startsWith('rebuild/backend/')).map(row=>[row.path.slice('rebuild/backend/'.length),row.sha256]));
  const missing=Object.keys(expected).filter(file=>!(file in actual.files));
  const extra=Object.keys(actual.files).filter(file=>!(file in expected));
  const mismatches=Object.keys(expected).filter(file=>file in actual.files&&actual.files[file]!==expected[file]);
  const lock=manifest.files.find(row=>row.path==='rebuild/requirements.lock').sha256;
  ensure(!missing.length&&!extra.length&&!mismatches.length&&actual.lock===lock);
  const result={atUTC:new Date().toISOString(),pass:true,tag,id,manifest:manifest.materializedSha256,
    backendHashesVerifiedWithoutBindOrNetwork:Object.keys(expected).length,missing,extra,mismatches,requirementsLockMatches:true,originalAdoption:false};
  fs.writeFileSync(path.join(__dirname,'candidate-image-verification.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
}catch{console.log('{"pass":false,"kind":"candidate_image_verification_failed"}');process.exitCode=1;}
