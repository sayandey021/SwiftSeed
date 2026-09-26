from setuptools import setup, find_packages

setup(
    name="SwiftSeed",
    version="2.3.1",
    description="A modern, standalone torrent search and download application",
    author="Sayan Dey",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "flet>=0.86.5,<1.0.0",
        "requests>=2.28.0",
        "PySocks>=1.7.1",
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
        "pystray>=0.19.5",
        "Pillow>=10.0.0",
        "comtypes>=1.2.0",
        "pywin32>=305",
        "libtorrent>=2.1.1",
    ],
    entry_points={
        "console_scripts": [
            "swiftseed=main:main",
        ],
    },
    python_requires=">=3.10",
)
