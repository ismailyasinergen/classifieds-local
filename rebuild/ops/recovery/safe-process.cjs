'use strict';
const {spawn} = require('node:child_process');
const {Transform} = require('node:stream');
const {pipeline} = require('node:stream/promises');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
async function runBinaryPipeline(producer,consumer,{maxBytes,timeoutMs}) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1 || !Number.isSafeInteger(timeoutMs) || timeoutMs < 1)
    throw new Error('pipeline_limits');
  const children=[]; let reason=null, bytes=0;
  const hash=createHash('sha256');
  const cancel=code=>{
    if(reason)return;
    reason=code;
    for(const child of children) {
      if(child.exitCode===null)child.kill('SIGKILL');
      for(const name of ['stdin','stdout','stderr'])child[name].destroy();
      child.settle?.(null);
    }
  };
  const start=spec=>{
    const child=spawn(spec.command,spec.args,{cwd:spec.cwd,env:spec.env || process.env,windowsHide:true,shell:false,stdio:['pipe','pipe','pipe']});
    children.push(child); child.stderr.resume();
    child.on('error',()=>cancel('pipeline_spawn_failed'));
    child.stdin.on('error',()=>cancel('pipeline_failed'));
    child.done=new Promise(resolve=>{
      child.settle=resolve;
      child.on('exit',code=>{if(code!==0)cancel('pipeline_failed');resolve(code);});
      child.on('close',code=>{if(code!==0)cancel('pipeline_failed');resolve(code);});
    });
    return child;
  };
  const timer=setTimeout(()=>cancel('pipeline_timeout'),timeoutMs);
  try {
    const source=start(producer), sink=start(consumer);
    source.stdin.end(producer.input); sink.stdout.resume();
    const meter=new Transform({transform(chunk,encoding,callback){
      bytes+=chunk.length;
      if(bytes>maxBytes) {cancel('pipeline_overflow'); callback(new Error('pipeline_overflow'));return;}
      hash.update(chunk);callback(null,chunk);
    }});
    const flow=pipeline(source.stdout,meter,sink.stdin).catch(()=>cancel('pipeline_failed'));
    const [producerExit,consumerExit]=await Promise.all([source.done,sink.done]);
    await flow;
    if(reason || producerExit!==0 || consumerExit!==0) throw new Error(reason || 'pipeline_failed');
    return {bytes,sha256:hash.digest('hex'),producerExit,consumerExit};
  } finally {clearTimeout(timer); for(const child of children) if(child.exitCode===null) child.kill();}
}
function acquireLock(file) {
  let fd; try {fd=fs.openSync(file,'wx');} catch {throw new Error('run_locked');}
  fs.writeFileSync(fd,JSON.stringify({pid:process.pid}));
  return ()=>{fs.closeSync(fd);fs.unlinkSync(file);};
}
module.exports = {runBinaryPipeline,acquireLock};
