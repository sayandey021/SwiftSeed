import sys
import os

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.providers.additional import SkidrowRepackProvider

provider = SkidrowRepackProvider()

html = provider._get("https://www.skidrowreloadedcrack.com/black-myth-wukong-empress/")
with open("skidrow_test.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Saved")
