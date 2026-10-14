# Mise à jour de Jarvis avec le dernier ZIP du dossier Téléchargements (lancé par METTRE-A-JOUR-JARVIS.bat).
$ErrorActionPreference = 'Stop'
$dossier = Join-Path $HOME 'Jarvis'
$zip = Get-ChildItem (Join-Path $HOME 'Downloads') -Filter 'jarvis*.zip' | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $zip) {
    Write-Host 'Aucun fichier jarvis*.zip dans Telechargements : telecharge-le d abord.' -ForegroundColor Red
    exit 1
}
Write-Host ('ZIP utilise : ' + $zip.Name + ' (' + $zip.LastWriteTime + ')')

Write-Host 'Arret de Jarvis...'
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*-m jarvis*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

$tmp = Join-Path $HOME 'jarvis-maj'
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Expand-Archive -Path $zip.FullName -DestinationPath $tmp -Force
robocopy (Join-Path $tmp 'jarvis') $dossier /E /NFL /NDL /NJH /NJS /NP | Out-Null
Remove-Item $tmp -Recurse -Force
Write-Host 'Fichiers copies.'

Write-Host 'Installation des composants (quelques secondes)...'
$python = Join-Path $dossier '.venv\Scripts\python.exe'
& $python -m pip install -q --disable-pip-version-check -r (Join-Path $dossier 'requirements.txt')

Start-Process (Join-Path $dossier '.venv\Scripts\pythonw.exe') -ArgumentList '-m', 'jarvis', '--fond' -WorkingDirectory $dossier
Write-Host 'Jarvis est a jour et relance !' -ForegroundColor Green
