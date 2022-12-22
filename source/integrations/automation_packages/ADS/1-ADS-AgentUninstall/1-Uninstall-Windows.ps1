 param ($Servername,
       [string] $windowsuser = [System.Management.Automation.Language.NullString]::Value,
       [string] $windowspwd = [System.Management.Automation.Language.NullString]::Value,
       $harduninstall = 'No',
       $agent_download_url = [System.Management.Automation.Language.NullString]::Value)

# Read Server name #

function agent-uninstall {
  Param($Servername, [string] $windowsuserl = [System.Management.Automation.Language.NullString]::Value,
  [string] $windowspwdl = [System.Management.Automation.Language.NullString]::Value)
  $ScriptPath = "c:\Scripts\"
  if ("" -ne $windowsuserl)
  {
    if ($Servername -ne "") {

      $creds = New-Object System.Management.Automation.PSCredential($windowsuserl, (ConvertTo-SecureString $windowspwdl -AsPlainText -Force))

      foreach ($machine in $Servername) {
        if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Get-WmiObject -Class Win32_Product | Where-Object{$_.Name -eq "AWS Discovery Agent"}} -Credential $creds)) {
          write-host
          write-host "** Agent not installed skipping uninstallation for : $machine **"
          write-host
        }
        else {
         write-host
         write-host "** Uninstalling ADS agent from : $machine **"
         write-host
         if ($harduninstall -eq 'Yes'){
          write-host "** Downloading installer to perform complete removal of ADS **"
          # Download original installer and run uninstall to completely remove the agent.
          if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\"} -Credential $creds)) {Invoke-Command -ComputerName $machine -ScriptBlock {New-Item -Path "c:\Scripts\" -ItemType directory} -Credential $creds}
          $download_command = "(New-Object System.Net.WebClient).DownloadFile('" + $agent_download_url + "','C:\Scripts\AWSDiscoveryAgentInstaller.exe')"
          $scriptblock = $executioncontext.invokecommand.NewScriptBlock($download_command)
          Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock -Credential $creds
          $fileexist = Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\AWSDiscoveryAgentInstaller.exe"} -Credential $creds

          $arguments = @()
          $arguments += "/uninstall"
          $arguments += "/quiet"

          $command = {
              param($arguments)

              $result = Start-Process -FilePath "C:\Scripts\AWSDiscoveryAgentInstaller.exe" -ArgumentList $arguments -Wait -WorkingDirectory "C:\Scripts\"
              write-host $result
          }
           $result = Invoke-Command -ComputerName $machine -ScriptBlock $command -ArgumentList @(,$arguments)-Credential $creds
         } else {
           write-host "** Removing ADS services and stopping processes **"
           # soft uninstall this will remove services and stop processes, but if reinstall required then a repair of package is needed.
           $command = {
            $Prod = Get-WMIObject -Classname Win32_Product | Where-Object Name -Match  'AWS Discovery Agent'
            $Prod.UnInstall()
           }
            $install_return = Invoke-Command -ComputerName $machine -ScriptBlock $command -Credential $creds
         }

         write-host
         write-host "** Uninstallation finished for : $machine **"
         write-host
        }
      }
    }
  }
  else
  {
    if ($Servername -ne "") {
      foreach ($machine in $Servername) {
        if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Get-WmiObject -Class Win32_Product | Where-Object{$_.Name -eq "AWS Discovery Agent"}})) {
          write-host
          write-host "** Agent not installed skipping uninstallation for : $machine **"
          write-host

        }
        else {
          write-host
          write-host "** Uninstalling ADS agent from : $machine **"
          write-host
         if ($harduninstall -eq 'Yes'){
          # Download original installer and run uninstall to completely remove the agent.
          write-host "** Downloading installer to perform complete removal of ADS **"
          if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\"})) {Invoke-Command -ComputerName $machine -ScriptBlock {New-Item -Path "c:\Scripts\" -ItemType directory}}
          $download_command = "(New-Object System.Net.WebClient).DownloadFile('" + $agent_download_url + "','C:\Scripts\AWSDiscoveryAgentInstaller.exe')"
          $scriptblock = $executioncontext.invokecommand.NewScriptBlock($download_command)
          Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock
          $fileexist = Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\AWSDiscoveryAgentInstaller.exe"}

          $arguments = @()
          $arguments += "/uninstall"
          $arguments += "/quiet"

          $command = {
              param($arguments)

              $result = Start-Process -FilePath "C:\Scripts\AWSDiscoveryAgentInstaller.exe" -ArgumentList $arguments -Wait -WorkingDirectory "C:\Scripts\"
              write-host $result
          }
          $result = Invoke-Command -ComputerName $machine -ScriptBlock $command -ArgumentList @(,$arguments)
         } else {
           # soft uninstall this will remove services and stop processes, but if reinstall required then a repair of package is needed.
           write-host "** Removing ADS services and stopping processes **"
           $command = {
            $Prod = Get-WMIObject -Classname Win32_Product | Where-Object Name -Match  'AWS Discovery Agent'
            $Prod.UnInstall()
           }
           $install_return = Invoke-Command -ComputerName $machine -ScriptBlock $command
         }
          write-host
          write-host "** Uninstallation finished for : $machine **"
          write-host
        }
      }
    }
  }
}

agent-uninstall $Servername $windowsuser $windowspwd $harduninstall $agent_download_url

