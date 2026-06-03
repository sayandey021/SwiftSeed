import os
import sys
import re

def bump_version(new_version):
    """Bumps the version in multiple files across the repository."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Extract components
    parts = new_version.split('.')
    if len(parts) == 2:
        parts.append('0')
    if len(parts) == 3:
        parts.append('0')
        
    v_major, v_minor, v_patch, v_build = parts[0], parts[1], parts[2], parts[3]
    v_short = f"{v_major}.{v_minor}"
    v_medium = f"{v_major}.{v_minor}.{v_patch}"
    v_full = f"{v_major}.{v_minor}.{v_patch}.{v_build}"
    
    updates = [
        # 1. version_info.txt
        {
            "file": "version_info.txt",
            "replacements": [
                (r"filevers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)", f"filevers=({v_major}, {v_minor}, {v_patch}, {v_build})"),
                (r"prodvers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)", f"prodvers=({v_major}, {v_minor}, {v_patch}, {v_build})"),
                (r"StringStruct\(u'FileVersion',\s*u'[\d\.]+'\)", f"StringStruct(u'FileVersion', u'{v_full}')"),
                (r"StringStruct\(u'ProductVersion',\s*u'[\d\.]+'\)", f"StringStruct(u'ProductVersion', u'{v_full}')")
            ]
        },
        # 2. setup.py
        {
            "file": "setup.py",
            "replacements": [
                (r'version="[\d\.]+"', f'version="{v_medium}"')
            ]
        },
        # 3. installer_script.iss
        {
            "file": "installer_script.iss",
            "replacements": [
                (r'#define MyAppVersion "[\d\.]+"', f'#define MyAppVersion "{v_medium}"')
            ]
        },
        # 4. src/main.py (About page)
        {
            "file": "src/main.py",
            "replacements": [
                (r'ft\.Text\("Version [\d\.]+"', f'ft.Text("Version {v_short}"')
            ]
        },
        # 5. scripts/build_exe.py
        {
            "file": "scripts/build_exe.py",
            "replacements": [
                (r"elif 'productversion' in name or name == 'uctversion':\s+k.val = '[\d\.]+'", f"elif 'productversion' in name or name == 'uctversion':\n                    k.val = '{v_full}'"),
                (r"elif 'fileversion' in name:\s+k.val = '[\d\.]+'", f"elif 'fileversion' in name:\n                    k.val = '{v_full}'")
            ]
        },
        # 6. scripts/brand_dev_flet.py
        {
            "file": "scripts/brand_dev_flet.py",
            "replacements": [
                (r"elif 'productversion' in name or name == 'uctversion':\s+print\(f\"  {k.name}: '{k.val}' -> '[\d\.]+'\"\)\s+k.val = '[\d\.]+'", f"elif 'productversion' in name or name == 'uctversion':\n                print(f\"  {{k.name}}: '{{k.val}}' -> '{v_full}'\")\n                k.val = '{v_full}'"),
                (r"elif 'fileversion' in name:\s+print\(f\"  {k.name}: '{k.val}' -> '[\d\.]+'\"\)\s+k.val = '[\d\.]+'", f"elif 'fileversion' in name:\n                print(f\"  {{k.name}}: '{{k.val}}' -> '{v_full}'\")\n                k.val = '{v_full}'")
            ]
        },
        # 7. store/AppxManifest_TEMPLATE.xml
        {
            "file": "../store/AppxManifest_TEMPLATE.xml",
            "replacements": [
                (r'\bVersion="[\d\.]+"', f'Version="{v_full}"')
            ]
        }
    ]
    
    print(f"Bumping version to {new_version}...")
    
    for update in updates:
        file_path = os.path.join(base_dir, update["file"])
        if not os.path.exists(file_path):
            print(f"  [WARN] File not found: {update['file']}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        for pattern, replacement in update["replacements"]:
            content = re.sub(pattern, replacement, content)
            
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  [OK] Updated {update['file']}")
        else:
            print(f"  [SKIP] No changes needed in {update['file']}")
            
    print("Version bump complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bump_version.py <new_version>")
        print("Example: python bump_version.py 2.6.0")
        sys.exit(1)
        
    bump_version(sys.argv[1])
