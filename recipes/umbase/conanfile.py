from os import path

from conan import ConanFile
from conan.tools.files import copy
from conan.tools.scm import Version
from conan.errors import ConanException


class UMBaseConanfile(object):
    """
    Ultimaker base conanfile, for reusing Python code in our repositories
    https://docs.conan.io/en/latest/extending/python_requires.html
    """

    def _um_data(self) -> dict:
        """
        Extract the version specific data out of a conandata.yml
        """
        try:
            recipe_version = self.version
        except ConanException:
            recipe_version = "None"

        try:
            channel = self.channel
        except ConanException:
            channel = ""

        if channel:

            if channel == "testing":
                self.output.info(f"Using conandata.yml from channel: {channel}")
                return self.conan_data["None"]

            elif channel == "stable" or channel == "_" or channel == "":
                if recipe_version:
                    if recipe_version in self.conan_data:
                        self.output.info(f"Using conandata.yml from channel: {channel} and recipe version: {recipe_version}")
                        return self.conan_data[recipe_version]

                    recipe_version = Version(recipe_version)
                    all_versions = []
                    for k in self.conan_data:
                        try:
                            v = Version(k)
                        except ConanException:
                            continue
                        all_versions.append(v)

                    # First try to find a version which might take into account prereleases
                    satifying_versions = sorted([v for v in all_versions if v <= recipe_version])
                    if len(satifying_versions) == 0:
                        # Then try to find a version which only takes into account major.minor.patch
                        satifying_versions = sorted([v for v in all_versions if Version(f"{v.major}.{v.minor}.{v.patch}") <= Version(f"{recipe_version.major}.{recipe_version.minor}.{recipe_version.patch}")])
                        if len(satifying_versions) == 0:
                            self.output.warn(f"Could not find a maximum satisfying version from channel: {channel} for {recipe_version} in {[str(v) for v in all_versions]}, defaulting to testing channel")
                            return self.conan_data["None"]
                    version = str(satifying_versions[-1])
                    self.output.info(f"Using conandata.yml from channel: {channel} and recipe version: {version}")
                    return self.conan_data[version]

            elif channel in self.conan_data:
                self.output.info(f"Using conandata.yml from channel: {channel}")
                return self.conan_data[channel]

        self.output.info(f"Using conandata.yml defaulting to testing channel")
        return self.conan_data["None"]


class Pkg(ConanFile):
    name = "umbase"
    version = "0.1.7"
    default_user = "ultimaker"
    default_channel = "stable"
    exports_sources = "StandardProjectSettings.cmake"

    def package(self):
        copy(self, "StandardProjectSettings.cmake", "cmake")

    def package_info(self):
        self.cpp_info.set_property("name", "umbase")
        self.cpp_info.set_property("cmake_build_modules", [path.join("cmake", "StandardProjectSettings.cmake")])
