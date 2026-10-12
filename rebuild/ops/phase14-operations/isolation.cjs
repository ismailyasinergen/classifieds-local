'use strict';
function assertIsolation(result) {
  const names=['host8088','host8089','gateway8088','gateway8089','external443'];
  if(!Array.isArray(result)||result.length!==names.length||new Set(result.map(r=>r.name)).size!==names.length||
    !result.every(r=>names.includes(r.name)&&r.resolved===true&&r.connected===false&&r.completed===true))
    throw new Error('isolation_blocked');
  return true;
}
function verifyTargetIsolation(target) {
  const {validateOwned}=require('./runtime.cjs');
  const {command,image}=require('./inspect.cjs');
  const path=require('node:path');
  validateOwned(target);
  const dns=require('./owned-helper.cjs').resolveHost(target.run),hosts=dns.hosts;
  if(!Array.isArray(hosts)||!hosts.length||!hosts.every(h=>require('node:net').isIP(h)))throw new Error('isolation_blocked');
  try {
  const net=JSON.parse(command('docker',['network','inspect','--format','{{json .}}',target.networkId]));
  const probes=JSON.parse(command('docker',['exec',target.services.web,'python','/ops/network_probe.py',net.IPAM.Config[0].Gateway,JSON.stringify(hosts)]));
  assertIsolation(probes);
  const result={run:target.run,networkId:target.networkId,containerId:target.services.web,probes,pass:true,...require('./lifecycle.cjs').lifecycleFields(dns),atUTC:new Date().toISOString()};
  require('node:fs').writeFileSync(path.resolve(__dirname,'../../docs/phase15',`target-isolation-${target.run}-${Date.now()}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  return result;
  } catch(e){throw Object.assign(require('./lifecycle.cjs').failure(e,'operation_failed'),require('./lifecycle.cjs').lifecycleFields(dns));}
}
module.exports={assertIsolation,verifyTargetIsolation};
