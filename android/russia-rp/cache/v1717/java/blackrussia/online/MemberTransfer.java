package blackrussia.online;

import java.io.*;
import java.net.*;

final class MemberTransfer {
    static void fetch(WeikCache cache, String name, WeikCache.Entry entry, File part, long before, long total) throws IOException {
        URL url = cache.source;
        long existing = part.length();
        long start = entry.offset + existing;
        long end = entry.offset + entry.packed - 1;
        if (existing == entry.packed) return;
        String interval = start + "-" + end;
        for (int redirects = 0; redirects < 8; redirects++) {
            if (!"https".equals(url.getProtocol())) throw new IOException("Нужен HTTPS для загрузки кеша");
            HttpURLConnection http = (HttpURLConnection)url.openConnection();
            try {
                http.setInstanceFollowRedirects(false);
                http.setConnectTimeout(15000);
                http.setReadTimeout(30000);
                http.setUseCaches(false);
                http.setRequestProperty("Accept-Encoding", "identity");
                http.setRequestProperty("Range", "bytes=" + interval);
                int code = http.getResponseCode();
                if (code == 301 || code == 302 || code == 303 || code == 307 || code == 308) {
                    String target = http.getHeaderField("Location");
                    if (target == null) throw new IOException("Отсутствует адрес файла");
                    url = new URL(url, target);
                    continue;
                }
                String expected = "bytes " + interval + "/" + cache.archiveSize;
                if (code != 206 || !expected.equals(http.getHeaderField("Content-Range"))) {
                    throw new IOException("Сервер не выдал запрошенную часть файла " + name + " (HTTP " + code + ")");
                }
                byte[] buffer = new byte[65536];
                try (InputStream input = http.getInputStream(); OutputStream output = new FileOutputStream(part, true)) {
                    long received = existing;
                    while (received < entry.packed) {
                        cache.progress.check();
                        int count = input.read(buffer, 0, (int)Math.min(buffer.length, entry.packed - received));
                        if (count < 0) throw new EOFException("Загрузка прервана: " + name);
                        output.write(buffer, 0, count);
                        received += count;
                        cache.progress.update(2, name, before + received, total);
                    }
                }
                return;
            } finally { http.disconnect(); }
        }
        throw new IOException("Слишком много перенаправлений при загрузке " + name);
    }
}
