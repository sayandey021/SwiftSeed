from models.category import Category
from dataclasses import dataclass

@dataclass
class ProviderInfo:
    id: str
    name: str
    specialized_category: Category
    language: str = "Multi"

class Provider:
    def __init__(self, info):
        self.info = info

providers = [
    Provider(ProviderInfo("1", "1337x", Category.ALL, "Multi")),
    Provider(ProviderInfo("2", "YTS", Category.MOVIES, "English")),
    Provider(ProviderInfo("3", "Nyaa", Category.ANIME, "Japanese")),
]

def get_provider_category(provider):
    if provider.info.specialized_category is not None:
        return provider.info.specialized_category.display_name
    return "All"

def filter_providers(category_filter, language_filter):
    results = []
    for provider in providers:
        provider_category = get_provider_category(provider)
        provider_language = getattr(provider.info, 'language', 'Multi')
        
        if category_filter != "All":
            if category_filter == "Series" and provider_category not in ["Series", "TV"]:
                continue
            elif category_filter == "Other" and provider_category != "Other":
                continue
            elif category_filter not in ["Series", "Other"] and provider_category != category_filter:
                continue
                
        if language_filter != "All" and provider_language != language_filter and provider_language != "Multi":
            continue
            
        results.append(provider.info.name)
    return results

print("Movies, All:", filter_providers("Movies", "All"))
print("All, Japanese:", filter_providers("All", "Japanese"))
