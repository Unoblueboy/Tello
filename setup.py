import setuptools
import versioneer

with open("README.md", "r") as fh:
    long_description = fh.read()
with open("requirements.txt", "r") as fh:
    requirements = [line.strip() for line in fh]

setuptools.setup(
    name="tello",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="Nathan Douglas",
    author_email="Nathan20467@gmail.com",
    description="A Python library implementing the Tello 1.3.0.0 SDK.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
    install_requires=requirements,
)
