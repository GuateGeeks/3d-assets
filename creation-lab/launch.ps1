$ErrorActionPreference = 'Stop'
$creationRoot = Split-Path -Parent $PSScriptRoot
$creationDistro = 'Ubuntu'
if ($creationRoot -match '^\\\\wsl(?:\.localhost|\$)\\([^\\]+)\\(.*)$') {
    $creationDistro = $Matches[1]
    $creationLinuxRoot = '/' + $Matches[2].Replace('\', '/')
} else {
    $creationLinuxRoot = (& wsl.exe -d $creationDistro --exec wslpath -a -u $creationRoot).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve repository path in WSL.' }
}
# Argument arrays only; never pass user input through sh -c.
& wsl.exe -d $creationDistro --cd $creationLinuxRoot --exec python3 creation-lab/create.py @args
exit $LASTEXITCODE
