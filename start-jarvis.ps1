Write-Host "=== Starting JARVIS ===" -ForegroundColor Cyan

# Start Ollama
Write-Host "Starting Ollama..." -ForegroundColor Yellow
Start-Process "C:\Users\dardi\AppData\Local\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 8

# Start JARVIS server
Write-Host "Starting JARVIS server..." -ForegroundColor Yellow
Start-Process python -ArgumentList "-m uvicorn backend.main:app --host 0.0.0.0 --port 8080"
Start-Sleep -Seconds 4

# Start Cloudflare tunnel
Write-Host "Starting tunnel..." -ForegroundColor Yellow
Start-Process cloudflared -ArgumentList "tunnel --url http://localhost:8080"

Write-Host ""
Write-Host "=== JARVIS is running! ===" -ForegroundColor Green
Write-Host "Local: http://localhost:8080" -ForegroundColor Cyan
Write-Host "Internet: Check the tunnel URL above" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
