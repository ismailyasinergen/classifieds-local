'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {runBinaryPipeline}=require('../safe-process.cjs');
const {acquireLock}=require('../safe-process.cjs');
const node=code=>({command:process.execPath,args:['-e',code]});
const consumer=node('process.stdin.resume();');
test('producer input remains private binary stdin',async()=>{
  const producer={...node('process.stdin.pipe(process.stdout);'),input:Buffer.from([0,255,128])};
  const r=await runBinaryPipeline(producer,node('let a=[];process.stdin.on("data",b=>a.push(b));process.stdin.on("end",()=>process.exit(Buffer.concat(a).equals(Buffer.from([0,255,128]))?0:2));'),{maxBytes:100,timeoutMs:5000});
  assert.equal(r.bytes,3);
});
test('binary pipeline preserves NUL ff CR LF through a verifying consumer',async()=> {
  const input=Buffer.from([0,255,13,10,0,128]);
  const result=await runBinaryPipeline(node('process.stdout.write(Buffer.from([0,255,13,10,0,128]));'),node("const a=[];process.stdin.on('data',b=>a.push(b));process.stdin.on('end',()=>process.exit(Buffer.concat(a).equals(Buffer.from([0,255,13,10,0,128]))?0:9));"),{maxBytes:100,timeoutMs:5000});
  assert.equal(result.bytes,6); assert.equal(result.sha256,crypto.createHash('sha256').update(input).digest('hex'));
  assert.equal(result.producerExit,0);assert.equal(result.consumerExit,0);
});
test('producer failure cannot be hidden by consumer success',async()=>{
  await assert.rejects(runBinaryPipeline(node('process.stdout.write("partial");process.exitCode=1;'),consumer,{maxBytes:100,timeoutMs:5000}),/pipeline_failed/);
});
test('consumer failure prevents completion',async()=>{
  await assert.rejects(runBinaryPipeline(node('process.stdout.write("abc");'),node('process.stdin.resume();process.exitCode=2;'),{maxBytes:100,timeoutMs:5000}),/pipeline_failed/);
});
test('overflow cancels owned children with no data in error',async()=>{
  await assert.rejects(runBinaryPipeline(node('process.stdout.write("SECRET_CANARY".repeat(100));'),consumer,{maxBytes:10,timeoutMs:5000}),e=>e.message==='pipeline_overflow'&&!JSON.stringify(e).includes('SECRET_CANARY'));
});
test('timeout cancels owned children',async()=>{
  await assert.rejects(runBinaryPipeline(node('setInterval(()=>{},1000);'),consumer,{maxBytes:100,timeoutMs:100}),/pipeline_timeout/);
});
test('stderr and stdout canaries never enter public error projection',async()=>{
  await assert.rejects(runBinaryPipeline(node('process.stderr.write("SECRET_CANARY");process.stdout.write("SECRET_CANARY");process.exitCode=4;'),consumer,{maxBytes:100,timeoutMs:5000}),e=>e.message==='pipeline_failed'&&!JSON.stringify(e).includes('SECRET_CANARY'));
});
test('same run cannot acquire simultaneous operation locks',()=>{
  const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'phase7-lock-')),file=path.join(dir,'lock');
  const release=acquireLock(file);
  try {assert.throws(()=>acquireLock(file),/run_locked/);}finally{release();fs.rmdirSync(dir);}
});
test('slow consumer verifies multi-megabyte binary stream with backpressure',async()=>{
  const r=await runBinaryPipeline(node('const b=Buffer.alloc(65536,255);let i=0;function go(){while(i++<64){if(!process.stdout.write(b)){process.stdout.once("drain",go);return;}}}go();'),
    node('let n=0,bad=false;process.stdin.on("data",b=>{n+=b.length;bad ||= b.some(x=>x!==255);process.stdin.pause();setTimeout(()=>process.stdin.resume(),2);});process.stdin.on("end",()=>process.exit(n===4194304&&!bad?0:1));'),{maxBytes:4194304,timeoutMs:5000});
  assert.equal(r.bytes,4194304);
});
test('bounded teardown when OS reports exit but inherited pipe never closes',async(t)=>{
  const {EventEmitter}=require('node:events'),{PassThrough}=require('node:stream');
  const cp=require('node:child_process'),children=[];
  t.mock.method(cp,'spawn',()=>{
    const child=new EventEmitter();child.exitCode=null;
    for(const name of ['stdin','stdout','stderr'])child[name]=new PassThrough();
    child.kill=()=>{child.exitCode=1;child.emit('exit',1);child.emit('close',1);};
    children.push(child);
    if(children.length===1)queueMicrotask(()=>{child.exitCode=0;child.emit('exit',0);});
    return child;
  });
  delete require.cache[require.resolve('../safe-process.cjs')];
  const bounded=require('../safe-process.cjs').runBinaryPipeline;
  t.after(()=>{for(const c of children){c.emit('close',c.exitCode);for(const s of ['stdin','stdout','stderr'])c[s].destroy();}});
  const result=await Promise.race([bounded(node(''),consumer,{maxBytes:100,timeoutMs:50}).then(()=> 'unexpected_success',e=>e.message),
    new Promise(resolve=>setTimeout(()=>resolve('hung_after_deadline'),250))]);
  assert.equal(result,'pipeline_timeout');
});
