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

    def _umdefault_version(self):
        return list(self.conan_data)[0]

    def _um_data(self) -> dict:
        """
        Extract the version specific data out of a conandata.yml
        """
        if self.version in self.conan_data:
            return self.conan_data[self.version]

        recipe_version = Version(self.version)
        available_versions = max(sorted([version for version in self.conan_data.keys() if Version(version) <= recipe_version]))
        self.output.warn(f"Using dependencies specified in conandata.yml for version: {available_versions} while recipe is build for version: {self.version}")
        return self.conan_data[available_versions]

class Pkg(ConanFile):
    name = "umbase"
    version = "0.1.7"
    default_user = "ultimaker"
    default_channel = "stable"
    exports_sources = "StandardProjectSettings.cmake"

    def package(self):
        copy(self, "StandardProjectSettings.cmake", src = self.export_sources_folder, dst = path.join(self.package_folder, "share", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("name", "umbase")
        self.cpp_info.set_property("cmake_build_modules", [path.join("share", "cmake", "StandardProjectSettings.cmake")])
