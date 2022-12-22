param (
	$Username,
	$Password,
	$Server,
	$wantedApplications,
	$unwantedApplications,
	$runningApplications
)

#$session = &".\0-Session-Creation.ps1" -user $Username -password "$($Password)" -hostname $Server
#$session
$path = $PSScriptRoot

function Get_Creds {
    [CmdletBinding()]
    param(
        [String] $user,
        [String] $password
    )

    if ($user -ne "") {
        $creds = New-Object System.Management.Automation.PSCredential($user, (ConvertTo-SecureString $password -AsPlainText -Force))
    }
    return $creds
}

function Create_PSSession {
	param(
		[System.Management.Automation.PSCredential] $creds,
		[String] $hostname
	)

    <#
	Write-Host
	Write-Host "$Server : Attempting Session Creation"
	Write-Host
    #>
	$SessionOpt = ''
	$error.clear()

    <#
	Write-Host
	Write-Host "$Server : Trying without Session Option"
	Write-Host
    #>
	$session = New-PSSession -ComputerName $hostname -Credential $creds -ErrorAction SilentlyContinue

	if ((-not $session) -and ($error)) {
        <#
		Write-Host
		Write-Host "$Server : Trying with Session Option"
		Write-Host
        #>
		$SessionOpt = New-PSSessionOption -IncludePortInSPN
		$session = New-PSSession -ComputerName $hostname -Credential $creds -SessionOpt $SessionOpt -ErrorAction SilentlyContinue
		if ((-not $session) -and ($error)) {

			Write-Host
			Write-Host $error -BackgroundColor Red -ForegroundColor Black
			Write-Host

		}
		else {
            <#
			Write-Host
			Write-Host "$Server : Created Session..."
			Write-Host
            #>
			return $session
		}
	}
	else {
        <#
		Write-Host
		Write-Host "$Server : Created Session..."
		Write-Host
        #>
		return $session
	}
}

$creds = Get_Creds -user $Username -password $Password
$session = Create_PSSession -creds $creds -hostname $Server


try {
	Invoke-Command -Session $session -FilePath ".\Software-Validation-Windows.ps1" -ArgumentList $wantedApplications,$unwantedApplications,$runningApplications
}
catch {
	if ($session) {
		Remove-PSSession -Session $session
	}
}