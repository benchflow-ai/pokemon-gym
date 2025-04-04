from setuptools import setup, find_packages

setup(
    name="pokemon_env",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyboy==2.2.0",
        "Pillow",
        "numpy==1.24.4",
        "fastapi>=0.103.1",
        "uvicorn>=0.23.2",
        "requests>=2.31.0",
        "pydantic>=2.4.2",
        "pygame==2.6.1",
        "benchflow>=0.1.13",
        "opencv-python",
    ],
) 