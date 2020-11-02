import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="al_decorators",
    version="0.0.1",
    author="AdamantLife",
    author_email="",
    description="A collections of Decorator Utilities split off from ALcustoms for lighter packaging",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AdamantLife/AL_Decorators",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[]
)
