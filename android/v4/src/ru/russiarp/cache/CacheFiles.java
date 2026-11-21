package ru.russiarp.cache;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

final class CacheFiles {
    interface Status { void set(String label, long done, long total); }
    static final class Entry {
        final String source, path;
        final long size, crc;
        final boolean personal;
        Entry(String line) throws IOException {
            String[] f = line.split("\\t", -1);
            if (f.length != 5) throw new IOException("Ошибка списка файлов кэша");
            source=f[0]; path=f[1]; size=Long.parseLong(f[2]); crc=Long.parseLong(f[3]); personal=f[4].equals("1");
        }
    }
    private final File root;
    private final List<Entry> entries = new ArrayList<>();
    CacheFiles(File root, InputStream index) throws IOException {
        this.root = root.getCanonicalFile();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(index, "UTF-8"))) {
            for (String s; (s=r.readLine())!=null;) entries.add(new Entry(s));
        }
        if (!root.getAbsoluteFile().equals(this.root)) throw new IOException("Недопустимая папка кэша");
        if (entries.isEmpty()) throw new IOException("Список файлов кэша пуст");
    }
    private File target(Entry e) throws IOException {
        File f=new File(root,e.path);
        String path=f.getCanonicalPath();
        if (!path.equals(f.getAbsolutePath()) || !path.startsWith(root.getPath()+File.separator))
            throw new IOException("Недопустимый путь в кэше");
        return f;
    }
    private boolean check(Entry e, File f, boolean deep, byte[] buf) throws IOException {
        if (!f.isFile()) return false;
        if (e.personal && f.length()>0) return true;
        if (f.length()!=e.size) return false;
        if (!deep) return true;
        CRC32 crc=new CRC32();
        try (InputStream in=new FileInputStream(f)) {
            for (int n;(n=in.read(buf))!=-1;) crc.update(buf,0,n);
        }
        return crc.getValue()==e.crc;
    }
    boolean complete(boolean deep, Status status) throws IOException {
        byte[] buf=new byte[262144];
        int count=0;
        for (Entry e:entries) {
            if (!check(e,target(e),deep,buf)) return false;
            status.set("Проверка файлов",++count,entries.size());
        }
        return true;
    }
    private File partial(File f) {
        return new File(f.getParentFile(), ".russia-rp-v4-"+f.getName()+".partial");
    }
    void clearInterruptedWrites() throws IOException {
        for (Entry e:entries) Files.deleteIfExists(partial(target(e)).toPath());
    }
    long missingBytes() throws IOException {
        long total=0, largestReplacement=0;
        for (Entry e:entries) {
            File f=target(e);
            if (!f.isFile()) total+=e.size;
            else if (!e.personal) {
                total+=Math.max(0,e.size-f.length());
                largestReplacement=Math.max(largestReplacement, Math.min(e.size,f.length()));
            }
        }
        return total+largestReplacement;
    }
    void install(File archive, Status status) throws IOException {
        byte[] buf=new byte[262144];
        int count=0;
        try (ZipFile zip=new ZipFile(archive)) {
            for (Entry e:entries) {
                File f=target(e);
                status.set("Распаковка • "+e.path,count,entries.size());
                ZipEntry item=zip.getEntry(e.source);
                if (item==null || item.getCrc()!=e.crc || item.getSize()!=e.size)
                    throw new IOException("Не совпадает индекс кэша: "+e.path);
                if (!check(e,f,true,buf)) {
                    Files.createDirectories(f.getParentFile().toPath());
                    File tmp=partial(f);
                    Files.createFile(tmp.toPath());
                    try {
                        long size=0; CRC32 crc=new CRC32();
                        try (InputStream in=zip.getInputStream(item); FileOutputStream out=new FileOutputStream(tmp)) {
                            for (int n;(n=in.read(buf))!=-1;) {
                                out.write(buf,0,n);crc.update(buf,0,n);size+=n;
                            }
                        }
                        if (size!=e.size || crc.getValue()!=e.crc) throw new IOException("Повреждён файл "+e.path);
                        move(tmp,f);
                    } finally { tmp.delete(); }
                }
                status.set("Распаковка кэша",++count,entries.size());
            }
        }
    }
    static void move(File from,File to) throws IOException {
        try {Files.move(from.toPath(),to.toPath(),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);}
        catch (AtomicMoveNotSupportedException err) {
            Files.move(from.toPath(),to.toPath(),StandardCopyOption.REPLACE_EXISTING);
        }
    }
}
