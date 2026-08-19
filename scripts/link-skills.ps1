# The team installer for Windows (Linux and macOS: scripts/link-skills.sh).
#
# Links every skill in this repository into the local skill directories used
# by each agent harness:
#   - $HOME\.claude\skills  (Claude Code)
#   - $HOME\.agents\skills  (Codex and other Agent Skills-compatible harnesses)
# Each entry is a directory junction into this repo, so a `git pull` keeps
# installed skills current. Junctions need no admin rights or Developer Mode,
# unlike symlinks. Re-run after a skill is added, removed, or renamed.
#
# It also installs the team's global instructions file,
# templates\CLAUDE.global.md, as $HOME\.claude\CLAUDE.md (and
# $HOME\.codex\AGENTS.md when $HOME\.codex exists). It never overwrites a copy
# that differs from the template: it tells you so and leaves merging to you.
#
# Anything it replaces is copied into backup\<timestamp>\ inside this repo
# first, and the path is printed when it finishes. That directory is
# gitignored.
#
# Usage:
#   .\scripts\link-skills.ps1                  install or upgrade
#   .\scripts\link-skills.ps1 -ListBackups     show what can be restored
#   .\scripts\link-skills.ps1 -Restore [id]    put a backup back
# If scripts are blocked:
#   powershell -ExecutionPolicy Bypass -File .\scripts\link-skills.ps1

[CmdletBinding()]
param(
  [switch]$ListBackups,
  [string]$Restore
)

$ErrorActionPreference = 'Stop'

$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BackupRoot = Join-Path $Repo 'backup'
$Dests = @(
  (Join-Path $HOME '.claude\skills'),
  (Join-Path $HOME '.agents\skills')
)

# ---- backup helpers ---------------------------------------------------------
# Created lazily on the first item actually saved, so a no-op run leaves no
# empty directory behind.
$script:BackupDir = $null
$script:BackupCount = 0

function Ensure-BackupDir {
  if ($script:BackupDir) { return }
  $base = Join-Path $BackupRoot (Get-Date -Format 'yyyyMMdd-HHmmss')
  # Two runs inside the same second must not share a directory: the second
  # would truncate the first's manifest and orphan everything it had saved.
  $stamp = $base; $n = 1
  while (Test-Path $stamp) { $stamp = "$base-$n"; $n++ }
  $script:BackupDir = $stamp
  New-Item -ItemType Directory -Path (Join-Path $stamp 'files') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $stamp 'dirs')  -Force | Out-Null
  Set-Content -Path (Join-Path $stamp 'MANIFEST.tsv') -Value $null -NoNewline
}

function Save-BackupFile([string]$Src) {
  if (-not (Test-Path $Src -PathType Leaf)) { return }
  Ensure-BackupDir
  $script:BackupCount++
  $slot = 'files\{0:d3}-{1}' -f $script:BackupCount, (Split-Path $Src -Leaf)
  Copy-Item $Src (Join-Path $script:BackupDir $slot) -Force
  Add-Content -Path (Join-Path $script:BackupDir 'MANIFEST.tsv') -Value ("FILE`t$Src`t$slot")
}

function Save-BackupDir([string]$Src) {
  if (-not (Test-Path $Src -PathType Container)) { return }
  Ensure-BackupDir
  $script:BackupCount++
  $slot = 'dirs\{0:d3}-{1}' -f $script:BackupCount, (Split-Path $Src -Leaf)
  Copy-Item $Src (Join-Path $script:BackupDir $slot) -Recurse -Force
  Add-Content -Path (Join-Path $script:BackupDir 'MANIFEST.tsv') -Value ("DIR`t$Src`t$slot")
}

function Read-Manifest([string]$Dir) {
  Get-Content (Join-Path $Dir 'MANIFEST.tsv') | Where-Object { $_ -match "`t" } | ForEach-Object {
    $p = $_ -split "`t"
    [pscustomobject]@{ Kind = $p[0]; Original = $p[1]; Slot = $p[2] }
  }
}

function Show-Backups {
  if (-not (Test-Path $BackupRoot) -or -not (Get-ChildItem $BackupRoot -Directory -EA SilentlyContinue)) {
    Write-Host "No backups yet. One is written the first time an install replaces something."
    return
  }
  Write-Host "Backups in ${BackupRoot}:"
  foreach ($d in Get-ChildItem $BackupRoot -Directory | Sort-Object Name) {
    $mf = Join-Path $d.FullName 'MANIFEST.tsv'
    if (-not (Test-Path $mf)) { continue }
    $entries = @(Read-Manifest $d.FullName)
    $word = if ($entries.Count -eq 1) { 'item' } else { 'items' }
    Write-Host ("  {0,-20} {1} {2}" -f $d.Name, $entries.Count, $word)
    foreach ($e in $entries) { Write-Host ("      {0,-5} {1}" -f $e.Kind, $e.Original) }
  }
  Write-Host ""
  Write-Host "Restore one with: .\scripts\link-skills.ps1 -Restore <id>"
}

