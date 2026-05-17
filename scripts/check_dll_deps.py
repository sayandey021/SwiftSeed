"""Check DLL dependencies of a .pyd or .dll file using PE header parsing."""
import struct
import sys
import os

def get_pe_imports(filepath):
    """Parse PE file to find DLL imports (minimal parser)."""
    with open(filepath, 'rb') as f:
        # Read DOS header
        dos_magic = f.read(2)
        if dos_magic != b'MZ':
            return []
        
        f.seek(0x3C)
        pe_offset = struct.unpack('<I', f.read(4))[0]
        
        f.seek(pe_offset)
        pe_magic = f.read(4)
        if pe_magic != b'PE\x00\x00':
            return []
        
        # COFF header
        machine = struct.unpack('<H', f.read(2))[0]
        num_sections = struct.unpack('<H', f.read(2))[0]
        f.read(12)  # skip timestamp, symbols
        opt_header_size = struct.unpack('<H', f.read(2))[0]
        f.read(2)  # characteristics
        
        # Optional header
        opt_start = f.tell()
        opt_magic = struct.unpack('<H', f.read(2))[0]
        
        if opt_magic == 0x20b:  # PE32+
            f.seek(opt_start + 24)  # to ImageBase
            f.read(8)  # ImageBase (8 bytes for PE32+)
            f.read(8)  # SectionAlignment, FileAlignment
            f.read(16)  # versions
            f.read(8)   # Win32VersionValue, SizeOfImage 
            f.read(4)   # SizeOfHeaders
            f.read(4)   # CheckSum
            f.read(4)   # Subsystem, DllCharacteristics
            f.read(40)  # stack/heap sizes (8 each) + loaderflags + numberofRvaAndSizes
            # Now at Data Directory
            f.seek(opt_start + 120)  # Import table is the 2nd entry (index 1)
        elif opt_magic == 0x10b:  # PE32
            f.seek(opt_start + 104)
        else:
            return []
        
        import_rva = struct.unpack('<I', f.read(4))[0]
        import_size = struct.unpack('<I', f.read(4))[0]
        
        if import_rva == 0:
            return []
        
        # Read section headers to map RVA -> file offset
        f.seek(opt_start + opt_header_size)
        sections = []
        for _ in range(num_sections):
            name = f.read(8).rstrip(b'\x00')
            virtual_size = struct.unpack('<I', f.read(4))[0]
            virtual_addr = struct.unpack('<I', f.read(4))[0]
            raw_size = struct.unpack('<I', f.read(4))[0]
            raw_ptr = struct.unpack('<I', f.read(4))[0]
            f.read(16)  # skip rest
            sections.append((name, virtual_addr, virtual_size, raw_ptr, raw_size))
        
        def rva_to_offset(rva):
            for name, va, vs, rp, rs in sections:
                if va <= rva < va + vs:
                    return rp + (rva - va)
            return None
        
        # Read import directory
        offset = rva_to_offset(import_rva)
        if offset is None:
            return []
        
        imports = []
        f.seek(offset)
        while True:
            ilt_rva = struct.unpack('<I', f.read(4))[0]
            f.read(4)  # timestamp
            f.read(4)  # forwarder chain
            name_rva = struct.unpack('<I', f.read(4))[0]
            f.read(4)  # IAT rva
            
            if name_rva == 0:
                break
            
            name_offset = rva_to_offset(name_rva)
            if name_offset:
                pos = f.tell()
                f.seek(name_offset)
                name = b''
                while True:
                    c = f.read(1)
                    if c == b'\x00' or not c:
                        break
                    name += c
                imports.append(name.decode('ascii', errors='replace'))
                f.seek(pos)
        
        return imports


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if not target:
        # Default: check libtorrent
        target = os.path.join(os.path.dirname(__file__), '..', 'dist', 'SwiftSeed', '_internal', 'libtorrent', '__init__.cp313-win_amd64.pyd')
    
    target = os.path.abspath(target)
    print(f"Checking: {target}")
    print(f"Exists: {os.path.exists(target)}")
    
    if os.path.exists(target):
        deps = get_pe_imports(target)
        print(f"\nDLL Dependencies ({len(deps)}):")
        for d in sorted(deps):
            print(f"  - {d}")
