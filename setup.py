# This setup.py file is a combination of:
#
# + "setup.py (for humans)", as the whole base.
#       https://github.com/navdeep-G/setup.py/blob/master/setup.py
#
# + "discord.py", for the version regex and the appending of git metadata
#   on pre-release versions.
#       https://github.com/Rapptz/discord.py/blob/master/setup.py

import os
import re

from setuptools import setup

# Package meta-data.
NAME = "f2e-alt-cover"
DESCRIPTION = "A wrapper script that replaces the default cover of fimfic2epub."
URL = "https://github.com/ZodiacalComet/f2e-alt-cover"
AUTHOR = "ZodiacalComet"
EMAIL = "ZodiacalComet@gmail.com"
REQUIRES_PYTHON = ">=3.7.0"

# Root directory and module directory
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_SLUG = NAME.lower().replace("-", "_").replace(" ", "_")


with open(os.path.join(ROOT_DIR, "README.md")) as fd:
    LONG_DESCRIPTION = fd.read()


with open(os.path.join(ROOT_DIR, "requirements.txt")) as fd:
    REQUIRED = fd.read().splitlines()


# Acquiring version from f2e_alt_cover.py file.
VERSION = ""
VERSION_FILE = os.path.join(ROOT_DIR, f"{PROJECT_SLUG}.py")

with open(VERSION_FILE) as fd:
    VERSION = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE
    ).group(1)


if not VERSION:
    raise RuntimeError(f"__version__ is not set in {VERSION_FILE}")


# Appending git metadata to pre-release versions
if VERSION.endswith(("a", "b", "rc")):
    try:
        from subprocess import run

        out = run(["git", "rev-list", "--count", "HEAD"], capture_output=True).stdout
        if out:
            VERSION += out.decode("utf-8").strip()

        out = run(["git", "rev-parse", "--short", "HEAD"], capture_output=True).stdout
        if out:
            VERSION += "+g" + out.decode("utf-8").strip()
    except Exception:
        pass


setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    py_modules=[PROJECT_SLUG],
    entry_points={"console_scripts": [f"{NAME}={PROJECT_SLUG}:main"]},
    install_requires=REQUIRED,
    include_package_data=True,
    license="Unlicense",
)
