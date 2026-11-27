package com.russiarp.inventory;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.net.Uri;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.PopupWindow;
import android.widget.TextView;
import com.wn.blackrussia.game.Multiplayer;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

public final class BagWindow extends PopupWindow {
    private static final int ID = 29560;
    private final Multiplayer game;
    private final int rows;
    private final boolean legacy;
    private boolean finished;
    private WebView web;
    private View hud;
    private float originalAlpha;
    private boolean pageReady;
    private InventoryModels models;
    private final java.util.Map<String,String> pendingModels=new java.util.HashMap<>();

    private void flushModels() {
        if (!pageReady || web==null || finished) return;
        for (java.util.Map.Entry<String,String> entry:pendingModels.entrySet()) {
            web.evaluateJavascript("window.applyInventoryModel("+JSONObject.quote(entry.getKey())+","+JSONObject.quote(entry.getValue())+")",null);
        }
        pendingModels.clear();
    }
    private void section(String key) {
        if(finished || key==null) return;
        String cmd;
        switch(key){
            case "donate": cmd="/donate"; break;
            case "bank": cmd="/bank"; break;
            case "pass": cmd="/bp"; break;
            case "awards": cmd="/reward"; break;
            case "eat": cmd="/eat"; break;
            default: return;
        }
        finished=true;
        dismiss();
        reply(0,-1);
        game.sendCommand(cmd.getBytes(StandardCharsets.US_ASCII));
    }

    public static PopupWindow open(Activity activity, int id, String title, String body) {
        if (id != ID || !(activity instanceof Multiplayer) || body == null || title == null ||
            !title.contains("Инвентарь") || !body.startsWith("Одежда") || body.length() > 8192) return null;
        BagWindow bag = new BagWindow((Multiplayer)activity, body);
        try {
            bag.present(body);
            return bag;
        } catch (Exception | LinkageError failure) {
            android.util.Log.w("RussiaInventory","Opening standard inventory dialog",failure);
            bag.finished = true;
            bag.dismiss();
            bag.release();
            return null;
        }
    }
    public static boolean setContentVisible(PopupWindow window, boolean visible) {
        if (!(window instanceof BagWindow) || !window.isShowing()) return false;
        window.getContentView().setVisibility(visible ? View.VISIBLE : View.GONE);
        return true;
    }
    public static void replace(PopupWindow last) {
        if (last instanceof BagWindow) {
            BagWindow bag = (BagWindow)last;
            bag.finished = true;
            bag.dismiss();
        }
    }
    private BagWindow(Multiplayer activity,String body) {
        game = activity;
        rows = body.split("\n").length;
        legacy = !body.contains("Профиль\t");
    }
    private void present(String body) throws Exception {
        String cash = "";
        int id = game.getResources().getIdentifier("brHudMoney","id",game.getPackageName());
        View money = id == 0 ? null : game.findViewById(id);
        if (money instanceof TextView) cash = ((TextView)money).getText().toString().replace("₽","").trim();
        JSONObject snapshot = new JSONObject().put("body",body).put("cash",cash);
        String data = snapshot.toString().replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026");
        String html;
        try (InputStream in = game.getAssets().open("russia/inventory.html");
             ByteArrayOutputStream bytes = new ByteArrayOutputStream()) {
            byte[] chunk = new byte[8192];
            int n;
            while ((n=in.read(chunk)) != -1) bytes.write(chunk,0,n);
            html = new String(bytes.toByteArray(),StandardCharsets.UTF_8).replace("__GAME_DATA__",data);
        }
        web = new WebView(game);
        web.setBackgroundColor(Color.TRANSPARENT);
        web.setVerticalScrollBarEnabled(false);
        WebSettings settings=web.getSettings();
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setBlockNetworkLoads(true);
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        web.setWebViewClient(new WebViewClient(){
            private boolean handle(Uri uri) {
                if (!"rrp-inv".equals(uri.getScheme())) return true;
                if ("section".equals(uri.getHost())) section(uri.getLastPathSegment());
                if ("action".equals(uri.getHost())) {
                    try { respond(Integer.parseInt(uri.getLastPathSegment())); }
                    catch (NumberFormatException ignored) { }
                }
                return true;
            }
            @Override public void onPageFinished(WebView view,String url) {pageReady=true;flushModels();}
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                return !req.isForMainFrame() || handle(req.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view,String url) { return handle(Uri.parse(url)); }
        });
        web.setOnKeyListener((v,key,event)->{
            if(key!=KeyEvent.KEYCODE_BACK && key!=KeyEvent.KEYCODE_ESCAPE) return false;
            if(event.getAction()==KeyEvent.ACTION_UP){if(pageReady)web.evaluateJavascript("window.bagBack()",null);else respond(-1);}
            return true;
        });
        setContentView(web);
        setWidth(ViewGroup.LayoutParams.MATCH_PARENT);
        setHeight(ViewGroup.LayoutParams.MATCH_PARENT);
        setFocusable(true);
        setInputMethodMode(PopupWindow.INPUT_METHOD_NOT_NEEDED);
        setBackgroundDrawable(new ColorDrawable(Color.TRANSPARENT));
        web.setSystemUiVisibility(game.getWindow().getDecorView().getSystemUiVisibility());
        setOnDismissListener(()->{ if(!finished){finished=true;reply(0,-1);} release(); });
        web.loadDataWithBaseURL("https://inventory.russiarp.invalid/",html,"text/html","UTF-8",null);
        showAtLocation(game.getWindow().getDecorView(),Gravity.CENTER,0,0);
        web.requestFocus();
        int hudId=game.getResources().getIdentifier("brHudRoot","id",game.getPackageName());
        hud=hudId==0?null:game.findViewById(hudId);
        if(hud!=null){originalAlpha=hud.getAlpha();hud.setAlpha(0f);}
        try {
            models=new InventoryModels(game,(key,image)->{if(!finished){pendingModels.put(key,image);flushModels();}});
            models.load(body);
        } catch (RuntimeException | LinkageError failed) {android.util.Log.w("RussiaInventory","Using world preview",failed);}
    }
    private void respond(int row) {
        if(finished || row < -1 || row>=rows) return;
        finished=true;
        dismiss();
        if(legacy && (row==2 || row==5)) {
            reply(0,-1);
            game.sendCommand((row==2?"/healme":"/drugs 1").getBytes(StandardCharsets.US_ASCII));
        } else reply(row<0?0:1,row);
    }
    private void reply(int button,int row) { game.sendDialogResponse(button,ID,row,new byte[0]); }
    private void release() {
        if(hud!=null){hud.setAlpha(originalAlpha);hud=null;}
        if(models!=null){models.close();models=null;}
        pendingModels.clear();
        if(web!=null){WebView old=web;web=null;new android.os.Handler(android.os.Looper.getMainLooper()).post(()->{ if(old.getParent() instanceof ViewGroup)((ViewGroup)old.getParent()).removeView(old);old.destroy(); });}
    }
}
