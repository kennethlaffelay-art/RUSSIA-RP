package blackrussia.online;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.security.spec.X509EncodedKeySpec;
import java.util.*;

final class CacheUpdates {
    private static final String CHANNEL = "https://raw.githubusercontent.com/kennethlaffelay-art/RUSSIA-RP/main/cache/winter16/channel-v1.rrc";
    private static final String RELEASES = "https://github.com/kennethlaffelay-art/RUSSIA-RP/releases/download/";
    private static final String PUBLIC_KEY = "MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA0bK24AJ8N7gqH2QnWxopgrCGeVfg5LMx8v1w+BRYNINeVXn/P7J0HJZd8tl0wPeEXTV2rhwx6gpgtwLzahMJW+ycXx/FH3jii7sfJkg57+bi0OEEj4nv+ENxbismnojIUtUmU04xnzqomCYobZYP+VZO/3c3tvHvF6gHEjR+Avs4/arKAQDN/LwpMWzjepcFGJXL7R9oCl3lrFiZkYv01jfo9olA5SM3edj5RsxpQlvymJ5fxa/9EQqQ8mADN/rZHs3nJ6VQSirUWeCct1eswNqp3dx/N5euzYtwMN3LoDBWRmVZHw9HMh9ulZrxZ0qS4jj7jj4oj/BGdo9cp/UgNoBLBSONauGfuEMkQ+rdMVw2mo6Kb7wju6hBh1kMMIk3PwpOStU81Gyf8POS7jwJnjNWIE8l04QbOgO8ZdQ6/m0uzjzTOotzD/QOIQiKTY0kWiBjch+koornq++36/Qk5eFwmPFT3oPBqTLVnBbfgDI4IU9/jVt8/ElEG3odHpeBAgMBAAE=";
    private static final int LIMIT = 2 * 1024 * 1024;
    private static volatile Map<String, Member> active = Collections.emptyMap();

