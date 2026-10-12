'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{EventEmitter}=require('node:events');
module.exports=function fixture(){
 const root=path.resolve(__dirname,'..'),binding={run:'a'.repeat(16),attempt:'b'.repeat(32),containerId:'c'.repeat(64)},child=new EventEmitter(),timers=new Map(),writes=[];let seq=0;
 for(const key of ['stdin','stdout','stderr'])child[key]=Object.assign(new EventEmitter(),{resume(){},end(value){writes.push(value);},destroy(){}});child.unref=()=>{};child.kill=()=>{throw Error('kill_forbidden');};
 const module={exports:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'snapshot.cjs'),'utf8'),{module,Buffer,process,__dirname:root,setTimeout:(fn,ms)=>{const id=++seq;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id),require:n=>n==='node:child_process'?{spawn:()=>child}:require(n.startsWith('.')?path.resolve(root,n):n)});
 const send=value=>child.stdout.emit('data',Buffer.from(JSON.stringify({run:binding.run,attempt:binding.attempt,...value})+'\n'));
 return {binding,child,writes,send,api:module.exports,tick(ms){for(const [id,t]of [...timers])if(t.ms===ms){timers.delete(id);t.fn();}},start(){const work=module.exports.startSnapshotCommand({command:'synthetic',args:[],snapshotBinding:binding});child.emit('spawn');return work;},catalog(){send({type:'catalog',catalog:{snapshot:'00000001-00000001-1'}});},ack(){send({type:'snapshot_closed',transactionClosed:true,connectionClosed:true});},exit(code=0){child.emit('close',code);}};
};
