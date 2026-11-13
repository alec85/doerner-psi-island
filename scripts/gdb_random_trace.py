"""gdb extension: log every call of Delphi's random routines in Psi.exe.

Loaded by scripts/trace_random.py with ``gdb -x``. Configuration comes from
environment variables:

    PSI_TRACE_OUT     output file (one line per draw, tab-separated)
    PSI_TRACE_EVENTS  path of the event protocol Protokoll(1).Dat; its size at
                      each draw is logged so draws can be mapped to cycles
    PSI_TRACE_LIMIT   stop after this many draws (0 = no limit)
    PSI_TRACE_NAMES   optional draw range "from-to": for draws of Junction in
                      this range, also log the names of the two neurons
                      (column "names", "In>Out")

Addresses were taken from the machine code of Psi.exe (ADR 0008):

    0x402B88  System Random(n)  - n in EAX on entry
    0x402BA0  System Random     - real result
    0x4A803C  RandSeed

Logged per draw: running number, kind (I = Random(n), R = Random), n,
RandSeed before the draw, return addresses of three stack levels (the direct
caller and, via the EBP chain, two further callers), size of the event
protocol in bytes.
"""

import os

import gdb

RANDSEED = 0x4A803C
ADDR_INT = 0x402B88
ADDR_REAL = 0x402BA0

out = open(os.environ["PSI_TRACE_OUT"], "w", buffering=1 << 16)
events_path = os.environ.get("PSI_TRACE_EVENTS", "")
limit = int(os.environ.get("PSI_TRACE_LIMIT", "0"))
watch = [int(a, 16) for a in os.environ.get("PSI_TRACE_WATCH", "").split(",") if a]
_names = os.environ.get("PSI_TRACE_NAMES", "")
names_range = tuple(int(x) for x in _names.split("-")) if _names else None
JUNCTION_DRAW = 0x47916F  # return address of Random in Junction
inferior = gdb.selected_inferior()
count = 0

out.write("nr\tkind\tn\trandseed\tret0\tret1\tret2\tevents_bytes"
          + "".join(f"\tw{a:X}" for a in watch) + ("\tnames" if names_range else "") + "\n")


def u32(addr: int):
    try:
        return int.from_bytes(bytes(inferior.read_memory(addr, 4)), "little")
    except gdb.MemoryError:
        return None


def neuron_name(ptr):
    """Name of a neuron record: AnsiString pointer at offset 8 (layout from the machine code)."""
    if not ptr:
        return "nil"
    s = u32(ptr + 8)
    if not s:
        return "?"
    n = u32(s - 4) or 0
    try:
        return bytes(inferior.read_memory(s, min(n, 40))).decode("cp1252")
    except gdb.MemoryError:
        return "?"


def hexa(value):
    return "" if value is None else f"{value:08X}"


class RandomBreak(gdb.Breakpoint):
    def __init__(self, address: int, kind: str):
        super().__init__(f"*{address:#x}", internal=True)
        self.kind = kind

    def stop(self):
        global count
        count += 1
        frame = gdb.selected_frame()
        eax = int(frame.read_register("eax")) & 0xFFFFFFFF
        esp = int(frame.read_register("esp")) & 0xFFFFFFFF
        ebp = int(frame.read_register("ebp")) & 0xFFFFFFFF
        seed = u32(RANDSEED)
        ret0 = u32(esp)
        ret1 = u32(ebp + 4)
        prev = u32(ebp)
        ret2 = u32(prev + 4) if prev else None
        try:
            size = os.stat(events_path).st_size if events_path else -1
        except OSError:
            size = -1
        n = eax if self.kind == "I" else ""
        extra = "".join(f"\t{u32(a)}" for a in watch)
        if names_range:
            label = ""
            if names_range[0] <= count <= names_range[1] and ret0 == JUNCTION_DRAW:
                # Junction's frame: InNeuron at [ebp-0x1c], OutNeuron at [ebp-0x8]
                label = f"{neuron_name(u32(ebp - 0x1C))}>{neuron_name(u32(ebp - 0x8))}"
            extra += "\t" + label
        out.write(f"{count}\t{self.kind}\t{n}\t{seed}\t{hexa(ret0)}\t{hexa(ret1)}\t{hexa(ret2)}\t{size}{extra}\n")
        if limit and count >= limit:
            out.flush()
            dump = os.environ.get("PSI_TRACE_DUMP")
            if dump:  # raw DATA+BSS segment, used once to locate global variables
                with open(dump, "wb") as fh:
                    fh.write(bytes(inferior.read_memory(0x4A6000, 0x6000)))
            return True  # halt; the driver detaches and stops the program
        return False


RandomBreak(ADDR_INT, "I")
RandomBreak(ADDR_REAL, "R")


def on_exit(event):
    out.flush()


gdb.events.exited.connect(on_exit)
