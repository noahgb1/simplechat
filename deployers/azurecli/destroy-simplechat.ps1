<#
az cloud set --name AzureUSGovernment
az login --scope https://management.core.usgovcloudapi.net//.default
az login --scope https://graph.microsoft.us//.default
az account get-access-token --resource https://management.core.usgovcloudapi.net/
az account get-access-token --resource https://graph.microsoft.us/
#>

param (
    [Parameter(Mandatory = $true)]
    [string]$p,

    [Parameter(Mandatory = $true)]
    [string]$e
)

# Mofify these values
$productName = $p
$productEnvironment = $e

# No not modify values
$appPrefix ="sc"
$resourceGroupName = "{0}-{1}-{2}-rg" -f $appPrefix, $productName, $productEnvironment
$entraGroupName = "{0}-{1}-sg" -f $productName, $productEnvironment
$appRegistrationName = "{1}-{2}-ar" -f $appPrefix, $productName, $productEnvironment

$SecurityGroupPrefix = $entraGroupName
$entraGroupName_Admins = $entraGroupName + "-Admins"
$entraGroupName_Users = $entraGroupName + "-Users"
$entraGroupName_CreateGroup = $entraGroupName + "-CreateGroup"
$entraGroupName_SafetyViolationAdmin = $entraGroupName + "-SafetyViolationAdmin"
$entraGroupName_FeedbackAdmin = $entraGroupName + "-FeedbackAdmin"
$entraSecurityGroupNames = @($entraGroupName_Admins, $entraGroupName_Users, $entraGroupName_CreateGroup, $entraGroupName_SafetyViolationAdmin, $entraGroupName_FeedbackAdmin)

# --- Destroy Instance ---
Clear-Host
Write-Host "`nSimpleChat Destroy Executing:" -ForegroundColor Green

Write-Host "`nHow to run this script: ./destroy-simplechat.ps1 -p <productName> -e <environment>" -ForegroundColor Yellow

Write-Host "`nGetting Access Tokeen Refreshed for: https://management.core.usgovcloudapi.net/" -ForegroundColor Yellow
az account get-access-token --resource https://management.core.usgovcloudapi.net/ --output none
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to get ARM  Access Token." ; exit 1 } # Basic error check
Write-Host "`nGetting Access Tokeen Refreshed for: https://graph.microsoft.us/" -ForegroundColor Yellow
az account get-access-token --resource https://graph.microsoft.us/ --output none
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to get MSGraph Access Token." ; exit 1 } # Basic error check

Read-Host -Prompt "Press Enter to delete all created resources in group '$($resourceGroupName)' (or Ctrl+C to exit)"
Write-Host "Deleting Resource Group: $($resourceGroupName)..."
az group delete --name $resourceGroupName --yes --no-wait
if ($LASTEXITCODE -ne 0) { Write-Warning "Failed to delete Resource Group." }
else { Write-Host "Resource Group '$($resourceGroupName)' deletion initiated." }

foreach ($securityGroupName in $global_EntraSecurityGroupNames) {
    Write-Host "`nChecking if exists Security Group: $($securityGroupName)..." -ForegroundColor Yellow
    $entraGroup = az ad group show --group $securityGroupName --query "id" -o tsv 2>$null
    if (-not $entraGroup) {
        Write-Host "Entra ID Security Group '$($securityGroupName)' does not exist."
    } else {
        Write-Host "Attempting to delete Entra ID Security Group: $($securityGroupName)..."
        az ad group delete --group $securityGroupName
        if ($LASTEXITCODE -ne 0) { Write-Warning "Failed to delete Entra ID Security Group '$($securityGroupName)'."}
        else { Write-Host "Entra ID Security Group '$($securityGroupName)' deleted."}
    }
}

Write-Host "`nAttempting to delete Entra Application Registration: [$($appRegistrationName)]..." -ForegroundColor Yellow
$clientId = $(az ad app list --display-name $appRegistrationName --query "[0].appId" --output tsv)
if ($LASTEXITCODE -ne 0) { Write-Warning "Failed to get Entra App Registration." }
else { Write-Host "Deleting Entra App Registration '$($appRegistrationName)'." }

if ($clientId -and $clientId -ne "00000000-0000-0000-0000-000000000000")
{
    Write-Host "Delete Entra Application Registration with clientid: [$($clientId)]..."
    az ad app delete --id $clientId
}
else {
    Write-Warning "Delete Entra Application Registration failed. Could not get clientid..."
}


try {
    # Get all security groups where securityEnabled is true
    # Convert the JSON output from az cli to PowerShell objects
    $groupsToDelete = az ad group list | ConvertFrom-Json | Where-Object { $_.displayName -like "$SecurityGroupPrefix*" }

    if (-not $groupsToDelete) {
        Write-Host "`nNo Microsoft Entra Security Groups found with prefix '$SecurityGroupPrefix'." -ForegroundColor Green
        exit 0
    }

    Write-Host "`nThe following Microsoft Entra Security Groups will be deleted:" -ForegroundColor Yellow
    $groupsToDelete | Format-Table displayName, id, @{Name='CreatedDateTime'; Expression={$_.createdDateTime | Get-Date -Format 'yyyy-MM-dd HH:mm:ss'}}

    $confirmation = Read-Host "Are you sure you want to delete these groups? Type 'yes' to confirm"

    if ($confirmation -ne "yes") {
        Write-Host "Deletion cancelled." -ForegroundColor Yellow
        exit 0
    }

    foreach ($group in $groupsToDelete) {
        Write-Host "Deleting group: '$($group.displayName)' (ID: $($group.id))..." -ForegroundColor DarkYellow
        try {
            az ad group delete --group $($group.id)
            Write-Host "Successfully deleted group: '$($group.displayName)'" -ForegroundColor Green
        }
        catch {
            Write-Warning "Failed to delete group: '$($group.displayName)'. Error: $($_.Exception.Message)"
        }
    }

    Write-Host "Deletion process completed." -ForegroundColor Green
}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    Write-Error "Ensure Azure CLI is installed and you are logged in (`az login`)."
}