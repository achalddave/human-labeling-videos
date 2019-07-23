import setuptools

# with open("README.md", "r") as fh:
#     long_description = fh.read()
long_description = ''

setuptools.setup(
    name="labeler",
    version="0.0.1",
    author="Achal Dave",
    author_email="achalddave@gmail.com",
    description="Classification labeler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
