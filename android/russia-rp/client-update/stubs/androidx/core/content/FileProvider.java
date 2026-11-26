package androidx.core.content;
import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import java.io.File;
// Compile-time signature of the AndroidX class already packaged in the game.
public class FileProvider extends ContentProvider {
    public static Uri getUriForFile(Context c,String authority,File file) { throw new UnsupportedOperationException(); }
    public boolean onCreate(){return true;}
    public Cursor query(Uri u,String[] p,String s,String[] args,String o){return null;}
    public String getType(Uri u){return null;}
    public Uri insert(Uri u,ContentValues v){return null;}
    public int delete(Uri u,String s,String[] args){return 0;}
    public int update(Uri u,ContentValues v,String s,String[] args){return 0;}
}
