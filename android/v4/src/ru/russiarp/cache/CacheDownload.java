package ru.russiarp.cache;

import java.io.*;
import java.net.*;
import java.security.*;
import java.util.Locale;

final class CacheDownload {
    static final long BYTES=1488834187L;
    static final String HASH="f701d99e857a2d9e5fe9127ab00c0161bc71f94c7f8281456af776a33007df9a";
    static final String URL_STRING="https://github.com/kennethlaffelay-art/RUSSIA-RP/releases/download/russia-f701d99e857a2d9e5fe9127ab00c0161-b9180d3ebef8/Rkkdev.zip";
    private static HttpURLConnection open(long have) throws IOException {
        URL url=new URL(URL_STRING);
        for (int i=0;i<8;i++) {
            if (!"https".equals(url.getProtocol())) throw new IOException("Требуется HTTPS");
            HttpURLConnection c=(HttpURLConnection)url.openConnection();
            c.setInstanceFollowRedirects(false); c.setConnectTimeout(20000); c.setReadTimeout(45000);
            c.setRequestProperty("Accept-Encoding","identity");
            if (have>0) c.setRequestProperty("Range","bytes="+have+"-");
            int code=c.getResponseCode();
            if (code==301||code==302||code==303||code==307||code==308) {
                String next=c.getHeaderField("Location"); c.disconnect();
                if (next==null) throw new IOException("GitHub не указал адрес файла");
                url=new URL(url,next);continue;
            }
            return c;
        }
        throw new IOException("Слишком много перенаправлений GitHub");
    }
    static void get(File part,CacheFiles.Status status) throws IOException {
        long have=part.length();
        if (have>BYTES) {if (!part.delete()) throw new IOException("Не удалось сбросить загрузку");have=0;}
        if (have!=BYTES) {
            status.set("Скачивание с GitHub",have,BYTES);
            HttpURLConnection c=open(have);
            try {
                int code=c.getResponseCode();
                if (code==206) {
                    String range=c.getHeaderField("Content-Range");
                    if (!("bytes "+have+"-"+(BYTES-1)+"/"+BYTES).equals(range))
                        throw new IOException("GitHub вернул другой диапазон байтов");
                } else if (code==200) have=0;
                else throw new IOException("GitHub вернул HTTP "+code);
                try (InputStream in=c.getInputStream(); OutputStream out=new FileOutputStream(part,have>0)) {
                    byte[] buf=new byte[262144];
                    for (int n;(n=in.read(buf))!=-1;) {
                        if (have+n>BYTES) throw new IOException("Размер архива изменился");
                        out.write(buf,0,n);have+=n;status.set("Скачивание с GitHub",have,BYTES);
                    }
                }
                if (have!=BYTES) throw new IOException("Загрузка прервана. Можно продолжить.");
            } finally {c.disconnect();}
        }
        MessageDigest digest;
        try {digest=MessageDigest.getInstance("SHA-256");} catch (NoSuchAlgorithmException e) {throw new IOException(e);}
        status.set("Проверка SHA-256",0,BYTES);
        try (InputStream in=new FileInputStream(part)) {
            byte[] buf=new byte[262144];long done=0;
            for (int n;(n=in.read(buf))!=-1;) {
                digest.update(buf,0,n);done+=n;status.set("Проверка SHA-256",done,BYTES);
            }
        }
        StringBuilder hex=new StringBuilder();
        for (byte b:digest.digest()) hex.append(String.format(Locale.ROOT,"%02x",b&255));
        if (!HASH.contentEquals(hex)) {
            if (!part.delete()) throw new IOException("Повреждённый архив не удалось удалить");
            throw new IOException("SHA-256 не совпала. Повторите загрузку.");
        }
    }
}
