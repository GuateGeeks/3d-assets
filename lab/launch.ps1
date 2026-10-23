$ErrorActionPreference = 'Stop'
$rigRepoRoot = Split-Path -Parent $PSScriptRoot
$rigDistro = 'Ubuntu'
if ($rigRepoRoot -match '^\\\\wsl(?:\.localhost|\$)\\([^\\]+)\\(.*)$') {
    $rigDistro = $Matches[1]
    $rigLinuxRoot = '/' + $Matches[2].Replace('\', '/')
} else {
    $rigLinuxRoot = (& wsl.exe -d $rigDistro -- wslpath -a -u $rigRepoRoot).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo convertir la ruta del repositorio a WSL.' }
}
& wsl.exe -d $rigDistro --cd $rigLinuxRoot -- python3 lab/lab.py @args
exit $LASTEXITCODE
