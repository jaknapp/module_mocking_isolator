from setuptools import find_packages, setup

setup(
    name="module_mocking_isolator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "mock",
    ],
    author="John Knapp",
    description="A module mocking isolator for Python testing",
    license="MIT",
)
