import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="charm-k8s-alertmanager",
    version="0.1.0",
    author="Mark S. Maglana",
    author_email="mark.maglana@canonical.com",
    description="Kubernetes Charm/Operator for Prometheus",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/relaxdiego/charm-k8s-alertmanager",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
