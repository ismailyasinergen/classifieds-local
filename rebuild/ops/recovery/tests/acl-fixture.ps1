function Invoke-RecoveryAclFixture {
    $probe = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) ('ClassifiedsRecovery\phase7\acl-probe-' + [Guid]::NewGuid().ToString('N'))
    $access = [Security.AccessControl.AccessControlSections]::Access
    $result = @{ setup=$false; applicationRefused=$false; restored=$false; removed=$false; pass=$false; errors=@() }
    $stage = 'create'
    $created = $false
    $saved = $null
    function Get-DaclBytes($Security) {
        $raw=New-Object Security.AccessControl.RawSecurityDescriptor($Security.GetSecurityDescriptorBinaryForm(),0)
        $bytes=New-Object byte[] $raw.DiscretionaryAcl.BinaryLength
        $raw.DiscretionaryAcl.GetBinaryForm($bytes,0)
        return [Convert]::ToBase64String($bytes)
    }
    function Assert-OwnedEmptyProbe {
        if ((Assert-RecoveryPath $probe) -ne $probe) { throw 'fixture_identity_refused' }
        $item = Get-Item -LiteralPath $probe -Force
        if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
            $item.CreationTimeUtc.Ticks -ne $createdTicks -or @(Get-ChildItem -LiteralPath $probe -Force).Count -ne 0) { throw 'fixture_identity_refused' }
        $owner = (Get-Acl -LiteralPath $probe).GetOwner([Security.Principal.SecurityIdentifier])
        if ($owner.Value -ne (Assert-RecoveryContext).Value) { throw 'fixture_identity_refused' }
    }
    function Safe-FixtureError($ErrorRecord,[string]$At) {
        $ex = $ErrorRecord.Exception
        while ($ex.InnerException) { $ex = $ex.InnerException }
        $privilege = 'not_reported'
        if ($ex -is [Security.AccessControl.PrivilegeNotHeldException]) {
            $privilege = if ($ex.PrivilegeName -in @('SeSecurityPrivilege','SeRestorePrivilege','SeTakeOwnershipPrivilege')) { $ex.PrivilegeName } else { 'other_privilege' }
        }
        return @{stage=$At;exceptionType=$ex.GetType().FullName;privilegeCategory=$privilege}
    }
    try {
        if (Test-Path -LiteralPath $probe) { throw 'fixture_already_exists' }
        New-RecoveryDirectory $probe | Out-Null
        $created=$true
        $createdTicks=(Get-Item -LiteralPath $probe).CreationTimeUtc.Ticks
        Assert-OwnedEmptyProbe
        $original=[IO.Directory]::GetAccessControl($probe,$access)
        $saved=$original.GetSecurityDescriptorSddlForm($access)
        $savedDacl=Get-DaclBytes $original
        $protected=$original.AreAccessRulesProtected
        $stage='access_only_setup'
        $everyone=New-Object Security.Principal.SecurityIdentifier('S-1-1-0')
        $rule=New-Object Security.AccessControl.FileSystemAccessRule($everyone,'Read','Allow')
        $original.AddAccessRule($rule)
        [IO.Directory]::SetAccessControl($probe,$original)
        $readback=[IO.Directory]::GetAccessControl($probe,$access)
        $found=@($readback.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | Where-Object {
            $_.IdentityReference.Value -eq 'S-1-1-0' -and $_.AccessControlType -eq 'Allow' -and
            ($_.FileSystemRights -band [Security.AccessControl.FileSystemRights]::Read) -eq [Security.AccessControl.FileSystemRights]::Read
        })
        if ($found.Count -ne 1) { throw 'fixture_rule_not_persisted' }
        Assert-OwnedEmptyProbe
        $result.setup=$true
        $stage='application_guard'
        try { New-RecoveryDirectory $probe | Out-Null } catch {
            if ($_.Exception.Message -ne 'key_acl_refused') { throw }
            $result.applicationRefused=$true
        }
        if (-not $result.applicationRefused) { throw 'fixture_guard_accepted_broad_acl' }
    } catch { $result.errors += Safe-FixtureError $_ $stage }
    finally {
        if ($created -and $null -ne $saved) {
            try {
                Assert-OwnedEmptyProbe
                # Loading only Access marks the DACL modified even when the saved object was unchanged.
                $restore=New-Object Security.AccessControl.DirectorySecurity
                $restore.SetSecurityDescriptorSddlForm($saved,$access)
                $restore.SetAccessRuleProtection($protected,$false)
                [IO.Directory]::SetAccessControl($probe,$restore)
                $after=[IO.Directory]::GetAccessControl($probe,$access)
                if ((Get-DaclBytes $after) -ne $savedDacl -or $after.AreAccessRulesProtected -ne $protected) { throw 'fixture_restore_mismatch' }
                New-RecoveryDirectory $probe | Out-Null
                $result.restored=$true
                Assert-OwnedEmptyProbe
                [IO.Directory]::Delete($probe,$false)
                $result.removed=-not (Test-Path -LiteralPath $probe)
                if (-not $result.removed) { throw 'fixture_remove_failed' }
            } catch { $result.errors += Safe-FixtureError $_ 'cleanup_blocked' }
        } elseif ($created) {
            $result.errors += @{stage='cleanup_blocked';exceptionType='original_dacl_unavailable';privilegeCategory='not_reported'}
        }
    }
    $result.pass=$result.setup -and $result.applicationRefused -and $result.restored -and $result.removed -and $result.errors.Count -eq 0
    if (-not $result.removed) { $result.remainingProbe=[IO.Path]::GetFileName($probe) }
    return $result
}
