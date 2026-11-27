// Local camera route used only by the Android acceptance job.
#include <open.mp>
new carA,carB,extraCars[4],snow[5];
forward StartRoute(p);
forward Frame(p,step);
main() {}
public OnGameModeInit() {
    SetGameModeText("Winter acceptance");
    ManualVehicleEngineAndLights();
    AddPlayerClass(60,719.0,-2325.0,37.45,0.0,WEAPON_FIST,0,WEAPON_FIST,0,WEAPON_FIST,0);
    carA=CreateVehicle(411,714.0,-2325.0,37.15,0.0,0,0,-1);
    carB=CreateVehicle(445,724.0,-2325.0,37.15,0.0,1,1,-1);
    SetVehicleNumberPlate(carA,"A518MP");SetVehicleNumberPlate(carB,"T204KK");
    for(new i;i<4;i++)extraCars[i]=CreateVehicle(445,704.0+4.0*i,-2335.0,37.15,0.0,5,5,-1);
    return 1;
}
public OnPlayerConnect(playerid) {
    SetSpawnInfo(playerid,NO_TEAM,60,719.0,-2325.0,37.45,0.0,WEAPON_FIST,0,WEAPON_FIST,0,WEAPON_FIST,0);
    SetTimerEx("StartRoute",1800,false,"i",playerid);return 1;
}
public OnPlayerRequestClass(playerid,classid) { return 1; }
public StartRoute(p) { if(IsPlayerConnected(p)) SpawnPlayer(p);return 1; }
public OnPlayerSpawn(playerid) {
    TogglePlayerControllable(playerid,false);
    SetPlayerWeather(playerid,1);
    SetTimerEx("Frame",3500,false,"ii",playerid,0);
    return 1;
}
stock Camera(p,Float:x,Float:y,Float:z,Float:tx,Float:ty,Float:tz) {
    SetPlayerCameraPos(p,x,y,z);SetPlayerCameraLookAt(p,tx,ty,tz);
}
public Frame(p,step) {
    if(!IsPlayerConnected(p))return 1;
    switch(step) {
        case 0: {SetPlayerTime(p,13,0);Camera(p,753.0,-2351.0,85.0,719.0,-2297.0,37.0);}
        case 1: Camera(p,713.0,-2321.0,38.1,719.0,-2312.0,42.0);
        case 2: {SetPlayerTime(p,23,0);Camera(p,710.0,-2298.0,40.0,722.0,-2268.0,46.0);}
        case 3: {SetPlayerTime(p,12,0);Camera(p,729.0,-2319.0,38.0,718.0,-2325.0,37.0);}
        case 4: {SetPlayerTime(p,22,30);SetVehicleParamsEx(carA,1,0,0,0,0,0,0);Camera(p,717.0,-2317.0,38.2,714.0,-2325.0,37.2);}
        case 5: SetVehicleParamsEx(carA,1,1,0,0,0,0,0);
        case 6: {SetVehicleZAngle(carA,55.0);SetVehiclePos(carA,717.0,-2324.0,37.1);}
        case 7: {SetVehicleToRespawn(carA);SetVehicleParamsEx(carA,0,0,0,0,0,0,0);}
        case 8: {SetPlayerTime(p,13,0);Camera(p,714.0,-2321.6,37.06,714.0,-2325.2,37.01);}
        case 9: Camera(p,724.0,-2328.5,37.08,724.0,-2325.0,37.02);
        case 10: {SetPlayerTime(p,18,0);Camera(p,718.0,-2328.0,38.0,718.0,-2320.0,38.0);snow[0]=CreatePlayerObject(p,18864,718.0,-2324.0,39.0,0.0,0.0,0.0,40.0);}
        case 11: {for(new i=1;i<5;i++)snow[i]=CreatePlayerObject(p,18864,716.0+i,-2324.0+i,38.0+i*0.6,0.0,0.0,i*17.0,40.0);}
        case 12: {
            for(new i;i<5;i++)DestroyPlayerObject(p,snow[i]);
            SetPlayerTime(p,22,30);SetVehicleParamsEx(carA,1,1,0,0,0,0,0);SetVehicleParamsEx(carB,1,1,0,0,0,0,0);
            for(new i;i<4;i++)SetVehicleParamsEx(extraCars[i],1,1,0,0,0,0,0);
            Camera(p,706.0,-2313.0,41.5,714.0,-2327.0,37.0);
        }
        default: {print("RRP QA END");return 1;}
    }
    printf("RRP QA FRAME %d",step);
    SetTimerEx("Frame",6500,false,"ii",p,step+1);
    return 1;
}
