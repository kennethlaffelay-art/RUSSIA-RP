package com.russiarp.updates;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.*;
import java.util.regex.Pattern;

final class Releases {
    static final String REPO = "kennethlaffelay-art/RUSSIA-RP";
    static final String API = "https://api.github.com/repos/" + REPO + "/releases";
    static final String TAG = "russia-rp-v";
    static final long MAX_APK = 512L * 1024 * 1024;
    static final Pattern VERSION = Pattern.compile("(?:0|[1-9][0-9]{0,5})(?:\\.(?:0|[1-9][0-9]{0,5})){2}");

    static final class Build {
        final String version, sha, url;
        final long size;
        Build(String version, String sha, long size) {
            this.version = version;
            this.sha = sha;
            this.size = size;
            this.url = "https://github.com/" + REPO + "/releases/download/" + TAG + version + "/RUSSIA-RP-" + version + ".apk";
        }
    }

    static int compare(String left, String right) {
        if (!VERSION.matcher(left).matches() || !VERSION.matcher(right).matches()) throw new IllegalArgumentException("Invalid version");
        String[] a = left.split("\\."), b = right.split("\\.");
        for (int i = 0; i < 3; i++) {
            int n = Integer.compare(Integer.parseInt(a[i]), Integer.parseInt(b[i]));
            if (n != 0) return n;
        }
        return 0;
    }

    static Build fromRelease(JSONObject release) {
        String tag = release.optString("tag_name");
        if (release.optBoolean("draft") || release.optBoolean("prerelease") || !tag.startsWith(TAG)) return null;
        String version = tag.substring(TAG.length());
        if (!VERSION.matcher(version).matches()) return null;
        JSONArray assets = release.optJSONArray("assets");
        if (assets == null) return null;
        for (int i = 0; i < assets.length(); i++) {
            JSONObject a = assets.optJSONObject(i);
            if (a == null || !("RUSSIA-RP-" + version + ".apk").equals(a.optString("name"))) continue;
            String digest = a.optString("digest");
            long size = a.optLong("size", -1);
            if (!digest.matches("sha256:[0-9a-f]{64}") || size < 1 || size > MAX_APK) continue;
            Build build = new Build(version, digest.substring(7), size);
            if (build.url.equals(a.optString("browser_download_url")) && "uploaded".equals(a.optString("state"))) return build;
        }
        return null;
    }

    static HttpURLConnection connect(URL url, long offset) throws IOException {
        for (int step = 0; step < 5; step++) {
            String host = url.getHost();
            if (!"https".equals(url.getProtocol()) || (url.getPort() != -1 && url.getPort() != 443) || url.getUserInfo() != null ||
                !(host.equals("github.com") || host.equals("api.github.com") || host.equals("release-assets.githubusercontent.com") ||
                  host.equals("objects.githubusercontent.com") || host.equals("github-releases.githubusercontent.com"))) throw new IOException("Unexpected download host");
            HttpURLConnection c = (HttpURLConnection)url.openConnection();
            c.setInstanceFollowRedirects(false);
            c.setConnectTimeout(8000);
            c.setReadTimeout(18000);
            c.setRequestProperty("User-Agent","RUSSIA-RP-Android-Updater");
            c.setRequestProperty("Accept-Encoding","identity");
            if (offset > 0) c.setRequestProperty("Range","bytes="+offset+"-");
            int code;
            try {code = c.getResponseCode();} catch(IOException e) {c.disconnect(); throw e;}
            if (code != 301 && code != 302 && code != 303 && code != 307 && code != 308) return c;
            String loc=c.getHeaderField("Location");
            c.disconnect();
            if (loc == null) throw new IOException("Redirect without URL");
            url = new URL(url,loc);
        }
        throw new IOException("Too many redirects");
    }

    static Build fromChannel(JSONObject channel) {
        String version=channel.optString("versionName"), sha=channel.optString("sha256");
        long size=channel.optLong("size",-1);
        if(channel.optInt("format")!=1 || !"com.russiarp.hudx".equals(channel.optString("package")) ||
            !VERSION.matcher(version).matches() || !sha.matches("[0-9a-f]{64}") || size<1 || size>MAX_APK) return null;
        return new Build(version,sha,size);
    }

