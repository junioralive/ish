from setuptools import setup, find_packages

setup(
    name="ish-tool",
    version="1.0",
    description="because why not !",
    author="JuniorAlive",
    author_email="support@junioralive.in",
    packages=find_packages(),
    py_modules=["ish"],  # Reference to ish.py
    entry_points={
        "console_scripts": [
            "ish=ish:main",  # Maps `ish` command to the `main()` function in ish.py
        ],
    },
    install_requires=[
        "flask>=2.0.0",  # Ensure Flask version compatibility
        "cloudscraper>=1.2.0",  # Ensure the cloudscraper version is adequate
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
