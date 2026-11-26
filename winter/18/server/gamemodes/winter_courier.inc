#define COURIER_TRIP_BONUS (1500)
#define COURIER_DISPATCH (29782)
stock CourierNearDepot(p) {
    return GetPlayerVirtualWorld(p)==0 && GetPlayerInterior(p)==0 && IsPlayerInRangeOfPoint(p,5.0,2761.081,-2391.776,21.891);
}
stock CourierMark(p) {
    new stop=GetPVarInt(p,"PizzaCheck")-1;
    if(stop<0 || stop>=sizeof PizzaCheckpoint) return 0;
    DisablePlayerGPS(p);
    SetPlayerCheckpoint(p,PizzaCheckpoint[stop][0],PizzaCheckpoint[stop][1],PizzaCheckpoint[stop][2],3.0,CP_ACTION_TYPE_COURIER);
    BR_SetGPSLine(p,PizzaCheckpoint[stop][0],PizzaCheckpoint[stop][1],PizzaCheckpoint[stop][2]);
    return 1;
}
stock CourierFinish(p,bool:restore=true) {
    if(!GetPVarInt(p,"PizzaCheck")) return 0;
    new vehicle=Pizza[p], skin=GetPVarInt(p,"GetPlayerSkin");
    Pizza[p]=0;
    DeletePVar(p,"PizzaCheck");
    DeletePVar(p,"PizzaTime");
    DeletePVar(p,"CourierDrops");
    DeletePVar(p,"GetPlayerSkin");
    if(restore) {
        if(GetPlayerCPInfo(p,CP_ACTION_TYPE)==CP_ACTION_TYPE_COURIER) {
            DisablePlayerCheckpoint(p);
            BR_SetGPSLine(p,0.0,0.0,0.0);
        }
        if(GetPlayerSkin(p)==155) SetPlayerSkin(p,skin);
        SendClientMessage(p,-1,"Смена завершена. Деньги за доставленные заказы уже на счёте.");
    }
    if(vehicle>0 && vehicle!=INVALID_VEHICLE_ID && IsValidVehicle(vehicle)) DestroyVehicle(vehicle);
    return 1;
}
stock CourierStart(p) {
    if(!IsPlayerLogged(p) || GetPVarInt(p,"PizzaCheck") || !CourierNearDepot(p) || GetPlayerState(p)!=PLAYER_STATE_ONFOOT) return 1;
    if(GetPlayerLevel(p)<2 || GetPlayerTeamEx(p)!=0)
        return SendClientMessage(p,-1,"Для работы нужен 2 уровень. Сотрудники фракций не могут начать смену.");
    if(GetPlayerJob(p)!=0 && GetPlayerJob(p)!=JOB_KYRER)
        return SendClientMessage(p,-1,"Сначала завершите работу и увольтесь с текущей должности в мэрии.");
    if(GetPlayerTempJob(p)!=TEMP_JOB_NONE || IsPlayerInJob(p))
        return SendClientMessage(p,-1,"Сначала завершите действующую смену.");
    if(GetPlayerJob(p)==0) {
        new query[110];
        mysql_format(mysql,query,sizeof query,"UPDATE accounts SET job=%d WHERE id=%d AND job=0 LIMIT 1",JOB_KYRER,GetPlayerAccountID(p));
        new Cache:result=mysql_query(mysql,query);
        if(!cache_is_valid(result)) return SendClientMessage(p,-1,"Не удалось оформить трудоустройство. Повторите попытку.");
        new hired=cache_affected_rows();
        cache_delete(result);
        if(hired!=1) return SendClientMessage(p,-1,"Не удалось оформить трудоустройство. Проверьте должность в мэрии.");
        SetPlayerData(p,P_JOB,JOB_KYRER);
    }
    new vehicle=CreateVehicle(462,2772.0488,-2394.6960,21.4869,183.3,0,0,-1);
    if(vehicle<=0 || vehicle==INVALID_VEHICLE_ID) return SendClientMessage(p,-1,"Свободных мопедов сейчас нет. Попробуйте ещё раз.");
    Pizza[p]=vehicle;
    SetPVarInt(p,"GetPlayerSkin",GetPlayerSkin(p));
    SetPVarInt(p,"PizzaCheck",random(sizeof PizzaCheckpoint)+1);
    SetPVarInt(p,"PizzaTime",gettime()+PizzaTime);
    SetPVarInt(p,"CourierDrops",0);
    SetPlayerSkin(p,155);
    PutPlayerInVehicle(p,vehicle,0);
    CourierMark(p);
    BR_BlackPassProgress(p,BP_EVENT_JOB_COURIER_START,1);
    SendClientMessage(p,-1,"Первый заказ на карте. За доставку 1 000 руб., за каждые три подряд — ещё 1 500 руб.");
    return 1;
}
stock CourierDeliver(p) {
    new stop=GetPVarInt(p,"PizzaCheck")-1;
    if(stop<0 || stop>=sizeof PizzaCheckpoint) return 1;
    if(gettime()>=GetPVarInt(p,"PizzaTime") || GetPlayerJob(p)!=JOB_KYRER) return CourierFinish(p);
    if(GetPlayerVirtualWorld(p)!=0 || GetPlayerInterior(p)!=0 ||
       !IsPlayerInRangeOfPoint(p,4.5,PizzaCheckpoint[stop][0],PizzaCheckpoint[stop][1],PizzaCheckpoint[stop][2])) return 1;
    if(GetPlayerState(p)!=PLAYER_STATE_DRIVER || GetPlayerVehicleID(p)!=Pizza[p])
        return SendClientMessage(p,-1,"Подъедьте к адресу на мопеде, выданном для смены.");
    new count=GetPVarInt(p,"CourierDrops")+1, pay=PizzaMoney;
    if(count%3==0) pay+=COURIER_TRIP_BONUS;
    new next=(stop+1+random(sizeof PizzaCheckpoint-1))%sizeof PizzaCheckpoint;
    SetPVarInt(p,"PizzaCheck",next+1);
    SetPVarInt(p,"CourierDrops",count);
    SetPVarInt(p,"PizzaTime",gettime()+PizzaTime);
    GivePlayerMoneyEx(p,pay,"Зимняя доставка",true,true);
    new text[124];
    if(count%3==0) format(text,sizeof text,"Три заказа доставлены. На счёт зачислено %d руб. вместе с зимней премией.",pay);
    else format(text,sizeof text,"Заказ доставлен. +%d руб. До зимней премии осталось адресов: %d.",pay,3-count%3);
    SendClientMessage(p,-1,text);
    return CourierMark(p);
}
CMD:courier(playerid) {
    if(!IsPlayerLogged(playerid)) return 1;
    if(GetPVarInt(playerid,"PizzaCheck")) {
        new title[85], remain=GetPVarInt(playerid,"PizzaTime")-gettime();
        if(remain<=0) return CourierFinish(playerid);
        format(title,sizeof title,"Зимняя доставка | Заказов: %d | %d:%02d",GetPVarInt(playerid,"CourierDrops"),remain/60,remain%60);
        return Dialog(playerid,COURIER_DISPATCH,DIALOG_STYLE_LIST,title,"Показать адрес заказа\nЗавершить смену","Выбрать","Закрыть");
    }
    if(CourierNearDepot(playerid))
        return Dialog(playerid,17173,DIALOG_STYLE_MSGBOX,"Зимняя доставка","Начать смену курьера? Нужен 2 уровень.\nМопед выдаётся на складе. На каждый адрес даётся 5 минут.\nОплата: 1 000 руб. за заказ и ещё 1 500 руб. за три подряд.","Начать","Закрыть");
    return EnablePlayerGPS(playerid,55,2761.081,-2391.776,21.891,"Склад отмечен в GPS. Подойдите к форме курьера, чтобы начать смену.");
}
