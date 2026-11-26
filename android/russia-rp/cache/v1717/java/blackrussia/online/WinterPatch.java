package blackrussia.online;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

final class WinterPatch {
    private static final int BUFFER = 256 * 1024;
    private static MessageDigest sha() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException e) { throw new AssertionError(e); }
    }
    private static String hex(byte[] bytes) {
        String digits="0123456789abcdef";
        StringBuilder text=new StringBuilder(64);
        for(byte b:bytes) text.append(digits.charAt((b&255)>>>4)).append(digits.charAt(b&15));
        return text.toString();
    }
    private static void unchanged(RandomAccessFile file, long length, MessageDigest hash,
                                  byte[] buffer, WeikCache.Progress progress) throws IOException {
        while (length>0) {
            progress.check();
            int count=(int)Math.min(length,buffer.length);
            file.readFully(buffer,0,count);
            hash.update(buffer,0,count);
            length-=count;
        }
    }
    private static boolean process(File target,String path,WeikCache.Entry entry,WeikCache.Defaults assets,
                                   WeikCache.Progress progress,boolean commit) throws IOException {
        MessageDigest hash=sha();
        byte[] buffer=new byte[BUFFER];
        try(DataInputStream delta=new DataInputStream(new BufferedInputStream(assets.open(path+".patch"),BUFFER));
            RandomAccessFile cache=new RandomAccessFile(target,commit?"rw":"r")) {
            if(delta.readInt()!=0x57533134 || delta.readLong()!=entry.size) throw new IOException("Неверная версия зимнего пакета: "+path);
            int ranges=delta.readInt();
            if(ranges<1||ranges>65536) throw new IOException("Неверная таблица зимнего пакета");
            for(int i=0;i<ranges;i++) {
                long pos=delta.readLong(),gap=pos-cache.getFilePointer();
                int length=delta.readInt();
                if(gap<0||length<1||pos>entry.size-length) throw new IOException("Повреждена таблица зимних ресурсов");
                if(commit) cache.seek(pos);
                else unchanged(cache,gap,hash,buffer,progress);
                for(int left=length;left>0;) {
                    progress.check();
                    int count=Math.min(left,BUFFER);
                    delta.readFully(buffer,0,count);
                    if(commit) cache.write(buffer,0,count);
                    else hash.update(buffer,0,count);
                    left-=count;
                }
                if(!commit) cache.seek(pos+length);
            }
            if(delta.read()!=-1) throw new IOException("Повреждён зимний пакет");
            if(!commit) {
                unchanged(cache,entry.size-cache.getFilePointer(),hash,buffer,progress);
                return hex(hash.digest()).equals(entry.hash);
            }
            cache.getFD().sync();
            cache.seek(0);
            unchanged(cache,entry.size,hash,buffer,progress);
            if(!hex(hash.digest()).equals(entry.hash)) throw new IOException("Проверка зимнего кеша не пройдена: "+path);
            return true;
        }
    }
    static boolean apply(File target,String path,WeikCache.Entry entry,WeikCache.Defaults assets,
                         WeikCache.Progress progress) throws IOException {
        if(!target.isFile() || target.length()!=entry.size) return false;
        if(!process(target,path,entry,assets,progress,false)) return false;
        return process(target,path,entry,assets,progress,true);
    }
}
