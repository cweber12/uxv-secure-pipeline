param()
$ErrorActionPreference = "Stop"
if (-not (Test-Path "diagrams")) { New-Item -ItemType Directory -Path "diagrams" | Out-Null }
npx mmdc -i diagrams/architecture-flow.mmd -o diagrams/architecture-flow.svg -b transparent
npx mmdc -i diagrams/architecture-seq.mmd  -o diagrams/architecture-seq.svg  -b transparent
Write-Host "SVGs written to diagrams/"
