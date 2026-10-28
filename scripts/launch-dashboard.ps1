param(
    [string]$Server = '',
    [int]$LocalPort = 8766,
    [int]$RemotePort = 8765
)

$ErrorActionPreference = 'Stop'
$dashboardUrl = "http://127.0.0.1:$LocalPort"
$tunnelProcess = $null

function Test-SchoolDashboard {
    try {
        $response = Invoke-WebRequest -Uri "$dashboardUrl/login" -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -eq 200 -and $response.Content -match '<title>[^<]*Hermes School')
    } catch {
        return $false
    }
}

try {
    if ([string]::IsNullOrWhiteSpace($Server)) {
        $Server = Read-Host 'Destination SSH (utilisateur@nom-tailscale-ou-IP)'
    }
    if ($Server -notmatch '^[a-zA-Z0-9_.-]+@[a-zA-Z0-9.-]+$') {
        throw 'Indiquez une destination SSH utilisateur@serveur valide.'
    }
    if ($LocalPort -lt 1024 -or $LocalPort -gt 65535 -or $RemotePort -lt 1 -or $RemotePort -gt 65535) {
        throw 'Port invalide.'
    }
    $sshCommand = Get-Command ssh.exe -ErrorAction SilentlyContinue
    if (-not $sshCommand) {
        throw 'Client OpenSSH introuvable. Activez le Client OpenSSH dans les fonctionnalites facultatives de Windows.'
    }

    if (Test-SchoolDashboard) {
        Write-Host 'Le dashboard est deja accessible. Ouverture du navigateur...'
        Start-Process $dashboardUrl
        exit 0
    }

    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $LocalPort)
    try {
        $listener.Start()
    } catch {
        throw "Le port local $LocalPort est occupe. Fermez l'ancien tunnel ou utilisez un autre port avec -LocalPort."
    } finally {
        $listener.Stop()
    }

    Write-Host 'HERMES SCHOOL' -ForegroundColor Green
    Write-Host "Connexion au serveur $Server"
    Write-Host 'Tailscale doit etre connecte sur Windows et sur le serveur.'
    Write-Host 'Si SSH le demande, saisissez votre mot de passe Debian dans cette fenetre.'
    Write-Host 'La saisie du mot de passe reste invisible. Aucun mot de passe n est memorise par ce lanceur.'
    Write-Host ''

    # Shared console lets ssh handle passwords and host-key verification itself.
    $sshArguments = @(
        '-N', '-o', 'ExitOnForwardFailure=yes',
        '-o', 'ConnectTimeout=10',
        '-o', 'ServerAliveInterval=30',
        '-o', 'ServerAliveCountMax=3',
        '-L', "127.0.0.1:${LocalPort}:127.0.0.1:${RemotePort}",
        $Server
    )
    $tunnelProcess = Start-Process -FilePath $sshCommand.Source -ArgumentList $sshArguments -NoNewWindow -PassThru
    $deadline = [DateTime]::UtcNow.AddMinutes(3)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($tunnelProcess.HasExited) {
            throw 'Connexion SSH interrompue. Verifiez Tailscale, le serveur et votre authentification.'
        }
        if (Test-SchoolDashboard) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 700
    }
    if (-not $ready) {
        throw 'Dashboard inaccessible apres 3 minutes. Verifiez le service hermes-school-dashboard sur Debian.'
    }

    Write-Host "Dashboard pret : $dashboardUrl" -ForegroundColor Green
    Write-Host 'Gardez cette fenetre ouverte pendant la consultation.'
    Write-Host 'Fermez-la ou faites Ctrl+C pour couper votre tunnel. Le serveur Debian reste en fonctionnement.'
    Start-Process $dashboardUrl
    while (-not $tunnelProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
    throw 'Le tunnel SSH a ete ferme. Relancez le lanceur pour vous reconnecter.'
} catch {
    Write-Host ''
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    if ($tunnelProcess -and -not $tunnelProcess.HasExited) {
        Stop-Process -Id $tunnelProcess.Id -ErrorAction SilentlyContinue
    }
}
