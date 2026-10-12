'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../media-audit'),{observe}=require('../media-audit/observe.cjs');
function harness(fault){
 const id='b'.repeat(64),run='a'.repeat(24),image='sha256:'+'c'.repeat(64),volume='classifieds-rebuild-dev_rebuild_media';let nonce,created=false,removed=0,stopped=false;
 const metadata={id,image,run,user:'0:0',network:'none',readonly:true,privileged:false,capAdd:[],capDrop:['ALL'],security:['no-new-privileges'],pid:'',userns:'',ipc:'private',ports:{},mounts:[{Type:'volume',Name:volume,Destination:'/media',RW:false},{Type:'bind',Source:root,Destination:'/ops',RW:false}]};
 const volumeMeta={name:volume,createdAt:'synthetic',driver:'local',scope:'local'};
 const rows=[{service:'web',id:'d'.repeat(64),image,mounts:[{Type:'volume',Name:volume,Destination:'/var/lib/classifieds/media'}]},{service:'db',ip:'172.1.0.2'}];
 function exec(_,args){
  if(args[0]==='ps'){if(created&&fault==='lost-unknown')throw Error('PRIVATE_CANARY');return created?id:'';}
  if(args[0]==='volume')return JSON.stringify(volumeMeta);
  if(args[0]==='create'){nonce=args.find(x=>x.startsWith('phase15.attempt=')).split('=')[1];created=true;if(fault.startsWith('lost-'))throw Error('PRIVATE_CANARY');return id;}
  if(args[0]==='inspect')return args[2]==='{{json .State.Status}}'?JSON.stringify(stopped?'exited':'running'):JSON.stringify({...metadata,nonce:fault==='foreign'?'wrong':nonce});
  if(args[0]==='start')return '';
  if(args[0]==='kill'){if(fault==='cleanup')throw Error('PRIVATE_CANARY');stopped=true;return '';}
  if(args[0]==='rm'){removed++;created=false;return '';}
  if(args[0]==='exec'){
   if(args.includes('/ops/preflight.py')){if(fault==='preflight')throw Error('PRIVATE_CANARY');return JSON.stringify({metadataAccessVerified:true,directories:{root:'present',originals:'present',derivatives:'absent'}});}
   if(args.includes('scan'))throw Error(fault==='scan'?'PRIVATE_CANARY':'scan-stop');
   if(args.includes('-c')&&args.at(-1)==='172.1.0.2')return '{"ok":true,"assets":[]}';
   return JSON.stringify({uid:0,gid:0,uidMap:['0','0','4294967295'],gidMap:['0','0','4294967295'],directories:[[0,0,493,true]]});
  }
  throw Error('unexpected_test_command');
 }
 const module={exports:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'transport.cjs'),'utf8'),{module,__dirname:root,performance,process,Buffer,require:n=>n==='node:child_process'?{execFileSync:exec}:n==='../inspect.cjs'?{verifySources(){}}:n==='../gate.cjs'?{verifyAcceptance(){}}:n==='../observability/core.cjs'?{inspect:()=>rows,validateRuntime:r=>r,project:()=> 'classifieds-rebuild-dev'}:n.endsWith('/baseline.json')?{volumes:[volumeMeta],containerIds:[]}:require(n.startsWith('.')?path.resolve(root,n):n)});
 return {adapter:module.exports.makeAdapter('developer',run),stats:()=>({created,removed})};
}
for(const fault of ['lost-create','lost-unknown','foreign','preflight','scan','cleanup'])test('real transport-observe handles '+fault,async()=>{
 const h=harness(fault),result=await observe(h.adapter);assert.equal(result.observationComplete,false);assert(!JSON.stringify(result).includes('PRIVATE_CANARY'));
 if(['cleanup','foreign','lost-unknown'].includes(fault)){assert.equal(h.stats().removed,0);if(fault==='lost-unknown')assert.equal(result.resources.unknown,true);else assert.equal(result.resources.retained.length,1);}else{assert.equal(h.stats().removed,1);assert.equal(h.stats().created,false);}
 try{h.adapter.close();}catch{}assert(h.stats().removed<=1);
});
