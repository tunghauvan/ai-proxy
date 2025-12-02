#!/usr/bin/env python3
"""Setup script for LangChain Proxy CLI"""
from setuptools import setup, find_packages

setup(
    name="langchain-proxy-cli",
    version="1.0.0",
    description="CLI tool for managing LangChain Proxy Server",
    author="Your Name",
    packages=find_packages(),
    py_modules=["cli"],
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "lcp=cli:cli",
            "langchain-proxy=cli:cli",
        ],
    },
    python_requires=">=3.9",
)
