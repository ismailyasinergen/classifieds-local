'use strict';
// Ownership must be proven by the caller before this bounded stop; never sends KILL.
function gracefulStop(docker,id,limit=15000){
 if(!/^[a-f0-9]{64}$/.test(id))throw Error('cleanup_blocked');
 const state=()=>JSON.parse(docker(['inspect','--format','{{json .State.Status}}',id]));
 if(['exited','created'].includes(state()))return;
 docker(['kill','--signal','SIGTERM',id]);const end=Date.now()+limit;
 do{if(['exited','created'].includes(state()))return;Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,100);}while(Date.now()<end);
 throw Error('cleanup_blocked');
}
module.exports={gracefulStop};
