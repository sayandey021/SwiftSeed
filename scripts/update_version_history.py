import os
import re
import sys

def update_version_history(mode="auto"):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_file = os.path.join(base_dir, "docs", "RELEASE_NOTES.md")
    main_py = os.path.join(base_dir, "src", "main.py")

    if not os.path.exists(main_py):
        print(f"Error: {main_py} not found.")
        return

    # Read main.py
    with open(main_py, "r", encoding="utf-8") as f:
        main_content = f.read()

    # Extract existing versions from main.py
    pattern = re.compile(r'ft\.Text\("([^"]+)", weight=ft\.FontWeight\.BOLD, size=16\),\s*ft\.Text\("([^"]+)", size=13\),')
    matches = pattern.findall(main_content)
    
    versions_to_write = []

    if mode == "auto":
        print("\n--- Auto-updating from RELEASE_NOTES.md ---")
        if not os.path.exists(md_file):
            print(f"Error: {md_file} not found.")
            return
            
        with open(md_file, "r", encoding="utf-8") as f:
            md_content = f.read()

        current_version = None
        current_bullets = []

        for line in md_content.split('\n'):
            line = line.strip()
            v_match = re.match(r"^##\s+Version\s+([\d\.]+)", line, re.IGNORECASE)
            if v_match:
                if current_version:
                    bullet_text = "\\n".join(current_bullets) + "\\n"
                    bullet_text = bullet_text.replace('"', '\\"')
                    versions_to_write.append((current_version, bullet_text))
                ver_num = v_match.group(1)
                current_version = f"v{ver_num}"
                current_bullets = []
                continue
                
            if current_version:
                if line.startswith("- "):
                    bullet = line[2:].replace("**", "")
                    current_bullets.append(f"• {bullet}")

        if current_version:
            bullet_text = "\\n".join(current_bullets) + "\\n"
            bullet_text = bullet_text.replace('"', '\\"')
            versions_to_write.append((current_version, bullet_text))
            
    elif mode == "manual":
        print("\n--- Manual Version History Input ---")
        ver_num = input("Enter version number (e.g. 2.1.2): ").strip()
        if not ver_num:
            print("Operation cancelled.")
            return
            
        current_version = ver_num if ver_num.lower().startswith('v') else f"v{ver_num}"
        current_bullets = []
        
        print(f"Enter release notes for {current_version} (leave line empty to finish):")
        while True:
            bullet = input("- ").strip()
            if not bullet:
                break
            if bullet.startswith("- ") or bullet.startswith("• "):
                bullet = bullet[2:]
            current_bullets.append(f"• {bullet}")
            
        if not current_bullets:
            print("No bullets entered. Operation cancelled.")
            return
            
        bullet_text = "\\n".join(current_bullets) + "\\n"
        bullet_text = bullet_text.replace('"', '\\"')
        
        versions_to_write.append((current_version, bullet_text))
        
        # Add existing versions that don't match this one
        for v, b in matches:
            if v != current_version:
                versions_to_write.append((v, b))
                
    elif mode == "edit":
        print("\n--- Edit Previous Version Log ---")
        if not matches:
            print("No existing versions found in app to edit.")
            return
            
        for idx, (ver, _) in enumerate(matches):
            print(f"  [{idx+1}] {ver}")
            
        choice = input(f"Select version to edit (1-{len(matches)}): ").strip()
        try:
            choice_idx = int(choice) - 1
            if choice_idx < 0 or choice_idx >= len(matches):
                print("Invalid choice.")
                return
        except ValueError:
            print("Invalid input.")
            return
            
        selected_ver, old_bullets_str = matches[choice_idx]
        print(f"\nEditing log for {selected_ver}")
        print("Current log:")
        old_lines = old_bullets_str.replace('\\"', '"').split('\\n')
        for line in old_lines:
            if line:
                print(f"  {line}")
                
        print("\nEnter new log for this version (leave line empty to finish):")
        current_bullets = []
        while True:
            bullet = input("- ").strip()
            if not bullet:
                break
            if bullet.startswith("- ") or bullet.startswith("• "):
                bullet = bullet[2:]
            current_bullets.append(f"• {bullet}")
            
        if not current_bullets:
            print("No bullets entered. Operation cancelled.")
            return
            
        new_bullets_str = "\\n".join(current_bullets) + "\\n"
        new_bullets_str = new_bullets_str.replace('"', '\\"')
        
        # Reconstruct list
        matches[choice_idx] = (selected_ver, new_bullets_str)
        versions_to_write = matches

    if not versions_to_write:
        print("No versions to update.")
        return

    # Generate Python code snippet
    snippet_lines = []
    snippet_lines.append("        changelog_content = ft.ListView([")
    
    for ver, bullet_text in versions_to_write[:10]:
        snippet_lines.append(f'            ft.Text("{ver}", weight=ft.FontWeight.BOLD, size=16),')
        snippet_lines.append(f'            ft.Text("{bullet_text}", size=13),')
        
    snippet_lines.append("        ], expand=True, padding=ft.Padding(0, 0, 15, 0), spacing=5)")
    new_snippet = "\n".join(snippet_lines)

    # Replace old snippet
    block_pattern = re.compile(r"        changelog_content = ft\.ListView\(\[.*?        \], expand=True, padding=ft\.Padding\(0, 0, 15, 0\), spacing=5\)", re.DOTALL)
    
    m = block_pattern.search(main_content)
    if not m:
        print("Could not find the changelog_content block in main.py!")
        return
        
    updated_content = main_content[:m.start()] + new_snippet + main_content[m.end():]
    
    with open(main_py, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    print("Successfully updated version history in src/main.py!")

if __name__ == "__main__":
    if "--manual" in sys.argv:
        update_version_history(mode="manual")
    elif "--edit" in sys.argv:
        update_version_history(mode="edit")
    else:
        update_version_history(mode="auto")
