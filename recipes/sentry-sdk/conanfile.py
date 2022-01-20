import os

from conans import tools
from conan import ConanFile
from conan.tools.env.virtualrunenv import VirtualRunEnv
from conan.tools.env.virtualbuildenv import VirtualBuildEnv
from conan.tools.files.packager import AutoPackager

required_conan_version = ">=1.44.1"


class SentrySDKConan(ConanFile):
    name = "sentry-sdk"
    version = "0.13.5"
    description = "Python client for Sentry (https://sentry.io)"
    topics = ("conan", "python", "pypi", "pip")
    license = "BSD"
    homepage = "https://github.com/getsentry/sentry-python"
    url = "https://github.com/getsentry/sentry-python"
    settings = "os", "compiler", "build_type", "arch"
    build_policy = "missing"
    default_user = "python"
    default_channel = "stable"
    python_requires = "PipBuildTool/0.1@ultimaker/testing"
    requires = "python/3.10.2@python/stable"
    hashes = []

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
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "lib", f"python{v.major}.{v.minor}"))
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

        self.buildenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "lib", f"python{v.major}.{v.minor}"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))