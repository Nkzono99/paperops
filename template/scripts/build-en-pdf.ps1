[CmdletBinding()]
param(
    [switch]$NoDownload
)

& "$PSScriptRoot\build-pdf.ps1" -Language en -NoDownload:$NoDownload
exit $LASTEXITCODE
