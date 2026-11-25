$ErrorActionPreference = "Stop"
$root  = Split-Path $PSScriptRoot -Parent
$state = Get-Content (Join-Path $root ".fabric\deployment.json") -Raw | ConvertFrom-Json
$wsId  = $state.workspaceId
$lhId  = $state.lakehouseId

function Get-StorageToken {
    $t = az account get-access-token --resource https://storage.azure.com --query accessToken -o tsv
    if ($LASTEXITCODE -ne 0) { throw "Brak tokenu storage." }
    return $t
}
$tok = Get-StorageToken
$base = "https://onelake.dfs.fabric.microsoft.com/$wsId/$lhId"

function New-OneLakeDir {
    param([string]$Path)
    $u = "$base/Files/$Path`?resource=directory"
    Invoke-WebRequest -Method PUT -Uri $u -Headers @{ Authorization = "Bearer $tok" } `
        -SkipHttpErrorCheck | Out-Null
}

function Send-OneLakeFile {
    param([string]$LocalPath, [string]$RemotePath)
    $h = @{ Authorization = "Bearer $tok" }
    $u = "$base/Files/$RemotePath"

    $r = Invoke-WebRequest -Method PUT -Uri "$u`?resource=file" -Headers $h -SkipHttpErrorCheck
    if ($r.StatusCode -notin 201, 202) { throw "create $RemotePath -> $($r.StatusCode) $($r.Content)" }

    $bytes = [System.IO.File]::ReadAllBytes($LocalPath)
    $r = Invoke-WebRequest -Method PATCH -Uri "$u`?action=append&position=0" -Headers $h `
         -Body $bytes -ContentType "application/octet-stream" -SkipHttpErrorCheck
    if ($r.StatusCode -notin 200, 202) { throw "append $RemotePath -> $($r.StatusCode) $($r.Content)" }

    $r = Invoke-WebRequest -Method PATCH -Uri "$u`?action=flush&position=$($bytes.Length)" -Headers $h -SkipHttpErrorCheck
    if ($r.StatusCode -notin 200, 202) { throw "flush $RemotePath -> $($r.StatusCode) $($r.Content)" }

    "{0,-42} {1,8} KB" -f $RemotePath, [math]::Round($bytes.Length / 1KB, 0)
}

Write-Host "== Katalogi"
New-OneLakeDir "raw"
New-OneLakeDir "raw/data"
New-OneLakeDir "raw/derived"

Write-Host "== Wymiary i fakty (CSV i JSONL, plasko w raw/data)"
Get-ChildItem (Join-Path $root "datasets") -File | Where-Object { $_.Extension -in ".csv", ".jsonl" } | ForEach-Object {
    Send-OneLakeFile $_.FullName "raw/data/$($_.Name)"
}

Write-Host "== Wyniki analiz (CSV i JSON)"
Get-ChildItem (Join-Path $root "datasets\derived") -File | Where-Object { $_.Extension -in ".csv", ".json" } | ForEach-Object {
    Send-OneLakeFile $_.FullName "raw/derived/$($_.Name)"
}

Write-Host "`nGotowe."
