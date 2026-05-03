[CmdletBinding()]
param(
    [switch]$NoDownload
)

& "$PSScriptRoot\build-pdf.ps1" -Language ja -NoDownload:$NoDownload
exit $LASTEXITCODE
