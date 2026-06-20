from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="okf-toolkit",
    version="0.1.0",
    description="CLI toolkit for working with Google's Open Knowledge Format (OKF)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/openclaw/okf-toolkit",
    license="Apache 2.0",
    py_modules=["okf"],
    python_requires=">=3.10",
    install_requires=["pyyaml>=6.0"],
    entry_points={
        "console_scripts": [
            "okf=okf:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: AI Agents",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Documentation",
        "Topic :: Text Processing :: Markup",
    ],
)
