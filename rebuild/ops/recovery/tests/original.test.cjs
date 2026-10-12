'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {guardOriginal}=require('../original-source.cjs');
const {image,manifest,original}=require('../inspect.cjs');
const good=()=>({app:{id:'a'.repeat(64),image,state:'running',project:'classifieds-rebuild',service:'web',configHash:'c',networks:['n'],mounts:[{Type:'bind',Source:original+'/rebuild/backend',Destination:'/app',RW:false},{Type:'volume',Name:'classifieds-rebuild_rebuild_media',Destination:'/var/lib/classifieds/media',RW:true}]},db:{id:'b'.repeat(64),image:'pg',state:'running',project:'classifieds-rebuild',service:'db',configHash:'d',networks:['n']},manifest});
const expected=good();
test('exact Docker Desktop operations mount spelling maps to same reviewed directory',()=>{
 const path=require('node:path'),root=path.resolve(__dirname,'..');
 const alias='/run/desktop/mnt/host/'+root[0].toLowerCase()+root.slice(2).replaceAll('\\','/');
 assert.equal(require('../original-source.cjs').isOpsMount(alias),true);
 assert.equal(require('../original-source.cjs').isOpsMount(alias+'/foreign'),false);
 assert.equal(require('../original-source.cjs').isOpsMount('/var/run/docker.sock'),false);
});
test('memory transport uses fixed modes, read-only PostgreSQL and no helper file',()=>{
 const spec=require('../original-source.cjs').memoryCommand('a'.repeat(64),'snapshot',{dbIp:'172.18.0.2',dbBinding:'b'.repeat(64)});
 assert.equal(spec.command,'docker');assert.deepEqual(spec.args.slice(0,3),['exec','-i','-e']);
 assert(spec.args.includes('PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=300000 -c lock_timeout=5000'));
 assert(spec.args.includes('-B'));assert(!spec.args.some(x=>x.includes('/ops/')));
});
test('memory transport rejects arbitrary mode before spawn',()=>assert.throws(()=>require('../original-source.cjs').memoryCommand('a'.repeat(64),'shell',{}),/^Error: original_transport_refused$/));
test('exact original metadata accepted before any private process',()=>assert.equal(guardOriginal(good(),expected),true));
test('Docker mount ordering is not a source identity change',()=>{const x=good();x.app.mounts.reverse();assert.equal(guardOriginal(x,expected),true);});
for(const [name,change] of [
 ['app ID',x=>x.app.id='f'.repeat(64)],['DB ID',x=>x.db.id='f'.repeat(64)],
 ['app image',x=>x.app.image='wrong'],['DB image',x=>x.db.image='wrong'],
 ['manifest',x=>x.manifest='wrong'],['source network',x=>x.app.networks=['foreign']],
 ['DB network',x=>x.db.networks=['foreign']],['config drift',x=>x.app.configHash='wrong'],
 ['media volume',x=>x.app.mounts[1].Name='foreign'],['writable code',x=>x.app.mounts[0].RW=true],
 ['stopped source',x=>x.app.state='exited'],['wrong project',x=>x.app.project='classifieds-rebuild-dev']])
 test('refuses '+name,()=>{const x=good();change(x);assert.throws(()=>guardOriginal(x,expected),/^Error: original_identity_refused$/);});
