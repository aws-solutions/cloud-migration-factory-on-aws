param ($reinstall,
       $agent_download_url,
       $region,
       $accesskeyid,
       $secretaccesskey,
       $Servername,
       [string] $windowsuser = [System.Management.Automation.Language.NullString]::Value,
       [string] $windowspwd = [System.Management.Automation.Language.NullString]::Value)

# Read Server name #

function agent-install {
  Param($agent_download_url, $region, $accesskeyid, $secretaccesskey, $Servername, [string] $windowsuserl = [System.Management.Automation.Language.NullString]::Value,
  [string] $windowspwdl = [System.Management.Automation.Language.NullString]::Value)
  $ScriptPath = "c:\Scripts\"
  if ("" -ne $windowsuserl)
  {
    if ($Servername -ne "") {

      $creds = New-Object System.Management.Automation.PSCredential($windowsuserl, (ConvertTo-SecureString $windowspwdl -AsPlainText -Force))

      foreach ($machine in $Servername) {
        if ($reinstall -eq 'Yes' -or ($reinstall -ne 'Yes' -and (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "C:\Program Files (x86)\AWS Replication Agent\dist\windows_service_wrapper.exe"} -Credential $creds)))) {
        write-host "----------------------------------------------------------------------------"
        write-host "- Installing Application Migration Service Agent for:   $machine -" -BackgroundColor Blue
        write-host "----------------------------------------------------------------------------"
        if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\"} -Credential $creds)) {Invoke-Command -ComputerName $machine -ScriptBlock {New-Item -Path "c:\Scripts\" -ItemType directory} -Credential $creds}
        $download_command = "(New-Object System.Net.WebClient).DownloadFile('" + $agent_download_url + "','C:\Scripts\AwsReplicationWindowsInstaller.exe')"
        $scriptblock = $executioncontext.invokecommand.NewScriptBlock($download_command)
        Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock -Credential $creds
        $fileexist = Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\AwsReplicationWindowsInstaller.exe"} -Credential $creds
        if ($fileexist -eq "true") {
          $message = "** Successfully downloaded Agent installer for: " + $machine + " **"
          Write-Host $message
           }
        $command = $ScriptPath + "AwsReplicationWindowsInstaller.exe --region " + $region + " --aws-access-key-id " + $accesskeyid + " --aws-secret-access-key " + $secretaccesskey + " --no-prompt"
        $scriptblock2 = $executioncontext.invokecommand.NewScriptBlock($command)
        Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock2 -Credential $creds
        write-host
        write-host "** Installation finished for : $machine **"
        write-host
        }
        else {
         $message = "Agent already installed for machine: " + $machine + " , please reinstall manually if required"
         write-host $message -BackgroundColor Red
        }
      }
    }
  }
  else
  {
    if ($Servername -ne "") {
      foreach ($machine in $Servername) {
        if ($reinstall -eq 'Yes' -or ($reinstall -eq 'No' -and (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "C:\Program Files (x86)\AWS Replication Agent\dist\windows_service_wrapper.exe"})))) {
        write-host "----------------------------------------------------------------------------"
        write-host "- Installing Application Migration Service Agent for:   $machine -" -BackgroundColor Blue
        write-host "----------------------------------------------------------------------------"
        if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\"})) {Invoke-Command -ComputerName $machine -ScriptBlock {New-Item -Path "c:\Scripts\" -ItemType directory}}
        $download_command = "(New-Object System.Net.WebClient).DownloadFile('" + $agent_download_url + "','C:\Scripts\AwsReplicationWindowsInstaller.exe')"
        $scriptblock = $executioncontext.invokecommand.NewScriptBlock($download_command)
        Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock
        $fileexist = Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\AwsReplicationWindowsInstaller.exe"}
        if ($fileexist -eq "true") {
          $message = "** Successfully downloaded Agent installer for: " + $machine + " **"
          Write-Host $message
           }
        $command = $ScriptPath + "AwsReplicationWindowsInstaller.exe --region " + $region + " --aws-access-key-id " + $accesskeyid + " --aws-secret-access-key " + $secretaccesskey + " --no-prompt"
        $scriptblock2 = $executioncontext.invokecommand.NewScriptBlock($command)
        Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock2
        write-host
        write-host "** Installation finished for : $machine **"
        write-host
        }
        else {
         $message = "Agent already installed for machine: " + $machine + " , please reinstall manually if required"
         write-host $message -BackgroundColor Red
        }
      }
    }
  }
}

agent-install $agent_download_url $region $accesskeyid $secretaccesskey $Servername $windowsuser $windowspwd
