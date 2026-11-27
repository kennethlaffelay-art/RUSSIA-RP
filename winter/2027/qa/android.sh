#!/usr/bin/env bash
set -euo pipefail
src="$GITHUB_WORKSPACE/winter/2027"
jobdir="$RUNNER_TEMP/winter"
mkdir -p "$jobdir/evidence"
cd "$jobdir"
sudo apt-get -qq update
sudo apt-get -qq install -y adb apksigner fonts-dejavu-core python3-pil python3-venv
if ! sudo modprobe binder_linux; then
  sudo apt-get -qq install -y "linux-modules-extra-$(uname -r)"
  sudo modprobe binder_linux
fi
docker run --name qa-phone --privileged -d -p 127.0.0.1:5555:5555 redroid/redroid:12.0.0-latest androidboot.use_memfd=1 androidboot.redroid_gpu_mode=guest androidboot.redroid_width=1280 androidboot.redroid_height=720
export ANDROID_SERIAL=127.0.0.1:5555
for n in $(seq 1 90); do
  adb connect "$ANDROID_SERIAL" >/dev/null || true
  if test "$(timeout 3 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1; then break; fi
  sleep 2
done
adb shell getprop sys.boot_completed | grep -q 1
fetch() { curl -fsSL --retry 3 "$1" -o "$2"; }
origin="https://github.com/kennethlaffelay-art/RUSSIA-RP/releases/download"
fetch "$origin/russia-rp-v1.7.22-preview/RUSSIA-RP-1.7.22.apk" baseline.apk
fetch "$origin/winter-cache-20/cache-aec496b553b3528483d9dea231440bc861a9c910588d99de20c67b0b5afbbe5c.zip" cache20.zip
fetch https://github.com/sunshineq1/cash-samp-russia/releases/download/v1.0/Weik.zip world.zip
echo '090aaaf02b2697e8a6945cf4e0a82aa28c459a85d426f7a3a038e0aa8871050b  world.zip' | sha256sum -c -
unzip -q world.zip
rm world.zip
pkg=com.russiarp.hudx
root=Weik
app=baseline.apk
if test "$EDITION" = winter; then
  git clone -q https://github.com/Parik27/DragonFF.git dragon
  git -C dragon checkout -q 319847f7803f102c5aa31fa38e8b3284117db40a
  python3 -m venv env
  env/bin/pip -q install 'Pillow==12.2.0' numpy scipy fonttools
  fetch https://github.com/iBotPeaches/Apktool/releases/download/v2.11.1/apktool_2.11.1.jar apktool.jar
  PYTHONPATH=dragon env/bin/python "$src/build_assets.py" baseline.apk cache20.zip Weik assets-out /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
  env/bin/python "$src/package.py" baseline.apk assets-out apktool.jar unsigned.apk --preview
  keytool -genkeypair -keystore qa.p12 -storetype PKCS12 -storepass android-test -keyalg RSA -keysize 2048 -alias qa -dname 'CN=Isolated Android QA' -validity 5
  apksigner sign --ks qa.p12 --ks-pass pass:android-test --out winter.apk unsigned.apk
  app=winter.apk
  pkg=com.russiarp.snow
  root=RWin
fi
# Stage the same install that the production launcher verifies. Only the local test host differs.
python3 "$src/qa/stage.py" Weik "$app" cache20.zip
fetch https://github.com/openmultiplayer/open.mp/releases/download/v1.6.7.3218/open.mp-linux-x86.tar.gz omp.tar.gz
echo '0f7bfe70bb68ea780fe24a910b69412046e53d10feb65a9d4a9de8ff1f7f1329  omp.tar.gz' | sha256sum -c -
tar xzf omp.tar.gz
cp "$src/qa/plaza.pwn" Server/gamemodes/
python3 - <<'PY'
from pathlib import Path
import json
p=Path('Server/config.json');d=json.loads(p.read_bytes())
d.update(announce=False,max_players=2,enable_query=False)
d['network'].update(bind='127.0.0.1',port=7777)
d['pawn'].update(main_scripts=['plaza 1'],side_scripts=[],legacy_plugins=[])
d['rcon'].update(enable=False)
p.write_text(json.dumps(d))
PY
docker build -q -t qa-loopback - <<'DOCKER'
FROM debian:bookworm-slim
RUN dpkg --add-architecture i386 && apt-get -qq update && apt-get -qq install -y --no-install-recommends qemu-user libc6:i386 libstdc++6:i386 libatomic1:i386 zlib1g:i386
DOCKER
docker run --name qa-server --network container:qa-phone -v "$PWD/Server:/input:ro" --tmpfs /stage:rw,exec,size=256m -w /stage -d qa-loopback sh -ec 'cp -a /input/. .; LD_LIBRARY_PATH=qawno qemu-i386 qawno/pawncc gamemodes/plaza.pwn -iqawno/include -ogamemodes/plaza.amx; exec qemu-i386 ./omp-server'
adb install -g "$app"
adb shell appops set --uid "$pkg" MANAGE_EXTERNAL_STORAGE allow
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
adb shell settings put secure immersive_mode_confirmations confirmed
adb push Weik/. "/sdcard/$root/" >push.log
adb logcat -c
# Launch the real native activity with the loopback settings already written.
docker exec qa-phone am start -W -n "$pkg/com.wn.blackrussia.game.Multiplayer"
declare -A seen
for n in $(seq 1 145); do
  docker logs qa-server >evidence/server.txt 2>&1
  stage=$(awk '/RRP QA FRAME [0-9]+/{print $NF}' evidence/server.txt | tail -1)
  if [[ -n "$stage" && -z "${seen[$stage]:-}" ]]; then
    sleep 2
    if test "$stage" = 0; then
      adb shell dumpsys activity activities | grep -E 'topResumedActivity|mResumedActivity' >evidence/focus.txt || true
      adb shell uiautomator dump /sdcard/qa-window.xml >/dev/null || true
      adb pull /sdcard/qa-window.xml evidence/window.xml >/dev/null || true
      adb shell dumpsys SurfaceFlinger --list >evidence/surfaces.txt
    fi
    adb exec-out screencap -p >"evidence/scene-$stage.png"
    while IFS= read -r surface; do
      adb shell "dumpsys SurfaceFlinger --latency '$surface'" >frames.tmp
      if awk 'NF==3 && $2>0 && $2<9e18 {n++} END {exit !(n>=5)}' frames.tmp; then
        cp frames.tmp "evidence/frames-$stage.txt"
        break
      fi
    done < <(adb shell dumpsys SurfaceFlinger --list | tr -d '\r' | grep SurfaceView | grep -F "$pkg")
    seen[$stage]=yes
  fi
  if grep -q 'RRP QA END' evidence/server.txt; then break; fi
  if ! adb shell pidof "$pkg" >/dev/null; then break; fi
  sleep 1
done
adb logcat -b crash -d >evidence/crash.txt
adb shell "tail -120 /sdcard/$root/reBRClientLog.txt" >evidence/client.txt || true
grep -q 'RRP QA END' evidence/server.txt
test "${#seen[@]}" = 13
test "$(sha256sum evidence/scene-*.png | cut -d' ' -f1 | sort -u | wc -l)" -ge 7
