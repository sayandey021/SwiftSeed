import flet as ft
with open("flet_api.txt", "w") as f:
    f.write("PAGE API:\n")
    f.write("\n".join(dir(ft.Page)))
    f.write("\n\nCLIPBOARD API:\n")
    f.write("\n".join(dir(ft.Clipboard)))
