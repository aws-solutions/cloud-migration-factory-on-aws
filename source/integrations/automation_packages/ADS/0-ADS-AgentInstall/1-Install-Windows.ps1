 param ($reinstall,
       $agent_download_url,
       $region,
       $accesskeyid,
       $secretaccesskey,
       $Servername,
       [string] $windowsuser = [System.Management.Automation.Language.NullString]::Value,
       [string] $windowspwd = [System.Management.Automation.Language.NullString]::Value,
       [bool] $usessl = $false
)

# Read Server name #

function agent-install
{
  $ScriptPath = "c:\Scripts\"

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

  if ($Servername -ne "")
  {
      foreach ($machine in $Servername)
      {
        $parameters_test_installed = @{
          ComputerName  = $machine
          UseSSL        = $usessl
          ScriptBlock   = {Get-WmiObject -Class Win32_Product | Where-Object{ $_.Name -eq "AWS Discovery Agent" }}
          SessionOption = $sessionoptions
          Credential    = $creds
        }
        if ($reinstall -eq 'Yes' -or ($reinstall -ne 'Yes' -and (!(Invoke-Command @parameters_test_installed))))
        {
          write-host "----------------------------------------------------------------------------"
          write-host "- Installing Application Discovery Service Agent for:   $machine -" -BackgroundColor Blue
          write-host "----------------------------------------------------------------------------"
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
            (New-Object System.Net.WebClient).DownloadFile("$agent_download_url", 'C:\Scripts\AWSDiscoveryAgentInstaller.exe')
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

          $parameters_test_path.ScriptBlock = { Test-path "C:\Scripts\AWSDiscoveryAgentInstaller.exe" }
          $fileexist = Invoke-Command @parameters_test_path

          if ($fileexist -eq "true")
          {
            $message = "** Successfully downloaded Agent installer for: " + $machine + " **"
            Write-Host $message
            write-host

            $arguments = @()
            $arguments += "REGION=$( $region )"
            $arguments += "KEY_ID=$( $accesskeyid )"
            $arguments += "KEY_SECRET=$( $secretaccesskey )"
            $arguments += "/log $( $ScriptPath )install.log"
            $arguments += "/quiet"

            $command = {
              param($arguments)

              $result = Start-Process -FilePath "C:\Scripts\AWSDiscoveryAgentInstaller.exe" -ArgumentList $arguments -Wait -WorkingDirectory "C:\Scripts\"
              write-host $result
            }

            $parameters_install = @{
              ComputerName = $machine
              UseSSL = $usessl
              ScriptBlock = $command
              SessionOption = $sessionoptions
              Credential = $creds
              ArgumentList = @(,$arguments)
            }

            $result = Invoke-Command @parameters_install
            write-host "$install_return"
            write-host "run command $command_secret"
            write-host "** Installation finished for : $machine **"
            write-host
          }
          else
          {
            $message = "** Agent Installer was not found on: " + $machine + " **"
            Write-Host $message
          }
        }
        else
        {
          $message = "Agent already installed for machine: " + $machine + " , please reinstall manually if required"
          write-host $message -BackgroundColor Red
        }
      }
    } else {
      write-host "ERROR: Server name parameter not provided." -BackgroundColor Red
      exit 1
    }
  }

agent-install

