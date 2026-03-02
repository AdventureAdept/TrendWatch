"""Setup script for trendwatch."""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="trendwatch",
    version="0.1.0",
    description="Split videos into platform-specific reels for social media",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AdventureAdept",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "yt-dlp>=2024.8.0",
        "click>=8.1.0",
        "opencv-python>=4.8.0",
        "mediapipe>=0.10.0,<0.11.0",
        "requests>=2.31.0",
        "google-api-python-client>=2.100.0",
        "google-auth>=2.23.0",
        "google-auth-oauthlib>=1.1.0",
        "google-auth-httplib2>=0.1.1",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "trendwatch=trendwatch.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
