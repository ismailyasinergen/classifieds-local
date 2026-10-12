'use strict';
// Only the synthetic test launcher adds this preload to its own observer child.
setTimeout(()=>Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,350),100);
