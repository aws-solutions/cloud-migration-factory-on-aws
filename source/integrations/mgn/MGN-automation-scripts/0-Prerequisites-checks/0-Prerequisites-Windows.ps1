param ($MGNRepServerIP, $MGNEndpoint)

function Get-TCPPort443
{
    Param
    (
         [Parameter(Mandatory=$true)]
         [string] $Ipaddress
    )
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
    $url = "https://" + $Ipaddress
    $content=$WebClient.DownloadString($url)
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

function Get-DiskSpace
{
    $driveLetterFree = [math]::Round(((Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'" | Select-Object Size,FreeSpace).freespace)/1GB,2)

    if($driveLetterFree -gt 2){
        write-output 'FreeSpace:Pass'
    }else{
        write-output 'FreeSpace:Fail'
    }

}

Get-TCPPort443 $MGNEndpoint
Get-TCPPort1500 $MGNRepServerIP
Get-DiskSpace