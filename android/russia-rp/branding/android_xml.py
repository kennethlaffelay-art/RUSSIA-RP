"""Small editor for compiled Android layout XML, preserving namespaces and resource IDs."""

import struct

U = lambda b, p: struct.unpack_from("<I", b, p)[0]
H = lambda b, p: struct.unpack_from("<H", b, p)[0]
p32 = lambda n: struct.pack("<I", n)
NIL = 0xFFFFFFFF
ANDROID = "http://schemas.android.com/apk/res/android"


def chunks(b):
    pos = H(b, 2)
    while pos < len(b):
        size = U(b, pos + 4)
        assert size >= 8 and pos + size <= len(b)
        yield b[pos : pos + size]
        pos += size


class Pool:
    def __init__(self, b):
        self.utf8 = bool(U(b, 16) & 256)
        assert H(b, 2) == 28 and U(b, 12) == 0
        self.values = []
        for i in range(U(b, 8)):
            p = U(b, 20) + U(b, 28 + 4 * i)
            if self.utf8:
                p += 2 if b[p] & 128 else 1
                n = b[p]
                p += 1
                if n & 128:
                    n = ((n & 127) << 8) + b[p]
                    p += 1
                self.values.append(b[p : p + n].decode("utf-8", "surrogatepass"))
            else:
                n = H(b, p)
                p += 2
                if n & 0x8000:
                    n = ((n & 32767) << 16) + H(b, p)
                    p += 2
                self.values.append(b[p : p + n * 2].decode("utf-16le", "surrogatepass"))

    def add(self, s):
        if s not in self.values:
            self.values.append(s)
        return self.values.index(s)

    def encode(self):
        data = bytearray()
        offsets = bytearray()

        def length8(n):
            return bytes([n]) if n < 128 else bytes([128 | (n >> 8), n & 255])

        for s in self.values:
            offsets.extend(p32(len(data)))
            s16 = s.encode("utf-16le", "surrogatepass")
            n = len(s16) // 2
            if self.utf8:
                raw = s.encode("utf-8", "surrogatepass")
                data.extend(length8(n) + length8(len(raw)) + raw + b"\0")
            else:
                data.extend(
                    (
                        struct.pack("<H", n)
                        if n < 32768
                        else struct.pack("<HH", 32768 | (n >> 16), n & 65535)
                    )
                    + s16
                    + b"\0\0"
                )
        data.extend(b"\0" * (-len(data) % 4))
        start = 28 + len(offsets)
        return (
            struct.pack(
                "<HH6I",
                1,
                28,
                start + len(data),
                len(self.values),
                0,
                256 if self.utf8 else 0,
                start,
                0,
            )
            + offsets
            + data
        )


class Element:
    def __init__(self, doc, chunk):
        self.doc = doc
        self.head = bytearray(chunk[:36])
        self.attrs = [bytearray(chunk[p : p + 20]) for p in range(36, len(chunk), 20)]
        assert (
            H(chunk, 24) == 20
            and H(chunk, 26) == 20
            and len(self.attrs) == H(chunk, 28)
        )

    @property
    def tag(self):
        return self.doc.pool.values[U(self.head, 20)]

    def name(self, a):
        return self.doc.pool.values[U(a, 4)]

    def get(self, k):
        return next((U(a, 16) for a in self.attrs if self.name(a) == k), None)

    def drop(self, k):
        self.attrs = [a for a in self.attrs if self.name(a) != k]

    def set(self, k, t, data, rid=None):
        a = next((a for a in self.attrs if self.name(a) == k), None)
        if a is None:
            assert rid is not None, k
            idx = self.doc.pool.add(k)
            ids = self.doc.ids
            ids.extend([0] * max(0, idx + 1 - len(ids)))
            assert ids[idx] in (0, rid)
            ids[idx] = rid
            a = bytearray(
                struct.pack(
                    "<IIIHBBI", self.doc.pool.add(ANDROID), idx, NIL, 8, 0, t, data
                )
            )
            self.attrs.append(a)
        struct.pack_into("<I", a, 8, data if t == 3 else NIL)
        a[15] = t
        struct.pack_into("<I", a, 16, data)

    def encode(self):
        keys = lambda a: self.doc.ids[U(a, 4)] if U(a, 4) < len(self.doc.ids) else 0
        attrs = sorted(self.attrs, key=keys)
        for i, nam in enumerate(("id", "class", "style")):
            struct.pack_into(
                "<H",
                self.head,
                30 + 2 * i,
                next((j + 1 for j, a in enumerate(attrs) if self.name(a) == nam), 0),
            )
        struct.pack_into("<I", self.head, 4, 36 + 20 * len(attrs))
        struct.pack_into("<H", self.head, 28, len(attrs))
        return self.head + b"".join(attrs)


class Doc:
    def __init__(self, b):
        self.parts = []
        for c in chunks(b):
            t = H(c, 0)
            if t == 1:
                self.pool = Pool(c)
                self.parts.append("pool")
            elif t == 0x180:
                self.ids = list(
                    struct.unpack_from("<" + "I" * ((len(c) - 8) // 4), c, 8)
                )
                self.parts.append("ids")
            elif t == 0x102:
                self.parts.append(Element(self, c))
            else:
                self.parts.append(c)

    def elements(self):
        return [v for v in self.parts if isinstance(v, Element)]

    def image(self, root, src):
        pos = self.parts.index(root) + 1
        node = Element(
            self,
            struct.pack(
                "<HH8I",
                0x102,
                16,
                36,
                1,
                NIL,
                NIL,
                self.pool.add("ImageView"),
                0x140014,
                0,
                0,
            ),
        )
        node.set("layout_width", 16, NIL, 0x10100F4)
        node.set("layout_height", 16, NIL, 0x10100F5)
        node.set("src", 1, src, 0x1010119)
        node.set("scaleType", 16, 6, 0x101011D)
        node.set("importantForAccessibility", 16, 2, 0x10103AA)
        end = struct.pack(
            "<HH5I", 0x103, 16, 24, 1, NIL, NIL, self.pool.add("ImageView")
        )
        self.parts[pos:pos] = [node, end]
        return node

    def encode(self):
        out = bytearray()
        for c in self.parts:
            if c == "pool":
                raw = self.pool.encode()
            elif c == "ids":
                raw = struct.pack("<HHI", 0x180, 8, 8 + 4 * len(self.ids)) + b"".join(
                    map(p32, self.ids)
                )
            elif isinstance(c, Element):
                raw = c.encode()
            else:
                raw = c
            out += raw
        return struct.pack("<HHI", 3, 8, len(out) + 8) + out
