from setuptools import setup, find_packages

setup(
    name="SwiftSeed",
    version="1.5.0",
    description="A modern, standalone torrent search and download application",
    author="Sayan Dey",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "flet>=0.10.0",
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
    ],
    entry_points={
        "console_scripts": [
            "swiftseed=main:main",
        ],
    },
    python_requires=">=3.7",
)
