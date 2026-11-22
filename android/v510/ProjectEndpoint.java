package ru.russiarp.install;

import android.app.Activity;
import blackrussia.online.Preferences;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class ProjectEndpoint {
    private static final Pattern SECTION = Pattern.compile("^\\s*\\[([^]\\r\\n]+)\\]\\s*(?:[;#].*)?$");
    private static final Pattern VALUE = Pattern.compile("^(\\s*(host|port)\\s*=\\s*)[^;#\\r\\n]*?(\\s*(?:[;#].*)?)$", Pattern.CASE_INSENSITIVE);

    static void configure(Activity activity, File config) throws IOException {
        String host, port;
        try (InputStream in = activity.getAssets().open("russia-project.endpoint");
             BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.US_ASCII))) {
            host = reader.readLine();
            port = reader.readLine();
        }
        if (host == null || port == null || !host.matches("(?:[0-9]{1,3}\\.){3}[0-9]{1,3}") || !port.matches("[0-9]{1,5}"))
            throw new IOException("Некорректный адрес игрового сервера в сборке");
        for (String octet : host.split("\\."))
            if (Integer.parseInt(octet) > 255) throw new IOException("Некорректный адрес игрового сервера");
        int number = Integer.parseInt(port);
        if (number < 1 || number > 65535) throw new IOException("Некорректный порт игрового сервера");

        Path path = config.toPath();
        if (!Files.isRegularFile(path) || Files.size(path) > 1024 * 1024)
            throw new IOException("Не удалось прочитать настройки игры");
        String before = new String(Files.readAllBytes(path), StandardCharsets.ISO_8859_1);
        String after = update(before, host, Integer.toString(number));
        if (!after.equals(before)) {
            Path temp = Files.createTempFile(path.getParent(), ".russia-server-", ".tmp");
            try {
                Files.write(temp, after.getBytes(StandardCharsets.ISO_8859_1));
                try { Files.move(temp, path, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
                catch (AtomicMoveNotSupportedException ex) { Files.move(temp, path, StandardCopyOption.REPLACE_EXISTING); }
            } finally { Files.deleteIfExists(temp); }
        }
        Preferences.putString(activity, "HOST_WN", host);
        Preferences.putString(activity, "PORT_WN", Integer.toString(number));
    }

    static String update(String before, String host, String port) {
        String newline = before.contains("\r\n") ? "\r\n" : "\n";
        StringBuilder out = new StringBuilder();
        boolean client = false, found = false, hasHost = false, hasPort = false;
        int position = 0;
        while (position < before.length()) {
            int next = before.indexOf('\n', position);
            int end = next < 0 ? before.length() : next + 1;
            String row = before.substring(position, end);
            String body = row.replaceFirst("[\\r\\n]+$", "");
            String ending = row.substring(body.length());
            Matcher section = SECTION.matcher(body);
            if (section.matches()) {
                if (client) appendMissing(out, hasHost, hasPort, host, port, newline);
                client = section.group(1).trim().equalsIgnoreCase("client");
                found |= client;
                hasHost = hasPort = false;
            } else if (client) {
                Matcher setting = VALUE.matcher(body);
                if (setting.matches()) {
                    boolean isHost = setting.group(2).equalsIgnoreCase("host");
                    body = setting.group(1) + (isHost ? host : port) + setting.group(3);
                    hasHost |= isHost;
                    hasPort |= !isHost;
                }
            }
            out.append(body).append(ending);
            position = end;
        }
        if (!found) {
            endLine(out, newline);
            out.append("[client]").append(newline);
        }
        if (!found || client) appendMissing(out, hasHost, hasPort, host, port, newline);
        return out.toString();
    }

    private static void endLine(StringBuilder out, String newline) {
        if (out.length() > 0 && out.charAt(out.length()-1) != '\n') out.append(newline);
    }

    private static void appendMissing(StringBuilder out, boolean hasHost, boolean hasPort, String host, String port, String newline) {
        if (hasHost && hasPort) return;
        endLine(out, newline);
        if (!hasHost) out.append("host = ").append(host).append(newline);
        if (!hasPort) out.append("port = ").append(port).append(newline);
    }
}
