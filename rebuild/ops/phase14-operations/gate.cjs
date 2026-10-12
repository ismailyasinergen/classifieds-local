'use strict';
const fs=require('node:fs'),path=require('node:path');
const {developer,docs,hash,image,manifest,isPrivateEnv}=require('./inspect.cjs');
const scopes=['source_runtime_identity','readonly_observability','owner_identity_media','developer_fixture_layout','snapshot_capture_restore','favorite_savedsearch_nonempty_restore','key_privacy','health_lifecycle','quarantine_cleanup','deployment_overlay_binding','notification_state_restore_resume','consumer_disabled_quarantine','storefront_schema_snapshot','storefront_nonempty_restore_behavior','private_file_preclassification','owned_archive_dns_lifecycle','snapshot_close_acknowledgement','capture_preflight_mount_contract'];
function check(ok){if(!ok)throw Error('acceptance_unavailable');}
function validateReviewPacket(review,digest){check(review?.verdict==='PASS'&&review.independent===true&&review.scope==='phase14_integrated_operations_v3'&&review.operationsSha256===digest&&review.productManifest===manifest&&review.image===image&&typeof review.reviewer==='string'&&review.reviewer.length>0&&JSON.stringify(review.coveredScopes)===JSON.stringify(scopes)&&review.ownerIdentityProfile==='original-owner-0:0-capless');return true;}
function verifyAcceptance(){try{
 const map=JSON.parse(fs.readFileSync(path.join(docs,'operations-manifest-v3.json'))),review=JSON.parse(fs.readFileSync(path.join(docs,'review-v3.json')));
 const dependencies=JSON.parse(fs.readFileSync(path.join(__dirname,'dependencies.json')));
 check(JSON.stringify(map.dependencies.map(f=>f.path).sort())===JSON.stringify([...dependencies].sort()));
 const actual=fs.readdirSync(__dirname,{recursive:true}).filter(f=>{const s=fs.lstatSync(path.join(__dirname,f));check(!s.isSymbolicLink());if(s.isDirectory())return false;check(s.isFile());return true;}).map(f=>'rebuild/ops/phase14-operations/'+f.replaceAll('\\','/')).sort();check(JSON.stringify(actual)===JSON.stringify(map.files.map(f=>f.path).sort()));
 const all=[...map.files,...map.dependencies].sort((a,b)=>a.path.localeCompare(b.path,'en'));check(new Set(all.map(f=>f.path)).size===all.length);
 for(const f of all){check(!isPrivateEnv(f.path)&&/^rebuild\//.test(f.path)&&!f.path.includes('\\')&&!f.path.split('/').some(p=>['..','.',''].includes(p)));let p=developer;for(const segment of f.path.split('/')){p=path.join(p,segment);check(!fs.lstatSync(p).isSymbolicLink());}check(fs.lstatSync(p).isFile()&&hash(fs.readFileSync(p))===f.sha256);}
 const digest=hash(Buffer.from(all.map(f=>f.sha256+'  '+f.path+'\n').join('')));check(map.materializedSha256===digest);validateReviewPacket(review,digest);
 const bytes=fs.readFileSync(path.join(docs,'tests-v3.json'));check(hash(bytes)===review.regressionsSha256);const tests=JSON.parse(bytes);check(tests.operationsSha256===digest);
 for(const k of ['node','python','isolatedDbFsOwner','syntheticRestore']){const r=tests.runs?.[k];check(r&&r.exit===0&&r.tests>0&&r.passed===r.tests&&r.failed===0&&r.skipped===0);}
 check(tests.ownedHelpersVerified===true&&tests.snapshotClosureVerified===true);
 check(tests.nonemptyFavorites===true&&tests.nonemptySavedSearches===true&&tests.separateProcessRestore===true&&tests.nonemptyNotifications===true&&tests.syntheticResumeVerified===true&&tests.deploymentRoundTrip===true&&tests.consumerDisabledQuarantine===true&&tests.nonemptyStorefronts===true&&tests.storefrontBehaviorVerified===true);
 check(Array.isArray(tests.evidence)&&tests.evidence.length>0&&new Set(tests.evidence.map(e=>e.name)).size===tests.evidence.length);
 for(const e of tests.evidence){check(/^[a-z0-9][a-zA-Z0-9.-]+\.(json|log)$/.test(e.name));const p=path.join(docs,e.name);check(!fs.lstatSync(p).isSymbolicLink()&&fs.lstatSync(p).isFile()&&hash(fs.readFileSync(p))===e.sha256);}return digest;
 }catch{throw Error('acceptance_unavailable');}}
module.exports={verifyAcceptance,verifyReview:verifyAcceptance,validateReviewPacket,scopes};
