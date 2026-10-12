'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {developer}=require('../../inspect.cjs');
const run=crypto.randomBytes(8).toString('hex'),name='phase8-test-'+run,ops=path.resolve(__dirname,'..');
const pg='sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826',app='sha256:23e5fe716cd2f2e73c189f035eb3df345ca155c1cd31c78bfdbd0c06839a1839';
const owned=[],result={run,pass:false,stage:'create_network',checks:0,cleanup:[],liveDataAccess:false};let network;
const docker=args=>execFileSync('docker',args,{encoding:'utf8',timeout:30000,maxBuffer:8192,windowsHide:true,stdio:['ignore','pipe','pipe']}).trim();
const metadata=id=>JSON.parse(docker(['inspect','--format','{"id":{{json .Id}},"image":{{json .Image}},"label":{{json (index .Config.Labels "phase8.run")}},"ports":{{json .HostConfig.PortBindings}},"networks":{{json .NetworkSettings.Networks}},"mounts":{{json .Mounts}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"capDrop":{{json .HostConfig.CapDrop}},"security":{{json .HostConfig.SecurityOpt}},"state":{{json .State.Status}},"health":{{with index .State "Health"}}{{json .Status}}{{else}}null{{end}}}',id]));
function guard(id,image){const m=metadata(id);assert.equal(m.id,id);assert.equal(m.label,run);assert.equal(m.image,image);assert.equal(Object.keys(m.ports||{}).length,0);assert.equal(m.readonly,true);assert(m.capDrop.includes('ALL'));assert(m.security.includes('no-new-privileges'));assert.deepEqual(Object.keys(m.networks),[name]);assert(m.mounts.every(x=>x.Type==='tmpfs'||x.Type==='bind'&&x.Destination==='/ops'&&!x.RW));return m;}
async function main(){
 try{
  network=docker(['network','create','--internal','--label','phase8.run='+run,name]);
  const n=JSON.parse(docker(['network','inspect','--format','{"id":{{json .Id}},"internal":{{json .Internal}},"label":{{json (index .Labels "phase8.run")}}}',network]));assert.equal(n.id,network);assert(n.internal);assert.equal(n.label,run);
  const common=['--pull','never','--network',name,'--label','phase8.run='+run,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges'];
  result.stage='create_db';const db=docker(['create','--name',name+'-db',...common,'--network-alias','db','--user','999:999','-e','POSTGRES_USER=observation','-e','POSTGRES_DB=observation','-e','POSTGRES_HOST_AUTH_METHOD=trust',
   '--tmpfs','/var/lib/postgresql/data:rw,nosuid,noexec,size=512m,uid=999,gid=999,mode=0700','--tmpfs','/var/run/postgresql:rw,nosuid,noexec,size=8m,uid=999,gid=999','--tmpfs','/tmp:rw,nosuid,noexec,size=8m,uid=999,gid=999',
   '--health-cmd','pg_isready -h 127.0.0.1 -U observation -d observation','--health-interval','1s','--health-timeout','1s','--health-retries','20',pg]);owned.push({id:db,image:pg});guard(db,pg);docker(['start',db]);
  result.stage='db_readiness';const until=Date.now()+25000;while(metadata(db).health!=='healthy'){assert(Date.now()<until);await new Promise(r=>setTimeout(r,250));}
  const dbInfo=guard(db,pg),ip=dbInfo.networks[name].IPAddress;
  result.stage='create_helper';const helper=docker(['create','--name',name+'-helper',...common,'--user','1000:1000','--mount','type=bind,source='+ops+',target=/ops,readonly','--entrypoint','python',app,'-B','/ops/tests/db_integration.py',ip]);owned.push({id:helper,image:app});guard(helper,app);
  result.stage='synthetic_db_assertions';let output;try{output=docker(['start','-a',helper]);}catch(e){output=String(e.stdout||'');}
  const status=Number(docker(['inspect','--format','{{.State.ExitCode}}',helper]));result.helperExit=status;
  const outcome=JSON.parse(output);assert(Number.isInteger(outcome.checks));result.checks=outcome.checks;
  if(outcome.pass!==true){result.helperError=/^[A-Za-z]{1,50}$/.test(outcome.errorType)?outcome.errorType:'invalid_response';result.sqlstate=/^[A-Z0-9]{5}$/.test(outcome.sqlstate)?outcome.sqlstate:null;
   result.category=['identity_mismatch','input_refused','test_failure'].includes(outcome.category)?outcome.category:'invalid_response';result.hostAddressMatches=outcome.diagnostic?.hostAddressMatches===true;result.textAddressMatches=outcome.diagnostic?.textAddressMatches===true;}
  assert.equal(status,0);assert.equal(outcome.pass,true);assert.equal(outcome.checks,12);result.pass=true;result.repeatedReadsUnchanged=outcome.repeatedReadsUnchanged===true;
 }catch{result.pass=false;result.error='isolated_integration_failed';process.exitCode=1;}
 finally{
  for(const item of owned.reverse())try{guard(item.id,item.image);require('../../graceful.cjs').gracefulStop(docker,item.id);docker(['rm',item.id]);result.cleanup.push({id:item.id,status:'removed_exact_owned'});}catch{result.cleanup.push({id:item.id,status:'cleanup_blocked'});result.pass=false;process.exitCode=1;}
  if(network)try{const n=JSON.parse(docker(['network','inspect','--format','{"id":{{json .Id}},"label":{{json (index .Labels "phase8.run")}},"containers":{{json .Containers}}}',network]));assert.equal(n.id,network);assert.equal(n.label,run);assert.equal(Object.keys(n.containers).length,0);docker(['network','rm',network]);result.networkRemoved=true;}catch{result.networkRemoved=false;result.pass=false;process.exitCode=1;}
  fs.writeFileSync(path.join(developer,'rebuild/docs/phase15/db-integration-'+run+'.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
 }
}
main();
