package blackrussia.online;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

public final class SharedCache {
    private SharedCache() {}

    // The first winter preview stored a separate world next to the original Weik directory.
    public static synchronized void adopt(File root) {
        if (!root.getName().equals("Weik") || root.exists()) return;
        File preview = new File(root.getParentFile(), "RWin");
        if (!new File(preview, "texdb").isDirectory()) return;
        try {
            Files.move(preview.toPath(), root.toPath());
        } catch (IOException | SecurityException ignored) {
            // Android can grant shared-storage access after Settings first loads. The installer retries.
        }
    }

    // Called for manifest resources that already failed validation in Weik. Private settings
    // and generated files are excluded by the caller's original installer loop.
    public static boolean reuse(File root, File target, String name, long size, String expected) throws IOException {
        if (!root.getName().equals("Weik")) return false;
        File preview = new File(root.getParentFile(), "RWin");
        File source = new File(preview, name);
        if (!source.isFile() || source.length() != size) return false;
        if (!source.getCanonicalFile().toPath().startsWith(preview.getCanonicalFile().toPath())) return false;
        Path destination = target.toPath();
        Path parent = destination.getParent();
        Files.createDirectories(parent);
        Path temp = Files.createTempFile(parent, ".rrp-import-", ".tmp");
        try {
            MessageDigest hash;
            try { hash = MessageDigest.getInstance("SHA-256"); }
            catch (NoSuchAlgorithmException ex) { throw new AssertionError(ex); }
            try (InputStream in = Files.newInputStream(source.toPath()); OutputStream out = Files.newOutputStream(temp)) {
                byte[] buffer = new byte[262144];
                int count;
                while ((count = in.read(buffer)) != -1) {
                    hash.update(buffer, 0, count);
                    out.write(buffer, 0, count);
                }
            }
            byte[] digest = hash.digest();
            if (expected.length() != digest.length * 2) return false;
            for (int i = 0; i < digest.length; i++) {
                int value = digest[i] & 255;
                if (Character.digit(expected.charAt(2*i),16) != value / 16 ||
                    Character.digit(expected.charAt(2*i+1),16) != value % 16) return false;
            }
            try { Files.move(temp, destination, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
            catch (AtomicMoveNotSupportedException ex) { Files.move(temp, destination, StandardCopyOption.REPLACE_EXISTING); }
            return true;
        } finally { Files.deleteIfExists(temp); }
    }
}
