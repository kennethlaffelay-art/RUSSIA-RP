package com.russiarp.updates;

import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import org.json.*;

public class ReleaseTest {
    static void expect(boolean value) {if(!value) throw new AssertionError();}
    static void expectFailure(Action a) throws Exception {try{a.run();}catch(IOException ok){return;}throw new AssertionError("expected failure");}
    interface Action {void run() throws Exception;}
    static final class Reply extends HttpURLConnection {
        final byte[] data; final String range; final int status;
        Reply(int status,byte[] data,String range) throws Exception {super(new URL("https://github.com/"));this.status=status;this.data=data;this.range=range;}
        public String getHeaderField(String name){return range;}
        public int getResponseCode(){return status;}
        public InputStream getInputStream(){return new ByteArrayInputStream(data);}
        public void connect(){} public void disconnect(){} public boolean usingProxy(){return false;}
    }
    static Reply reply(int status,byte[] bytes,String range) throws IOException {
        try{return new Reply(status,bytes,range);}catch(Exception e){throw new IOException(e);}
    }
    public static void main(String[] argv) throws Exception {
        JSONArray page=new JSONArray(new String(Files.readAllBytes(Paths.get(argv[0])),"UTF-8"));
        JSONObject official=null;for(int i=0;i<page.length();i++) if(page.getJSONObject(i).optString("tag_name").equals("russia-rp-v1.7.17")) official=page.getJSONObject(i);
        expect(official!=null);
        expect(Releases.fromRelease(official)==null); // Published 1.7.17 is explicitly a prerelease.
        JSONObject stable=new JSONObject(official.toString()).put("prerelease",false);
        Releases.Build old=Releases.fromRelease(stable);
        expect(old!=null && Releases.valid(new File(argv[1]),old));
        JSONObject metadata=new JSONObject().put("format",1).put("package","com.russiarp.hudx").put("versionName",old.version).put("size",old.size).put("sha256",old.sha);
        expect(Releases.fromChannel(metadata).url.equals(old.url));
        metadata.put("package","other.game");expect(Releases.fromChannel(metadata)==null);
        JSONObject edited=new JSONObject(stable.toString());edited.put("prerelease",true);expect(Releases.fromRelease(edited)==null);
        edited=new JSONObject(stable.toString());edited.put("draft",true);expect(Releases.fromRelease(edited)==null);
        edited=new JSONObject(stable.toString());edited.put("tag_name","winter-cache-99");expect(Releases.fromRelease(edited)==null);
        edited=new JSONObject(stable.toString());
        for(int i=0;i<edited.getJSONArray("assets").length();i++) edited.getJSONArray("assets").getJSONObject(i).put("browser_download_url","https://example.org/fake.apk");
        expect(Releases.fromRelease(edited)==null);
        expect(Releases.compare("1.7.18","1.7.9")>0 && Releases.compare("1.7.18","1.7.18")==0 && Releases.compare("1.7.17","2.0.0")<0);
        File dir=Paths.get(argv[2]).toFile();dir.mkdirs();
        byte[] data="fragment-0123456789".getBytes("UTF-8");
        StringBuilder hash=new StringBuilder();for(byte v:MessageDigest.getInstance("SHA-256").digest(data))hash.append(String.format("%02x",v));
        Releases.Build b=new Releases.Build("1.7.19",hash.toString(),data.length);
        File apk=new File(dir,b.sha+".apk"),part=new File(dir,b.sha+".part");apk.delete();part.delete();
        expectFailure(()->Releases.fetch(dir,b,offset->reply(200,Arrays.copyOf(data,5),null)));
        expect(part.length()==5 && !apk.exists());
        Releases.fetch(dir,b,offset->{expect(offset==5);return reply(206,Arrays.copyOfRange(data,5,data.length),"bytes 5-"+(data.length-1)+"/"+data.length);});
        expect(Releases.valid(apk,b) && !part.exists());
        Releases.fetch(dir,b,n->{throw new AssertionError("verified APK should not be downloaded again");});
        apk.delete();Files.write(part.toPath(),Arrays.copyOf(data,4));
        expectFailure(()->Releases.fetch(dir,b,n->reply(206,data,"bytes 9-18/19")));expect(!part.exists());
        Files.write(part.toPath(),Arrays.copyOf(data,6));
        expect(Releases.valid(Releases.fetch(dir,b,n->{expect(n==6);return reply(200,data,null);}),b));
        apk.delete();byte[] corrupt=data.clone();corrupt[8]++;
        expectFailure(()->Releases.fetch(dir,b,n->reply(200,corrupt,null)));expect(!apk.exists()&&!part.exists());
        expectFailure(()->Releases.connect(new URL("http://github.com/example"),0));
        expectFailure(()->Releases.connect(new URL("https://some-other-host.example/file"),0));
        if(argv.length>3 && argv[3].equals("live")) {
            Releases.Build live=Releases.newest("1.7.3");
            expect(live!=null && Releases.compare(live.version,"1.7.3")>0);
            System.out.println("Live stable selection: "+live.version);
            File actual=Releases.fetch(dir,old,n->Releases.connect(new URL(old.url),n));
            expect(Releases.valid(actual,old));System.out.println("Live existing APK download verified: "+old.version+" ("+actual.length()+" bytes)");
        }
        System.out.println("Release selection, official digest, cached reuse, resume, ignored range, corruption and HTTPS checks passed.");
    }
}
