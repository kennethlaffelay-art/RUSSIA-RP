#!/usr/bin/env bash
set -euo pipefail
src="$GITHUB_WORKSPACE/winter/2027"
jobdir="$RUNNER_TEMP/winter"
mkdir -p "$jobdir/evidence"
cd "$jobdir"
sudo apt-get -qq update
sudo apt-get -qq install -y adb aapt apksigner fonts-dejavu-core python3-pil python3-venv
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
mkdir -p recorder
fetch https://storage.googleapis.com/r8-releases/raw/8.3.37/r8.jar recorder/r8.jar
if test "$EDITION" = winter; then
  git clone -q https://github.com/Parik27/DragonFF.git dragon
  git -C dragon checkout -q 319847f7803f102c5aa31fa38e8b3284117db40a
  python3 -m venv env
  env/bin/pip -q install 'Pillow==12.2.0' numpy scipy fonttools
  fetch https://github.com/iBotPeaches/Apktool/releases/download/v2.11.1/apktool_2.11.1.jar apktool.jar
  PYTHONPATH=dragon env/bin/python "$src/build_assets.py" baseline.apk cache20.zip Weik assets-out /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
  env/bin/python "$src/package.py" baseline.apk assets-out apktool.jar unsigned.apk --preview --r8 recorder/r8.jar
  app=unsigned.apk
  pkg=com.russiarp.snow
elif test "$EDITION" = standalone; then
  pkg=com.russiarp.winter27
  app="$RUNNER_TEMP/RUSSIA-RP-1.7.24-Winter-Weik.apk"
  apksigner verify --verbose "$app"
  adb install -g baseline.apk
  adb install -g "$app"
  adb shell pm path com.russiarp.hudx | grep -q 'base.apk'
  adb shell pm path "$pkg" | grep -q 'base.apk'
  echo 'Both signed APKs installed alongside each other' >evidence/coexistence.txt
  # Instrumentation needs the same test certificate as its target on the disposable device.
  adb uninstall "$pkg"
