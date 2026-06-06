import sys
import os
sys.path.append(os.path.abspath('src'))

def dump_providers():
    from providers import get_all_providers
    providers = get_all_providers()
    
    with open('providers_dump.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total providers: {len(providers)}\n")
        
        for p in providers:
            # Replicate the logic from settings_view.py
            provider_category = "All"
            if p.info.specialized_category is not None:
                provider_category = p.info.specialized_category.display_name
                
            provider_language = getattr(p.info, 'language', 'Multi')
            provider_name = p.info.name.lower()
            
            f.write(f"{provider_name} | Cat: {provider_category} | Lang: {provider_language}\n")

if __name__ == "__main__":
    dump_providers()
