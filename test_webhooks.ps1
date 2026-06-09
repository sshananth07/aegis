param(
    [Parameter(Mandatory=$true)]
    [string]$JWT
)

$base = "http://localhost:8000"
$headers = @{ "Authorization" = "Bearer $JWT"; "Content-Type" = "application/json" }

function Test-Step($label, $block) {
    Write-Host "`n--- $label ---" -ForegroundColor Cyan
    try { & $block } catch { Write-Host "ERROR: $_" -ForegroundColor Red }
}

$webhookUrl = "https://webhook.site/050a3433-f631-4a37-8d7a-c568f457810b"
Write-Host "`nUsing webhook URL: $webhookUrl" -ForegroundColor Yellow
Write-Host "Open https://webhook.site in your browser to see incoming requests`n" -ForegroundColor Yellow

Test-Step "Create webhook (evaluation.completed)" {
    $body = @{
        url = $webhookUrl
        event_types = @("evaluation.completed", "benchmark.completed")
    } | ConvertTo-Json
    $script:webhook = Invoke-RestMethod -Uri "$base/webhooks/" -Method POST -Headers $headers -Body $body
    Write-Host "ID:     $($script:webhook.id)" -ForegroundColor Green
    Write-Host "URL:    $($script:webhook.url)" -ForegroundColor Green
    Write-Host "Secret: $($script:webhook.secret)" -ForegroundColor Yellow
}

Test-Step "List webhooks" {
    $r = Invoke-RestMethod -Uri "$base/webhooks/" -Headers $headers
    Write-Host "Total webhooks: $($r.total)" -ForegroundColor Green
    foreach ($wh in $r.items) {
        Write-Host "  $($wh.id) active=$($wh.active)" -ForegroundColor Gray
    }
}

Test-Step "Check delivery history (should be 0 so far)" {
    if (-not $script:webhook) { Write-Host "SKIP"; return }
    $r = Invoke-RestMethod -Uri "$base/webhooks/$($script:webhook.id)/deliveries" -Headers $headers
    Write-Host "Deliveries: $($r.total)" -ForegroundColor Green
}

Test-Step "Fetch a prompt version to use for eval trigger" {
    $r = Invoke-RestMethod -Uri "$base/prompts/" -Headers $headers
    if ($r.items.Count -eq 0) {
        Write-Host "No prompts found - skipping eval trigger" -ForegroundColor Yellow
        $script:skipEval = $true
        return
    }
    # Find first prompt that has at least one version
    foreach ($prompt in $r.items) {
        try {
            $versions = Invoke-RestMethod -Uri "$base/prompts/$($prompt.id)/versions" -Headers $headers
            if ($versions -and $versions.Count -gt 0) {
                Write-Host "Using prompt: $($prompt.name) ($($prompt.id))" -ForegroundColor Green
                $script:promptVersionId = $versions[0].id
                Write-Host "Using version ID: $($script:promptVersionId)" -ForegroundColor Green
                return
            }
        } catch {}
    }
    Write-Host "No prompt versions found - skipping eval trigger" -ForegroundColor Yellow
    $script:skipEval = $true
}

Test-Step "Trigger evaluation (fires webhook on completion)" {
    if ($script:skipEval) { Write-Host "SKIP - no prompt version available"; return }
    $body = "{`"prompt_version_id`":`"$($script:promptVersionId)`",`"provider`":`"gemini`"}"
    $r = Invoke-RestMethod -Uri "$base/evaluations/" -Method POST -Headers $headers -Body $body
    Write-Host "Evaluation started: $($r.id)" -ForegroundColor Green
    Write-Host "Status: $($r.status)" -ForegroundColor Green
}

if (-not $script:skipEval) {
    Write-Host "`nWaiting 15 seconds for evaluation to complete and webhook to fire..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
}

Test-Step "Check delivery history after eval" {
    if (-not $script:webhook) { Write-Host "SKIP"; return }
    $r = Invoke-RestMethod -Uri "$base/webhooks/$($script:webhook.id)/deliveries" -Headers $headers
    Write-Host "Deliveries: $($r.total)" -ForegroundColor Green
    foreach ($d in $r.items) {
        if ($d.status -eq "success") {
            Write-Host "  [success] $($d.event_type) HTTP $($d.response_code) at $($d.attempted_at)" -ForegroundColor Green
        } else {
            Write-Host "  [failed]  $($d.event_type) HTTP $($d.response_code) at $($d.attempted_at)" -ForegroundColor Red
            if ($d.error_message) { Write-Host "  Error: $($d.error_message)" -ForegroundColor Red }
        }
    }
    if ($r.total -eq 0 -and -not $script:skipEval) {
        Write-Host "  No deliveries yet - eval may still be running" -ForegroundColor Yellow
    }
}

if ($script:webhook) {
    Write-Host "`n--- HMAC Signature Verification ---" -ForegroundColor Cyan
    Write-Host "Secret: $($script:webhook.secret)" -ForegroundColor Yellow
    Write-Host "Verify in Python:" -ForegroundColor White
    Write-Host "  import hmac, hashlib" -ForegroundColor Gray
    Write-Host "  sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()" -ForegroundColor Gray
    Write-Host "  assert headers['X-Aegis-Signature'] == f'sha256={sig}'" -ForegroundColor Gray
}

Test-Step "Invalid event type rejected" {
    try {
        Invoke-RestMethod -Uri "$base/webhooks/" -Method POST -Headers $headers `
            -Body '{"url":"https://example.com","event_types":["invalid.event"]}'
        Write-Host "FAIL: Should have been rejected" -ForegroundColor Red
    } catch {
        Write-Host "PASS: Invalid event type rejected ($($_.Exception.Response.StatusCode))" -ForegroundColor Green
    }
}

Test-Step "Delete test webhook" {
    if (-not $script:webhook) { Write-Host "SKIP"; return }
    Invoke-RestMethod -Uri "$base/webhooks/$($script:webhook.id)" -Method DELETE -Headers $headers
    Write-Host "PASS: Webhook deleted" -ForegroundColor Green
}

Test-Step "Verify webhook is gone" {
    $r = Invoke-RestMethod -Uri "$base/webhooks/" -Headers $headers
    $found = $r.items | Where-Object { $_.id -eq $script:webhook.id }
    if (-not $found) {
        Write-Host "PASS: Webhook no longer in list" -ForegroundColor Green
    } else {
        Write-Host "FAIL: Webhook still present" -ForegroundColor Red
    }
}

Write-Host "`n=== Webhook smoke test complete ===" -ForegroundColor Cyan
Write-Host "Check https://webhook.site to confirm the POST arrived with X-Aegis-Signature header" -ForegroundColor Yellow
