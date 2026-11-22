package ru.russiarp.report;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** Extract the faulting thread and ELF-relative frames. Raw Android dumps may contain memory. */
public final class NativeStack {
    private static final class Fields {
        final byte[] bytes;
        final int end;
        int pos, field, start, length, wire;
        long number;
        Fields(byte[] bytes, int start, int length) {
            this.bytes = bytes;
            pos = start;
            end = start + length;
        }
        long varint() throws IOException {
            long value = 0;
            for (int shift = 0; shift < 64 && pos < end; shift += 7) {
                int octet = bytes[pos++] & 255;
                if (shift == 63 && (octet & 254) != 0) break;
                value |= (long)(octet & 127) << shift;
                if (octet < 128) return value;
            }
            throw new IOException("Invalid varint");
        }
        boolean next() throws IOException {
            if (pos == end) return false;
            long key = varint();
            field = (int)(key >>> 3);
            wire = (int)(key & 7);
            if (field <= 0) throw new IOException("Invalid tag");
            if (wire == 0) { number = varint(); return true; }
            long size;
            if (wire == 1) size = 8;
            else if (wire == 2) size = varint();
            else if (wire == 5) size = 4;
            else throw new IOException("Invalid field");
            if (size < 0 || size > end - pos) throw new IOException("Invalid length");
            start = pos;
            length = (int)size;
            pos += length;
            return true;
        }
        Fields sub() { return new Fields(bytes, start, length); }
        String string() {
            if (length > 4096) return "";
            return new String(bytes, start, length, StandardCharsets.UTF_8).replaceAll("[\\p{Cntrl}]", "");
        }
    }
    private static String frame(Fields f) throws IOException {
        String lib = "", fn = "", build = "";
        long pc = 0;
        while (f.next()) {
            if (f.field == 1 && f.wire == 0) pc = f.number;
            if (f.wire != 2) continue;
            if (f.field == 4) fn = f.string();
            if (f.field == 6) {
                String path = f.string();
                lib = path.substring(Math.max(path.lastIndexOf('/'), path.lastIndexOf('!')) + 1);
            }
            if (f.field == 8) build = f.string();
        }
        return "pc " + Long.toHexString(pc) + " " + lib + " " + fn + " " + build + "\n";
    }
    public static String summarize(byte[] bytes) throws IOException {
        Fields root = new Fields(bytes, 0, bytes.length);
        long tid = -1;
        StringBuilder out = new StringBuilder();
        while (root.next()) {
            if (root.wire == 0) {
                if (root.field == 6) tid = root.number;
                if (root.field == 20) out.append("uptime_s=").append(root.number).append('\n');
                if (root.field == 22) out.append("page_bytes=").append(root.number).append('\n');
            }
            if (root.field == 10 && root.wire == 2) {
                Fields signal = root.sub();
                while (signal.next())
                    if ((signal.field == 2 || signal.field == 4) && signal.wire == 2)
                        out.append(signal.string()).append('\n');
            }
        }
        root.pos = 0;
        while (root.next()) {
            if (root.field != 16 || root.wire != 2) continue;
            Fields entry = root.sub(), thread = null;
            long key = -2;
            while (entry.next()) {
                if (entry.field == 1 && entry.wire == 0) key = entry.number;
                if (entry.field == 2 && entry.wire == 2) thread = entry.sub();
            }
            if (key != tid || thread == null) continue;
            int count = 0;
            while (thread.next()) {
                if (thread.field == 2 && thread.wire == 2) out.append("thread=").append(thread.string()).append('\n');
                if (thread.field == 4 && thread.wire == 2 && count++ < 64) out.append(frame(thread.sub()));
            }
            break;
        }
        if (out.length() == 0) throw new IOException("No crash fields");
        return out.toString();
    }
}
