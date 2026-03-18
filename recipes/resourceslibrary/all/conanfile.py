import hashlib

from conan import ConanFile

required_conan_version = ">=2.7.0"


class ResourcesLibrary:
    def package_id(self):
        # Add a checksum of the source files to the package_id, so that any source file change will be considered for a rebuild
        sources_checksum = hashlib.sha256()
        for source_file in self.package_folder.rglob('*'):
            with open(source_file, 'rb') as f:
                sources_checksum.update(f.read())

        self.info.settings.append("source_checksum", sources_checksum.hexdigest())


class PyReq(ConanFile):
    name = "resourceslibrary"
    description = "This is a base conan file description for packages that define resources to be appended to cura"
    package_type = "python-require"
