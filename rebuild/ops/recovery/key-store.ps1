param([ValidateSet('None','Read','Create','CreateRepository','CheckRepository')][string]$Mode = 'None', [string]$RepoId)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security

function Assert-RecoveryContext {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $expected = New-Object Security.Principal.NTAccount($env:COMPUTERNAME, 'ismai')
    if ($identity.User.Value -ne $expected.Translate([Security.Principal.SecurityIdentifier]).Value -or
        [Environment]::GetFolderPath('UserProfile') -ne 'C:\Users\ismai' -or
        [Environment]::GetFolderPath('LocalApplicationData') -ne 'C:\Users\ismai\AppData\Local') { throw 'key_context_refused' }
    return $identity.User
}
function Assert-RecoveryPath([string]$Path) {
    $root = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClassifiedsRecovery\phase7'
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'key_path_refused' }
    $part = $full
    while ($part) {
        if (Test-Path -LiteralPath $part) {
            if ((Get-Item -LiteralPath $part -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'key_reparse_refused' }
        }
        $part = [IO.Path]::GetDirectoryName($part)
    }
    return $full
}
function Assert-RecoveryAcl([string]$Path) {
    $sid = Assert-RecoveryContext
    $acl = Get-Acl -LiteralPath $Path
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $sid.Value) { throw 'key_owner_refused' }
    foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow -and
            $rule.IdentityReference.Value -notin @($sid.Value,'S-1-5-18')) { throw 'key_acl_refused' }
    }
}
function New-RecoveryDirectory([string]$Path) {
    $sid = Assert-RecoveryContext
    $full = Assert-RecoveryPath $Path
    if (Test-Path -LiteralPath $full) {
        if (-not (Test-Path -LiteralPath $full -PathType Container)) { throw 'key_path_refused' }
        Assert-RecoveryAcl $full
        return $full
    }
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetOwner($sid)
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($principal in @($sid,(New-Object Security.Principal.SecurityIdentifier('S-1-5-18')))) {
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($principal,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
        $acl.AddAccessRule($rule)
    }
    [IO.Directory]::CreateDirectory($full,$acl) | Out-Null
    Assert-RecoveryAcl $full
    return $full
}
function Get-RecoveryKey {
    param([string]$RepoId, [switch]$Create)
    $sid = Assert-RecoveryContext
    if ($RepoId -notmatch '\A(?:[a-f0-9]{16}|[a-f0-9]{32})\z') { throw 'key_id_refused' }
    $root = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClassifiedsRecovery\phase7\keys'
    $file = Assert-RecoveryPath (Join-Path $root ($RepoId + '.dpapi'))
    $entropy = [Text.Encoding]::UTF8.GetBytes('classifieds-phase7-repository-v1:' + $RepoId)
    if ($Create) {
        if (Test-Path -LiteralPath $file) { throw 'key_exists' }
        New-RecoveryDirectory $root | Out-Null
        $key = New-Object byte[] 32
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($key) } finally { $rng.Dispose() }
        $encrypted = [Security.Cryptography.ProtectedData]::Protect($key,$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
        $envelope = @{ format='classifieds-dpapi-currentuser-v1'; repoId=$RepoId; user=$sid.Value; blob=[Convert]::ToBase64String($encrypted) } | ConvertTo-Json -Compress
        $stream = [IO.File]::Open($file,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {
            $bytes = [Text.Encoding]::UTF8.GetBytes($envelope)
            $stream.Write($bytes,0,$bytes.Length)
            $stream.Flush($true)
        } finally { $stream.Dispose(); [Array]::Clear($key,0,$key.Length) }
    }
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw 'key_missing' }
    Assert-RecoveryAcl $root
    Assert-RecoveryAcl $file
    if ((Get-Item -LiteralPath $file).Length -gt 16384) { throw 'key_envelope_refused' }
    try {
        $value = [IO.File]::ReadAllText($file) | ConvertFrom-Json
        if ($value.format -ne 'classifieds-dpapi-currentuser-v1' -or $value.repoId -ne $RepoId -or $value.user -ne $sid.Value) { throw 'key_envelope_refused' }
        $key = [Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($value.blob),$entropy,[Security.Cryptography.DataProtectionScope]::CurrentUser)
        if ($key.Length -ne 32) { throw 'key_envelope_refused' }
        return ,$key
    } catch { throw 'key_envelope_refused' }
}
if ($Mode -in @('CreateRepository','CheckRepository')) {
    try {
        Assert-RecoveryContext | Out-Null
        if ($RepoId -notmatch '\A[a-f0-9]{32}\z') { throw 'key_id_refused' }
        $parent = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'ClassifiedsRecovery\phase7\repositories'
        $target = Assert-RecoveryPath (Join-Path $parent $RepoId)
        if ($Mode -eq 'CreateRepository') {
            if (Test-Path -LiteralPath $target) { throw 'repository_exists' }
            New-RecoveryDirectory $parent | Out-Null
            New-RecoveryDirectory $target | Out-Null
        } else {
            if (-not (Test-Path -LiteralPath $target -PathType Container)) { throw 'repository_missing' }
            Assert-RecoveryAcl $parent
            Assert-RecoveryAcl $target
        }
    } catch { [Console]::Error.WriteLine('repository_create_failed'); exit 1 }
}
if ($Mode -in @('Read','Create')) {
    try {
        $key = Get-RecoveryKey -RepoId $RepoId -Create:($Mode -eq 'Create')
        $output = [Console]::OpenStandardOutput()
        $output.Write($key,0,$key.Length)
        $output.Flush()
        [Array]::Clear($key,0,$key.Length)
    } catch { [Console]::Error.WriteLine('key_read_failed'); exit 1 }
}
