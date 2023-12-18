  param (
   [bool] $reinstall = $false,
   $agent_download_url,
   $region,
   $accesskeyid,
   $secretaccesskey,
   $sessiontoken,
   $Servername,
   [string] $windowsuser = [System.Management.Automation.Language.NullString]::Value,
   [string] $windowspwd = [System.Management.Automation.Language.NullString]::Value,
   $s3endpoint,
   $mgnendpoint,
   [bool] $usessl = $false
 )

# Read Server name #

function agent-install {
  $ScriptPath = "c:\Scripts\"

  # Determine download path for agent based on if using s3 endpoints or public.
  if ("$s3endpoint".Trim() -ne "") {
    # S3 Endpoints use certificates based on the parent S3 domain excluding the vpc endpoint name, this means
    # the certificate name and the dns name used do not match and causes errors in verification of cert auth
    # we disable checks for cert auth when using s3 endpoints only.
    $download_command = {
      param($agent_download_url)
      [System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}
      [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
      (New-Object System.Net.WebClient).DownloadFile("$agent_download_url",'C:\Scripts\AwsReplicationWindowsInstaller.exe')
      }
  }
  else {
    $download_command = {
      param($agent_download_url)
      [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
      (New-Object System.Net.WebClient).DownloadFile("$agent_download_url",'C:\Scripts\AwsReplicationWindowsInstaller.exe')
      }
  }

  # If windowsuser is not set then the script will use intergarted authentication based on the the credentials of the user running the script.
  # when run through SSM this will be the localsystem account which will restrict the access and capabilities of the script.
  if ("" -ne $windowsuser)
  {
    $creds = New-Object System.Management.Automation.PSCredential($windowsuser, (ConvertTo-SecureString $windowspwd -AsPlainText -Force))
  } else
  {
    $creds = $null
  }

  $sessionoptions = New-PSSessionOption -SkipCACheck
  $sessionoption_wsman = New-WSManSessionOption -SkipCACheck

  if ($Servername -ne "") {
    foreach ($machine in $Servername) {
      $parameters_wsman = @{
        ComputerName  = $machine
        UseSSL        = $usessl
      }
      if (!(Test-WSMan @parameters_wsman))
      {
        $cert_error = $false
        foreach ($error_item in $Error) {
          if ($error_item.ToString().Contains("unknown certificate authority")){
            #   Ignore any CA check errors as connection was successful.
            $cert_error = $true
            break
          }
        }

        if (!($cert_error)){
            write-host "ERROR: Cannot connect to WinRM on server." -BackgroundColor Red
            exit 1
        }
      }

      $parameters = @{
        ComputerName  = $machine
        UseSSL        = $usessl
        ScriptBlock   = {Test-path "C:\Program Files (x86)\AWS Replication Agent\dist\windows_service_wrapper.exe"}
        SessionOption = $sessionoptions
        Credential    = $creds
      }
      if ($reinstall -or (!(Invoke-Command @parameters))) {
        write-host "----------------------------------------------------------------------------"
        write-host "- Installing Application Migration Service Agent for:   $machine -" -BackgroundColor Blue
        write-host "----------------------------------------------------------------------------"
        $parameters.ScriptBlock = {Test-path "c:\Scripts\"}
        if (!(Invoke-Command @parameters)) {
          $parameters.ScriptBlock = {New-Item -Path "c:\Scripts\" -ItemType directory}
          Invoke-Command @parameters
        }

        $parameters_download = @{
          ComputerName  = $machine
          UseSSL        = $usessl
          ScriptBlock   = $download_command
          SessionOption = $sessionoptions
          Credential    = $creds
          ArgumentList  = $agent_download_url
        }
        Invoke-Command @parameters_download
        $parameters.ScriptBlock = {Test-path "c:\Scripts\AwsReplicationWindowsInstaller.exe"}
        $fileexist = Invoke-Command @parameters

        if ($fileexist -eq "true") {
          $message = "** Successfully downloaded Agent installer for: " + $machine + " **"
          Write-Host $message
        }

        # add session token parameter to install if set.
        if ("$sessiontoken".Trim() -ne "") {
            $command = $ScriptPath + "AwsReplicationWindowsInstaller.exe --region " + $region + " --aws-access-key-id " + $accesskeyid + " --aws-secret-access-key " + $secretaccesskey + " --aws-session-token " + $sessiontoken + " --no-prompt"
            $display_command = $ScriptPath + "AwsReplicationWindowsInstaller.exe --region " + $region + " --aws-access-key-id ***** --aws-secret-access-key ***** --aws-session-token ***** --no-prompt"
        }
        else {
            $command = $ScriptPath + "AwsReplicationWindowsInstaller.exe --region " + $region + " --aws-access-key-id " + $accesskeyid + " --aws-secret-access-key " + $secretaccesskey + " --no-prompt"
            $display_command = $ScriptPath + "AwsReplicationWindowsInstaller.exe --region " + $region + " --aws-access-key-id ***** --aws-secret-access-key ***** --no-prompt"
        }

        # add s3 endpoint parameter to installation command if set.
        if ("$s3endpoint".Trim() -ne "") {
            $command += " --s3-endpoint " + $s3endpoint
            $display_command += " --s3-endpoint " + $s3endpoint
        }

        # add mgn endpoint parameter to installation command if set.
        if ("$mgnendpoint".Trim() -ne "") {
            $command += " --endpoint " + $mgnendpoint
            $display_command += " --endpoint " + $mgnendpoint
        }
        write-host "Running command $display_command."
        $scriptblock2 = $executioncontext.invokecommand.NewScriptBlock($command)
        $parameters = @{
          ComputerName  = $machine
          UseSSL        = $usessl
          ScriptBlock   = $scriptblock2
          SessionOption = $sessionoptions
          Credential    = $creds
        }
        $result = Invoke-Command @parameters
        write-host $result
        write-host
        write-host "** Installation finished for : $machine **"
        write-host
        exit 0
      }
      else {
       $message = "Agent already installed for machine: " + $machine + " , please reinstall manually if required"
       write-host $message -BackgroundColor Red
       exit 0
      }
    }
  } else {
   write-host "ERROR: Server name parameter not provided." -BackgroundColor Red
   exit 1
  }
}

agent-install
