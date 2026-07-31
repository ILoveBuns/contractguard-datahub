#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out="$root/demo-output"
tts="/root/.local/bin/edge-tts"
ffmpeg="/root/.codex/tools/ffmpeg/ffmpeg"
ffprobe="/root/.codex/tools/ffmpeg/ffprobe"
font="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
mono="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
voice="en-US-AriaNeural"
durations=(11 12 12 13 13 13 13)

mkdir -p "$out/frames" "$out/audio"
rm -f "$out/frames/concat.txt" "$out/audio/concat.txt"

scene() {
  local number="$1" title="$2" body="$3" footer="$4"
  convert -size 1920x1080 xc:'#061421' \
    -fill '#20d6c7' -draw 'rectangle 0,0 1920,14' \
    -fill '#20d6c7' -font "$font" -pointsize 31 \
    -annotate +110+105 'CONTRACTGUARD  ×  DATAHUB' \
    -fill '#f8fafc' -font "$font" -pointsize 58 \
    -annotate +110+205 "$title" \
    -fill '#0e2636' -draw 'roundrectangle 95,265 1825,900 26,26' \
    -fill '#d9f5f1' -font "$mono" -pointsize 31 \
    -interline-spacing 14 -annotate +145+345 "$body" \
    -fill '#91a9b7' -font "$font" -pointsize 24 \
    -annotate +110+1015 "$footer" \
    "$out/frames/scene-$number.png"
}

scene 01 'Stop breaking data changes before merge' \
  'A SQL diff shows code.\nDataHub shows organizational impact.\n\nContractGuard combines both:\n  schema · lineage · usage · ownership\n\nDecision: PASS · REVIEW · BLOCK' \
  'Metadata-aware SQL and dbt change review'

scene 02 'A deceptively small migration' \
  '-- examples/breaking_change.sql\n\nALTER TABLE analytics.customers\n  DROP COLUMN email;\n\nSELECT *\nFROM analytics.customers;' \
  'Syntax alone cannot reveal every affected dashboard and model'

scene 03 'One reproducible review command' \
  '$ python3 -m contractguard.cli \\\n+    examples/breaking_change.sql \\\n+    --write-back \\\n+    --output artifacts/review.json\n\nResolved governed asset: analytics.customers' \
  'Deterministic fixture included · live DataHub MCP adapter ready'

scene 04 'Real blast radius changes the decision' \
  'VERDICT                         BLOCK\nRISK SCORE                      70 / 100\n\nCRITICAL · BREAKING_LINEAGE\nDropping email affects 2 downstream assets:\n  growth.customer_retention\n  finance.customer_ltv' \
  'Catalog evidence makes the gate explainable'

scene 05 'Actionable guidance, not generic lint' \
  'MEDIUM · UNSTABLE_PROJECTION\nSELECT * couples code to future schema drift.\n\nSAFER MIGRATION\n  stage a compatibility view\n  enumerate approved fields\n  notify downstream owners before removal' \
  'Each finding includes evidence and a remediation path'

scene 06 'DataHub is in the critical path' \
  'search                 resolve identifiers\nget_entities           schema · owners · status\nget_lineage            downstream blast radius\nget_dataset_queries    real usage evidence\nsave_document          durable review decision\n\nOfficial DataHub MCP server over JSON-RPC' \
  'Read metadata → decide → write the result back to the catalog'

scene 07 'Verified, portable, and ready to extend' \
  '$ python3 -m unittest discover -s tests -v\n\nTests cover:\n  breaking lineage detection\n  risk scoring and remediation\n  durable DataHub document writeback\n\nOPEN SOURCE  github.com/ILoveBuns/contractguard-datahub' \
  'ContractGuard · metadata made actionable at review time'

for number in $(seq 1 7); do
  index="$(printf '%02d' "$number")"
  duration="${durations[$((number - 1))]}"
  "$tts" --voice "$voice" --rate='+6%' \
    --text "$(cat "$root/demo_narration/$index.txt")" \
    --write-media "$out/audio/raw-$index.mp3"
  "$ffmpeg" -y -v error -i "$out/audio/raw-$index.mp3" \
    -af "loudnorm=I=-16:TP=-1.5:LRA=11,apad=pad_dur=$duration,atrim=duration=$duration" \
    -ar 48000 -ac 2 "$out/audio/scene-$index.wav"
  printf "file 'scene-%s.png'\nduration %s\n" "$index" "$duration" >> "$out/frames/concat.txt"
  printf "file 'scene-%s.wav'\n" "$index" >> "$out/audio/concat.txt"
done
printf "file 'scene-07.png'\n" >> "$out/frames/concat.txt"

"$ffmpeg" -y -v error -f concat -safe 0 -i "$out/frames/concat.txt" \
  -vf 'fps=24,format=yuv420p' -c:v libx264 -preset ultrafast -crf 23 \
  "$out/video-only.mp4"
"$ffmpeg" -y -v error -f concat -safe 0 -i "$out/audio/concat.txt" \
  -c:a aac -b:a 160k "$out/narration.m4a"
"$ffmpeg" -y -v error -i "$out/video-only.mp4" -i "$out/narration.m4a" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 160k \
  -shortest -movflags +faststart "$out/contractguard-datahub-demo-1080p.mp4"

"$ffprobe" -v error -show_entries format=duration,size \
  -show_entries stream=index,codec_type,codec_name,width,height \
  -of json "$out/contractguard-datahub-demo-1080p.mp4"
