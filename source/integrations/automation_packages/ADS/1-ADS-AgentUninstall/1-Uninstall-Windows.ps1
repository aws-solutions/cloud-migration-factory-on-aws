  param ($Servername,
       [string] $windowsuser = [System.Management.Automation.Language.NullString]::Value,
       [string] $windowspwd = [System.Management.Automation.Language.NullString]::Value,
       $harduninstall = 'No',
       $agent_download_url = [System.Management.Automation.Language.NullString]::Value,
       [bool] $usessl = $false
 )

# Read Server name #

function agent-uninstall {
  $sessionoptions = New-PSSessionOption -SkipCACheck
  $sessionoption_wsman = New-WSManSessionOption -SkipCACheck

  # If windowsuser is not set then the script will use intergarted authentication based on the the credentials of the user running the script.
  # when run through SSM this will be the localsystem account which will restrict the access and capabilities of the script.
  if ("" -ne $windowsuser)
  {
    $creds = New-Object System.Management.Automation.PSCredential($windowsuser, (ConvertTo-SecureString $windowspwd -AsPlainText -Force))
  }
  else
  {
    $creds = $null
  }

  if ($Servername -ne "") {
    foreach ($machine in $Servername) {
      $parameters_test_installed = @{
        ComputerName  = $machine
        UseSSL        = $usessl
        ScriptBlock   = {Get-WmiObject -Class Win32_Product | Where-Object{ $_.Name -eq "AWS Discovery Agent" }}
        SessionOption = $sessionoptions
        Credential    = $creds
      }

      if (!(Invoke-Command @parameters_test_installed)) {
        write-host
        write-host "** Agent not installed skipping uninstallation for : $machine **"
        write-host
      } else {
        write-host
        write-host "** Uninstalling ADS agent from : $machine **"
        write-host
        if ($harduninstall -eq 'Yes') {
          write-host "** Downloading installer to perform complete removal of ADS **"
          # Download original installer and run uninstall to completely remove the agent.
          $parameters_test_path = @{
            ComputerName = $machine
            UseSSL = $usessl
            ScriptBlock = { Test-path "c:\Scripts\" }
            SessionOption = $sessionoptions
            Credential = $creds
          }
          $parameters_create_path = @{
            ComputerName = $machine
            UseSSL = $usessl
            ScriptBlock = { New-Item -Path "c:\Scripts\" -ItemType directory }
            SessionOption = $sessionoptions
            Credential = $creds
          }
          if (!(Invoke-Command @parameters_test_path))
          {
            Invoke-Command @parameters_create_path
          }
          $download_command = {
            param($agent_download_url)
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            (New-Object System.Net.WebClient).DownloadFile("$agent_download_url", "c:\Scripts\AWSDiscoveryAgentInstaller.exe")
          }
          $parameters_download = @{
            ComputerName = $machine
            UseSSL = $usessl
            ScriptBlock = $download_command
            SessionOption = $sessionoptions
            Credential = $creds
            ArgumentList = $agent_download_url
          }
          Invoke-Command @parameters_download

          $parameters_test_path.ScriptBlock = { Test-path "c:\Scripts\AWSDiscoveryAgentInstaller.exe" }
          $fileexist = Invoke-Command @parameters_test_path

          if ($fileexist -eq "true")
          {
            $message = "** Successfully downloaded Agent installer for: " + $machine + " **"
            Write-Host $message
            write-host

            $arguments = @()
            $arguments += "/uninstall"
            $arguments += "/quiet"

            $command = {
              param($arguments)

              $result = Start-Process -FilePath "c:\Scripts\AWSDiscoveryAgentInstaller.exe" -ArgumentList $arguments -Wait -WorkingDirectory "c:\Scripts\"
              write-host $result
            }

            $parameters_uninstall = @{
              ComputerName = $machine
              UseSSL = $usessl
              ScriptBlock = $command
              SessionOption = $sessionoptions
              Credential = $creds
              ArgumentList = @(,$arguments)
            }

            $result = Invoke-Command @parameters_uninstall

          } else {
            $message = "** Agent Installer was not found on: " + $machine + " **"
            Write-Host $message
          }
        } else {
          write-host "** Removing ADS services and stopping processes **"
          # soft uninstall this will remove services and stop processes, but if reinstall required then a repair of package is needed.

          $command = {
            $Prod = Get-WMIObject -Classname Win32_Product | Where-Object Name -Match  $AgentWMIName
            $Prod.UnInstall()
          }

          $parameters_uninstall = @{
            ComputerName = $machine
            UseSSL = $usessl
            ScriptBlock = $command
            SessionOption = $sessionoptions
            Credential = $creds
            ArgumentList = @(,$arguments)
          }

          $install_return = Invoke-Command @parameters_uninstall
        }

         write-host
         write-host "** Uninstallation finished for : $machine **"
         write-host
      }
    }
  }
}

agent-uninstall


