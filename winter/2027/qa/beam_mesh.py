"""Execute the APK's ARM headlamp geometry and inspect the RenderWare draw input."""
from io import BytesIO
import math
import struct
import sys
from zipfile import ZipFile

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_ARCH_ARM64, UC_MODE_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn import arm_const, arm64_const

STACK = 0x4020000
MATRIX = STACK + 0x1000
CAR = MATRIX + 0x100
FAN = (0, 1, 4, 1, 3, 4, 2, 3, 4, 0, 2, 4)


def float_bits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0]


def unit(vec):
    length = math.sqrt(sum(x*x for x in vec))
    return tuple(x / length for x in vec)


class Beam:
    def __init__(self, data, stock):
        elf = ELFFile(BytesIO(data))
        self.arm64 = elf.elfclass == 64
        self.stock = stock
        machine = UC_ARCH_ARM64 if self.arm64 else UC_ARCH_ARM
        self.uc = uc = Uc(machine, UC_MODE_ARM if self.arm64 else UC_MODE_THUMB)
        for seg in elf.iter_segments():
            if seg['p_type'] == 'PT_LOAD':
                addr = seg['p_vaddr']
                low, high = addr & ~4095, (addr + seg['p_memsz'] + 4095) & ~4095
                uc.mem_map(low, high-low)
                uc.mem_write(addr, seg.data())
        syms = elf.get_section_by_name('.dynsym')
        relocs = elf.get_section_by_name('.rela.dyn' if self.arm64 else '.rel.dyn')
        for rel in relocs.iter_relocations():
            if rel['r_info_type'] == (1025 if self.arm64 else 21):
                val = syms.get_symbol(rel['r_info_sym'])['st_value']
                uc.mem_write(rel['r_offset'], struct.pack('<Q' if self.arm64 else '<I', val))
        uc.mem_map(STACK-0x1000, 0x4000)
        if not self.arm64:
            uc.reg_write(arm_const.UC_ARM_REG_C1_C0_2, 0x00f00000)
            uc.reg_write(arm_const.UC_ARM_REG_FPEXC, 0x40000000)
        # Stop at the indexed renderer. Intercept only vector math and the
        # pipeline transform so the actual game code writes the vertices and indices.
        addresses = {
            (True, True): (0x6b48e8, 0x22b8a0, 0x219110, 0x2261c0),
            (True, False): (0x1b25a4, 0x37ddd0, 0x37ed50, 0x37ed60),
            (False, True): (0x5908b8, 0x19ba24, 0x189f1c, 0x1966f4),
            (False, False): (0x123b50, 0x280a50, 0x2819d0, 0x2819e0),
        }
        self.start, normalise, transform, self.draw = addresses[self.arm64, stock]
        self.arg = 'X0' if self.arm64 else 'R0'
        for addr, func in ((normalise, self.normalise), (transform, self.transform)):
            uc.hook_add(UC_HOOK_CODE, func, begin=addr, end=addr)

    def reg(self, name):
        if self.arm64:
            return getattr(arm64_const, 'UC_ARM64_REG_' + name)
        return getattr(arm_const, 'UC_ARM_REG_' + name)

    def set(self, name, value):
        self.uc.reg_write(self.reg(name), value)

    def get(self, name):
        return self.uc.reg_read(self.reg(name))

    def normalise(self, uc, addr, size, user):
        p = self.get(self.arg)
        normal = unit(struct.unpack('<3f', uc.mem_read(p, 12)))
        uc.mem_write(p, struct.pack('<3f', *normal))
        self.set('PC', self.get('LR'))

    def transform(self, uc, addr, size, user):
        assert self.get('X1' if self.arm64 else 'R1') == 5
        self.vertex_buffer = self.get(self.arg)
        self.set('PC', self.get('LR'))

    def run(self, yaw, pitch, camera):
        right = (math.cos(yaw), math.sin(yaw), 0)
        forward = (-math.sin(yaw)*math.cos(pitch), math.cos(yaw)*math.cos(pitch), math.sin(pitch))
        up = (math.sin(yaw)*math.sin(pitch), -math.cos(yaw)*math.sin(pitch), math.cos(pitch))
        lamp = (12., -3., .65)
        view = unit(camera)
        dot = sum(a*b for a,b in zip(forward,view))
        self.set('SP', STACK)
        self.uc.mem_write(STACK, bytes(0x300))
        for i, axis in enumerate((right, forward, up)):
            self.uc.mem_write(MATRIX+i*16, struct.pack('<3f', *axis))
        if self.arm64:
            self.set('X19', MATRIX)
            if self.stock:
                self.set('X20', CAR)
                self.set('W21', 5)
                self.set('W22', 12)
                self.uc.mem_write(CAR+0x32, struct.pack('<H', 411))
                for i,v in enumerate((*lamp, dot),8):
                    self.set('S'+str(i), float_bits(v))
            else:
                self.set('X29', STACK+0x170)
                self.uc.mem_write(STACK+0x1c, struct.pack('<3f', *lamp))
                for off in (0x2c,0x30,0x34):
                    self.uc.mem_write(STACK+off, b'\xff')
                self.set('S0', float_bits(dot))
                self.uc.emu_start(0x1b24e0, 0x1b2510)
        else:
            self.set('R4', MATRIX)
            if self.stock:
                self.set('R5', CAR)
                self.set('R9', 5)
                self.set('R10', 12)
                self.uc.mem_write(CAR+0x26, struct.pack('<H', 411))
                self.uc.mem_write(STACK+0x24, struct.pack('<3f', *lamp))
                for i,v in zip((16,20,18,22,26,24), (*forward,*view)):
                    self.set('S'+str(i), float_bits(v))
            else:
                self.set('R6', 0)
                self.set('R9', float_bits(dot))
                self.set('R11', STACK+0x78)
                self.uc.mem_write(STACK+0x30, struct.pack('<3f', *lamp))
                self.uc.mem_write(STACK+0x40, b'\xff'*3)
        self.uc.emu_start(self.start | int(not self.arm64), self.draw, count=1000)
        assert self.get('PC') == self.draw, hex(self.get('PC'))
        arg2 = 'X2' if self.arm64 else 'R2'
        assert self.get(self.arg) == 3 and self.get(arg2) == 12
        indices = self.uc.mem_read(self.get('X1' if self.arm64 else 'R1'), 24)
        assert struct.unpack('<12H', indices) == FAN, 'Incomplete headlamp fan'
        raw = self.uc.mem_read(self.vertex_buffer, 5*36)
        verts = [struct.unpack_from('<3f', raw, i*36) for i in range(5)]
        alphas = [raw[i*36+27] for i in range(5)]
        assert alphas[2:4] == [0,0] and 79 <= alphas[4] <= 112, alphas
        direction = unit(tuple(f-u*3/64 for f,u in zip(forward,up)))
        setback = .125 if self.stock else .1
        for vertex, dist, half in zip(verts, (0,0,12,12,2), (-.05,.05,-1.875,1.875,0)):
            expected = [l-setback*f + dist*d + half*r for l,f,d,r in zip(lamp,forward,direction,right)]
            assert math.dist(expected,vertex) < .0001, (expected,vertex)
        return verts, alphas


if __name__ == '__main__':
    with ZipFile(sys.argv[1]) as apk:
        for abi in ('arm64-v8a','armeabi-v7a'):
            for lib in ('libGame.so','libmultiplayer.so'):
                beam = Beam(apk.read(f'lib/{abi}/{lib}'), lib=='libGame.so')
                for yaw,pitch in ((0.,0.),(1.1,.095)):
                    reference = None
                    for camera in ((.1,7,1.3),(-4,6,2),(8,.1,1.5),(0,-5,4),(0,0,8)):
                        vertices, alpha = beam.run(yaw,pitch,camera)
                        if reference is not None:
                            assert vertices == reference, 'Camera changed beam geometry'
                        reference = vertices
                print(f'{abi}/{lib}: four complete triangles, five views, level and inclined chassis')
