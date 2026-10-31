param(
    [string]$InstallRoot = $(if ($env:ProgramW6432) { $env:ProgramW6432 } else { $env:ProgramFiles }),
    [ValidateSet('Machine', 'Process')][string]$PathScope = 'Machine',
    [version]$MinDenoVersion = '2.3.0',
    [version]$MinNodeVersion = '22.0.0',
    [switch]$CheckOnly
)

function Get-ToolInfo {
    param([string]$Name, [string]$FilePath, [version]$Minimum)
    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) { return $null }
    $process = New-Object System.Diagnostics.Process
    try {
        $process.StartInfo.FileName = (Resolve-Path -LiteralPath $FilePath).Path
        $process.StartInfo.Arguments = if ($Name -in @('ffmpeg', 'ffprobe')) { '-version' } else { '--version' }
        $process.StartInfo.UseShellExecute = $false
        $process.StartInfo.CreateNoWindow = $true
        $process.StartInfo.RedirectStandardOutput = $true
        $process.StartInfo.RedirectStandardError = $true
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(10000)) {
            $process.Kill()
            $process.WaitForExit()
            return $null
        }
        if ($process.ExitCode -ne 0) { return $null }
        $output = $stdout.Result + "`n" + $stderr.Result
        if ($Name -in @('ffmpeg', 'ffprobe')) {
            $match = [regex]::Match($output, '(?m)^' + $Name + ' version\s+(\S+)')
        } elseif ($Name -eq 'deno') {
            $match = [regex]::Match($output, '(?m)^deno\s+(\d+\.\d+\.\d+)')
        } else {
            $match = [regex]::Match($output, '(?m)^v?(\d+\.\d+\.\d+)')
        }
        if (-not $match.Success) { return $null }
        $versionText = $match.Groups[1].Value
        if ($Minimum -and ([version]$versionText -lt $Minimum)) { return $null }
        return [pscustomobject]@{ Name = $Name; Path = $process.StartInfo.FileName; Version = $versionText }
    } catch {
        return $null
    } finally {
        $process.Dispose()
    }
}

function Find-Tool {
    param([string]$Name, [string]$ManagedPath, [version]$Minimum)
    # Check the command the app will actually find, then our managed fallback.
    # A newer copy later on PATH cannot rescue an unsupported first match.
    $candidates = @((Get-Command -Name "$Name.exe" -CommandType Application -ErrorAction SilentlyContinue) |
        Select-Object -First 1 |
        Select-Object -ExpandProperty Source)
    $candidates += $ManagedPath
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        $tool = Get-ToolInfo -Name $Name -FilePath $candidate -Minimum $Minimum
        if ($tool) { return $tool }
    }
    return $null
}

function Get-DependencyState {
    param([string]$Root, [version]$DenoMinimum, [version]$NodeMinimum)
    $ffmpeg = Find-Tool 'ffmpeg' (Join-Path $Root 'FFmpeg\bin\ffmpeg.exe')
    $ffprobe = Find-Tool 'ffprobe' (Join-Path $Root 'FFmpeg\bin\ffprobe.exe')
    $deno = Find-Tool 'deno' (Join-Path $Root 'Deno\deno.exe') $DenoMinimum
    $node = Find-Tool 'node' (Join-Path $Root 'nodejs\node.exe') $NodeMinimum
    return [pscustomobject]@{
        Ready = [bool]($ffmpeg -and $ffprobe -and ($deno -or $node))
        FFmpeg = $ffmpeg; FFprobe = $ffprobe; Deno = $deno; Node = $node
    }
}

function Get-FfmpegRelease {
    $base = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
    $response = Invoke-WebRequest -UseBasicParsing -Uri "$base.sha256" -TimeoutSec 60
    $match = [regex]::Match([string]$response.Content, '(?i)\b[0-9a-f]{64}\b')
    if (-not $match.Success) { throw 'The FFmpeg download checksum is unavailable.' }
    return @{ Url = $base; Sha256 = $match.Value }
}

function Get-DenoRelease {
    $headers = @{ 'User-Agent' = 'YT-Channel-Downloader-Installer'; Accept = 'application/vnd.github+json' }
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/denoland/deno/releases/latest' -Headers $headers -TimeoutSec 60
    $name = 'deno-x86_64-pc-windows-msvc.zip'
    $asset = $release.assets | Where-Object { $_.name -eq $name } | Select-Object -First 1
    if (-not $asset) { throw 'The Windows x64 Deno download is unavailable.' }
    $digest = if ($asset.PSObject.Properties['digest']) { [string]$asset.digest } else { '' }
    if ($digest -match '^sha256:([0-9a-fA-F]{64})$') {
        $checksum = $Matches[1]
    } else {
        $checksumAsset = $release.assets | Where-Object { $_.name -eq "$name.sha256sum" } | Select-Object -First 1
        if (-not $checksumAsset) { throw 'The Deno download checksum is unavailable.' }
        $response = Invoke-WebRequest -UseBasicParsing -Uri $checksumAsset.browser_download_url -TimeoutSec 60
        $match = [regex]::Match([string]$response.Content, '(?i)\b[0-9a-f]{64}\b')
        if (-not $match.Success) { throw 'The Deno download checksum is invalid.' }
        $checksum = $match.Value
    }
    return @{ Url = $asset.browser_download_url; Sha256 = $checksum }
}

function Expand-VerifiedRelease {
    param([hashtable]$Release, [string]$Directory)
    if ($Release.Sha256 -notmatch '^[0-9a-fA-F]{64}$') { throw 'Invalid download checksum.' }
    $null = New-Item -ItemType Directory -Path $Directory -Force
    $archive = Join-Path $Directory 'release.zip'
    Write-Host "Downloading $($Release.Url)"
    Invoke-WebRequest -UseBasicParsing -Uri $Release.Url -OutFile $archive -TimeoutSec 600
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ine $Release.Sha256) {
        throw 'The download checksum did not match. No downloaded tools were installed.'
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $Directory -Force
}

