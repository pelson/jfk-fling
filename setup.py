import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="jfk-fling",
    version="2019.2",
    author="Phil Elson",
    author_email="pelson.pub@gmail.com",
    description="A simple REPL for Fortran within a Jupyter environment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        'fparser',
        'ipykernel',
    ],
    url="https://github.com/pelson/jfk-fling",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
    ],
    entry_points={
        'console_scripts': [
            'jfk-fling = jfk_fling.launch_kernel:main',
        ],
    }
)
