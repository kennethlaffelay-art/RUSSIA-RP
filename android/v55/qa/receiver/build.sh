set -euo pipefail
androidjar="$ANDROID_HOME/platforms/android-35/android.jar"
tools=$(ls -d "$ANDROID_HOME/build-tools"/* | sort -V | tail -1)
mkdir -p compiled dex
javac -source 8 -target 8 -classpath "$androidjar" -d compiled Receiver.java
jar cf classes.jar -C compiled .
"$tools/d8" --min-api 26 --lib "$androidjar" --output dex classes.jar
"$tools/aapt" package -f -M AndroidManifest.xml -I "$androidjar" -F draft.apk
(cd dex && zip -q ../draft.apk classes.dex)
"$tools/zipalign" -f 4 draft.apk aligned.apk
keytool -genkeypair -keyalg RSA -keystore qa.p12 -storepass tempqa123 -alias receiver -dname CN=Disposable-Test -validity 5 >/dev/null 2>&1
"$tools/apksigner" sign --ks qa.p12 --ks-pass pass:tempqa123 --out receiver.apk aligned.apk
adb install receiver.apk
