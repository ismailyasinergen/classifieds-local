'use strict';
const fs=require('node:fs'),path=require('node:path');
const {execFileSync,spawnSync}=require('node:child_process');
const {prepareRepository,readComponent}=require('../repository.cjs');
const {validateOwned}=require('../runtime.cjs');
const {requireSafe}=require('../guards.cjs');
const run='86ff5926b99865ed';
const target=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../../docs/phase7',`runtime-${run}.json`)));
validateOwned(target);
const repo=prepareRepository({root:'C:/Users/ismai/AppData/Local/ClassifiedsRecovery/phase7/repositories',repoId:'76836c56abe8d4d86f4a2f24a20ba4da',create:false});
for(const [kind,id,mode] of [
  ['source.tar','380c2c7a351bbbc0368c311b7a07c10b333bff5ec5a2e22bfb42dc289a714afc','source'],
  ['application-image.tar','150db38416d4c6fc7461aa8d1c2e27950a114c5c0bf37f212b348e0c2abb019e','image']]) {
  const spec=readComponent(repo,id,kind);
  const input=execFileSync(spec.command,spec.args,{env:spec.env,windowsHide:true,stdio:['ignore','pipe','pipe'],maxBuffer:128*1024*1024,timeout:120000});
  const output=spawnSync('docker',['exec','-i',target.services.web,'python','/ops/restore_runtime.py',mode],{input,windowsHide:true,stdio:['pipe','pipe','pipe'],maxBuffer:1024,timeout:120000});
  const category=output.stderr.toString().trim();
  requireSafe(!category||/^restore_runtime_failed:[A-Za-z_]+$/.test(category));
  console.log(JSON.stringify({kind,exit:output.status,category}));
  if(output.status)process.exitCode=1;
}
