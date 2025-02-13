# setup.py
import setuptools
import os


# Load the version from the package __init__.py
def load_version():
    version_file = os.path.join(
        os.path.dirname(__file__), "src", "pumle", "__init__.py"
    )
    with open(version_file) as f:
        for line in f:
            if line.startswith("__version__"):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")


def load_requirements(filename="requirements.txt"):
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def get_data_files():
    data_files = []
    # Include setup.ini and simulation_script.sh in the root
    data_files.append(("", ["setup.ini", "simulation_script.sh"]))

    # Include all files in benchmark and simulation folders
    for folder in ["benchmark", "simulation"]:
        file_list = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_list.append(os.path.join(root, file))
        if file_list:
            data_files.append((folder, file_list))
    return data_files


setuptools.setup(
    name="pumle",
    version=load_version(),
    author="Luiz Fernando",
    author_email="luizfernando@gmail.com",
    description="A simulation pipeline package for consolidating simulation data and optionally uploading to cloud storage",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/gcpeixoto/PUMLE/",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    install_requires=load_requirements(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    data_files=get_data_files(),
    package_data={
        "pumle": ["*", "simulation_script.sh", "benchmark/**/*", "simulation/**/*"],
    },
)
