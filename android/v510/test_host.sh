set -euo pipefail
cd "$RUNNER_TEMP"
mkdir -p omp-stage compiler
curl -fsSL --retry 3 https://github.com/openmultiplayer/open.mp/releases/download/v1.6.7.3218/open.mp-linux-x86.tar.gz -o omp.tgz
echo '0f7bfe70bb68ea780fe24a910b69412046e53d10feb65a9d4a9de8ff1f7f1329  omp.tgz' | sha256sum -c
tar -xzf omp.tgz -C omp-stage
curl -fsSL --retry 3 https://github.com/pawn-lang/compiler/releases/download/v3.10.10/pawnc-3.10.10-linux.tar.gz -o pawn.tgz
tar -xzf pawn.tgz -C compiler
dir=$(dirname "$(find "$RUNNER_TEMP/omp-stage" -type f -name omp-server | head -1)")
pawn=$(find "$RUNNER_TEMP/compiler" -type f -name pawncc | head -1)
cd "$dir"
cat > testmode.pwn <<'PAWN'
native print(const message[]);
native AddPlayerClass(modelid, Float:x, Float:y, Float:z, Float:angle, w1, a1, w2, a2, w3, a3);
native SetSpawnInfo(playerid, team, skin, Float:x, Float:y, Float:z, Float:angle, w1, a1, w2, a2, w3, a3);
native SpawnPlayer(playerid);
native SetCameraBehindPlayer(playerid);
forward OnGameModeInit();
forward OnPlayerConnect(playerid);
forward OnPlayerRequestClass(playerid,classid);
forward OnPlayerSpawn(playerid);
main() {}
public OnGameModeInit() {
    AddPlayerClass(0, 0.0, 0.0, 15.0, 0.0, 0, 0, 0, 0, 0, 0);
    print("TEST_SERVER_READY");
    return 1;
}
public OnPlayerConnect(playerid) {
    print("TEST_PLAYER_CONNECTED");
    SetSpawnInfo(playerid, 255, 0, 0.0, 0.0, 15.0, 0.0, 0, 0, 0, 0, 0, 0);
    SpawnPlayer(playerid);
    return 1;
}
public OnPlayerRequestClass(playerid, classid) {
    SpawnPlayer(playerid);
    return 1;
}
public OnPlayerSpawn(playerid) {
    SetCameraBehindPlayer(playerid);
    print("TEST_PLAYER_SPAWNED");
    return 1;
}
PAWN
mkdir -p gamemodes scriptfiles
export LD_LIBRARY_PATH="$(dirname "$pawn"):$(dirname "$(find "$RUNNER_TEMP/compiler" -name 'libpawnc.so*' | head -1)"):${LD_LIBRARY_PATH:-}"
"$pawn" testmode.pwn -ogamemodes/testmode.amx
test -s gamemodes/testmode.amx
cat > config.json <<'JSON'
{"name":"Local test server","announce":false,"rcon":{"enable":false},"pawn":{"main_scripts":["testmode 1"],"side_scripts":[]},"network":{"bind":"127.0.0.1","port":7777,"allow_037_clients":true,"use_omp_encryption":false},"artwork":{"enable":false}}
JSON
chmod +x ./omp-server
./omp-server > "$RUNNER_TEMP/local-server.log" 2>&1 &
for _ in $(seq 1 25); do
  if grep -Fq TEST_SERVER_READY "$RUNNER_TEMP/local-server.log"; then echo SERVER_FIXTURE_READY; break; fi
  sleep 1
done
if ! grep -Fq TEST_SERVER_READY "$RUNNER_TEMP/local-server.log"; then
  tail -25 "$RUNNER_TEMP/local-server.log"; exit 1
fi
# Only count game traffic to the loopback test fixture. Packet bodies are never collected.
sudo tcpdump -n -l -q -i lo 'udp dst port 7777 and dst host 127.0.0.1' > "$RUNNER_TEMP/local-udp-count.log" 2>/dev/null &
