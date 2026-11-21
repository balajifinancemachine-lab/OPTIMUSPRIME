from setuptools import setup, find_packages

setup(
    name="optimusprime",
    version="2.0.0",
    author="OPTIMUSPRIME Team",
    description="Ultimate Windows System Optimizer & Administrator",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/balajifinancemachine-lab/OPTIMUSPRIME",
    packages=find_packages(),
    classifiers=[
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=[
        "customtkinter>=5.2.0",
        "Pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "optimusprime=optimusprime:main",
        ],
    },
)
