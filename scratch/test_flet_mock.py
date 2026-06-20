import sys
import flet as ft
from ui.settings_view import SettingsView

class MockPage:
    def __init__(self):
        self.theme_mode = ft.ThemeMode.DARK
        self.overlay = []
    def update(self):
        pass
    def run_thread(self, target, *args, **kwargs):
        pass

class MockProviderManager:
    def __init__(self):
        from models.category import Category
        from dataclasses import dataclass
        @dataclass
        class ProviderInfo:
            id: str
            name: str
            specialized_category: Category
            language: str = "Multi"
            url: str = ""
            safety_status = type('Safety', (), {'value': 'safe'})
            safety_reason: str = ""
        class Provider:
            def __init__(self, info):
                self.info = info
        self.providers = [
            Provider(ProviderInfo("1", "1337x", Category.ALL, "Multi")),
            Provider(ProviderInfo("2", "YTS", Category.MOVIES, "English")),
        ]
    def add_provider(self, name, url, api_key):
        return True

class MockSettingsManager:
    def get_enabled_providers(self):
        return ["1", "2"]

class MockApp:
    def __init__(self):
        self.provider_manager = MockProviderManager()
        self.settings_manager = MockSettingsManager()

page = MockPage()
settings_mgr = MockSettingsManager()
download_mgr = None
provider_mgr = MockProviderManager()
providers = provider_mgr.providers

view = SettingsView(page, settings_mgr, download_mgr, providers, provider_mgr)

# Build provider tab directly
provider_tab = view._build_provider_settings()

# Get dropdowns
advanced_filters = provider_tab.content.controls[4]  # type: ignore
row = advanced_filters.content  # type: ignore
cat_drop = row.controls[0]  # type: ignore
lang_drop = row.controls[1]  # type: ignore

prov_col = provider_tab.content.controls[8]  # type: ignore
print("Initial controls:", len(prov_col.controls))  # type: ignore

class MockEvent:
    def __init__(self, control):
        self.control = control

# Test category
cat_drop.value = "Movies"
cat_drop.on_change(MockEvent(cat_drop))
print("After Movies filter:", len(prov_col.controls))
for c in prov_col.controls:
    if hasattr(c, 'content') and hasattr(c.content, 'controls'):
        for cc in c.content.controls:
            if hasattr(cc, 'content') and hasattr(cc.content, 'value'):
                print("Provider shown:", cc.content.value)
            if hasattr(cc, 'content') and type(cc.content).__name__ == "Text":
                print("Text:", cc.content.value)

# Test language
cat_drop.value = "All"
cat_drop.on_change(MockEvent(cat_drop))
lang_drop.value = "English"
lang_drop.on_change(MockEvent(lang_drop))
print("After English filter:", len(prov_col.controls))
