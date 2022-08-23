import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import files, replace_in_file
from conan.tools.layout import cmake_layout
from conans.tools import chdir, vcvars

from jinja2 import Template

required_conan_version = ">=1.33.0"


class PyQt6Conan(ConanFile):
    name = "pyqt6"
    author = "Riverbank Computing Limited"
    description = "Python bindings for the Qt cross platform application toolkit"
    topics = ("conan", "python", "pypi", "pip")
    license = "LGPL v3"
    homepage = "https://www.riverbankcomputing.com/software/pyqt/"
    url = "https://www.riverbankcomputing.com/software/pyqt/"
    settings = "os", "compiler", "build_type", "arch"
    build_policy = "missing"

    python_requires = "pyprojecttoolchain/[>=0.1.6]@ultimaker/stable", "sipbuildtool/[>=0.2.2]@ultimaker/stable"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "py_build_requires": ["ANY"],
        "py_build_backend": ["ANY"],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "py_build_requires": '"sip >=6.5, <7", "PyQt-builder >=1.11, <2", "PyQt6-sip >=13.4, <14"',
        "py_build_backend": "sipbuild.api",
    }

    def layout(self):
        cmake_layout(self)
        self.folders.source = "source"

    def requirements(self):
        self.requires("cpython/3.10.4")
        self.requires(f"qt/{self.version}")

        # Overriding version conflicts of dependencies for cpython and qt
        self.requires("zlib/1.2.11")
        self.requires("openssl/1.1.1l")
        self.requires("libffi/3.2.1")
        self.requires("sqlite3/3.36.0")
        self.requires("expat/2.4.1")

    def configure(self):
        self.options["cpython"].shared = self.options.shared
        self.options["qt"].shared = self.options.shared

        # Disbabled harfbuzz and glib for now since these require the use of a bash such as msys2. If we still need
        # these libraries. We should fix these recipes such that they don't use automake and autoconf on Windows and
        # add the configure option: `-o msys2:packages=base-devel,binutils,gcc,autoconf,automake`
        # These recipes are older version and don't handle the the run/build environment and the win_bash config options
        # well. Preinstalling these packages is a quick and dirty solution but a viable one due to the time constraints
        self.options["qt"].with_harfbuzz = False
        self.options["qt"].with_glib = False

    def source(self):
        sources = self.conan_data["sources"][self.version]
        files.get(self, **sources, strip_root = True)

        # Might be a bug in PyQt-builder but the option link-full-dll isn't available, even though it is set in the
        # module pyqtbuild\project.py. A simple hack is to add `self.link_full_dll = True` to the project such that
        # we don't link against the limited Python ABI but against the full python<major><minor> ABI
        replace_in_file(self, Path(self.source_folder, "project.py"), "def apply_user_defaults(self, tool):", """def apply_user_defaults(self, tool):
        self.link_full_dll = True
        """)

    def generate(self):
        # Generate the pyproject.toml and override the shipped pyproject.toml, This allows us to link to our CPython
        # lib
        pp = self.python_requires["pyprojecttoolchain"].module.PyProjectToolchain(self)
        pp.blocks["tool_sip_metadata"].values["name"] = "PyQt6"
        pp.blocks["tool_sip_metadata"].values["description_file"] = "README"

        # The following setting keys and blocks are not used by PyQt6, we should remove these
        pp.blocks["tool_sip_project"].values["sip_files_dir"] = None
        pp.blocks.remove("tool_sip_bindings")
        pp.blocks.remove("extra_sources")
        pp.blocks.remove("compiling")

        pp.generate()

    def build(self):
        # The vcvars context should have no effect on non-windows operating systems (We should however still look at how
        # this behaves on Windows when we use a different compiler such as Clang
        with chdir(self.source_folder):
            with vcvars(self):

                # self.run(f"""sip-install --pep484-pyi --verbose --no-tools --qt-shared --confirm-license""", run_environment = True, env = "conanrun")
                self.run(f"""sip-install --pep484-pyi --verbose --confirm-license""", run_environment = True, env = "conanrun")

    def package(self):
        # already installed by our use of the `sip-install` command during build
        pass

    def package_info(self):
        self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "site-packages"))
