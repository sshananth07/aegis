param(
    [Parameter(Mandatory=$true)]
    [string]$JWT
)

$base = "http://localhost:8000"
$headers = @{ "Authorization" = "Bearer $JWT"; "Content-Type" = "application/json" }

Write-Host "`n--- Listing prompts ---" -ForegroundColor Cyan
$rawPrompts = Invoke-RestMethod -Uri "$base/prompts/" -Headers $headers
# /prompts/ returns a plain array, not a paginated object
$promptList = @($rawPrompts)
Write-Host "Total prompts: $($promptList.Count)"
foreach ($p in $promptList) {
    Write-Host "  $($p.id) | $($p.name)"
}

if ($promptList.Count -eq 0) {
    Write-Host "No prompts found. Create a prompt first in the web app." -ForegroundColor Red
    exit
}

Write-Host "`n--- Listing versions for each prompt ---" -ForegroundColor Cyan
$script:versionId = $null
foreach ($p in $promptList) {
    try {
        $versions = Invoke-RestMethod -Uri "$base/prompts/$($p.id)/versions" -Headers $headers
        $versionList = @($versions)
        Write-Host "  Prompt '$($p.name)' ($($p.id)) -> $($versionList.Count) version(s)"
        foreach ($v in $versionList) {
            Write-Host "    Version: $($v.id) | $($v.version_number)"
        }
        if ($versionList.Count -gt 0 -and -not $script:versionId) {
            $script:versionId = $versionList[0].id
            $script:promptName = $p.name
        }
    } catch {
        Write-Host "  Prompt '$($p.name)' ($($p.id)) -> ERROR: $_" -ForegroundColor Red
    }
}

if (-not $script:versionId) {
    Write-Host "`nNo versions found. Create a prompt version first in the web app." -ForegroundColor Red
    exit
}

Write-Host "`n--- Triggering evaluation ---" -ForegroundColor Cyan
Write-Host "Using prompt: $($script:promptName)"
Write-Host "Using version: $($script:versionId)"

$body = "{`"prompt_version_id`":`"$($script:versionId)`",`"provider`":`"gemini`"}"
try {
    $job = Invoke-RestMethod -Uri "$base/evaluations/" -Method POST -Headers $headers -Body $body
    Write-Host "Job created!" -ForegroundColor Green
    Write-Host "  Job ID: $($job.id)"
    Write-Host "  Status: $($job.status)"

    Write-Host "`nPolling job status (up to 30s)..." -ForegroundColor Yellow
    $evalId = $null
    for ($i = 0; $i -lt 6; $i++) {
        Start-Sleep -Seconds 5
        $jobResult = Invoke-RestMethod -Uri "$base/jobs/$($job.id)" -Headers $headers
        Write-Host "  [$($i*5+5)s] Job status: $($jobResult.status) | result_id: $($jobResult.result_id)"
        if ($jobResult.status -eq "completed" -or $jobResult.status -eq "failed") {
            $evalId = $jobResult.result_id
            break
        }
    }

    if (-not $evalId) {
        Write-Host "`nJob did not complete within 30s. Final job status: $($jobResult.status)" -ForegroundColor Yellow
        Write-Host "Check server logs or try again later." -ForegroundColor Yellow
        exit
    }

    Write-Host "`n--- Checking evaluation result ---" -ForegroundColor Cyan
    Write-Host "Evaluation ID: $evalId"
    $result = Invoke-RestMethod -Uri "$base/evaluations/$evalId" -Headers $headers
    Write-Host "  Status:   $($result.status)" -ForegroundColor Green
    Write-Host "  Score:    $($result.score)"
    Write-Host "  Provider: $($result.provider)"

    Write-Host "`n--- Check webhook.site for the delivery ---" -ForegroundColor Cyan
    Write-Host "Open https://webhook.site/050a3433-f631-4a37-8d7a-c568f457810b" -ForegroundColor Yellow
    Write-Host "You should see a POST request with X-Aegis-Signature header" -ForegroundColor Yellow
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}
