'use strict';
async function main(){
 const args=process.argv.slice(2),command=args[0]&&!args[0].startsWith('--')?args.shift():'observe';
 if(!['observe','media','capture-preflight','capture-original','restore-original'].includes(command))throw Error('input_refused');
 require('./gate.cjs').verifyAcceptance();
 if(command==='capture-preflight'){
  if(args.length)throw Error('input_refused');
  require('./unresolved.cjs').assertNoUnresolved();
  if(require('node:fs').existsSync(require('node:path').join(require('./inspect.cjs').docs,'operation.lock')))throw Error('run_locked');
  require('./capture-entry.cjs').inspectPreconditions();
  const result={pass:true,stage:'preflight',activity:{repository:'not_run',capture:'not_run',health:'not_run'}};console.log(JSON.stringify(result));return result;
 }
 if(command==='observe'||command==='media'){require('./media-audit/contract.cjs').environment(args);process.argv=[process.argv[0],process.argv[1],...args];return require(command==='observe'?'./observability/run.cjs':'./media-audit/run.cjs').main();}
 if(command==='capture-original'){if(args.length)throw Error('input_refused');return require('./capture-entry.cjs').main();}
 if(args.length!==2||!(/^[a-f0-9]{32}$/.test(args[0])&&/^[a-f0-9]{64}$/.test(args[1])))throw Error('input_refused');return require('./restore-entry.cjs').main(...args);
}
function reportFailure(error){console.log(JSON.stringify(require('./lifecycle.cjs').failureOutput(error)));process.exitCode=1;}
if(require.main===module)main().catch(reportFailure);
module.exports={main,reportFailure};
