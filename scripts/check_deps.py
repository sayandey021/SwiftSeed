import pefile, os, sys
p = os.path.join('dist','SwiftSeed','_internal','libtorrent','__init__.cp313-win_amd64.pyd')
pe = pefile.PE(p)
print("=== PE IMPORTS ===")
for e in pe.DIRECTORY_ENTRY_IMPORT:
    n = e.dll.decode()
    lt = os.path.join(os.path.dirname(p), n)
    it = os.path.join('dist','SwiftSeed','_internal', n)
    s = os.path.join(os.environ.get('SystemRoot','C:\\Windows'),'System32',n)
    f = "FOUND" if (os.path.exists(lt) or os.path.exists(it) or os.path.exists(s)) else "MISSING"
    print(f"  {f}: {n}")
pe.close()
