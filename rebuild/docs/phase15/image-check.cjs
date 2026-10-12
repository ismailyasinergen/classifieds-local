'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const p=require('../../ops/phase14-operations/inspect.cjs'),{docker,oneShot}=require('../phase14/adoption/runtime.cjs');
async function main(){
 const files=p.verifySources(),expected=files.filter(f=>f.path.startsWith('rebuild/backend/')).map(f=>[f.path.slice('rebuild/backend/'.length),f.sha256]);
 const lock=files.find(f=>f.path==='rebuild/requirements.lock');if(expected.length!==288||!lock)throw Error('image_scope_refused');expected.push(['requirements.lock',lock.sha256]);
 const code=`import json,hashlib,pathlib,sys\nrows=json.load(sys.stdin)\nroot=pathlib.Path('/app')\nfor name,digest in rows:\n p=pathlib.Path('/tmp/requirements.lock') if name=='requirements.lock' else root/name\n assert not any(part.startswith('.env') for part in p.parts)\n assert not p.is_symlink() and p.is_file()\n assert hashlib.sha256(p.read_bytes()).hexdigest()==digest\nprint(json.dumps({'nativeSuccess':True,'backendFiles':288,'requirementsLockVerified':True}))`;
 const run=crypto.randomBytes(8).toString('hex'),name='phase15-image-'+run,file=path.join(p.docs,'image-'+run+'.json');
 const baseline=docker(['ps','-aq','--no-trunc']).split(/\r?\n/);
 const spec={name,run,baseline,kind:'probe',timeoutMs:20000,collect:id=>JSON.parse(docker(['logs',id]))};
 let created=false;const result=await oneShot(spec,()=>docker(['create','--pull','never','--name',name,'--label','phase14.adoption.run='+run,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','-i','--entrypoint','python',p.image,'-B','-c',code]),r=>{fs.writeFileSync(file,JSON.stringify(r,null,2)+'\n',{flag:created?'w':'wx'});created=true;if(r.id&&r.nativeExit===null&&!r.primary)docker(['start','-a','-i',r.id],{input:JSON.stringify(expected)});});
 console.log(JSON.stringify(result));if(!result.ok)process.exitCode=1;
}
main().catch(()=>{console.log(JSON.stringify({ok:false,category:'image_check_failed'}));process.exitCode=1;});
