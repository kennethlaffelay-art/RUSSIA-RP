set -euo pipefail
sudo apt-get -qq update
sudo apt-get -qq install -y libsmali-java
ls /usr/share/java/*smali* 
for num in '' 4 8; do
    unzip -p base.apk "classes$num.dex" > launch.dex
    baksmali disassemble launch.dex -o "smali$num"
done
echo "Cache progress API"
rg 'setProgress\(' smali8/ru/russiarp/install/StockCache.smali
echo "Launcher classes"
rg -l 'Lcom/wn/blackrussia/game/Multiplayer;|samp/settings\.ini|SAMP/settings\.ini|setServer|server_ip|"ip"|"port"' smali/blackrussia smali4/com/wn/blackrussia/game/Multiplayer.smali | head -80 || true
echo "Entry method names and arguments"
rg -n -i '(^\.method|->get.*Extra\(|->putExtra\(|const-string.*"(ip|port|host|server|nickname|address)|Multiplayer;|->connect\()' smali4/com/wn/blackrussia/game/Multiplayer.smali | head -175 || true
for f in $(rg -l 'Lcom/wn/blackrussia/game/Multiplayer;' smali/blackrussia); do
 echo "ENTRY $f"
 rg -n -C 9 'Lcom/wn/blackrussia/game/Multiplayer;' "$f" | head -95 || true
done
echo "Original settings keys"
unzip -p base.apk assets/settings.ini | sed -E 's/^([^=]+)=.*/\1=.../'
unzip -p base.apk lib/arm64-v8a/libmultiplayer.so | strings | grep -Ei '^((ip|host|server|addr|port|client|name|nickname)|.*(server|connect)(ip|host|port)|server[_\.][a-z]{2,12})$' | sort -u | head -90 || true
