/* Read-only adoption probes. No file, credential, database or runtime mutations. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const developer = 'C:/Users/ismai/.devspace/worktrees/classifieds_local-a7be577c';
const original = 'C:/Users/ismai/Desktop/classifieds_local';
const digest = data => crypto.createHash('sha256').update(data).digest('hex');
const run = (program, args, cwd = original) => execFileSync(program, args, {
  cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 60000,
}).trim();
function requireTrue(condition) { if (!condition) throw new Error('Adoption guard failed.'); }
function read(relative) { return fs.readFileSync(path.join(developer, relative)); }
function norm(value) {
  return value.split(String.fromCharCode(92)).join('/').toLowerCase()
    .replace('/run/desktop/mnt/host/c/', 'c:/').replace('/host_mnt/c/', 'c:/');
}
function manifest() {
  const definition = JSON.parse(read('rebuild/docs/phase5/task-C-candidate-manifest.json'));
  for (const part of [definition.base, ...definition.overlays]) requireTrue(digest(read(part.path)) === part.sha256);
  const base = new Map(read(definition.base.path).toString('utf8').trim().split(/\r?\n/).map(line => [line.slice(66), line.slice(0, 64)]));
  const candidate = new Map(base);
  for (const overlay of definition.overlays) {
    for (const file of JSON.parse(read(overlay.path)).files) candidate.set(file.path, file[overlay.fileHashField]);
  }
  for (const [file, hash] of Object.entries(definition.overrides)) candidate.set(file, hash);
  const text = [...candidate.keys()].sort().map(file => candidate.get(file) + '  ' + file + '\n').join('');
  requireTrue(digest(text) === definition.materializedSha256);
  return { definition, base, candidate };
}
function sources() {
  const { definition, base, candidate } = manifest();
  const mismatches = [], pending = [], transferred = [], unchanged = [];
  for (const [file, hash] of candidate) {
    requireTrue(digest(read(file)) === hash);
    const target = path.join(original, file);
    const actual = fs.existsSync(target) ? digest(fs.readFileSync(target)) : null;
    if (actual === hash) (base.get(file) === hash ? unchanged : transferred).push(file);
    else if (actual === (base.get(file) || null)) pending.push(file);
    else mismatches.push(file);
  }
  return { manifest: definition.materializedSha256, paths: candidate.size,
    unchanged: unchanged.length, transferred: transferred.length, pending, conflicts: mismatches };
}
function runtime() {
  const projects = ['classifieds-rebuild', 'classifieds-rebuild-dev'];
  const names = projects.flatMap(project => ['web', 'worker', 'scheduler', 'db', 'redis'].map(service => project + '-' + service + '-1'));
  const format = '{"id":{{json .Id}},"image":{{json .Image}},"project":{{json (index .Config.Labels "com.docker.compose.project")}},' +
    '"service":{{json (index .Config.Labels "com.docker.compose.service")}},"configHash":{{json (index .Config.Labels "com.docker.compose.config-hash")}},' +
    '"state":{{json .State.Status}},"health":{{with index .State "Health"}}{{json .Status}}{{else}}null{{end}},' +
    '"mounts":{{json .Mounts}},"ports":{{json .NetworkSettings.Ports}},"networkIds":"{{range .NetworkSettings.Networks}}{{.NetworkID}} {{end}}"}';
  const rows = run('docker', ['inspect', '--format', format, ...names]).split(/\r?\n/).map(JSON.parse);
  return rows.map(row => {
    const app = ['web', 'worker', 'scheduler'].includes(row.service);
    const expected = norm((row.project.endsWith('-dev') ? developer : original) + '/rebuild/backend');
    const bind = row.mounts.filter(mount => mount.Destination === '/app');
    return { project: row.project, service: row.service, id: row.id, image: row.image,
      configHash: row.configHash, state: row.state, health: row.health,
      sourceMatches: !app || (bind.length === 1 && norm(bind[0].Source) === expected && bind[0].RW === false),
      volumes: row.mounts.filter(mount => mount.Type === 'volume').map(mount => mount.Name).sort(),
      ports: Object.values(row.ports || {}).flatMap(value => value || []).map(value => ({ host: value.HostIp, port: value.HostPort })),
      networkIds: row.networkIds.trim().split(/\s+/) };
  });
}
function configHashes(rows) {
  const configured = new Map(run('docker', ['compose', '-f', 'rebuild/compose.yaml', '-p', 'classifieds-rebuild', 'config', '--hash', '*']).split(/\r?\n/).map(line => line.split(' ')));
  return rows.filter(row => row.project === 'classifieds-rebuild').map(row => ({ service: row.service,
    matches: configured.get(row.service) === row.configHash, expected: row.configHash, actual: configured.get(row.service) }));
}
try {
  const action = process.argv[2];
  requireTrue(['sources', 'runtime', 'preflight', 'guard', 'final'].includes(action));
  const result = { atUTC: new Date().toISOString(), action };
  if (['sources', 'preflight', 'final'].includes(action)) {
    result.sources = sources(); requireTrue(result.sources.conflicts.length === 0);
    if (action === 'final') requireTrue(result.sources.pending.length === 0 && result.sources.transferred === 52);
  }
  if (['runtime', 'preflight', 'final'].includes(action)) {
    result.runtime = runtime();
    requireTrue(result.runtime.every(row => row.sourceMatches));
    if (action !== 'runtime') {
      requireTrue(result.runtime.every(row => row.state === 'running'));
      result.configHashes = configHashes(result.runtime);
      requireTrue(result.configHashes.every(row => row.matches));
    }
  }
  if (action === 'guard') {
    const { base, candidate } = manifest(); const files = process.argv.slice(3);
    requireTrue(files.length > 0);
    result.files = files.map(file => {
      requireTrue(candidate.has(file) && base.get(file) !== candidate.get(file));
      requireTrue(digest(read(file)) === candidate.get(file));
      const target = path.join(original, file);
      const actual = fs.existsSync(target) ? digest(fs.readFileSync(target)) : null;
      requireTrue(actual === (base.get(file) || null));
      return { path: file, beforeSha256: actual, expectedSha256: candidate.get(file) };
    });
  }
  result.pass = true; console.log(JSON.stringify(result, null, 2));
} catch {
  console.log(JSON.stringify({ pass: false, kind: 'read_only_adoption_guard_failed' })); process.exitCode = 1;
}
