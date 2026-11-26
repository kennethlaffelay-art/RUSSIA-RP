package blackrussia.online;
import java.io.*;
import java.net.URL;
import java.util.*;
final class WeikCache {
    interface Defaults { InputStream open(String path) throws IOException; }
    interface Progress { void check() throws InterruptedIOException; void update(int phase,String file,long done,long total); }
    static class Entry {
        final String hash; final long size,offset,packed; final int method;
        Entry(String h,long s,long o,long p,int m){hash=h;size=s;offset=o;packed=p;method=m;}
    }
    static final Set<String> LOCAL_DEFAULTS = new HashSet<>(Arrays.asList("SAMP/settings.ini","wn_graphics.cfg"));
    static final Set<String> GENERATED = new HashSet<>(Arrays.asList("SAMP/svlog.txt"));
    final File root,archive,receipt; final URL source; final long archiveSize;
    final Map<String,Entry> manifest; final Defaults defaults; final Progress progress;
    WeikCache(File r, File a, File rc, URL u, long s, String sh, Map<String,Entry> m, Defaults d, Progress p) {
        root=r; archive=a; receipt=rc; source=u; archiveSize=s; manifest=m; defaults=d; progress=p;
    }
}