fi
# Stage the same install that the production launcher verifies. Only the local test host differs.
python3 "$src/qa/stage.py" Weik baseline.apk cache20.zip
keytool -genkeypair -keystore qa.p12 -storetype PKCS12 -storepass android-test -keyalg RSA -keysize 2048 -alias qa -dname 'CN=Isolated Android QA' -validity 5
apksigner sign --ks qa.p12 --ks-pass pass:android-test --out client-qa.apk "$app"
mkdir -p recorder/classes recorder/dex
fetch https://raw.githubusercontent.com/Sable/android-platforms/1e98db1a199e8f7f85541af26bfc27019501b132/android-31/android.jar recorder/android.jar
echo 'd53c940da56e816deb259c3b43b667b43d82d8615029ee10fa5bff641ef0123d  recorder/android.jar' | sha256sum -c -
echo '900dfbc649519969fc5a4c7520d6b7355338e565fa1249874e0190b8d61b1199  recorder/r8.jar' | sha256sum -c -
javac -source 8 -target 8 -classpath recorder/android.jar -d recorder/classes "$src/qa/WorldCapture.java" "$src/qa/CacheUpgrade.java"
java -cp recorder/r8.jar com.android.tools.r8.D8 --min-api 26 --lib recorder/android.jar --output recorder/dex recorder/classes/com/russiarp/qa/*.class
cat >recorder/AndroidManifest.xml <<XML
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.russiarp.qa.capture">
  <uses-sdk android:minSdkVersion="26" android:targetSdkVersion="28"/>
  <application android:label="World capture"/>
  <instrumentation android:name="com.russiarp.qa.CacheUpgrade" android:targetPackage="$pkg"/>
  <instrumentation android:name="com.russiarp.qa.WorldCapture" android:targetPackage="$pkg"/>
</manifest>
XML
aapt package -f -M recorder/AndroidManifest.xml -I recorder/android.jar -F recorder/unsigned.apk
zip -qj recorder/unsigned.apk recorder/dex/classes.dex
apksigner sign --ks qa.p12 --ks-pass pass:android-test --out recorder/test.apk recorder/unsigned.apk
fetch https://github.com/openmultiplayer/open.mp/releases/download/v1.6.7.3218/open.mp-linux-x86.tar.gz omp.tar.gz
echo '0f7bfe70bb68ea780fe24a910b69412046e53d10feb65a9d4a9de8ff1f7f1329  omp.tar.gz' | sha256sum -c -
tar xzf omp.tar.gz
fetch https://github.com/katursis/Pawn.RakNet/releases/download/1.6.0-omp/pawnraknet-1.6.0-omp-linux.tar.gz plates-qa.tar.gz
echo '0cdc9690ea421dead02560f6c550c68ea17540d00a27eed4c8b6e3b0841afbe6  plates-qa.tar.gz' | sha256sum -c -
tar xOf plates-qa.tar.gz pawnraknet.so >Server/components/pawnraknet.so
tar xOf plates-qa.tar.gz Pawn.RakNet.inc >Server/qawno/include/Pawn.RakNet.inc
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
adb install -g client-qa.apk
adb install -t recorder/test.apk
adb shell appops set --uid "$pkg" MANAGE_EXTERNAL_STORAGE allow
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
adb shell settings put secure immersive_mode_confirmations confirmed
adb push Weik/. "/sdcard/$root/" >push.log
if [[ "$EDITION" = winter || "$EDITION" = standalone ]]; then
  adb shell am instrument -w com.russiarp.qa.capture/com.russiarp.qa.CacheUpgrade >evidence/cache-upgrade.txt 2>&1
  cat evidence/cache-upgrade.txt
  grep -Fq 'verified offline, zero archive requests' evidence/cache-upgrade.txt
  adb shell test -d /sdcard/Weik/texdb
  adb shell test ! -e /sdcard/RWin
fi
adb logcat -c
# Launch the real native activity with the loopback settings already written.
record_dir="/sdcard/Android/data/$pkg/files"
adb shell am instrument -w com.russiarp.qa.capture/com.russiarp.qa.WorldCapture >evidence/recorder.txt 2>&1 &
for n in $(seq 1 30); do
  if adb shell pidof "$pkg" >/dev/null; then break; fi
  sleep 1
done
declare -A seen
for n in $(seq 1 225); do
  docker logs qa-server >evidence/server.txt 2>&1
  stage=$(awk '/RRP QA FRAME [0-9]+/{print $NF}' evidence/server.txt | tail -1)
  if [[ -n "$stage" && -z "${seen[$stage]:-}" ]]; then
    if test "$stage" = 0; then
      adb shell touch "$record_dir/spawn.complete"
      sleep 1
    fi
    adb shell dumpsys SurfaceFlinger --timestats -clear -enable >/dev/null
    sleep 2
    if test "$stage" = 0; then
      adb shell dumpsys activity activities | grep -E 'topResumedActivity|mResumedActivity' >evidence/focus.txt || true
      adb shell uiautomator dump /sdcard/qa-window.xml >/dev/null || true
      adb pull /sdcard/qa-window.xml evidence/window.xml >/dev/null || true
      adb shell dumpsys SurfaceFlinger --list >evidence/surfaces.txt
    fi
    adb exec-out screencap -p >"evidence/scene-$stage.png"
    adb shell rm -f "$record_dir/world.png"
    adb shell touch "$record_dir/capture.request"
    for tick in $(seq 1 18); do
      if adb shell test -s "$record_dir/world.png"; then
        adb pull "$record_dir/world.png" "evidence/world-$stage.png" >/dev/null
        break
      fi
      sleep 0.1
    done
    adb shell dumpsys SurfaceFlinger --timestats -dump >"evidence/timestats-$stage.txt"
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
test "${#seen[@]}" = 17
test "$(sha256sum evidence/scene-*.png | cut -d' ' -f1 | sort -u | wc -l)" -ge 7
