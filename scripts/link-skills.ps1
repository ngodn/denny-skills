# Links every skill in this repo into the local skill directories used by each
# agent harness, on Windows:
#   - $HOME\.claude\skills  (Claude Code)
#   - $HOME\.agents\skills  (Codex and other Agent Skills-compatible harnesses)
#
# Each entry is a directory junction into this repo, so a `git pull` is all
# that's needed to keep installed skills current. Junctions need no admin
# rights or Developer Mode, unlike symlinks. Re-run after adding, removing, or
# renaming a skill.
#
# It also installs the team's global instructions file,
# templates\CLAUDE.global.md, as $HOME\.claude\CLAUDE.md (and
# $HOME\.codex\AGENTS.md when $HOME\.codex exists). It never overwrites a file
# that differs from the template: it tells you so and leaves merging to you.
#
# Usage (PowerShell 5.1 or 7+):
#   .\scripts\link-skills.ps1
# If scripts are blocked:
#   powershell -ExecutionPolicy Bypass -File .\scripts\link-skills.ps1

$ErrorActionPreference = 'Stop'

$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Dests = @(
  (Join-Path $HOME '.claude\skills'),
  (Join-Path $HOME '.agents\skills')
)

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
        # Junctions and symlinks: remove the link only, never the target's contents.
        $existing.Delete()
      } else {
        Remove-Item $target -Recurse -Force
      }
    }
    New-Item -ItemType Junction -Path $target -Target $src.FullName | Out-Null
    Write-Host "linked $($src.Name) -> $($src.FullName) ($dest)"
  }
}

# ---- global instructions file -------------------------------------------------
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
    Write-Warning "$target differs from templates\CLAUDE.global.md; not overwritten. Merge by hand (compare the two files)."
  }
}
