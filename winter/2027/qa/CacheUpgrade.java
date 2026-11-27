package com.russiarp.qa;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Context;
import android.os.Bundle;
import java.io.IOException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.net.URL;
import java.net.URLConnection;
import java.net.URLStreamHandler;
import java.util.concurrent.atomic.AtomicInteger;

/** Run the normal cache installer against the previous game's files with archive downloads forbidden. */
public final class CacheUpgrade extends Instrumentation {
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    @Override public void onStart() {
        Bundle report = new Bundle();
        try {
            AtomicInteger requests = new AtomicInteger();
            URL.setURLStreamHandlerFactory(protocol -> {
                if (!protocol.equals("http") && !protocol.equals("https")) return null;
                return new URLStreamHandler() {
                    protected URLConnection openConnection(URL url) throws IOException {
                        requests.incrementAndGet(); throw new IOException("Cache requested network access: " + url.getHost());
                    }
                };
            });
            Context ctx = getTargetContext();
            ClassLoader loader = ctx.getClassLoader();
            Class<?> progress = loader.loadClass("blackrussia.online.WeikCache$Progress");
            Object listener = Proxy.newProxyInstance(loader,new Class<?>[]{progress},(p,m,a)->null);
            Method factory = loader.loadClass("blackrussia.online.DownloadService").getDeclaredMethod("createCache",Context.class,boolean.class,progress);
            factory.setAccessible(true);
            Object cache = factory.invoke(null,ctx,false,listener);
            Method install = cache.getClass().getDeclaredMethod("install");install.setAccessible(true);
            Method ready = cache.getClass().getDeclaredMethod("isInstalled");ready.setAccessible(true);
            install.invoke(cache);
            if (!Boolean.TRUE.equals(ready.invoke(cache)) || requests.get()!=0) throw new AssertionError("Offline cache validation failed");
            report.putString("cache","verified offline, zero archive requests");
            finish(Activity.RESULT_OK,report);
        } catch (Throwable error) {
            report.putString("error", android.util.Log.getStackTraceString(error));finish(Activity.RESULT_CANCELED,report);
        }
    }
}
