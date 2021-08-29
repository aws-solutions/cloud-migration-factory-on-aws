param ($CERepServerIP)

function Get-TCPPort443
{
    $Ipaddress= 'console.cloudendure.com'
    $Port= 443

    $t = New-Object Net.Sockets.TcpClient
    try {
    $t.Connect($Ipaddress,$Port)
    write-output 'TCP443:Pass'
    }
    catch {
    $env_proxy = [Environment]::GetEnvironmentVariable('https_proxy')
    if ($env_proxy -Match 'https://') {
        $env_proxy = $env_proxy.replace("https://","")
    }
    elseif ($env_proxy -Match 'http://') {
        $env_proxy = $env_proxy.replace("http://","")
    }
    $proxy = new-object System.Net.WebProxy($env_proxy)
    $WebClient = new-object System.Net.WebClient
    $WebClient.proxy = $proxy
    Try {
    $content=$WebClient.DownloadString("https://console.cloudendure.com")
    write-output 'TCP443:Pass'
    } 
    catch {
        write-output 'TCP443:Fail'
    }
    }
}

function Get-TCPPort1500
{
    Param
    (
         [Parameter(Mandatory=$true)]
         [string] $Ipaddress
    )
    $Port= 1500

    $t = New-Object Net.Sockets.TcpClient
    try {
    $t.Connect($Ipaddress,$Port)
    write-output 'TCP1500:Pass'
    }
    catch
    {
        write-output 'TCP1500:Fail'
    }

}

function Get-NETVersion
{
    $v4 = Test-Path "HKLM:SOFTWARE\Microsoft\NET Framework Setup\NDP\v4"
    $v40 = Test-Path "HKLM:SOFTWARE\Microsoft\NET Framework Setup\NDP\v4.0"
    $v35 = Test-Path "HKLM:SOFTWARE\Microsoft\NET Framework Setup\NDP\v3.5"
    $Netversion = $false
    if ($v4 -or $v40 -or $v35) 
    {$Netversion = $true}

    if($Netversion){
        write-output 'NET35:Pass'
    }else{
        write-output 'NET35:Fail'
    }
}

function Get-DiskSpace
{
    $driveLetterFree = [math]::Round(((Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'" | Select-Object Size,FreeSpace).freespace)/1GB,2)

    if($driveLetterFree -gt 3){
        write-output 'FreeSpace:Pass'
    }else{
        write-output 'FreeSpace:Fail'
    }

}

Get-TCPPort443
Get-TCPPort1500 $CERepServerIP
Get-NETVersion
Get-DiskSpace