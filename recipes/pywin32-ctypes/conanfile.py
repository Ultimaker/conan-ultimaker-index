from conan import ConanFile
from conan.tools.env.virtualrunenv import VirtualRunEnv
from conan.tools.env.virtualbuildenv import VirtualBuildEnv

required_conan_version = ">=1.44.1"


class Pywin32CtypesConan(ConanFile):
    name = "pywin32-ctypes"
    version = "0.2.0"
    description = ""
    topics = ("conan", "python", "pypi", "pip")
    license = "BSD"
    homepage = "https://github.com/enthought/pywin32-ctypes"
    url = "https://github.com/enthought/pywin32-ctypes"
    settings = "os", "compiler", "build_type", "arch"
    build_policy = "missing"
    default_user = "pypi"
    default_channel = "stable"
    python_requires = ["UltimakerBase/0.4@ultimaker/testing", "PipBuildTool/0.2@ultimaker/testing"]
    python_requires_extend = "UltimakerBase.UltimakerBase"
    requires = "python/3.10.2@python/stable"
    hashes = []

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
        self.copy("*")

    def package_info(self):
        self._set_python_site_packages()

    def package_id(self):
        self.info.settings.build_type = "Release"
