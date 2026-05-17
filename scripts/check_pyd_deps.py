"""Check DLL dependencies of libtorrent .pyd using PE header parsing.
Run this on both the dev machine and the target machine to compare."""
import struct
import os
import sys

def get_pe_imports(filepath):
    """Parse PE file to find DLL imports."""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    if data[:2] != b'MZ':
        return []
    
    pe_offset = struct.unpack_from('<I', data, 0x3C)[0]
    if data[pe_offset:pe_offset+4] != b'PE\x00\x00':
        return []
    
    # COFF header
    coff = pe_offset + 4
    num_sections = struct.unpack_from('<H', data, coff + 2)[0]
    opt_header_size = struct.unpack_from('<H', data, coff + 16)[0]
    
    # Optional header
    opt = coff + 20
    opt_magic = struct.unpack_from('<H', data, opt)[0]
    
    if opt_magic == 0x20b:  # PE32+
        import_dir_offset = opt + 120  # 2nd data directory entry
    elif opt_magic == 0x10b:  # PE32
        import_dir_offset = opt + 104
    else:
        return []
    
    import_rva = struct.unpack_from('<I', data, import_dir_offset)[0]
    if import_rva == 0:
        return []
    
    # Read section headers
    sections_start = opt + opt_header_size
    sections = []
    for i in range(num_sections):
        sec_off = sections_start + i * 40
        va = struct.unpack_from('<I', data, sec_off + 12)[0]
        vs = struct.unpack_from('<I', data, sec_off + 8)[0]
        rp = struct.unpack_from('<I', data, sec_off + 20)[0]
        sections.append((va, vs, rp))
    
    def rva_to_offset(rva):
        for va, vs, rp in sections:
            if va <= rva < va + vs:
                return rp + (rva - va)
        return None
    
    # Read import directory
    offset = rva_to_offset(import_rva)
    if offset is None:
        return []
    
    imports = []
    pos = offset
    while True:
        name_rva = struct.unpack_from('<I', data, pos + 12)[0]
        if name_rva == 0:
            break
        name_offset = rva_to_offset(name_rva)
        if name_offset:
            end = data.index(b'\x00', name_offset)
            name = data[name_offset:end].decode('ascii', errors='replace')
            imports.append(name)
        pos += 20
    
    return imports


def main():
    # Find the libtorrent .pyd
    locations = []
    
    # Check dist
    dist_pyd = os.path.join(os.path.dirname(__file__), '..', 'dist', 'SwiftSeed', 
                            '_internal', 'libtorrent', '__init__.cp313-win_amd64.pyd')
    if os.path.exists(dist_pyd):
        locations.append(('dist', os.path.abspath(dist_pyd)))
    
    # Check site-packages
    try:
        import libtorrent
        sp_pyd = libtorrent.__file__
        locations.append(('site-packages', sp_pyd))
    except ImportError:
        pass
    
    # Check MSIX
    msix_pyd = os.path.join(os.path.dirname(__file__), '..', 'msix_package',
                            '_internal', 'libtorrent', '__init__.cp313-win_amd64.pyd')
    if os.path.exists(msix_pyd):
        locations.append(('msix', os.path.abspath(msix_pyd)))
    
    if not locations:
        print("ERROR: Could not find libtorrent .pyd file!")
        return
    
    for label, path in locations:
        print(f"\n{'='*60}")
        print(f"  {label}: {path}")
        print(f"  Size: {os.path.getsize(path):,} bytes")
        print(f"{'='*60}")
        
        imports = get_pe_imports(path)
        print(f"\nDLL Dependencies ({len(imports)}):")
        
        # Check which ones exist in the same directory
        pyd_dir = os.path.dirname(path)
        parent_dir = os.path.dirname(pyd_dir)
        
        for dll_name in sorted(imports):
            in_same = os.path.exists(os.path.join(pyd_dir, dll_name))
            in_parent = os.path.exists(os.path.join(parent_dir, dll_name))
            in_sys = os.path.exists(os.path.join('C:/Windows/System32', dll_name))
            
            status = []
            if in_same:
                status.append("co-located")
            if in_parent:
                status.append("in _internal")
            if in_sys:
                status.append("in System32")
            
            marker = "✓" if (in_same or in_parent or in_sys) else "✗ MISSING"
            print(f"  {marker} {dll_name} [{', '.join(status) if status else 'NOT FOUND ANYWHERE'}]")

    # Also check transitive deps of OpenSSL DLLs
    print(f"\n{'='*60}")
    print("  Checking OpenSSL DLL transitive dependencies")
    print(f"{'='*60}")
    for label, path in locations:
        pyd_dir = os.path.dirname(path)
        for ssl_dll in ['libcrypto-3.dll', 'libssl-3.dll']:
            ssl_path = os.path.join(pyd_dir, ssl_dll)
            if os.path.exists(ssl_path):
                ssl_imports = get_pe_imports(ssl_path)
                print(f"\n  {ssl_dll} ({label}) deps:")
                for dep in sorted(ssl_imports):
                    in_same = os.path.exists(os.path.join(pyd_dir, dep))
                    in_sys = os.path.exists(os.path.join('C:/Windows/System32', dep))
                    marker = "✓" if (in_same or in_sys) else "✗ MISSING"
                    print(f"    {marker} {dep}")


if __name__ == '__main__':
    main()
