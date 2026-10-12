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
  const hosts=JSON.parse(command('docker',['run','--rm','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',image,
    'python','-c',"import socket,json; print(json.dumps(sorted({r[4][0] for r in socket.getaddrinfo('host.docker.internal',8088,type=socket.SOCK_STREAM)})))"]));
  if(!Array.isArray(hosts)||!hosts.length||!hosts.every(h=>require('node:net').isIP(h)))throw new Error('isolation_blocked');
  const net=JSON.parse(command('docker',['network','inspect','--format','{{json .}}',target.networkId]));
  const probes=JSON.parse(command('docker',['exec',target.services.web,'python','/ops/network_probe.py',net.IPAM.Config[0].Gateway,JSON.stringify(hosts)]));
  assertIsolation(probes);
  const result={run:target.run,networkId:target.networkId,containerId:target.services.web,probes,pass:true,atUTC:new Date().toISOString()};
  require('node:fs').writeFileSync(path.resolve(__dirname,'../../docs/phase7',`target-isolation-${target.run}-${Date.now()}.json`),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  return result;
}
module.exports={assertIsolation,verifyTargetIsolation};
