from conan import ConanFile
from conan.tools.scm import Version


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
