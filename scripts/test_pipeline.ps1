# scripts/test_pipeline.ps1

$base = "http://localhost:8000"

Write-Host "`n=== GST-Sentinel Pipeline Test ===" -ForegroundColor Cyan

# 1) Health check
Write-Host "`n1) Health check..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Method Get -Uri "$base/health" -TimeoutSec 20
Write-Host "   OK -> status=$($health.status), service=$($health.service)" -ForegroundColor Green

# 2) Fetch dates
Write-Host "`n2) Fetch dates..." -ForegroundColor Yellow
$datesRes = Invoke-RestMethod -Method Get -Uri "$base/api/dates" -TimeoutSec 20
if (-not $datesRes.dates -or $datesRes.dates.Count -eq 0) { throw "No dates returned from /api/dates" }
$date = $datesRes.dates[0]
Write-Host "   OK -> first date=$date, count=$($datesRes.count)" -ForegroundColor Green

# 3) Fetch scores
Write-Host "`n3) Fetch scores for date=$date..." -ForegroundColor Yellow
$scoresRes = Invoke-RestMethod -Method Get -Uri "$base/api/scores?date=$date" -TimeoutSec 30
if (-not $scoresRes.top_zones -or $scoresRes.top_zones.Count -eq 0) { throw "No top_zones returned from /api/scores" }
$zone = $scoresRes.top_zones[0].zone_id
$z    = [double]$scoresRes.top_zones[0].z_score
Write-Host "   OK -> top zone=$zone, z_score=$z, source=$($scoresRes.source)" -ForegroundColor Green

# 4) Fetch alerts
Write-Host "`n4) Fetch alerts for date=$date..." -ForegroundColor Yellow
$alertsRes = Invoke-RestMethod -Method Get -Uri "$base/api/alerts?date=$date" -TimeoutSec 20
Write-Host "   OK -> alert count=$($alertsRes.count)" -ForegroundColor Green

# 5) Fetch zone history
Write-Host "`n5) Fetch zone history for $zone..." -ForegroundColor Yellow
$histRes = Invoke-RestMethod -Method Get -Uri "$base/api/zones/$zone/history" -TimeoutSec 20
Write-Host "   OK -> history records=$($histRes.count)" -ForegroundColor Green

# 6) Call explain
Write-Host "`n6) Call explain for zone=$zone..." -ForegroundColor Yellow
$body = @{
    zone_id = $zone
    z_score = $z
    date    = $date
    query   = "why is this zone critical?"
} | ConvertTo-Json
$explainRes = Invoke-RestMethod -Method Post `
    -Uri "$base/api/explain" `
    -ContentType "application/json" `
    -Body $body `
    -TimeoutSec 60
Write-Host "   OK -> intent=$($explainRes.intent)" -ForegroundColor Green

# 7) Print explanation
Write-Host "`n=== Explanation ===" -ForegroundColor Cyan
$explainRes.bullets | ForEach-Object { Write-Host "  $_" -ForegroundColor White }

Write-Host "`n=== All tests passed ===" -ForegroundColor Green