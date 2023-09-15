from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        name="cwi",
        version="0.1.0",
        author_email="ryan.hamilton@ec.gc.ca",
        author="Ryan Hamilton",
        package_dir={" ": "cwi"},
        packages=find_packages(where="cwi", include=["cwi", "cwi.*"]),
        entry_points={"console_scripts": ["cwiops = cwi.cli:cli"]},
    )
