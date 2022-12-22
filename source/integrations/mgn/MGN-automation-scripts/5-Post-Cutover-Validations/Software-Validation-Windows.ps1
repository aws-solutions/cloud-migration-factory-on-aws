param ($wantedApplications = "",
       $unwantedApplications = "",
       $runningApplications = "")

$global:overallStatus = "Pass"
function Get-InstalledApplication
{
    Param
    (
         [Parameter(Mandatory=$true)]
         [string[]] $Application,

         [Parameter(Mandatory=$true)]
         [string] $State
    )

    $installedApplications = Get-WmiObject -Class Win32_Product
    
    switch($State){
        'Verify' {
            $wantedApplicationStatus = "Win_Wanted_Apps|"
            foreach ($app in $Application)
            {
                if(![string]::IsNullOrEmpty($app)){
                    if (($InstalledApplications).Name -eq $app)
                    {
                        $wantedApplicationStatus = $wantedApplicationStatus + $app.Trim() + ",Pass|"
                    }
                    else
                    {
                        $wantedApplicationStatus = $wantedApplicationStatus + $app.Trim() + ",Fail|"
                        $global:overallStatus = "Fail"
                    }
                }
            }
            $wantedApplicationStatus = $wantedApplicationStatus -replace ".$"
            Write-Host $wantedApplicationStatus
        }
        'Unwanted' {
            $unwantedApplicationStatus = "Win_UnWanted_Apps|"
            foreach($app in $Application){
                if(![string]::IsNullOrEmpty($app))
                {
					if ("VMWare Tools" -like "*$app*") {
						if ( Test-Path -Path "C:\Program Files\VMware" ){
							$unwantedApplicationStatus = $unwantedApplicationStatus + $app.Trim() + ",Fail|"
							$global:overallStatus = "Fail"							
						}	
						else {
							$unwantedApplicationStatus = $unwantedApplicationStatus + $app.Trim() + ",Pass|"
						}
					}
                    elseif (($installedApplications).Name -like "*$app*")
                    {
                        $unwantedApplicationStatus = $unwantedApplicationStatus + $app.Trim() + ",Fail|"
                        $global:overallStatus = "Fail"
                    }
                    else
                    {
                        $unwantedApplicationStatus = $unwantedApplicationStatus + $app.Trim() + ",Pass|"
                    }
                }
            }
            $unwantedApplicationStatus = $unwantedApplicationStatus -replace ".$"
            Write-Host $unwantedApplicationStatus
        }
    }
}

function Get-ServiceStatus
{
    Param
    (
         [Parameter(Mandatory=$true)]
         [string[]] $Application,

         [Parameter(Mandatory=$false)]
         [ValidateSet("Running", "Stopped", "Started")]
         [string[]] $StatusDesired
    )
    $runningApplicationStatus = "Win_Running_Apps|"
    foreach($App in $Application){
        if(![string]::IsNullOrEmpty($App))
        {
            $status = (Get-Service $App.Trim() -ErrorAction Ignore).Status
            $runningApplicationStatus = $runningApplicationStatus + $App.Trim() + "," + $status + "|"
            if($status -ne "Running"){
                $global:overallStatus = "Fail"
            }
			if (("CloudEndureService" -like "*$app*") -and ($status -ne "Running")){
				$global:overallStatus = "Pass"
			}
			
        }
    }
    # Remove the extra comma at the end
    $runningApplicationStatus = $runningApplicationStatus -replace ".$"
    Write-Host $runningApplicationStatus
}

    #Checking Running Applications
    $runningApplications = $runningApplications.split(",")
    Get-ServiceStatus $runningApplications
    #Checking Unwanted Applications
    $unwantedApplications = $unwantedApplications.split(",")
    Get-InstalledApplication -Application $unwantedApplications -State Unwanted
    #Checking Wanted Applications
    $wantedApplications = $wantedApplications.split(",")
    Get-InstalledApplication -Application $wantedApplications -State Verify
    $serviceStatus = "validationStatus|" + $global:overallStatus
    Write-Host $serviceStatus