    static final class Pack {
        final URL url;
        final long size;
        final String hash;
        Pack(String tag, long size, String hash) throws IOException {
            this.size = size;
            this.hash = hash;
            this.url = new URL(RELEASES + tag + "/cache-" + hash + ".zip");
        }
    }
    static final class Member extends WeikCache.Entry {
        final Pack pack;
        Member(Pack pack, String[] row) {
            super(row[1], Long.parseLong(row[2]), Long.parseLong(row[3]), Long.parseLong(row[4]), Integer.parseInt(row[5]));
            this.pack = pack;
        }
    }
    final int generation;
    final Map<String, Member> members;
    private CacheUpdates(int generation, Map<String, Member> members) {
        this.generation = generation;
        this.members = Collections.unmodifiableMap(members);
    }
    private static void require(boolean condition) throws IOException {
        if (!condition) throw new IOException("Некорректный каталог обновлений");
    }
    static byte[] read(InputStream input) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int n;
        while ((n = input.read(buffer)) != -1) {
            require(bytes.size() <= LIMIT - n);
            bytes.write(buffer, 0, n);
        }
        return bytes.toByteArray();
    }
    static CacheUpdates parse(byte[] envelope) throws IOException {
        try {
            int at = 0;
            while (at < envelope.length && at < 1024 && envelope[at] != '\n') at++;
            require(at > 0 && at < envelope.length && at < 1024 && envelope.length <= LIMIT);
            Signature verifier = Signature.getInstance("SHA256withRSA");
            verifier.initVerify(KeyFactory.getInstance("RSA").generatePublic(new X509EncodedKeySpec(Base64.getDecoder().decode(PUBLIC_KEY))));
            verifier.update(envelope, at + 1, envelope.length - at - 1);
            require(verifier.verify(Base64.getDecoder().decode(Arrays.copyOf(envelope, at))));
            String[] lines = new String(envelope, at + 1, envelope.length - at - 1, StandardCharsets.UTF_8).split("\n");
            String[] header = lines[0].split("\t", -1);
            require(header.length == 6 && "RRP1".equals(header[0]) && "16".equals(header[1]));
            int version = Integer.parseInt(header[2]);
            long length = Long.parseLong(header[4]);
            require(version >= 17 && length > 0 && header[3].matches("[A-Za-z0-9][A-Za-z0-9._-]{0,95}") && header[5].matches("[0-9a-f]{64}"));
            Pack pack = new Pack(header[3], length, header[5]);
            Map<String, Member> files = new LinkedHashMap<>();
            for (int i = 1; i < lines.length; i++) {
                String[] row = lines[i].split("\t", -1);
                require(row.length == 6 && row[1].matches("[0-9a-f]{64}"));
                String path = row[0];
                require(path.length() <= 320 && !path.contains("\\") && !path.contains(":") && path.indexOf('\0') < 0);
                for (String component : path.split("/", -1)) {
                    require(!component.isEmpty() && !component.equals(".") && !component.equals(".."));
                }
                require(!WeikCache.LOCAL_DEFAULTS.contains(path) && !WeikCache.GENERATED.contains(path));
                Member member = new Member(pack, row);
                require(member.size >= 0 && member.offset > 0 && member.packed >= 0 && member.offset <= length - member.packed);
                require((member.method == 0 && member.packed == member.size) || (member.method == 8 && member.packed > 0));
                require(files.put(path, member) == null);
            }
            return new CacheUpdates(version, files);
        } catch (GeneralSecurityException | RuntimeException e) {
            throw new IOException("Ошибка подписи или формата каталога", e);
        }
    }
    private static CacheUpdates saved(File file) {
        if (file.isFile() && file.length() <= LIMIT) {
            try (InputStream input = new FileInputStream(file)) { return parse(read(input)); }
            catch (IOException ignored) { }
        }
        return new CacheUpdates(16, Collections.<String, Member>emptyMap());
    }
    static synchronized WeikRelease select(WeikRelease base, File directory, boolean online) {
        try { return selectAt(base, directory, online, new URL(CHANNEL)); }
        catch (MalformedURLException impossible) { throw new AssertionError(impossible); }
    }
    static WeikRelease selectAt(WeikRelease base, File directory, boolean online, URL channel) {
        File file = new File(directory, "rrp-winter16-channel-v1");
        CacheUpdates known = saved(file);
        if (online) {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection)channel.openConnection();
                connection.setConnectTimeout(3000);
                connection.setReadTimeout(3500);
                connection.setUseCaches(false);
                connection.setRequestProperty("Cache-Control", "no-cache");
                if (connection.getResponseCode() == 200) {
                    try (InputStream input = connection.getInputStream()) {
                        byte[] raw = read(input);
                        CacheUpdates next = parse(raw);
                        if (next.generation > known.generation) {
                            Path temp = Files.createTempFile(directory.toPath(), "rrp-channel-", ".tmp");
                            try {
                                Files.write(temp, raw);
                                Files.move(temp, file.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
                                known = next;
                            } finally { Files.deleteIfExists(temp); }
                        }
                    }
                }
            } catch (IOException ignored) {
                // A previously verified index remains usable during an outage.
            } finally { if (connection != null) connection.disconnect(); }
        }
        base.files.putAll(known.members);
        active = known.members;
        return base;
    }
    static boolean has(String path) { return active.containsKey(path); }
    static boolean updatedSample(File file, String path) {
        Member member = active.get(path);
        return member != null && file.isFile() && file.length() == member.size;
    }
    static WeikCache worker(WeikCache cache, WeikCache.Entry entry) {
        if (!(entry instanceof Member)) return cache;
        Pack pack = ((Member)entry).pack;
        return new WeikCache(cache.root, cache.archive, cache.receipt, pack.url, pack.size, pack.hash,
                             cache.manifest, cache.defaults, cache.progress);
    }
}
