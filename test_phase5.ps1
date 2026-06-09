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

# 1. Health check
Test-Step "Health check" {
    $r = Invoke-RestMethod -Uri "$base/health"
    Write-Host "Status: $($r.status)" -ForegroundColor Green
}

# 2. Create API key
Test-Step "Create API key" {
    $script:keyResponse = Invoke-RestMethod -Uri "$base/api-keys/" -Method POST -Headers $headers `
        -Body '{"name":"test-key","scopes":["evaluations:write","traces:read","metrics:read"]}'
    Write-Host "Key prefix: $($script:keyResponse.key_prefix)" -ForegroundColor Green
    Write-Host "Plaintext key: $($script:keyResponse.key)" -ForegroundColor Yellow
    $script:apiKey = $script:keyResponse.key
}

# 3. List API keys
Test-Step "List API keys" {
    $r = Invoke-RestMethod -Uri "$base/api-keys/" -Headers $headers
    Write-Host "Total keys: $($r.total)" -ForegroundColor Green
}

# 4. Test invalid key returns error contract
Test-Step "Invalid API key returns error contract" {
    try {
        Invoke-RestMethod -Uri "$base/v1/traces" -Headers @{"X-API-Key"="invalid_key"}
    } catch {
        $body = $_.ErrorDetails.Message | ConvertFrom-Json
        if ($body.error.code -eq "invalid_api_key") {
            Write-Host "PASS: Got error code 'invalid_api_key'" -ForegroundColor Green
        } else {
            Write-Host "FAIL: Unexpected response: $($_.ErrorDetails.Message)" -ForegroundColor Red
        }
    }
}

# 5. Test valid key on /v1/traces
Test-Step "Valid API key on GET /v1/traces" {
    if (-not $script:apiKey) { Write-Host "SKIP: no key created"; return }
    $r = Invoke-RestMethod -Uri "$base/v1/traces" -Headers @{"X-API-Key"=$script:apiKey}
    Write-Host "PASS: items=$($r.total), limit=$($r.limit)" -ForegroundColor Green
}

# 6. Test valid key on /v1/metrics
Test-Step "Valid API key on GET /v1/metrics" {
    if (-not $script:apiKey) { Write-Host "SKIP: no key created"; return }
    $r = Invoke-RestMethod -Uri "$base/v1/metrics" -Headers @{"X-API-Key"=$script:apiKey}
    Write-Host "PASS: evaluation_count=$($r.evaluation_count), pass_rate=$($r.pass_rate)" -ForegroundColor Green
}

# 7. Test scope enforcement — traces:read key can't use benchmarks:write scope
Test-Step "Scope enforcement (benchmarks:write denied)" {
    if (-not $script:apiKey) { Write-Host "SKIP: no key created"; return }
    try {
        Invoke-RestMethod -Uri "$base/v1/benchmarks/run" -Method POST `
            -Headers @{"X-API-Key"=$script:apiKey; "Content-Type"="application/json"} `
            -Body '{"suite_id":"00000000-0000-0000-0000-000000000000"}'
    } catch {
        $body = $_.ErrorDetails.Message | ConvertFrom-Json
        if ($body.error.code -eq "scope_denied") {
            Write-Host "PASS: Got error code 'scope_denied'" -ForegroundColor Green
        } else {
            Write-Host "Response: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
        }
    }
}

# 8. Create webhook
Test-Step "Create webhook" {
    $r = Invoke-RestMethod -Uri "$base/webhooks/" -Method POST -Headers $headers `
        -Body '{"url":"https://webhook.site/test","event_types":["evaluation.completed"]}'
    Write-Host "Webhook ID: $($r.id)" -ForegroundColor Green
    Write-Host "Secret (save this): $($r.secret)" -ForegroundColor Yellow
    $script:webhookId = $r.id
}

# 9. List webhooks
Test-Step "List webhooks" {
    $r = Invoke-RestMethod -Uri "$base/webhooks/" -Headers $headers
    Write-Host "Total webhooks: $($r.total)" -ForegroundColor Green
}

# 10. Check delivery history
Test-Step "Webhook delivery history" {
    if (-not $script:webhookId) { Write-Host "SKIP: no webhook created"; return }
    $r = Invoke-RestMethod -Uri "$base/webhooks/$($script:webhookId)/deliveries" -Headers $headers
    Write-Host "Total deliveries: $($r.total)" -ForegroundColor Green
}

# 11. Check OpenAPI docs
Test-Step "OpenAPI docs available" {
    $r = Invoke-WebRequest -Uri "$base/docs" -UseBasicParsing
    if ($r.StatusCode -eq 200) {
        Write-Host "PASS: /docs returned 200" -ForegroundColor Green
    }
}

# 12. Revoke the test key
Test-Step "Revoke API key" {
    if (-not $script:keyResponse) { Write-Host "SKIP: no key created"; return }
    Invoke-RestMethod -Uri "$base/api-keys/$($script:keyResponse.id)" -Method DELETE -Headers $headers
    Write-Host "PASS: key revoked" -ForegroundColor Green
}

Write-Host "`n=== Phase 5 smoke test complete ===" -ForegroundColor Cyan
