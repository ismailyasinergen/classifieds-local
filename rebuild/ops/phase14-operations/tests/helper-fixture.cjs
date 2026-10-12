'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
module.exports=function fixture(fault=''){
 const root=path.resolve(__dirname,'..'),id='d'.repeat(64),image='sha256:'+'e'.repeat(64),networkId='f'.repeat(64),records=[],calls=[];let m,removed=0,started=0,writes=0;
 const command=(cmd,args)=>{calls.push(args);if(args[0]==='network')return JSON.stringify({id:networkId,name:args.at(-1),driver:args.at(-1)==='none'?'null':'bridge'});
  if(args[0]==='ps'){if(fault==='discovery-denied'&&m)throw Error('command_failed');if(args.includes('--filter'))return m&&fault!=='lost-empty'?id:'';return m||fault==='baseline'?id:'';}
  if(args[0]==='create'){
   const after=key=>args[args.indexOf(key)+1],labels={};args.forEach((a,i)=>{if(a==='--label'){const [k,v]=args[i+1].split('=');labels[k]=v;}});const role=labels['phase15.role'];
   m={id,name:'/'+after('--name'),image,labels,entrypoint:['python'],cmd:args.slice(args.indexOf(image)+1),user:'1000:1000',stdin:true,tty:false,mounts:role==='dns'?[]:[{Type:'bind',Source:root,Destination:'/ops',RW:false},{Type:'bind',Source:'C:/developer',Destination:'/source',RW:false}],network:after('--network'),networks:{[after('--network')]:{NetworkID:networkId}},ports:{},readonly:true,privileged:false,capAdd:[],capDrop:['ALL'],security:['no-new-privileges'],pid:'',userns:'',ipc:'private',autoRemove:false,logDriver:'none',state:'created',exit:0};
   if(fault==='foreign')m.labels['phase15.attempt']='0'.repeat(32);if(fault==='writable')m.readonly=false;if(fault==='wrong-image')m.image='sha256:'+'1'.repeat(64);if(fault==='namespace')m.pid='host';if(fault==='wrong-network')m.network='host';if(fault==='wrong-command')m.cmd=['-c','PRIVATE_CANARY'];if(fault==='extra-mount')m.mounts.push({Type:'bind',Source:'C:/forbidden',Destination:'/private',RW:false});
   if(['lost','lost-empty','discovery-denied'].includes(fault))throw Error('command_failed');return id;
  }
  if(args[0]==='inspect'){if(!m)throw Error('command_failed');if(args[2]==='{{json .State.Status}}')return JSON.stringify(m.state);return JSON.stringify(m);}
  if(args[0]==='kill'){if(fault==='cleanup-denied')throw Error('command_failed');m.state='exited';return id;}
  if(args[0]==='rm'){if(fault==='cleanup-denied')throw Error('command_failed');m=null;removed++;return id;}throw Error('unexpected_command');
 };
 const fakefs={readFileSync:()=>JSON.stringify({containerIds:[]}),writeFileSync(file,value){writes++;if((fault==='first-receipt'&&writes===1)||(fault==='last-receipt'&&JSON.parse(value).phase==='closed')||(fault==='created-receipt'&&JSON.parse(value).phase==='created'))throw Error('PRIVATE_CANARY');records.push(JSON.parse(value));}};
 const module={exports:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'owned-helper.cjs'),'utf8'),{module,Buffer,process,structuredClone,__dirname:root,require:n=>n==='node:fs'?fakefs:n==='./inspect.cjs'?{command,image,developer:'C:/developer',docs:'C:/synthetic-docs',sourceAlias:(a,b)=>a===b}:n==='node:child_process'?{execFileSync(){started++;m.state='exited';m.exit=fault==='nonzero'?9:0;if(fault==='timeout'){m.state='running';throw Error('PRIVATE_CANARY');}return Buffer.from('["192.0.2.1"]');}}:n==='../recovery/repository.cjs'?{backupComponent:async()=>{started++;m.state=fault==='pipeline'?'running':'exited';if(fault==='pipeline')throw Error('pipeline_failed');return {bytes:10,producerExit:0,consumerExit:0};}}:require(n.startsWith('.')?path.resolve(root,n):n)});
 return {api:module.exports,records,calls,id,stats:()=>({removed,started,writes,exists:!!m}),running(){m.state='running';},exit(code=0){m.state='exited';m.exit=code;}};
};
