param([switch]$AclOnly)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../key-store.ps1')
. (Join-Path $PSScriptRoot 'acl-fixture.ps1')
if ($AclOnly) {
    $result=Invoke-RecoveryAclFixture
    $result | ConvertTo-Json -Depth 5 -Compress
    if (-not $result.pass) { exit 1 }
    exit 0
}
$repoId = [Guid]::NewGuid().ToString('N')
$checks = 0
function Assert-Refused([scriptblock]$Action) {
    $refused = $false
    try { & $Action | Out-Null } catch { $refused = $true }
    if (-not $refused) { throw 'assertion_missing_key_was_accepted' }
}
try {
    Assert-Refused { Get-RecoveryKey -RepoId $repoId }
    $checks++
    $key = Get-RecoveryKey -RepoId $repoId -Create
    $again = Get-RecoveryKey -RepoId $repoId
    if ($key.Length -ne 32 -or [Convert]::ToBase64String($key) -ne [Convert]::ToBase64String($again)) { throw 'assertion_roundtrip' }
    if (($key | Where-Object { $_ -ne 0 }).Count -eq 0) { throw 'assertion_not_random' }
    if ([Convert]::ToBase64String($key) -eq [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(('s' * 32)))) { throw 'assertion_application_key_reused' }
    $checks++
    Assert-Refused { Get-RecoveryKey -RepoId $repoId -Create }
    Assert-Refused { Get-RecoveryKey -RepoId '../escape' -Create }
    $checks += 2
    $otherId = [Guid]::NewGuid().ToString('N')
    $other = Get-RecoveryKey -RepoId $otherId -Create
    if ([Convert]::ToBase64String($key) -eq [Convert]::ToBase64String($other)) { throw 'assertion_independent_keys' }
    $checks++
    $child = New-Object Diagnostics.Process
    $child.StartInfo = New-Object Diagnostics.ProcessStartInfo
    $child.StartInfo.FileName = Join-Path $PSHOME 'powershell.exe'
    $helper = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../key-store.ps1'))
    $child.StartInfo.Arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File "' + $helper + '" -Mode Read -RepoId ' + $repoId
    $child.StartInfo.UseShellExecute = $false
    $child.StartInfo.CreateNoWindow = $true
    $child.StartInfo.RedirectStandardOutput = $true
    $child.StartInfo.RedirectStandardError = $true
    $child.Start() | Out-Null
    $buffer = New-Object IO.MemoryStream
    $copy = $child.StandardOutput.BaseStream.CopyToAsync($buffer)
    $errorDrain = $child.StandardError.ReadToEndAsync()
    if (-not $child.WaitForExit(10000)) { $child.Kill(); throw 'assertion_child_timeout' }
    $copy.GetAwaiter().GetResult() | Out-Null
    if ($child.ExitCode -ne 0 -or $buffer.Length -ne 32 -or
        [Convert]::ToBase64String($key) -ne [Convert]::ToBase64String($buffer.ToArray())) { throw 'assertion_separate_process_roundtrip' }
    $buffer.Dispose()
    $child.Dispose()
    $checks++
    $root = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClassifiedsRecovery\phase7\keys'
    Assert-RecoveryAcl $root
    Assert-RecoveryAcl (Join-Path $root ($repoId + '.dpapi'))
    $checks++
    $wrongId = [Guid]::NewGuid().ToString('N')
    $wrong = [IO.File]::ReadAllText((Join-Path $root ($repoId + '.dpapi'))) | ConvertFrom-Json
    $wrong.repoId = $wrongId
    [IO.File]::WriteAllText((Join-Path $root ($wrongId + '.dpapi')),($wrong | ConvertTo-Json -Compress))
    Assert-Refused { Get-RecoveryKey -RepoId $wrongId }
    $checks++
    $wrong.user = 'S-1-0-0'
    [IO.File]::WriteAllText((Join-Path $root ($wrongId + '.dpapi')),($wrong | ConvertTo-Json -Compress))
    Assert-Refused { Get-RecoveryKey -RepoId $wrongId }
    $checks++
    Assert-Refused { New-RecoveryDirectory ([IO.Path]::GetTempPath()) }
    $checks++
    $aclResult=Invoke-RecoveryAclFixture
    if (-not $aclResult.pass) {
        $aclResult | ConvertTo-Json -Depth 5 -Compress
        throw 'assertion_acl_fixture_failed'
    }
    $checks++
    @{ pass=$true; checks=$checks; aclFixture=$aclResult; separateProcessRoundtrip=$true; retainedSyntheticKeyIds=@($repoId,$otherId,$wrongId) } | ConvertTo-Json -Depth 5 -Compress
} catch {
    @{ pass=$false; checks=$checks; category=if ($_.Exception.Message -like 'assertion_*') { $_.Exception.Message } else { 'key_test_failed' }; exceptionType=$_.Exception.GetType().FullName; scriptLine=$_.InvocationInfo.ScriptLineNumber } | ConvertTo-Json -Compress
    exit 1
}
