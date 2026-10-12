'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {command,image,developer}=require('../inspect.cjs');
const {assertIsolation}=require('../isolation.cjs');
const {requireSafe}=require('../guards.cjs');
const run=crypto.randomBytes(8).toString('hex'),project=`classifieds-rebuild-recovery-${run}-synthetic-target`;
const result={run,project,atUTC:new Date().toISOString(),pass:false,containerRemoved:false,networkRemoved:false};
const file=path.join(developer,'rebuild/docs/phase7',`isolation-probe-${run}.json`);
const save=()=>fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');
const docker=args=>command('docker',args);
let network,container;
try {
  const hostAddresses=(process.argv[2]||'').split(',');
  requireSafe(Array.isArray(hostAddresses)&&hostAddresses.length>0&&hostAddresses.length<=4&&hostAddresses.every(a=>require('node:net').isIP(a)));
  result.hostAddresses=hostAddresses;
  network=docker(['network','create','--internal','--label',`phase7.run=${run}`,'--label',`phase7.project=${project}`,project]);
  requireSafe(/^[a-f0-9]{64}$/.test(network));result.networkId=network;save();
  const net=JSON.parse(docker(['network','inspect','--format','{{json .}}',network]));
  requireSafe(net.Internal===true&&net.Name===project&&net.Labels['phase7.run']===run);
  const gateway=net.IPAM.Config[0].Gateway;requireSafe(typeof gateway==='string');
  container=docker(['create','--name',project+'-probe','--label',`phase7.run=${run}`,'--network',network,
    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--env','PYTHONDONTWRITEBYTECODE=1',
    '--mount',`type=bind,source=${path.resolve(__dirname,'..')},target=/ops,readonly`,
    image,'python','/ops/network_probe.py',gateway,JSON.stringify(hostAddresses)]);
  requireSafe(/^[a-f0-9]{64}$/.test(container));result.containerId=container;save();
  const meta=JSON.parse(docker(['inspect','--format','{"image":{{json .Image}},"run":{{json (index .Config.Labels "phase7.run")}},"ports":{{json .HostConfig.PortBindings}},"networks":{{json .NetworkSettings.Networks}},"privileged":{{json .HostConfig.Privileged}}}',container]));
  requireSafe(meta.image===image&&meta.run===run&&!meta.privileged&&Object.keys(meta.ports||{}).length===0&&Object.keys(meta.networks).length===1);
  result.probes=JSON.parse(docker(['start','--attach',container]));
  result.probeExit=Number(docker(['inspect','--format','{{.State.ExitCode}}',container]));
  requireSafe(result.probeExit===0);assertIsolation(result.probes);result.pass=true;
} catch(error) {result.category=error.message==='isolation_blocked'?'isolation_blocked':'probe_failed';}
finally {
  try {
    if(container) {
      requireSafe(docker(['inspect','--format','{{index .Config.Labels "phase7.run"}}',container])===run);
      requireSafe(docker(['inspect','--format','{{.State.Running}}',container])==='false');
      docker(['rm',container]);result.containerRemoved=true;
    }
    if(network) {
      const net=JSON.parse(docker(['network','inspect','--format','{{json .}}',network]));
      requireSafe(net.Name===project&&net.Labels['phase7.run']===run&&Object.keys(net.Containers||{}).length===0);
      docker(['network','rm',network]);result.networkRemoved=true;
    }
  } catch {result.cleanupBlocked=true;result.pass=false;}
  save();console.log(JSON.stringify(result));process.exitCode=result.pass?0:1;
}
