// Local camera route used only by the Android acceptance job.
#include <open.mp>
#include <Pawn.RakNet>
new carA,carB,extraCars[4],snow[5];
forward StartRoute(p);
forward Frame(p,step);
forward SettleCars(p,phase);
main() {}
public OnGameModeInit() {
    SetGameModeText("Winter acceptance");
    ManualVehicleEngineAndLights();
    AddPlayerClass(60,719.0,-2325.0,37.45,0.0,WEAPON_FIST,0,WEAPON_FIST,0,WEAPON_FIST,0);
    carA=CreateVehicle(411,714.0,-2343.00,37.15,0.0,0,0,-1);
    carB=CreateVehicle(445,724.0,-2343.00,37.15,0.0,1,1,-1);
    SetVehicleNumberPlate(carA,"A518MP77");SetVehicleNumberPlate(carB,"T204KK197");
    for(new i;i<4;i++)extraCars[i]=CreateVehicle(445,704.0+4.0*i,-2353.00,37.15,0.0,5,5,-1);
    return 1;
}
public OnPlayerConnect(playerid) {
    SetSpawnInfo(playerid,NO_TEAM,60,719.0,-2325.0,37.45,0.0,WEAPON_FIST,0,WEAPON_FIST,0,WEAPON_FIST,0);
    SetTimerEx("StartRoute",1800,false,"i",playerid);return 1;
}
public OnPlayerRequestClass(playerid,classid) { return 1; }
public StartRoute(p) { if(IsPlayerConnected(p)) SpawnPlayer(p);return 1; }
public OnPlayerSpawn(playerid) {
    SetPlayerWeather(playerid,1);
    SetTimerEx("SettleCars",900,false,"ii",playerid,0);
    return 1;
}
public SettleCars(p,phase) {
    if(!IsPlayerConnected(p))return 1;
    if(phase<2) {
        PutPlayerInVehicle(p,phase==0?carA:carB,0);
        SetTimerEx("SettleCars",2200,false,"ii",p,phase+1);
        return 1;
    }
    RemovePlayerFromVehicle(p);
    SetPlayerPos(p,719.0,-2325.0,37.35);
    TogglePlayerControllable(p,false);
    SetTimerEx("Frame",1800,false,"ii",p,0);
    return 1;
}
stock Camera(p,Float:x,Float:y,Float:z,Float:tx,Float:ty,Float:tz) {
    SetPlayerCameraPos(p,x,y,z);SetPlayerCameraLookAt(p,tx,ty,tz);
}
stock ShowPlate(playerid,vehicleid,const number[],const region[]) {
    // Stock SA-MP sets a single text string. The Moscow client receives a typed
    // registration and its region separately when the vehicle is streamed in.
    new BitStream:bs=BS_New();
    BS_WriteValue(bs,PR_UINT8,251,PR_UINT32,516,PR_UINT32,vehicleid,PR_UINT32,1,PR_STRING8,number,PR_STRING8,region);
    PR_SendPacket(bs,playerid);
    BS_Delete(bs);
}
public Frame(p,step) {
    if(!IsPlayerConnected(p))return 1;
    if(step==1 || step==8) {
        ShowPlate(p,carA,"A518MP","77");
        ShowPlate(p,carB,"T204KK","197");
    }
    if(step==14)ShowPlate(p,carA,"P607CT","7");
    switch(step) {
        case 0: {SetPlayerTime(p,13,0);Camera(p,753.0,-2351.0,85.0,719.0,-2297.0,37.0);}
        case 1: Camera(p,708.0,-2335.0,38.1,718.5,-2313.0,42.8);
        case 2: {SetPlayerTime(p,23,0);Camera(p,710.0,-2298.0,40.0,722.0,-2268.0,46.0);}
        case 3: {SetPlayerPos(p,719.0,-2342.0,37.40);SetPlayerTime(p,12,0);Camera(p,729.0,-2337.00,38.0,718.0,-2343.00,37.0);}
        case 4: {SetPlayerTime(p,22,30);SetVehicleParamsEx(carA,1,0,0,0,0,0,0);Camera(p,717.0,-2335.00,38.2,714.0,-2343.00,37.2);}
        case 5: SetVehicleParamsEx(carA,1,1,0,0,0,0,0);
        case 6: {SetVehicleZAngle(carA,55.0);SetVehiclePos(carA,717.0,-2342.00,37.1);}
        case 7: {SetVehicleToRespawn(carA);SetVehicleParamsEx(carA,0,0,0,0,0,0,0);}
        case 8: {SetPlayerTime(p,13,0);Camera(p,714.0,-2339.10,37.12,714.0,-2340.75,36.91);}
        case 9: Camera(p,724.0,-2347.10,37.14,724.0,-2345.10,36.98);
        case 10: {SetPlayerPos(p,712.0,-2323.0,37.40);SetPlayerTime(p,18,0);Camera(p,718.0,-2328.0,38.0,718.0,-2320.0,38.0);snow[0]=CreatePlayerObject(p,18864,718.0,-2324.0,39.0,0.0,0.0,0.0,40.0);}
        case 11: {for(new i=1;i<5;i++)snow[i]=CreatePlayerObject(p,18864,716.0+i,-2324.0+i,38.0+i*0.6,0.0,0.0,i*17.0,40.0);}
        case 12: {
            for(new i;i<5;i++)DestroyPlayerObject(p,snow[i]);
            SetPlayerTime(p,22,30);SetVehicleParamsEx(carA,1,1,0,0,0,0,0);SetVehicleParamsEx(carB,1,1,0,0,0,0,0);
            for(new i;i<4;i++)SetVehicleParamsEx(extraCars[i],1,1,0,0,0,0,0);
            Camera(p,706.0,-2331.00,41.5,714.0,-2345.00,37.0);
        }
        case 13: {SetPlayerTime(p,13,0);Camera(p,717.0,-2335.00,38.2,714.0,-2343.00,37.2);}
        case 14: {SetPlayerTime(p,22,0);Camera(p,714.0,-2347.10,37.14,714.0,-2345.10,36.98);}
        case 15: {SetPlayerTime(p,13,0);Camera(p,724.0,-2339.10,37.12,724.0,-2340.75,36.91);}
        case 16: {SetPlayerTime(p,12,30);SetPlayerPos(p,848.0,-2310.0,38.8);Camera(p,848.0,-2308.5,39.35,845.0,-2333.0,38.4);}
        default: {print("RRP QA END");return 1;}
    }
    printf("RRP QA FRAME %d",step);
    SetTimerEx("Frame",8500,false,"ii",p,step+1);
    return 1;
}
