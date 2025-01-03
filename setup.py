from setuptools import setup, find_packages

setup(
    name="ish-tool",
    version="1.0",
    description="because why not !",
    author="JuniorAlive",
    author_email="support@junioralive.in",
    packages=find_packages(),
    py_modules=["ish"],
    entry_points={
        "console_scripts": [
            "ish=ish:local_start",
            "ishcf=ish:cf_start",
        ],
    },
    install_requires=[
        "flask>=2.0.0",
        "cloudscraper>=1.2.0",
        # "flask-cloudflared", #experimental
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