function Add-ManagedPath {
    param([string]$Directory, [string]$Scope)
    $directoryPath = [IO.Path]::GetFullPath($Directory).TrimEnd('\')
    if ($Scope -eq 'Machine') {
        $current = [Environment]::GetEnvironmentVariable('Path', 'Machine')
        $entries = @($current -split ';' | Where-Object { $_ -and $_.Trim().TrimEnd('\') -ine $directoryPath })
        $updated = (@($directoryPath) + $entries) -join ';'
        if ($updated -ne $current) { [Environment]::SetEnvironmentVariable('Path', $updated, 'Machine') }
    }
    $processEntries = @($env:Path -split ';' | Where-Object { $_ -and $_.Trim().TrimEnd('\') -ine $directoryPath })
    $env:Path = (@($directoryPath) + $processEntries) -join ';'
}

function Invoke-DependencySetup {
    param(
        [string]$Root,
        [ValidateSet('Machine', 'Process')][string]$Scope = 'Machine',
        [version]$DenoMinimum = '2.3.0',
        [version]$NodeMinimum = '22.0.0',
        [switch]$InspectOnly
    )
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $rootPath = [IO.Path]::GetFullPath($Root).TrimEnd('\')
    if ($rootPath -eq [IO.Path]::GetPathRoot($rootPath).TrimEnd('\')) { throw 'Use an installation directory, not a drive root.' }
    $state = Get-DependencyState $rootPath $DenoMinimum $NodeMinimum
    if ($InspectOnly) { return $state }
    $temporaryRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
    $workDir = Join-Path $temporaryRoot ('ytcd-dependencies-' + [guid]::NewGuid().ToString('N'))
    $null = New-Item -ItemType Directory -Path $workDir
    try {
        if (-not ($state.FFmpeg -and $state.FFprobe)) {
            $downloadDir = Join-Path $workDir 'ffmpeg'
            Expand-VerifiedRelease (Get-FfmpegRelease) $downloadDir
            $candidates = @(Get-ChildItem -LiteralPath $downloadDir -Filter ffmpeg.exe -Recurse -File |
                Where-Object { Test-Path -LiteralPath (Join-Path $_.DirectoryName 'ffprobe.exe') })
            if ($candidates.Count -ne 1) { throw 'The FFmpeg archive must contain one ffmpeg/ffprobe pair.' }
            $sourceBin = $candidates[0].DirectoryName
            foreach ($name in @('ffmpeg', 'ffprobe')) {
                if (-not (Get-ToolInfo $name (Join-Path $sourceBin "$name.exe"))) {
                    throw "The downloaded $name executable did not run successfully."
                }
            }
            $installBin = Join-Path $rootPath 'FFmpeg\bin'
            $null = New-Item -ItemType Directory -Path $installBin -Force
            foreach ($name in @('ffmpeg.exe', 'ffprobe.exe')) {
                Copy-Item -LiteralPath (Join-Path $sourceBin $name) -Destination (Join-Path $installBin $name) -Force
            }
            $license = Join-Path (Split-Path $sourceBin -Parent) 'LICENSE'
            if (Test-Path -LiteralPath $license -PathType Leaf) {
                Copy-Item -LiteralPath $license -Destination (Join-Path $rootPath 'FFmpeg\LICENSE.txt') -Force
            }
            Add-ManagedPath $installBin $Scope
        }
        if (-not ($state.Deno -or $state.Node)) {
            $downloadDir = Join-Path $workDir 'deno'
            Expand-VerifiedRelease (Get-DenoRelease) $downloadDir
            $candidates = @(Get-ChildItem -LiteralPath $downloadDir -Filter deno.exe -Recurse -File)
            if ($candidates.Count -ne 1 -or -not (Get-ToolInfo 'deno' $candidates[0].FullName $DenoMinimum)) {
                throw "The downloaded Deno executable does not meet the minimum version $DenoMinimum."
            }
            $installBin = Join-Path $rootPath 'Deno'
            $null = New-Item -ItemType Directory -Path $installBin -Force
            Copy-Item -LiteralPath $candidates[0].FullName -Destination (Join-Path $installBin 'deno.exe') -Force
            Add-ManagedPath $installBin $Scope
        }
        $state = Get-DependencyState $rootPath $DenoMinimum $NodeMinimum
        foreach ($tool in @($state.FFmpeg, $state.FFprobe, $state.Deno)) {
            if ($tool -and $tool.Path.StartsWith($rootPath + '\', [StringComparison]::OrdinalIgnoreCase)) {
                Add-ManagedPath (Split-Path $tool.Path -Parent) $Scope
            }
        }
        if (-not $state.Ready) { throw 'Dependency verification failed after installation.' }
        Write-Host 'FFmpeg, ffprobe and a supported JavaScript runtime are available.'
        return $state
    } finally {
        if (Test-Path -LiteralPath $workDir) {
            $resolved = (Resolve-Path -LiteralPath $workDir).Path
            if (-not $resolved.StartsWith($temporaryRoot + '\ytcd-dependencies-', [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Refusing to remove an unexpected temporary directory.'
            }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        $result = Invoke-DependencySetup -Root $InstallRoot -Scope $PathScope -DenoMinimum $MinDenoVersion -NodeMinimum $MinNodeVersion -InspectOnly:$CheckOnly
        $result | ConvertTo-Json -Depth 4
        if ($result.Ready) { exit 0 } else { exit 1 }
    } catch {
        Write-Host "Dependency setup failed: $($_.Exception.Message)"
        exit 1
    }
}
