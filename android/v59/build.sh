set -euo pipefail
export LC_ALL=C
checksrc="$GITHUB_WORKSPACE/android/v59"
cd "$RUNNER_TEMP"
curl -fsSL --retry 3 "https://github.com/$GITHUB_REPOSITORY/releases/download/client-v5.7-game-surface/RUSSIA_v5.7.apk" -o base.apk
echo '6fb0fb4cf7687e7c9687c097bde162432803c36543f365a720e8a015aefb1463  base.apk' | sha256sum -c
sdk="$ANDROID_HOME/build-tools/35.0.0"
androidjar="$ANDROID_HOME/platforms/android-36/android.jar"
test -f "$androidjar"
mkdir -p stubsrc/com/akexorcist/roundcornerprogressbar stubclasses cacheclasses dex
cat > stubsrc/com/akexorcist/roundcornerprogressbar/RoundCornerProgressBar.java <<'JAVA'
package com.akexorcist.roundcornerprogressbar;
public abstract class RoundCornerProgressBar extends android.view.View {
    public RoundCornerProgressBar(android.content.Context c) { super(c); }
    public abstract void setProgress(int progress);
}
JAVA
javac -source 8 -target 8 -classpath "$androidjar" -d stubclasses stubsrc/com/akexorcist/roundcornerprogressbar/RoundCornerProgressBar.java
javac -source 8 -target 8 -classpath "$androidjar:stubclasses" -d cacheclasses "$GITHUB_WORKSPACE/android/v54/StockCache.java"
jar cf cache.jar -C cacheclasses .
jar cf stubs.jar -C stubclasses .
"$sdk/d8" --min-api 26 --lib "$androidjar" --classpath stubs.jar --output dex cache.jar
unzip -p base.apk classes8.dex > previous.dex
for item in previous.dex dex/classes.dex; do
  "$sdk/dexdump" "$item" | sed -n 's/.*Class descriptor  *: //p' | LC_ALL=C sort > "$(basename "$item").list"
done
for list in previous.dex.list classes.dex.list; do
  grep -F -e 'Lru/russiarp/install/StockCache;' -e 'Lru/russiarp/install/StockCache$Entry;' "$list" | sort > "$list.api"
done
diff -u previous.dex.list.api classes.dex.list.api
test "$(wc -l < classes.dex.list.api)" -eq 2
"$sdk/dexdump" dex/classes.dex | grep 'canCheckSizeOnly' >/dev/null
python3 "$checksrc/package.py"
"$sdk/zipalign" -P 16 -f 4 rebuilt.apk aligned.apk
"$sdk/zipalign" -P 16 -c 4 aligned.apk
"$sdk/aapt" dump badging aligned.apk > badging.txt
grep -F "package: name='com.wn.russiarpfix' versionCode='27' versionName='1.7.1'" badging.txt
grep -F "launchable-activity: name='blackrussia.online.activities.SplashActivity'" badging.txt
grep "^native-code: .*'arm64-v8a'" badging.txt
python3 "$checksrc/signing.py" digest aligned.apk
