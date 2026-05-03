[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("ja", "en")]
    [string]$Language,

    [switch]$NoDownload
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$TectonicVersion = "0.16.9"
$TectonicAsset = "tectonic-$TectonicVersion-x86_64-pc-windows-msvc.zip"
$TectonicSha256 = "131a24604785a9600989a3d91225f597df52ac06f00aeffe86fd529f99ee5cdd"
$TectonicUrl = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40$TectonicVersion/$TectonicAsset"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..")).Path

function Resolve-Tectonic {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,

        [switch]$NoDownload
    )

    $installDir = Join-Path $RepoRoot ".tools\tectonic\$TectonicVersion"
    $localExe = Join-Path $installDir "tectonic.exe"
    if (Test-Path -LiteralPath $localExe) {
        return $localExe
    }
    if (Test-Path -LiteralPath $installDir) {
        $existing = Get-ChildItem -LiteralPath $installDir -Recurse -Filter "tectonic.exe" | Select-Object -First 1
        if ($existing) {
            return $existing.FullName
        }
    }

    if ($NoDownload) {
        $pathCommand = Get-Command tectonic -ErrorAction SilentlyContinue
        if ($pathCommand) {
            return $pathCommand.Source
        }
        throw "tectonic.exe が見つかりません。-NoDownload を外して pinned Tectonic を取得してください。"
    }

    $toolsDir = Join-Path $RepoRoot ".tools\tectonic"
    New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null

    $zipPath = Join-Path $toolsDir $TectonicAsset
    Write-Host "Downloading Tectonic $TectonicVersion..."
    Invoke-WebRequest -Uri $TectonicUrl -OutFile $zipPath

    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLowerInvariant()
    if ($hash -ne $TectonicSha256) {
        throw "Tectonic archive checksum mismatch: expected $TectonicSha256, got $hash"
    }

    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $installDir -Force

    $extracted = Get-ChildItem -LiteralPath $installDir -Recurse -Filter "tectonic.exe" | Select-Object -First 1
    if (-not $extracted) {
        throw "Tectonic archive did not contain tectonic.exe"
    }

    return $extracted.FullName
}

$langDir = Join-Path $Root "manuscript\$Language"
$buildDir = Join-Path $Root "manuscript\shared\build\$Language"
$mainTex = Join-Path $langDir "main.tex"
$styleDir = Join-Path $Root "manuscript\shared\style"
$bibDir = Join-Path $Root "manuscript\shared\bib"
$cacheDir = Join-Path $Root ".tools\tectonic\cache"

if (-not (Test-Path -LiteralPath $mainTex)) {
    throw "Main TeX file not found: $mainTex"
}

New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

$text = Get-Content -LiteralPath $mainTex -Raw -Encoding UTF8
$missing = @()
foreach ($match in [regex]::Matches($text, "\\input\{([^}]+)\}")) {
    $target = $match.Groups[1].Value
    if (-not $target.EndsWith(".tex")) {
        $target = "$target.tex"
    }
    $targetPath = Join-Path $langDir $target
    if (-not (Test-Path -LiteralPath $targetPath)) {
        $missing += $targetPath
    }
}

if ($missing.Count -gt 0) {
    Write-Host "不足している入力ファイル:"
    foreach ($item in $missing) {
        Write-Host "  - $item"
    }
    throw "入力ファイルの検証に失敗しました。"
}

Write-Host "$mainTex の入力ファイルを検証しました"

$tectonic = Resolve-Tectonic -RepoRoot $Root -NoDownload:$NoDownload
$env:TECTONIC_CACHE_DIR = $cacheDir

$compileArgs = @(
    "-X", "compile",
    (Resolve-Path -LiteralPath $mainTex).Path,
    "--outdir", (Resolve-Path -LiteralPath $buildDir).Path,
    "--keep-logs",
    "--keep-intermediates",
    "-Z", "search-path=$styleDir",
    "-Z", "search-path=$bibDir"
)

if ($NoDownload) {
    $compileArgs += "--only-cached"
}

& $tectonic @compileArgs
if ($LASTEXITCODE -ne 0) {
    throw "Tectonic build failed for $Language"
}

Write-Host "PDF build completed: $(Join-Path $buildDir 'main.pdf')"
