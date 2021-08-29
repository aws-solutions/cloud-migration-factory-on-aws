param ($reinstall = "No",
      $API_Token,
      $Servername,
      [string] $windowsuser = [System.Management.Automation.Language.NullString]::Value,
      [string] $windowspwd = [System.Management.Automation.Language.NullString]::Value)

# Read Server name #

function agent-install {
   Param($key,
   $account,
   [string] $windowsuserl = [System.Management.Automation.Language.NullString]::Value,
   [string] $windowspwdl = [System.Management.Automation.Language.NullString]::Value)
   $ScriptPath = "c:\Scripts\"

   if ("" -ne $windowsuserl)
   {
       $creds = New-Object System.Management.Automation.PSCredential($windowsuserl, (ConvertTo-SecureString $windowspwdl -AsPlainText -Force))

       if ($account -ne "") {
         foreach ($machine in $account) {

             if ($reinstall -eq 'Yes' -or ($reinstall -eq 'No' -and (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Program Files (x86)\CloudEndure\dist\windows_service_wrapper.exe"} -Credential $creds)))) {
                 write-host "--------------------------------------------------------"
                 write-host "- Installing CloudEndure for:   $machine -" -BackgroundColor Blue
                 write-host "--------------------------------------------------------"
                 if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\"} -Credential $creds)) {Invoke-Command -ComputerName $machine -ScriptBlock {New-Item -Path "c:\Scripts\" -ItemType directory} -Credential $creds}
                 Invoke-Command -ComputerName $machine -ScriptBlock {(New-Object System.Net.WebClient).DownloadFile("https://console.cloudendure.com/installer_win.exe","C:\Scripts\installer_win.exe")} -Credential $creds
                 $fileexist = Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\installer_win.exe"} -Credential $creds
                 if ($fileexist -eq "true") {
                   $message = "** Successfully downloaded CloudEndure for: " + $machine + " **"
                   Write-Host $message
                    }
                 $command = $ScriptPath + "installer_win.exe -t " + $key + " --no-prompt" + " --skip-dotnet-check"
                 $scriptblock2 = $executioncontext.invokecommand.NewScriptBlock($command)
                 Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock2 -Credential $creds
                 write-host
                 write-host "** CloudEndure installation finished for : $machine **"
                 write-host
             }
             else {
                 $message = "CloudEndure agent already installed for machine: " + $machine + " , please reinstall manually if required"
                 write-host $message -BackgroundColor Red
             }
         }
       }
   }
   else {
       if ($account -ne "") {
         foreach ($machine in $account) {

             if ($reinstall -eq 'Yes' -or ($reinstall -eq 'No' -and (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Program Files (x86)\CloudEndure\dist\windows_service_wrapper.exe"})))) {
                 write-host "--------------------------------------------------------"
                 write-host "- Installing CloudEndure for:   $machine -" -BackgroundColor Blue
                 write-host "--------------------------------------------------------"
                 if (!(Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\"})) {Invoke-Command -ComputerName $machine -ScriptBlock {New-Item -Path "c:\Scripts\" -ItemType directory}}
                 Invoke-Command -ComputerName $machine -ScriptBlock {(New-Object System.Net.WebClient).DownloadFile("https://console.cloudendure.com/installer_win.exe","C:\Scripts\installer_win.exe")}
                 $fileexist = Invoke-Command -ComputerName $machine -ScriptBlock {Test-path "c:\Scripts\installer_win.exe"}
                 if ($fileexist -eq "true") {
                   $message = "** Successfully downloaded CloudEndure for: " + $machine + " **"
                   Write-Host $message
                    }
                 $command = $ScriptPath + "installer_win.exe -t " + $key + " --no-prompt" + " --skip-dotnet-check"
                 $scriptblock2 = $executioncontext.invokecommand.NewScriptBlock($command)
                 Invoke-Command -ComputerName $machine -ScriptBlock $scriptblock2
                 write-host
                 write-host "** CloudEndure installation finished for : $machine **"
                 write-host
             }
             else {
                 $message = "CloudEndure agent already installed for machine: " + $machine + " , please reinstall manually if required"
                 write-host $message -BackgroundColor Red
             }
         }
       }
   }


}

agent-install $API_Token $Servername $windowsuser $windowspwd