    static String readJson(HttpURLConnection c,int limit) throws IOException {
        try {
            if(c.getResponseCode()!=200) throw new IOException("Release HTTP "+c.getResponseCode());
            try(InputStream in=c.getInputStream(); ByteArrayOutputStream out=new ByteArrayOutputStream()) {
                byte[] buf=new byte[8192]; int n;
                while((n=in.read(buf))!=-1) {
                    if(out.size()+n>limit) throw new IOException("Oversized metadata");
                    out.write(buf,0,n);
                }
                return new String(out.toByteArray(),StandardCharsets.UTF_8);
            }
        } finally {c.disconnect();}
    }

    static Build newest(String installed) throws IOException, JSONException {
        try {
            String metadata="https://github.com/"+REPO+"/releases/latest/download/client-update.json";
            Build stable=fromChannel(new JSONObject(readJson(connect(new URL(metadata),0),16384)));
            if(stable!=null) return compare(stable.version,installed)>0 ? stable : null;
        } catch(IOException | JSONException missing) { /* Older release publishers omit the small CDN index. */ }

        Build best = null;
        // Separate cache releases may be newer than the latest Android release.
        for (int page = 1; page <= 8; page++) {
            HttpURLConnection c = connect(new URL(API + "?per_page=25&page=" + page),0);
            JSONArray rows=new JSONArray(readJson(c,2*1024*1024));
            boolean reachedInstalled=false;
            for(int i=0;i<rows.length();i++) {
                JSONObject row=rows.optJSONObject(i);
                Build b=row==null ? null : fromRelease(row);
                if(b==null) continue;
                if(compare(b.version,installed)<=0) reachedInstalled=true;
                else if(best==null || compare(b.version,best.version)>0) best=b;
            }
            if(reachedInstalled || rows.length()<25) break;
        }
        return best;
    }

    static boolean valid(File file,Build build) throws IOException {
        if (!file.isFile() || file.length()!=build.size) return false;
        MessageDigest d;
        try {d=MessageDigest.getInstance("SHA-256");} catch(NoSuchAlgorithmException e) {throw new AssertionError(e);}
        try(InputStream in = new FileInputStream(file)) {
            byte[] buf=new byte[65536]; int n;
            while((n=in.read(buf))!=-1) d.update(buf,0,n);
        }
        final char[] hex="0123456789abcdef".toCharArray(); StringBuilder sum=new StringBuilder(64);
        for(byte b:d.digest()) sum.append(hex[(b&255)>>>4]).append(hex[b&15]);
        return sum.toString().equals(build.sha);
    }

    interface Connection { HttpURLConnection open(long offset) throws IOException; }
    static File fetch(File dir, Build build, Connection network) throws IOException {
        if (!dir.isDirectory() && !dir.mkdirs()) throw new IOException("Cannot create download directory");
        File apk=new File(dir,build.sha+".apk"), part=new File(dir,build.sha+".part");
        if(valid(apk,build)) return apk;
        long offset=part.isFile()?part.length():0;
        if(offset>build.size || (offset==build.size && !valid(part,build))) {
            Files.delete(part.toPath()); offset=0;
        }
        if(offset<build.size) {
            HttpURLConnection c=network.open(offset);
            try {
                int status=c.getResponseCode();
                if(status==200) offset=0;
                else if(status!=206 || !("bytes "+offset+"-"+(build.size-1)+"/"+build.size).equals(c.getHeaderField("Content-Range"))) {
                    if(status==206 || status==416) Files.deleteIfExists(part.toPath());
                    throw new IOException("Invalid download range or HTTP "+status);
                }
                if(dir.getUsableSpace()<build.size-offset+1024*1024) throw new IOException("Недостаточно места для обновления");
                try(InputStream in=c.getInputStream();FileOutputStream out=new FileOutputStream(part,offset>0)) {
                    byte[] buf=new byte[65536]; int n; long total=offset;
                    while((n=in.read(buf))!=-1) {
                        if(total+n>build.size) throw new IOException("Oversized APK");
                        out.write(buf,0,n); total+=n;
                    }
                    out.getFD().sync();
                    if(total!=build.size) throw new EOFException("Incomplete APK");
                }
            } finally {c.disconnect();}
        }
        if(!valid(part,build)) {
            Files.deleteIfExists(part.toPath());
            throw new IOException("Неверная контрольная сумма APK");
        }
        Files.move(part.toPath(),apk.toPath(),StandardCopyOption.REPLACE_EXISTING);
        return apk;
    }
}
