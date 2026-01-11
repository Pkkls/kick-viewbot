# ============================================================
# Script PowerShell pour contrôler les VMs facilement
# Usage: .\control-vms.ps1 [action] [channel] [viewers]
# ============================================================

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('status', 'deploy', 'start', 'stop', 'logs')]
    [string]$Action = 'status',
    
    [Parameter(Mandatory=$false)]
    [string]$Channel = '',
    
    [Parameter(Mandatory=$false)]
    [int]$Viewers = 100
)

$API_URL = "http://192.168.1.6:5000"

function Show-Menu {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   Kick Viewbot VM Control - Menu Principal" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Vérifier le statut de toutes les VMs" -ForegroundColor White
    Write-Host "2. Déployer le script sur toutes les VMs" -ForegroundColor White
    Write-Host "3. Démarrer toutes les VMs" -ForegroundColor Green
    Write-Host "4. Arrêter toutes les VMs" -ForegroundColor Red
    Write-Host "5. Voir les logs d'une VM" -ForegroundColor White
    Write-Host "6. Reconnecter Mullvad (toutes les VMs)" -ForegroundColor Yellow
    Write-Host "7. Locations Mullvad aléatoires (toutes les VMs)" -ForegroundColor Cyan
    Write-Host "0. Quitter" -ForegroundColor Gray
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
}

function Get-Status {
    Write-Host "`n[+] Récupération du statut des VMs..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$API_URL/status" -Method GET
        
        Write-Host "`n============================================================" -ForegroundColor Cyan
        Write-Host "   STATUT DES VMs" -ForegroundColor Yellow
        Write-Host "============================================================" -ForegroundColor Cyan
        
        foreach ($vm in $response.PSObject.Properties) {
            $ip = $vm.Name
            $status = $vm.Value.status
            $stats = $vm.Value.stats
            
            $color = switch ($status) {
                "running" { "Green" }
                "stopped" { "Red" }
                "offline" { "Gray" }
                default { "Yellow" }
            }
            
            Write-Host "`nVM: $ip" -ForegroundColor White
            Write-Host "  Status: $status" -ForegroundColor $color
            
            if ($stats) {
                Write-Host "  Connexions: $($stats.connections)" -ForegroundColor Cyan
                Write-Host "  Viewers: $($stats.viewers)" -ForegroundColor Cyan
                Write-Host "  Pings: $($stats.pings)" -ForegroundColor Cyan
                Write-Host "  Heartbeats: $($stats.heartbeats)" -ForegroundColor Cyan
            }
        }
        
        Write-Host "`n============================================================" -ForegroundColor Cyan
    }
    catch {
        Write-Host "[ERREUR] Impossible de contacter le serveur!" -ForegroundColor Red
        Write-Host "Assure-toi que le serveur tourne (start.bat)" -ForegroundColor Yellow
    }
}

