package blackrussia.online;
import java.io.*;
import java.util.Arrays;

/** Apply the quality profile once to stock installs. The in-game graphics panel owns subsequent edits. */
public final class MaximumGraphics {
    private static final byte[] MAX = {3,0,0,0, 3,0,0,0, 100,0,0,0, 0,0,1,1};
    private static final byte[] STOCK = {2,0,0,0, 3,0,0,0, 0,0,0,0, 1,1,0,1};
    public static void applyPath(String root) { if(root!=null) apply(new File(root)); }
    public static synchronized void apply(File root) {
        File config=new File(root,"wn_graphics.cfg"), done=new File(root,".russia-rp-quality-16");
        if(done.exists() || !config.isFile() || config.length()!=MAX.length) return;
        try {
            byte[] current=new byte[MAX.length];
            try(DataInputStream in=new DataInputStream(new FileInputStream(config))) { in.readFully(current); }
            byte[] old=STOCK.clone();old[8]=60;
            if(Arrays.equals(current,old)||Arrays.equals(current,STOCK)) {
                File next=File.createTempFile("quality-",".tmp",root);
                try {
                    try(FileOutputStream out=new FileOutputStream(next)) { out.write(MAX);out.getFD().sync(); }
                    if(!next.renameTo(config)) return;
                } finally { if(next.exists()) next.delete(); }
            }
            done.createNewFile();
        } catch(IOException ignored) { /* Retry a failed update on a later launch. */ }
    }
}