function Restore-Backup([string]$Id) {
  if (-not $Id) {
    Show-Backups
    Write-Host ""
    $Id = Read-Host "Which backup id?"
  }
  $dir = Join-Path $BackupRoot $Id
  if (-not (Test-Path (Join-Path $dir 'MANIFEST.tsv'))) {
    Write-Error "no backup '$Id' (looked for $dir\MANIFEST.tsv)"
    exit 1
  }

  $entries = @(Read-Manifest $dir)
  Write-Host "This will put the following back, overwriting what is there now:"
  foreach ($e in $entries) { Write-Host ("  {0,-5} {1}" -f $e.Kind, $e.Original) }
  Write-Host ""
  $reply = Read-Host "Proceed? [y/N]"
  if ($reply -notmatch '^[yY]') { Write-Host "Nothing restored."; exit 0 }

  foreach ($e in $entries) {
    $parent = Split-Path $e.Original -Parent
    if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $saved = Join-Path $dir $e.Slot
    if ($e.Kind -eq 'FILE') {
      Copy-Item $saved $e.Original -Force
      Write-Host "restored file $($e.Original)"
    } else {
      # Remove whatever occupies the path now, including a junction the
      # installer put there, then put the saved directory back.
      if (Test-Path $e.Original) {
        $item = Get-Item $e.Original -Force
        if ($item.LinkType) { $item.Delete() } else { Remove-Item $e.Original -Recurse -Force }
      }
      Copy-Item $saved $e.Original -Recurse -Force
      Write-Host "restored dir  $($e.Original)"
    }
  }
  Write-Host ""
  Write-Host "Restored from $dir"
  Write-Host "Re-run .\scripts\link-skills.ps1 when you want the skills linked again."
}

if ($ListBackups) { Show-Backups; exit 0 }
if ($PSBoundParameters.ContainsKey('Restore')) { Restore-Backup $Restore; exit 0 }

# ---- link the skills --------------------------------------------------------
$skills = Get-ChildItem -Path (Join-Path $Repo 'skills') -Recurse -Filter 'SKILL.md' |
  Where-Object { $_.FullName -notmatch '\\node_modules\\' -and $_.FullName -notmatch '\\deprecated\\' } |
  ForEach-Object { $_.Directory }

foreach ($dest in $Dests) {
  if (Test-Path $dest) {
    $item = Get-Item $dest -Force
    if ($item.LinkType -and $item.Target -and ($item.Target -like "$Repo*")) {
      Write-Error "$dest is a link into this repo ($($item.Target)). Remove it and re-run; the script will recreate it as a real directory."
      exit 1
    }
  }
  New-Item -ItemType Directory -Path $dest -Force | Out-Null

  foreach ($src in $skills) {
    $target = Join-Path $dest $src.Name
    if (Test-Path $target) {
      $existing = Get-Item $target -Force
      if ($existing.LinkType) {
        $existing.Delete()
      } else {
        # A real directory here is someone's own copy of a skill. Save it
        # before replacing it, or the install destroys their work.
        Save-BackupDir $target
        Remove-Item $target -Recurse -Force
      }
    }
    New-Item -ItemType Junction -Path $target -Target $src.FullName | Out-Null
    Write-Host "linked $($src.Name) -> $($src.FullName) ($dest)"
  }
}

# ---- global instructions file -----------------------------------------------
$template = Join-Path $Repo 'templates\CLAUDE.global.md'
$targets = @((Join-Path $HOME '.claude\CLAUDE.md'))
if (Test-Path (Join-Path $HOME '.codex')) { $targets += (Join-Path $HOME '.codex\AGENTS.md') }

foreach ($target in $targets) {
  if (-not (Test-Path $target)) {
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    Copy-Item $template $target
    Write-Host "installed global rules -> $target"
  } elseif ((Get-FileHash $template).Hash -eq (Get-FileHash $target).Hash) {
    Write-Host "global rules up to date ($target)"
  } else {
    Save-BackupFile $target
    Write-Warning "$target differs from templates\CLAUDE.global.md; not overwritten. Merge by hand (compare the two files)."
  }
}

# ---- report ------------------------------------------------------------------
Write-Host ""
if ($script:BackupDir) {
  Write-Host "Backed up $($script:BackupCount) item(s) this run:"
  Write-Host "  $($script:BackupDir)"
  Write-Host "Undo with: .\scripts\link-skills.ps1 -Restore $(Split-Path $script:BackupDir -Leaf)"
  Write-Host "See all:   .\scripts\link-skills.ps1 -ListBackups"
} else {
  Write-Host "Nothing needed backing up this run."
}
