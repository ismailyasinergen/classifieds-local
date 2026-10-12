'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {summary,validateProbe}=require('../observability/core.cjs');
for(const mode of ['populated','empty','unavailable'])test('Turkish summary agrees with measured consumer: '+mode,()=>{
 const data=mode==='unavailable'?null:{consumer:'saved_search_in_app_v1',sourceUnprocessed:mode==='empty'?0:12,oldestAgeSeconds:mode==='empty'?null:60,consumption:{pending:mode==='empty'?0:1,retry:0,completed:2,skipped:3,failed:0}};
 if(data)validateProbe(data,'outbox');
 const text=summary({environment:'developer',runId:'synthetic',sections:{outbox:{status:data?'measured':'unavailable',error:data?null:'query_failed',data,startedAt:'synthetic',durationMs:1},media:{data:null,status:'unavailable',durationMs:1}}});
 assert(!text.includes('uygulanmamış'));assert(text.includes('Tüketici'));assert(text.includes('gönderimi kanıtı değildir'));assert(text.includes('kontrol mesajı'));
 if(data){assert(text.includes('pending: '+data.consumption.pending));assert(text.includes('Kaynak outbox'));}else assert(text.includes('ölçülemedi'));
 assert.equal(Buffer.from(text,'utf8').toString('utf8'),text);
});
