'use strict';
const fs=require('node:fs'),path=require('node:path');
const {validateOwned}=require('../runtime.cjs');
const {command,developer}=require('../inspect.cjs');
const {requireSafe}=require('../guards.cjs');
try {
  const run=process.argv[2];requireSafe(/^[a-f0-9]{16}$/.test(run));
  const receipt=JSON.parse(fs.readFileSync(path.join(developer,'rebuild/docs/phase7',`runtime-${run}.json`)));
  validateOwned(receipt);requireSafe(receipt.role==='synthetic-source');
  const extra=process.argv[3]===undefined?[]:['augment'];requireSafe(!extra.length||process.argv[3]==='augment');
  const result=JSON.parse(command('docker',['exec',receipt.services.web,'python','/ops/synthetic_fixture.py',run,...extra]));
  requireSafe(extra.length?result.augmented===true:result.seeded===true);console.log(JSON.stringify(result));
} catch {console.log(JSON.stringify({pass:false,category:'synthetic_seed_failed'}));process.exitCode=1;}
