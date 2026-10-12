'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {fingerprint}=require('../inspect.cjs');
test('private env protection uses metadata without reading content',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'phase7-env-metadata-'));
  const file=path.join(dir,'.env');
  fs.writeFileSync(file,'SYNTHETIC_CANARY');
  try {
    const r=fingerprint(dir,'.env');
    assert.equal(r.protection,'metadata-only');assert.equal(r.size,16);
    assert.equal(Object.hasOwn(r,'sha256'),false);assert.ok(!JSON.stringify(r).includes('SYNTHETIC_CANARY'));
  } finally {fs.unlinkSync(file);fs.rmdirSync(dir);}
});
