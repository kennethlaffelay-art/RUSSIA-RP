set -euo pipefail
src="$GITHUB_WORKSPACE/android/v510"
cd "$RUNNER_TEMP"
curl -fsSL --retry 3 "https://github.com/$GITHUB_REPOSITORY/releases/download/client-v5.9-cache-repair/RUSSIA_v5.9.apk" -o base.apk
echo '4b30b67b77e9e9ca3d808d8ca1f1e557b59033cc79a967b36883b15de050c3e6  base.apk' | sha256sum -c
sdk="$ANDROID_HOME/build-tools/35.0.0"
androidjar="$ANDROID_HOME/platforms/android-36/android.jar"
mkdir -p stubsrc/com/akexorcist/roundcornerprogressbar stubsrc/blackrussia/online stubclasses compiled dex
cat > stubsrc/com/akexorcist/roundcornerprogressbar/RoundCornerProgressBar.java <<'JAVA'
package com.akexorcist.roundcornerprogressbar;
public abstract class RoundCornerProgressBar extends android.view.View {
    public RoundCornerProgressBar(android.content.Context c){super(c);}
    public abstract void setProgress(int value);
}
JAVA
cat > stubsrc/blackrussia/online/Preferences.java <<'JAVA'
package blackrussia.online;
public class Preferences {
    public static native void putString(android.content.Context context, String key, String value);
}
JAVA
python3 - "$GITHUB_WORKSPACE/android/v54/StockCache.java" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
marker='        if(!marker.isFile())Files.createFile(marker.toPath());'
assert s.count(marker)==1
Path('StockCache.java').write_text(s.replace(marker,'        ProjectEndpoint.configure(activity, target("SAMP/settings.ini"));\n'+marker))
PY
javac -source 8 -target 8 -cp "$androidjar" -d stubclasses $(find stubsrc -name '*.java')
javac -source 8 -target 8 -cp "$androidjar:stubclasses" -d compiled StockCache.java "$src/ProjectEndpoint.java"
jar cf stub.jar -C stubclasses .
jar cf client.jar -C compiled .
"$sdk/d8" --min-api 26 --lib "$androidjar" --classpath stub.jar --output dex client.jar
cp dex/classes.dex .
python3 "$src/prepare.py"
"$sdk/zipalign" -P 16 -f 4 stage.apk client-template.apk
"$sdk/zipalign" -P 16 -c 4 client-template.apk
"$sdk/aapt" dump badging client-template.apk | grep "^package: name='com.wn.russiarpfix' versionCode='28' versionName='1.7.2'"
# Include the official offline verifier for identical personalized APKs.
cp "$sdk/lib/apksigner.jar" .
