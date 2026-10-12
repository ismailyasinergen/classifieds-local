/* Pure guard/diagnostic tests: no Docker, browser, credentials or project writes. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runner = path.join(__dirname, 'mfa.cjs');
const root = 'C:/Users/ismai/.devspace/worktrees/classifieds_local-a7be577c';
const base = 'http://localhost:8089';
function helpers() {
  assert.ok(fs.existsSync(runner), 'Guarded MFA browser runner is not implemented.');
  return require(runner);
}
function runtime() {
  const records = [];
  for (const project of ['classifieds-rebuild-dev', 'classifieds-rebuild']) {
    for (const service of ['web', 'db', 'redis']) {
      const developer = project.endsWith('-dev');
      const source = developer ? root : 'C:/Users/ismai/Desktop/classifieds_local';
      const network = project + '_default';
      const record = { id: project + '-' + service, project, service, oneoff: 'False', running: true,
        workingDirectory: source + '/rebuild',
        configFiles: source + '/rebuild/compose.yaml' + (developer ? ',' + source + '/rebuild/compose.dev.yaml' : ''),
        mounts: [], networks: { [network]: { NetworkID: network + '-id', IPAddress: '192.0.2.10' } }, ports: {} };
      if (service === 'web') {
        record.mounts = [{ Destination: '/app', Type: 'bind', Source: source + '/rebuild/backend', RW: false },
          { Destination: '/var/lib/classifieds/media', Type: 'volume', Name: project + '_rebuild_media' }];
        record.ports = { '8000/tcp': [{ HostIp: '127.0.0.1', HostPort: developer ? '8089' : '8088' }] };
      } else {
        record.mounts = [{ Destination: service === 'db' ? '/var/lib/postgresql/data' : '/data', Type: 'volume',
          Name: project + (service === 'db' ? '_rebuild_postgres' : '_rebuild_redis') }];
        record.ports = { [service === 'db' ? '5432/tcp' : '6379/tcp']: null };
      }
      records.push(record);
    }
  }
  return records;
}
test('accept exact isolated runtime and return only independently resolved DB address', () => {
  assert.equal(helpers().validateRuntime(root, base, runtime()), '192.0.2.10');
});
test('reject original root, suffix-only spoof, non-loopback and wrong port origins', () => {
  const { validateRuntime } = helpers();
  for (const wrong of ['C:/Users/ismai/Desktop/classifieds_local', 'D:' + root.slice(2), root + '-other'])
    assert.throws(() => validateRuntime(wrong, base, runtime()));
  for (const wrong of ['http://localhost:8088', 'http://127.0.0.1:8089', 'https://example.invalid:8089'])
    assert.throws(() => validateRuntime(root, wrong, runtime()));
});
test('reject wrong labels, one-off service, writable/source-swapped mount and extra port', () => {
  const { validateRuntime } = helpers();
  for (const mutation of [
    data => { data[0].project = 'classifieds-rebuild'; },
    data => { data[0].service = 'worker'; },
    data => { data[0].oneoff = 'True'; },
    data => { data[0].running = false; },
    data => { data[0].mounts[0].RW = true; },
    data => { data[0].mounts[0].Source = 'C:/Users/ismai/Desktop/classifieds_local/rebuild/backend'; },
    data => { data[0].ports['8000/tcp'].push({ HostIp: '0.0.0.0', HostPort: '8089' }); },
    data => { data[0].configFiles = root + '/rebuild/compose.yaml'; },
  ]) { const data = runtime(); mutation(data); assert.throws(() => validateRuntime(root, base, data)); }
});
test('reject original/developer shared IDs, volumes, networks and exposed persistent service', () => {
  const { validateRuntime } = helpers();
  for (const mutation of [
    data => { data[1].id = data[4].id; },
    data => { data[1].mounts[0].Name = data[4].mounts[0].Name; },
    data => { data[1].networks.foreign = data[4].networks['classifieds-rebuild_default']; },
    data => { data[4].networks.foreign = data[1].networks['classifieds-rebuild-dev_default']; },
    data => { data[2].ports['6379/tcp'] = [{ HostIp: '127.0.0.1', HostPort: '6379' }]; },
  ]) { const data = runtime(); mutation(data); assert.throws(() => validateRuntime(root, base, data)); }
});
test('failure projection never contains framework message, stack or untrusted labels', () => {
  const { failureRecord } = helpers();
  const canary = 'synthetic-hidden-field-canary-938';
  const error = new Error('Locator value=' + canary); error.name = canary;
  const record = failureRecord(canary, canary, error);
  assert.equal(JSON.stringify(record).includes(canary), false);
  assert.deepEqual(record, { stage: 'unknown', operation: 'unknown', kind: 'verification_error' });
});
test('forbidden-response diagnostics expose only constant reason categories', () => {
  const { forbiddenDiagnosis } = helpers();
  assert.equal(typeof forbiddenDiagnosis, 'function');
  assert.equal(forbiddenDiagnosis('CSRF verification failed. CSRF cookie not set. hidden-canary'), 'csrf_cookie_missing');
  assert.equal(forbiddenDiagnosis('CSRF verification failed. Origin checking failed: hidden-canary'), 'csrf_origin');
  assert.equal(forbiddenDiagnosis('CSRF token from POST incorrect. hidden-canary'), 'csrf_token');
  assert.equal(forbiddenDiagnosis('Unrecognized hidden-canary'), 'other_forbidden');
});
test('screenshot allowlist rejects sensitive surfaces even when URL appears acceptable', () => {
  const { screenshotAllowed } = helpers();
  assert.equal(screenshotAllowed(base + '/accounts/security/', base, false), true);
  assert.equal(screenshotAllowed(base + '/accounts/security/', base, true), false);
  for (const route of ['/accounts/2fa/', '/accounts/2fa/totp/activate/', '/accounts/login/', '/admin/'])
    assert.equal(screenshotAllowed(base + route, base, false), false);
  assert.equal(screenshotAllowed('https://example.invalid/accounts/security/', base, false), false);
});
