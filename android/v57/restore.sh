set -euo pipefail
src="https://raw.githubusercontent.com/$GITHUB_REPOSITORY/$GITHUB_SHA/android/v57"
dl="https://github.com/$GITHUB_REPOSITORY/releases/download"
curl -fsSL --retry 3 "$dl/client-v5.6-arm64-world/RUSSIA_v5.6.apk" -o base.apk
echo '3b03e2ccd7a80f3894376f681b7e42b1b27e33daa0e562a42e56c859b458fce2  base.apk' | sha256sum -c
for file in client.zst.b64 changed.dex.b64 SHA256SUMS Merge.java release.md; do curl -fsSL --retry 3 "$src/$file" -o "$file"; done
mvn=https://repo.maven.apache.org/maven2
mkdir -p jars
curl -fsSL --retry 3 "$mvn/org/smali/dexlib2/2.5.2/dexlib2-2.5.2.jar" -o jars/dexlib2.jar
curl -fsSL --retry 3 "$mvn/com/google/guava/guava/27.1-android/guava-27.1-android.jar" -o jars/guava.jar
curl -fsSL --retry 3 "$mvn/com/google/guava/failureaccess/1.0.1/failureaccess-1.0.1.jar" -o jars/failureaccess.jar
unzip -p base.apk classes4.dex > base.dex
base64 -d changed.dex.b64 > small.dex
javac -cp 'jars/*' Merge.java
java -Xmx1500m -cp '.:jars/*' Merge base.dex small.dex merged.dex
echo 'e2e85b58a8e66a36d1142785ae251cfa629c0712d49dbb8d914c91fbe200ebb0  merged.dex' | sha256sum -c
cat base.apk merged.dex > basis
base64 -d client.zst.b64 > delta.zst
zstd -dq --long=27 --patch-from=basis delta.zst -o candidate.apk
sha256sum -c SHA256SUMS
