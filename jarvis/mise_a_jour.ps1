# Installe ou met a jour Jarvis depuis GitHub, en une commande (ou avec l'icone "Mettre a jour Jarvis") :
#   irm https://raw.githubusercontent.com/Geordhann/Jarvis/ccr-3c3d8b8c-punmtx/jarvis/mise_a_jour.ps1 | iex
# Les reglages (cle, voix, Google, Spotify, liste de charme...) sont ailleurs et ne bougent pas.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$depot = 'https://github.com/Geordhann/Jarvis/archive/refs/heads/ccr-3c3d8b8c-punmtx.zip'
$dossier = Join-Path $HOME 'Jarvis'
$tmp = Join-Path $env:TEMP 'jarvis-maj'
$pause = [bool]$MyInvocation.MyCommand.Path   # lance par l'icone : on garde la fenetre ouverte a la fin

try {
    Write-Host '1/5 Arret de Jarvis...'
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*-m jarvis*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2

    Write-Host '2/5 Telechargement de la derniere version...'
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    New-Item -ItemType Directory $tmp | Out-Null
    $zip = Join-Path $tmp 'jarvis.zip'
    Invoke-WebRequest -Uri $depot -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $source = Get-ChildItem $tmp -Directory | Select-Object -First 1

    Write-Host '3/5 Copie des fichiers...'
    New-Item -ItemType Directory $dossier -Force | Out-Null
    robocopy $source.FullName $dossier /E /NFL /NDL /NJH /NJS /NP | Out-Null
    Remove-Item $tmp -Recurse -Force

    $python = Join-Path $dossier '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        Write-Host '   Premiere installation : creation de l environnement Python...'
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv (Join-Path $dossier '.venv') }
        else { & python -m venv (Join-Path $dossier '.venv') }
    }

    Write-Host '4/5 Installation des composants (1 a 2 minutes la premiere fois)...'
    & $python -m pip install -q --disable-pip-version-check -r (Join-Path $dossier 'requirements.txt')

    Write-Host '5/5 Icones du Bureau et lancement au demarrage...'
    Push-Location $dossier
    & $python -m jarvis --installer | Out-Null
    Pop-Location

    Write-Host ''
    Write-Host 'Jarvis est a jour ! Double-clique sur l icone Jarvis du Bureau.' -ForegroundColor Green
} catch {
    Write-Host ''
    Write-Host ('Probleme : ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Fais une capture de cette fenetre et envoie-la.' -ForegroundColor Red
}
if ($pause) { Read-Host 'Appuie sur Entree pour fermer' | Out-Null }
