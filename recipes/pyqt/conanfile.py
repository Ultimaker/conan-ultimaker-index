import os

from conans import tools
from conan import ConanFile
from conan.tools.env.virtualrunenv import VirtualRunEnv
from conan.tools.env.virtualbuildenv import VirtualBuildEnv
from conan.tools.files.packager import AutoPackager

required_conan_version = ">=1.44.1"


class Pyqt6Conan(ConanFile):
    name = "pyqt6"
    version = "6.2.2"
    description = "Python bindings for the Qt cross platform application toolkit"
    topics = ("conan", "python", "pypi", "pip")
    license = "GPL v3"
    homepage = "https://www.riverbankcomputing.com/software/pyqt/"
    url = "https://www.riverbankcomputing.com/software/pyqt/"
    settings = "os", "compiler", "build_type", "arch"
    build_policy = "missing"
    default_user = "python"
    default_channel = "stable"
    python_requires = "PipBuildTool/0.1@ultimaker/testing"
    requires = "python/3.10.2@python/stable",\
                "pyqt6-sip/13.2.0@python/stable",\
                "pyqt6-qt6/6.2.2@python/stable"
    hashes = [

    ]

    def layout(self):
        self.folders.build = "build"
        self.folders.package = "package"
        self.folders.generators = os.path.join("build", "conan")

    def generate(self):
        rv = VirtualRunEnv(self)
        rv.generate()

        bv = VirtualBuildEnv(self)
        bv.generate()

    def build(self):
        pb = self.python_requires["PipBuildTool"].module.PipBuildTool(self)
        pb.configure()
        pb.build()

    def package(self):
        packager = AutoPackager(self)
        packager.patterns.lib = ["*.so", "*.so.*", "*.a", "*.lib", "*.dylib", "*.py*"]
        packager.run()

    def package_info(self):
        v = tools.Version(self.dependencies['python'].ref.version)
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "lib", f"python{v.major}.{v.minor}", "site-packages"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "lib", f"python{v.major}.{v.minor}", "site-packages"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def package_id(self):
        self.info.settings.build_type = "Release"