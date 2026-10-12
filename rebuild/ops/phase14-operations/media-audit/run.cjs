'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {persist,failure}=require('../lifecycle.cjs');
const {environment,counts,category}=require('./contract.cjs');
async function main(){
 const env=environment(process.argv.slice(2));
 const digest=require('../gate.cjs').verifyAcceptance();
 const {developer}=require('../inspect.cjs'),{guardDirectory}=require('../../recovery/guards.cjs');
 const runId=crypto.randomBytes(12).toString('hex');
 const report={runId,environment:env,operationsSha256:digest,...await require('./observe.cjs').observe(require('./transport.cjs').makeAdapter(env,runId)),
  consistency:'two_bounded_db_and_filesystem_observations_not_atomic',referenceScope:'all_assets_all_revision_states_all_report_retention_including_appeals',contentIntegrityVerified:false,applicationWritesPerformed:false};
 const dir=path.join(developer,'rebuild/docs/phase15/media-runs');
 try{fs.mkdirSync(dir,{recursive:true});guardDirectory(dir,developer);}catch{report.persistence='write_failed';throw Object.assign(failure(Error(report.error||'receipt_write_failed'),'receipt_write_failed',report.resources),{receipt:report});}
 report.persistence='written';report.persistence=persist(fs,path.join(dir,runId+'.json'),report,true);
 if(report.persistence!=='written')throw Object.assign(failure(Error(report.error||'receipt_write_failed'),'receipt_write_failed',report.resources),{receipt:report});
 const labels={scannedAssets:'Gözlenen asset',scannedFiles:'Gözlenen düzenli dosya',missingOriginals:'Eksik original',missingReadyDerivatives:'Eksik READY derivative',emptyReadyDerivatives:'Boş READY derivative kaydı',originalSizeMismatches:'Original boyut farkı',unlinkedButRetainedAssets:'Revizyonsuz ama korunan asset',unreferencedCandidates:'Gözlemde referanssız aday',temporaryOrInflight:'Geçici/işlenmekte',unreadableOrUnstable:'Okunamayan/değişken',unexpectedEntries:'Beklenmeyen girdi',multiRevisionAssets:'Birden fazla revizyondaki asset',evidenceRetainedAssets:'Şikâyet/itiraz saklama bağı',observedFileBytes:'Gözlenen dosya boyut toplamı'};
 const text=['# Medya tutarlılığı — '+env,'','Koşu: '+runId,'Tamamlandı: '+report.observationComplete+'; bulgu: '+report.findingsPresent+'; hata: '+(report.error||'yok')+'; cleanup: '+report.cleanup,'Başlangıç: '+report.startedAt+'; bitiş: '+report.endedAt+'; süre(ms): '+report.durationMs,...Object.entries(report.directories||{}).map(([k,v])=>'Dizin '+k+': '+v),...Object.entries(report.reasons||{}).map(([k,v])=>'Neden '+k+': '+v),...counts.map(k=>labels[k]+': '+(report[k]===null?'ölçülemedi':report[k])),'','Dosya içeriği okunmadı; boyut/varlık kontrolü içerik bütünlüğü kanıtı değildir.','İki gözlem atomik DB/dosya snapshot değildir. Referanssız aday kesin orphan veya silinebilir dosya değildir.','Tüm asset ve tüm revizyon/rapor saklama bağları kapsanır; bağlantısız ve FAILED asset korunur. Hiçbir silme/onarım yapılmadı.'].join('\n')+'\n';
 try{fs.writeFileSync(path.join(dir,runId+'.md'),text,{flag:'wx'});}catch{report.persistence='write_failed';throw Object.assign(failure(Error(report.error||'receipt_write_failed'),'receipt_write_failed',report.resources),{receipt:report});}console.log(text);console.log(JSON.stringify({resources:report.resources,cleanup:report.cleanup,persistence:report.persistence}));
 process.exitCode=report.observationComplete?0:['identity_mismatch','acceptance_unavailable','source_mismatch','reader_preflight_refused'].includes(report.error)?1:2;
}
if(require.main===module)main().catch(e=>{console.log(JSON.stringify(require('../lifecycle.cjs').failureOutput(e)));process.exitCode=1;});
module.exports={main};
