set -euo pipefail
cd "$RUNNER_TEMP"
sdk="$ANDROID_HOME/cmdline-tools/latest/bin"
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"
export ANDROID_AVD_HOME="$RUNNER_TEMP/cache-avd"
mkdir -p "$ANDROID_AVD_HOME"
pkg="system-images;android-36;google_apis;x86_64"
"$sdk/sdkmanager" "$pkg" emulator platform-tools > sdk.log
echo no | "$sdk/avdmanager" create avd --force -n repair -k "$pkg" --device pixel_4
cfg="$ANDROID_AVD_HOME/repair.avd/config.ini"
sed -i '/^disk.dataPartition.size=/d;/^hw.lcd./d' "$cfg"
echo 'disk.dataPartition.size=10000M' >> "$cfg"
echo 'hw.lcd.width=720' >> "$cfg"
echo 'hw.lcd.height=1280' >> "$cfg"
echo 'hw.lcd.density=240' >> "$cfg"
sudo apt-get -qq update
sudo apt-get -qq install -y libpulse0 libxkbcommon-x11-0 libxcb-cursor0 libglu1-mesa python3-pil
sudo setfacl -m "u:$(id -un):rw" /dev/kvm
adb start-server
emulator -avd repair -accel on -no-window -no-audio -no-boot-anim -no-snapshot -gpu swiftshader_indirect -feature -Vulkan -camera-back none -camera-front none -memory 3072 -cores 4 -partition-size 10000 >emu.log 2>&1 &
ep=$!
trap 'adb emu kill >/dev/null 2>&1 || true' EXIT
for i in $(seq 1 100); do
  kill -0 "$ep" || { tail -20 emu.log; exit 1; }
  if [[ "$(timeout 4 adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)" == 1 ]]; then break; fi
  sleep 3
done
test "$(timeout 8 adb shell getprop sys.boot_completed | tr -d '\r')" = 1
adb shell wm dismiss-keyguard
dl="https://github.com/$GITHUB_REPOSITORY/releases/download"
curl -fsSL --retry 3 "$dl/client-v5.7-game-surface/RUSSIA_v5.7.apk" -o baseline.apk
echo '6fb0fb4cf7687e7c9687c097bde162432803c36543f365a720e8a015aefb1463  baseline.apk' | sha256sum -c
adb install --abi arm64-v8a baseline.apk
adb install -g --abi arm64-v8a RUSSIA_v5.9.apk
adb shell pm path com.wn.blackrussia
adb shell pm path com.wn.russiarpfix
adb root
adb wait-for-device
adb shell appops set com.wn.russiarpfix MANAGE_EXTERNAL_STORAGE allow
adb shell settings put secure immersive_mode_confirmations confirmed
src="$GITHUB_WORKSPACE"
sed -e "s/^PKG='com.wn.blackrussia'/PKG='com.wn.russiarpfix'/" -e 's@/Android/data/com.wn.blackrussia/@/Android/data/com.wn.russiarpfix/@g' "$src/qa/v53-entry/full_check.py" > full_check.py
cp "$src/android/v54/fresh.py" .
/usr/bin/python3 -c 'from PIL import Image'
PYTHONPATH="$RUNNER_TEMP" /usr/bin/python3 -u "$src/android/v59/play_test.py"
