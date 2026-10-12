'use strict';
const fs=require('node:fs'),path=require('node:path');
const {hash,developer}=require('./inspect.cjs');
const {requireSafe}=require('./guards.cjs');
function validateReviewPacket(review,digest) {
  requireSafe(review?.verdict==='PASS'&&review.scope==='phase7_integrated_operations'&&review.independent===true&&review.syntheticAdapterPassed===true&&
    typeof review.reviewer==='string'&&review.reviewer.length>0&&
    JSON.stringify(review.coveredScopes)===JSON.stringify(['original_adapter','owner_identity_media','health_lifecycle'])&&
    /^[a-f0-9]{64}$/.test(digest)&&review.operationsSha256===digest,'original_export_gate_closed');return true;
}
function verifyReview() {
  try {
    const dir=path.join(developer,'rebuild/docs/phase7');
    // Explicit version only: neither historical owner approval nor a health-only review is interchangeable.
    const map=JSON.parse(fs.readFileSync(path.join(dir,'operations-manifest-final-integrated-v2.json')));
    const review=JSON.parse(fs.readFileSync(path.join(dir,'final-operations-review-v2.json')));
    requireSafe(review.ownerIdentityProfile==='original-owner-0:0-capless'&&review.ownerOsRegressionPassed===true,'original_export_gate_closed');
    const digest=hash(Buffer.from(map.files.map(f=>f.sha256+'  '+f.path+'\n').join('')));
    validateReviewPacket(review,digest);
    requireSafe(map.materializedSha256===digest&&map.files.length>0,'original_export_gate_closed');
    const names=fs.readdirSync(__dirname,{recursive:true}).filter(f=>{
      const stat=fs.lstatSync(path.join(__dirname,f));
      requireSafe(!stat.isSymbolicLink(),'original_export_gate_closed');
      if(stat.isDirectory())return false;
      requireSafe(stat.isFile(),'original_export_gate_closed');
      return true;
    }).map(f=>'rebuild/ops/recovery/'+f.replaceAll('\\','/')).sort();
    requireSafe(JSON.stringify(names)===JSON.stringify(map.files.map(f=>f.path).sort()),'original_export_gate_closed');
    requireSafe(map.files.every(f=>hash(fs.readFileSync(path.join(developer,f.path)))===f.sha256),'original_export_gate_closed');
    const evidenceBytes=fs.readFileSync(path.join(dir,'final-operations-regressions-v2.json'));
    requireSafe(hash(evidenceBytes)===review.regressionsSha256,'original_export_gate_closed');
    const evidence=JSON.parse(evidenceBytes);
    requireSafe(evidence.operationsSha256===digest,'original_export_gate_closed');
    for(const suite of ['gate','health','node']){
      const run=evidence.runs?.[suite];
      requireSafe(run&&Number.isSafeInteger(run.tests)&&run.tests>0&&run.passed===run.tests&&run.failed===0&&run.skipped===0&&run.exit===0,'original_export_gate_closed');
    }
    const historical=['owner-os-3aab7ab4a8ee2363.json','task6-owner-execution-evidence.json','task6-synthetic-c41832728f4863fd.json','verify-bce537aa8fbeac06-1791668086486.json'];
    requireSafe(JSON.stringify(evidence.historicalEvidence.map(f=>f.name))===JSON.stringify(historical),'original_export_gate_closed');
    requireSafe(evidence.historicalEvidence.every(f=>hash(fs.readFileSync(path.join(dir,f.name)))===f.sha256),'original_export_gate_closed');
    return digest;
  } catch {throw Error('original_export_gate_closed');}
}
module.exports={verifyReview,validateReviewPacket};
