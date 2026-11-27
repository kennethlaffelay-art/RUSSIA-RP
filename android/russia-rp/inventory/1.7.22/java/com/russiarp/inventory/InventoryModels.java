package com.russiarp.inventory;

import android.content.Context;
import android.graphics.Bitmap;
import android.util.Base64;
import android.widget.ImageView;
import com.wn.blackrussia.game.ui.util.EntitySnaps;
import com.wn.blackrussia.game.ui.util.SnapShot;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Requests the same cached model renders as the game's shop and battle pass. */
final class InventoryModels {
    interface Listener { void ready(String key, String png); }
    private final Context context;
    private final Listener listener;
    private final ArrayList<ImageView> targets=new ArrayList<>();
    private final ExecutorService encoder=Executors.newSingleThreadExecutor();
    private volatile boolean closed;

    InventoryModels(Context context, Listener listener) {
        this.context=context;
        this.listener=listener;
    }
    void load(String body) {
        for (String line:body.split("\n")) {
            String[] fields=line.split("\t",2);
            if(fields.length!=2) continue;
            if(fields[0].equals("Одежда")) {
                try {
                    int id=Integer.parseInt(fields[1].trim());
                    if(id>=0 && id!=74 && id<20000) request("player",1,id);
                } catch(NumberFormatException ignored) {}
            } else if(fields[0].matches("Оружие [0-9]+")) {
                String name=fields[1].split("\\|",2)[0];
                Integer id=WeaponModels.IDS.get(name);
                if(id!=null) request(name,0,id);
            }
        }
    }
    private void request(String key,int type,int model) {
        if(!EntitySnaps.INSTANCE.isModelAvailable(model)) return;
        ImageView target=new ImageView(context) {
            private boolean received;
            @Override public void setImageBitmap(Bitmap bitmap) {
                super.setImageBitmap(bitmap);
                if(bitmap==null || received || closed) return;
                received=true;
                encoder.execute(()->{
                    try {
                        String png=encode(bitmap);
                        if(png!=null && !closed) {
                            new android.os.Handler(android.os.Looper.getMainLooper()).post(()->{
                                if(!closed) listener.ready(key,png);
                            });
                        }
                    } catch(RuntimeException ex) {
                        android.util.Log.w("RussiaInventory","Model image unavailable",ex);
                    }
                });
            }
        };
        targets.add(target);
        SnapShot request=type==1 ? new SnapShot(type,model,0f,0f,-12f,1.05f,-1,-1)
                : new SnapShot(type,model,15f,0f,-72f,1f,-1,-1);
        EntitySnaps.INSTANCE.load(request,target);
    }
    private static String encode(Bitmap bitmap) {
        int w=bitmap.getWidth(),h=bitmap.getHeight();
        if(w<1 || h<1 || w>2048 || h>2048) return null;
        int[] pixels=new int[w*h];bitmap.getPixels(pixels,0,w,0,0,w,h);
        int left=w,top=h,right=-1,bottom=-1;
        for(int y=0; y<h; y++) for(int x=0; x<w; x++) {
            if((pixels[y*w+x]>>>24)<24) continue;
            left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);
        }
        if(right<left || bottom<top) return null;
        Bitmap crop=Bitmap.createBitmap(bitmap,left,top,right-left+1,bottom-top+1);
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        if(!crop.compress(Bitmap.CompressFormat.PNG,100,bytes)) return null;
        return "data:image/png;base64,"+Base64.encodeToString(bytes.toByteArray(),Base64.NO_WRAP);
    }
    void close() {
        closed=true;
        for(ImageView target:targets) EntitySnaps.INSTANCE.clear(target);
        targets.clear();encoder.shutdownNow();
    }
}
