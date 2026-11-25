package com.russiarp.qa;
import android.app.Instrumentation;
import android.content.Context;
import android.content.res.Configuration;
import android.graphics.*;
import android.graphics.drawable.Drawable;
import android.os.Bundle;
import android.util.AttributeSet;
import android.view.*;
import android.widget.*;
import java.io.*;

public class Screens extends Instrumentation {
    Context context;
    LayoutInflater inflater;
    int width,height;
    public void onCreate(Bundle args){super.onCreate(args);start();}
    int id(String name){return context.getResources().getIdentifier(name,"id","com.russiarp.game");}
    int res(String name,String kind){return context.getResources().getIdentifier(name,kind,"com.russiarp.game");}
    void check(boolean ok,String what){if(!ok)throw new AssertionError(what);}
    View inflate(String layout){return inflater.inflate(res(layout,"layout"),null);}
    void size(View v){v.measure(View.MeasureSpec.makeMeasureSpec(width,1073741824),View.MeasureSpec.makeMeasureSpec(height,1073741824));v.layout(0,0,width,height);}
    void capture(View v,String name) throws Exception{
        size(v);Bitmap bm=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(bm);c.drawColor(0xff343940);v.draw(c);
        Bitmap small=Bitmap.createScaledBitmap(bm,640,Math.round(640f*height/width),true);
        try(FileOutputStream os=new FileOutputStream(new File(getTargetContext().getFilesDir(),"qa175-"+width+"-"+name+".jpg"))){small.compress(Bitmap.CompressFormat.JPEG,90,os);}bm.recycle();small.recycle();
    }
    void configure(int w,int h){
        width=w;height=h;Context c=getTargetContext();
        Configuration cfg=new Configuration(c.getResources().getConfiguration());cfg.orientation=w>h?Configuration.ORIENTATION_LANDSCAPE:Configuration.ORIENTATION_PORTRAIT;
        cfg.densityDpi=240;cfg.screenWidthDp=w*160/240;cfg.screenHeightDp=h*160/240;cfg.smallestScreenWidthDp=Math.min(cfg.screenWidthDp,cfg.screenHeightDp);
        Context configured=c.createConfigurationContext(cfg);
        context=new ContextThemeWrapper(configured,c.getResources().getIdentifier("Theme.AppCompat.NoActionBar","style",c.getPackageName()));
        inflater=LayoutInflater.from(context).cloneInContext(context);
        inflater.setFactory2(new LayoutInflater.Factory2(){
            public View onCreateView(String n,Context c,AttributeSet a){return onCreateView(null,n,c,a);}
            public View onCreateView(View p,String n,Context c,AttributeSet a){
                if(n.equals("ImageView")||n.equals("Button")||n.equals("TextView")||n.equals("EditText")){
                    try{return (View)c.getClassLoader().loadClass("androidx.appcompat.widget.AppCompat"+n).getConstructor(Context.class,AttributeSet.class).newInstance(c,a);}
                    catch(Exception e){throw new RuntimeException(e);}
                }return null;
            }
        });
    }
    void runScreens(int w,int h) throws Exception{
        configure(w,h);
        ViewGroup loading=(ViewGroup)inflate("wn_loadingscreen");capture(loading,"loading");
        ImageView image=(ImageView)loading.getChildAt(0);float[] matrix=new float[9];image.getImageMatrix().getValues(matrix);
        check(image.getWidth()==w&&image.getHeight()==h,"fullscreen bounds");check(image.getScaleType()==ImageView.ScaleType.CENTER_CROP&&Math.abs(matrix[0]-matrix[4])<0.001f,"loading aspect ratio");
        ViewGroup chooser=(ViewGroup)inflate("br_serverselect");
        chooser.findViewById(id("choose_server_root_loading")).setVisibility(View.GONE);View area=chooser.findViewById(id("choose_server_root_choose"));area.setVisibility(View.VISIBLE);area.setAlpha(1);
        context.getClassLoader().loadClass("com.wn.blackrussia.databinding.BrServerselectBinding").getMethod("bind",View.class).invoke(null,chooser);
        bindCard(chooser);capture(chooser,"my-server");
        View mainCard=chooser.findViewById(id("server_main_frame"));
        int cardWidth=mainCard.getWidth(),cardHeight=mainCard.getHeight();
        View active=chooser.findViewById(id("servers_btn_my_server")),all=chooser.findViewById(id("all_servers_button"));
        check(active.getWidth()==all.getWidth(),"tab widths");
        active.setBackgroundResource(res("button_br_red_unfilled_ss","drawable"));
        all.setBackgroundResource(res("button_red_rectangle","drawable"));
        chooser.findViewById(id("main_servers_choose")).setVisibility(View.GONE);chooser.findViewById(id("list_servers_choose")).setVisibility(View.VISIBLE);
        LinearLayout list=chooser.findViewById(id("scroll_layout_servers"));
        View card=inflater.inflate(res("br_serverselect_server","layout"),list,false);list.addView(card);bindCard(card);
        capture(chooser,"all-servers");
        check(card.getWidth()==cardWidth&&card.getHeight()==cardHeight&&cardWidth>0,"same card geometry");
        spawn();
        ViewGroup auth=(ViewGroup)inflate("registration_view");FrameLayout inside=auth.findViewById(id("reg_container"));inside.addView(inflate("reg_login"));
        ImageView actor=auth.findViewById(id("reg_person"));ViewGroup.LayoutParams lp=actor.getLayoutParams();lp.width=lp.height=(int)(.7f*h);actor.setLayoutParams(lp);
        ((TextView)auth.findViewById(id("reg_header"))).setText("Авторизация");auth.findViewById(id("reg_info")).setVisibility(View.GONE);
        capture(auth,"login");Drawable drawable=actor.getDrawable();check(drawable!=null,"character artwork");
        RectF bounds=new RectF(drawable.getBounds());actor.getImageMatrix().mapRect(bounds);
        check(Math.abs(actor.getTop()+bounds.bottom-h)<2,"character is flush with bottom");
        ViewGroup hud=(ViewGroup)inflate("br_hud");ImageView logo=hud.findViewById(id("brHudLogo")),bonus=hud.findViewById(id("brHudDoubleLogo"));
        bonus.setVisibility(View.VISIBLE);capture(hud,"hud");
        check(logo.getDrawable()!=null&&bonus.getDrawable()!=null,"HUD artwork");check(Math.abs((logo.getTop()+logo.getBottom())-(bonus.getTop()+bonus.getBottom()))<=2,"HUD center alignment");
        check(logo.getLeft()>0&&bonus.getLeft()>=logo.getRight(),"HUD safe spacing");
        android.util.Log.i("RussiaUiTest",w+"x"+h+" loading scale "+matrix[0]+"/"+matrix[4]+", actor bottom "+(actor.getTop()+bounds.bottom)+", HUD x="+logo.getLeft()+" badge x="+bonus.getLeft());
    }
    void spawn() throws Exception {
        ViewGroup root=(ViewGroup)inflate("spawn_location_layout");
        View recycler=root.findViewById(id("recycler_view_spawn_location"));
        ViewGroup.LayoutParams params=recycler.getLayoutParams();
        root.removeView(recycler);
        HorizontalScrollView scroll=new HorizontalScrollView(context);scroll.setId(recycler.getId());scroll.setHorizontalScrollBarEnabled(false);root.addView(scroll,1,params);
        LinearLayout line=new LinearLayout(context);scroll.addView(line);
        String[] labels={"Вокзал","Дом","Организация"};
        View selected=null;
        for(int i=0;i<labels.length;i++){
            View card=inflater.inflate(res("spawn_location_item","layout"),line,false);line.addView(card);
            ((ImageView)card.findViewById(id("image_view_place"))).setImageResource(res("spawn_location_res_"+i,"drawable"));
            ((TextView)card.findViewById(id("text_view_place_name"))).setText(labels[i]);
            card.findViewById(id("view_selection")).setVisibility(i==0?View.VISIBLE:View.GONE);
            card.findViewById(id("view_selection_unavailable")).setVisibility(i==2?View.VISIBLE:View.GONE);
            card.findViewById(id("iv_lock")).setVisibility(i==2?View.VISIBLE:View.GONE);
            if(i==0)selected=card.findViewById(id("view_selection"));
        }
        capture(root,"spawn");
        check(selected.getHeight()>200&&selected.getTop()==0,"full spawn highlight");
    }
    void monitor() throws Exception {
        FrameLayout root=new FrameLayout(context);
        ImageView background=new ImageView(context);background.setScaleType(ImageView.ScaleType.CENTER_CROP);
        background.setImageResource(res("back","drawable"));root.addView(background,new FrameLayout.LayoutParams(-1,-1));
        View item=inflater.inflate(res("item_server","layout"),root,false);root.addView(item);
        ((TextView)item.findViewById(id("firstName"))).setText("МОСКВА");
        ((TextView)item.findViewById(id("secondName"))).setText("");
        ((TextView)item.findViewById(id("online"))).setText("12");
        ((TextView)item.findViewById(id("onlineTotal"))).setText("/100");
        capture(root,"monitor");
        View mark=item.findViewById(id("bearPaw"));
        check(mark.getWidth()==mark.getHeight()&&mark.getWidth()==context.getResources().getDimensionPixelSize(res("_62sdp","dimen")),"monitor emblem bounds");
    }
    void bindCard(View pane) throws Exception {
        View progress=pane.findViewById(id("br_server_progress"));progress.getClass().getMethod("setProgress",float.class).invoke(progress,12f);
        ((TextView)pane.findViewById(id("br_server_name"))).setText("МОСКВА");
        ((TextView)pane.findViewById(id("br_server_online"))).setText("12/100");
        pane.findViewById(id("server_list_back_color")).getBackground().mutate().setColorFilter(0xffbc5d33,PorterDuff.Mode.SRC_ATOP);
        ((ImageView)pane.findViewById(id("br_server_image"))).setColorFilter(0xffbc5d33,PorterDuff.Mode.SRC_ATOP);
    }
    void launcherIcon() throws Exception{
        Context app=getTargetContext();
        CharSequence label=app.getPackageManager().getApplicationLabel(app.getApplicationInfo());
        check("РОССИЯ РП".contentEquals(label),"application title");
        Drawable icon=app.getPackageManager().getApplicationIcon(app.getPackageName());
        check(icon instanceof android.graphics.drawable.AdaptiveIconDrawable,"adaptive launcher icon");
        Bitmap bm=Bitmap.createBitmap(320,280,Bitmap.Config.ARGB_8888);
        Canvas canvas=new Canvas(bm);canvas.drawColor(0xff282627);
        icon.setBounds(70,15,250,195);icon.draw(canvas);
        Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);paint.setColor(-1);paint.setTextAlign(Paint.Align.CENTER);paint.setTextSize(25);
        canvas.drawText(label.toString(),160,236,paint);
        try(FileOutputStream os=new FileOutputStream(new File(app.getFilesDir(),"qa175-app-icon.jpg"))){bm.compress(Bitmap.CompressFormat.JPEG,94,os);}
        bm.recycle();
    }
    public void onStart(){
        final Bundle result=new Bundle();final Throwable[] error={null};
        runOnMainSync(new Runnable(){public void run(){try{runScreens(1280,720);runScreens(1600,720);configure(720,1280);monitor();launcherIcon();}
        catch(Throwable e){error[0]=e;android.util.Log.e("RussiaUiTest","layout failure",e);}}});
        result.putString("stream",error[0]==null?"UI175 PASSED":android.util.Log.getStackTraceString(error[0]));finish(error[0]==null?-1:0,result);
    }
}