function Invoke-Action {
    param(
        [string]$ActionType,
        [string]$Ch,
        [int]$V
    )
    
    $body = @{
        action = $ActionType
    }
    
    if ($Ch -ne '') {
        $body.channel = $Ch
        $body.viewers = $V
    }
    
    $jsonBody = $body | ConvertTo-Json
    
    try {
        Write-Host "`n[+] Exécution de l'action: $ActionType..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri "$API_URL/execute" -Method POST -ContentType "application/json" -Body $jsonBody
        
        if ($response.success) {
            Write-Host "`n[OK] $($response.message)" -ForegroundColor Green
        } else {
            Write-Host "`n[ERREUR] $($response.message)" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "[ERREUR] $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Get-VMLogs {
    Write-Host "`nVMs disponibles:" -ForegroundColor Yellow
    Write-Host "1. 192.168.1.101"
    Write-Host "2. 192.168.1.84"
    Write-Host "3. 192.168.1.4"
    Write-Host "4. 192.168.1.11"
    Write-Host "5. 192.168.1.182"
    
    $choice = Read-Host "`nChoisis une VM (1-5)"
    
    $ips = @('192.168.1.101', '192.168.1.84', '192.168.1.4', '192.168.1.11', '192.168.1.182')
    
    if ($choice -ge 1 -and $choice -le 5) {
        $vmIp = $ips[$choice - 1]
        
        try {
            Write-Host "`n[+] Récupération des logs de $vmIp..." -ForegroundColor Yellow
            $response = Invoke-RestMethod -Uri "$API_URL/logs/$vmIp" -Method GET
            
            Write-Host "`n============================================================" -ForegroundColor Cyan
            Write-Host "   LOGS - $vmIp" -ForegroundColor Yellow
            Write-Host "============================================================" -ForegroundColor Cyan
            
            foreach ($log in $response.logs) {
                Write-Host $log
            }
            
            Write-Host "============================================================" -ForegroundColor Cyan
        }
        catch {
            Write-Host "[ERREUR] Impossible de récupérer les logs" -ForegroundColor Red
        }
    }
}

# Script principal avec menu interactif
if ($Action -eq 'status' -and $Channel -eq '') {
    # Mode interactif
    do {
        Show-Menu
        $choice = Read-Host "Choisis une option"
        
        switch ($choice) {
            '1' {
                Get-Status
                Write-Host "`nAppuie sur Entrée pour continuer..." -ForegroundColor Gray
                Read-Host
            }
            '2' {
                Invoke-Action -ActionType 'deploy'
                Write-Host "`nAppuie sur Entrée pour continuer..." -ForegroundColor Gray
                Read-Host
            }
            '3' {
                $ch = Read-Host "Nom du channel"
                $v = Read-Host "Nombre de viewers par VM (défaut: 100)"
                if ($v -eq '') { $v = 100 }
                Invoke-Action -ActionType 'start_all' -Ch $ch -V $v
                Write-Host "`nAppuie sur Entrée pour continuer..." -ForegroundColor Gray
                Read-Host
            }
            '4' {
                $confirm = Read-Host "Confirmer l'arrêt de toutes les VMs? (o/n)"
                if ($confirm -eq 'o') {
                    Invoke-Action -ActionType 'stop_all'
                }
                Write-Host "`nAppuie sur Entrée pour continuer..." -ForegroundColor Gray
                Read-Host
            }
            '5' {
                Get-VMLogs
                Write-Host "`nAppuie sur Entrée pour continuer..." -ForegroundColor Gray
                Read-Host
            }
            '6' {
                $confirm = Read-Host "Reconnecter Mullvad sur toutes les VMs? (o/n)"
                if ($confirm -eq 'o') {
                    Invoke-Action -ActionType 'mullvad_reconnect_all'
                }
                Write-Host "`nAppuie sur Entrée pour continuer..." -ForegroundColor Gray
                Read-Host
            }
            '7' {
                $confirm = Read-Host "Changer vers des locations aléatoires sur toutes les VMs? (o/n)"
                if ($confirm -eq 'o') {
                    Invoke-Action -ActionType 'mullvad_random_all'
                }
                Write-Host "`nAppuie sur Entrée pour continuer..." -ForegroundColor Gray
                Read-Host
            }
            '0' {
                Write-Host "`nAu revoir!" -ForegroundColor Green
                exit
            }
        }
    } while ($choice -ne '0')
}
else {
    # Mode ligne de commande
    switch ($Action) {
        'status' {
            Get-Status
        }
        'deploy' {
            Invoke-Action -ActionType 'deploy'
        }
        'start' {
            if ($Channel -eq '') {
                Write-Host "[ERREUR] Le channel est requis pour démarrer!" -ForegroundColor Red
                Write-Host "Usage: .\control-vms.ps1 start -Channel 'xqc' -Viewers 100" -ForegroundColor Yellow
                exit 1
            }
            Invoke-Action -ActionType 'start_all' -Ch $Channel -V $Viewers
        }
        'stop' {
            Invoke-Action -ActionType 'stop_all'
        }
    }
}