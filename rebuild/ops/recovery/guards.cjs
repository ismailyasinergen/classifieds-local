'use strict';
const fs = require('node:fs');
const path = require('node:path');
function requireSafe(ok, code='identity_refused') { if (!ok) throw new Error(code); }
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
function guardTarget(meta, receipt, baseline) {
  requireSafe(/^[a-f0-9]{16}$/.test(meta.run));
  requireSafe(['synthetic-target','original-target'].includes(meta.role));
  requireSafe(meta.project === `classifieds-rebuild-recovery-${meta.run}-${meta.role}`);
  for (const k of ['run','role','project','image']) requireSafe(meta[k] === receipt[k]);
  requireSafe(meta.image === baseline.image && receipt.containerIds.includes(meta.id));
  requireSafe(!baseline.containerIds.includes(meta.id) && /^[a-f0-9]{64}$/.test(meta.id));
  requireSafe(meta.empty === true && meta.privileged === false && meta.capAdd.length === 0);
  requireSafe(meta.ports.length === 0 && !['host','none'].includes(meta.networkMode));
  requireSafe(meta.networkIds.length === 1 && new Set(meta.networkIds).size === meta.networkIds.length);
  for (const n of meta.networkIds) requireSafe(receipt.networkIds.includes(n) && !baseline.networkIds.includes(n));
  for (const m of meta.mounts) {
    requireSafe((m.type === 'tmpfs' && ['/data','/var/lib/postgresql/data','/var/lib/classifieds/media','/tmp','/run','/dev/shm'].includes(m.target)) ||
      (m.type === 'bind' && m.target === '/ops' && m.rw === false && m.source === receipt.opsRoot &&
        typeof m.source==='string' && path.resolve(m.source)===path.resolve(__dirname)));
    requireSafe(!baseline.volumeNames.includes(m.name));
  }
  return freeze(structuredClone(meta));
}
function guardSource(meta, baseline) {
  requireSafe(meta.manifest === baseline.manifest && meta.image === baseline.image);
  requireSafe(['synthetic','original'].includes(meta.mode));
  requireSafe(baseline.sources?.some(s => JSON.stringify(s) === JSON.stringify(meta)));
  return freeze(structuredClone(meta));
}
function validateArchiveMember(name,type,size,inventory,seen) {
  requireSafe(typeof name === 'string' && /^[A-Za-z0-9_.\/-]+$/.test(name));
  requireSafe(name.split('/').every(p => p && p !== '.' && p !== '..'));
  requireSafe(type === 'file' && Number.isSafeInteger(size) && size >= 0 && size <= 512*1024*1024);
  requireSafe(inventory.has(name) && inventory.get(name) === size && !seen.has(name));
  seen.add(name); return true;
}
function guardDirectory(target, root) {
  const base=path.resolve(root), full=path.resolve(target);
  requireSafe(!full.startsWith('\\\\') && (full === base || full.startsWith(base + path.sep)), 'path_refused');
  let current=full;
  while (true) {
    if(fs.existsSync(current)) {
      const stat=fs.lstatSync(current);
      requireSafe(!stat.isSymbolicLink() && stat.isDirectory(), 'path_refused');
      requireSafe(path.resolve(fs.realpathSync.native(current)).toLowerCase() === current.toLowerCase(), 'path_refused');
    }
    const parent=path.dirname(current); if(parent===current) break; current=parent;
  }
  return full;
}
module.exports = { guardTarget, guardSource, validateArchiveMember, guardDirectory, requireSafe, freeze };
