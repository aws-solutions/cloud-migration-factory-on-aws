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
        if ($reinstall -eq 'Yes' -or ($reinstall -ne 'Yes' -and (!(Invoke-Command -ComputerName $machine -ScriptBlock {Get-WmiObject -Class Win32_Product | Where-Object{$_.Name -eq "AWS Discovery Agent"}} -Credential $creds)))) {
          write-host "----------------------------------------------------------------------------"
          write-host "- Installing Application Discovery Service Agent for:   $machine -" -BackgroundColor Blue
          write-host "----------------------------------------------------------------------------"
         if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\"} -Credential $creds)) {Invoke-Command -ComputerName $machine -ScriptBlock {New-Item -Path "c:\Scripts\" -ItemType directory} -Credential $creds}
          $download_command = "(New-Object System.Net.WebClient).DownloadFile('" + $agent_download_url + "','C:\Scripts\AWSDiscoveryAgentInstaller.exe')"
          $scriptblock = $executioncontext.invokecommand.NewScriptBlock($download_command)
          Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock -Credential $creds
          $fileexist = Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\AWSDiscoveryAgentInstaller.exe"} -Credential $creds
          if ($fileexist -eq "true") {
            $message = "** Successfully downloaded Agent installer for: " + $machine + " **"
            Write-Host $message
            write-host

            $arguments = @()
            $arguments += "REGION=$($region)"
            $arguments += "KEY_ID=$($accesskeyid)"
            $arguments += "KEY_SECRET=$($secretaccesskey)"
            $arguments += "/log $($ScriptPath)install.log"
            $arguments += "/quiet"

            $command = {
                param($arguments)

                $result = Start-Process -FilePath "C:\Scripts\AWSDiscoveryAgentInstaller.exe" -ArgumentList $arguments -Wait -WorkingDirectory "C:\Scripts\"
                write-host $result
            }
            $result = Invoke-Command -ComputerName $machine -ScriptBlock $command -ArgumentList @(,$arguments)-Credential $creds
            write-host "$install_return"
            write-host "run command $command_secret"
            write-host "** Installation finished for : $machine **"
            write-host
          }
          else {
            $message = "** Agent Installer was not found on: " + $machine + " **"
            Write-Host $message
          }
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
        if ($reinstall -eq 'Yes' -or ($reinstall -eq 'No' -and (!(Invoke-Command -ComputerName $machine -ScriptBlock {Get-WmiObject -Class Win32_Product | Where-Object{$_.Name -eq "AWS Discovery Agent"}})))) {
          write-host "----------------------------------------------------------------------------"
          write-host "- Installing Application Discovery Service Agent for:   $machine -" -BackgroundColor Blue
          write-host "----------------------------------------------------------------------------"
          if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\"})) {Invoke-Command -ComputerName $machine -ScriptBlock {New-Item -Path "c:\Scripts\" -ItemType directory}}
          $download_command = "(New-Object System.Net.WebClient).DownloadFile('" + $agent_download_url + "','C:\Scripts\AWSDiscoveryAgentInstaller.exe')"
          $scriptblock = $executioncontext.invokecommand.NewScriptBlock($download_command)
          Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock
          $fileexist = Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\AWSDiscoveryAgentInstaller.exe"}
          if ($fileexist -eq "true") {
            $message = "** Successfully downloaded Agent installer for: " + $machine + " **"
            Write-Host $message

            $arguments = @()
            $arguments += "REGION=$($region)"
            $arguments += "KEY_ID=$($accesskeyid)"
            $arguments += "KEY_SECRET=$($secretaccesskey)"
            $arguments += "/log $($ScriptPath)install.log"
            $arguments += "/quiet"

            $command = {
                param($arguments)

                $result = Start-Process -FilePath "C:\Scripts\AWSDiscoveryAgentInstaller.exe" -ArgumentList $arguments -Wait -WorkingDirectory "C:\Scripts\"
                write-host $result
            }
            $result = Invoke-Command -ComputerName $machine -ScriptBlock $command -ArgumentList @(,$arguments)-Credential
            write-host
            write-host "** Installation finished for : $machine **"
            write-host
            }
            else{
              $message = "** Agent Installer was not found on: " + $machine + " **"
              Write-Host $message
            }
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
