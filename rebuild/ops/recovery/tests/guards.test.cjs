'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {guardTarget, guardSource, validateArchiveMember} = require('../guards.cjs');
const {guardDirectory}=require('../guards.cjs');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const run = '0123456789abcdef';
const id = n => n.toString(16).padStart(64, '0');
const baseline = {containerIds:[id(1)], volumeNames:['live-data'], networkIds:[id(2)], manifest:id(3), image:id(4)};
const project = `classifieds-rebuild-recovery-${run}-synthetic-target`;
const good = () => ({run,role:'synthetic-target',project,id:id(5), image:id(4), networkIds:[id(6)],
  mounts:[{type:'tmpfs',target:'/data',rw:true}], ports:[], privileged:false, capAdd:[], networkMode:'default', empty:true});
const receipt = {run,role:'synthetic-target',project,containerIds:[id(5)],networkIds:[id(6)],image:id(4)};
test('accepts only an exact owned empty target and freezes identity',()=> {
  const value=guardTarget(good(),receipt,baseline); assert.equal(value.id,id(5)); assert.ok(Object.isFrozen(value));
});
for(const [name,patch] of Object.entries({source:{id:id(1)},foreign:{project:'foreign'},role:{role:'synthetic-source'},
  duplicateNetwork:{networkIds:[id(6),id(6)]},sourceNetwork:{networkIds:[id(2)]},unknownNetwork:{networkIds:[id(7)]},
  nonempty:{empty:false},hostPorts:{ports:[{host:'127.0.0.1',port:'9000'}]},hostNetwork:{networkMode:'host'},
  privilege:{privileged:true},capability:{capAdd:['NET_ADMIN']},wrongImage:{image:id(8)},wrongRun:{run:'fedcba9876543210'},
  sourceVolume:{mounts:[{type:'volume',name:'live-data',target:'/data',rw:true}]},
  socket:{mounts:[{type:'bind',source:'/var/run/docker.sock',target:'/var/run/docker.sock',rw:false}]},
  bind:{mounts:[{type:'bind',source:'C:/live',target:'/data',rw:true}]},
  unapprovedReadonly:{mounts:[{type:'bind',source:'C:/live',target:'/data',rw:false}]}})) {
  test(`refuses ${name} before a caller can write`,()=>assert.throws(()=>guardTarget({...good(),...patch},receipt,baseline)));
}
test('source manifest mismatch is refused',()=>assert.throws(()=>guardSource({manifest:id(9)},baseline)));
test('target refuses tmpfs that shadows application image',()=>assert.throws(()=>guardTarget({...good(),mounts:[{type:'tmpfs',target:'/app',rw:true}]},receipt,baseline)));
test('a forged operations-directory receipt cannot authorize the Docker socket',()=>{
  assert.throws(()=>guardTarget({...good(),mounts:[{type:'bind',source:'/var/run/docker.sock',target:'/ops',rw:false}]},{...receipt,opsRoot:'/var/run/docker.sock'},baseline));
});
test('source accepts only baseline identity and returns deeply immutable copy',()=>{
  const meta={manifest:id(3),image:id(4),mode:'original',appId:id(1),networkIds:[id(2)]};
  const b={...baseline,sources:[meta]}; const accepted=guardSource(meta,b);
  assert.ok(Object.isFrozen(accepted.networkIds)); meta.networkIds.push(id(6));assert.equal(accepted.networkIds.length,1);
  assert.throws(()=>guardSource({...meta,appId:id(7)},b));
});
test('directories reject traversal and existing reparse points',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'phase7-guard-'));
  const link=path.join(dir,'link');
  try {
    fs.symlinkSync(dir,link,'junction');
    assert.equal(guardDirectory(path.join(dir,'new'),dir),path.join(dir,'new'));
    assert.throws(()=>guardDirectory(path.join(dir,'..','escape'),dir));
    assert.throws(()=>guardDirectory(path.join(link,'new'),dir));
  } finally {fs.unlinkSync(link);fs.rmdirSync(dir);}
});
for (const name of ['/abs','../escape','a/../b','C:/evil','a\\b','./a','a//b','a\u0000b'])
  test('archive rejects unsafe spelling '+JSON.stringify(name),()=>assert.throws(()=>validateArchiveMember(name,'file',1,new Map([[name,1]]),new Set())));
test('archive permits only inventory regular files and rejects duplicates',()=>{
  const seen=new Set(), inventory=new Map([['originals/a.bin',3]]);
  assert.equal(validateArchiveMember('originals/a.bin','file',3,inventory,seen),true);
  assert.throws(()=>validateArchiveMember('originals/a.bin','file',3,inventory,seen));
  assert.throws(()=>validateArchiveMember('link','symlink',0,inventory,new Set()));
  assert.throws(()=>validateArchiveMember('originals/a.bin','file',4,inventory,new Set()));
});
