import sys
from io import StringIO
from pathlib import Path

from conan import ConanFile
from conan.tools.files import files, AutoPackager
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualRunEnv
from conans.errors import ConanException
from conans.tools import Version, chdir

from jinja2 import Template

required_conan_version = ">=1.33.0"


class PyQt6Conan(ConanFile):
    name = "pyqt6"
    description = "The subset of a Qt installation needed by PyQt6."
    topics = ("conan", "python", "pypi", "pip")
    license = "LGPL v3"
    homepage = "https://www.riverbankcomputing.com/software/pyqt/"
    url = "https://www.riverbankcomputing.com/software/pyqt/"
    settings = "os", "compiler", "build_type", "arch"
    build_policy = "missing"
    options = {
        "shared": [True, False],
        "fPIC": [True, False]
    }
    default_options = {
        "shared": True,
        "fPIC": True
    }

    @property
    def _venv_base_path(self):
        return Path(self.folders.generators_folder, "venv")

    @property
    def _venv_bin_path(self):
        is_windows = self.settings.os == "Windows"
        return Path(self._venv_base_path, "Scripts" if is_windows else "bin")

    @property
    def _source_folder(self):
        return "src"

    def layout(self):
        basic_layout(self, src_folder = self._source_folder)
        self.folders.generators = Path("generators")

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
        self.options["qt"].shared = self.options.shared
        self.options["cpython"].shared = self.options.shared

    def source(self):
        sources = self.conan_data["sources"][self.version]
        files.get(self, **sources, strip_root = True)

        pyproject_toml_location = Path(self.folders.source_folder).joinpath("pyproject.toml")
        with open(pyproject_toml_location, "r") as f:
            pyproject_toml = f.read()

        tool_sip_project = Template(r"""[tool.sip.project]
py-pylib-lib = "{{ python_lib_path }}"
py-include-dir = "{{ python_include_path }}/python{{ python_major_version }}.{{ python_minor_version }}"
py-major-version = {{ python_major_version }}
py-minor-version = {{ python_minor_version }}""")

        python_dep = self.dependencies["cpython"]
        python_version = Version(python_dep.ref.version)
        python_lib_path = python_dep.cpp_info.libdirs[0]
        python_include_path = python_dep.cpp_info.includedirs[0]

        pyproject_toml += tool_sip_project.render(python_lib_path = python_lib_path,
                                                  python_include_path = python_include_path,
                                                  python_major_version = python_version.major,
                                                  python_minor_version = python_version.minor)

        with open(pyproject_toml_location, "w") as f:
            f.write(pyproject_toml)

    def generate(self):
        vr = VirtualRunEnv(self)
        vr.generate()

    def build(self):
        python_interpreter = Path(self.deps_user_info["cpython"].python)

        # Create the virtual Python env and install the build tools: sip, PyQt6-sip and PyQt-builder (make sure these are build against the
        # CPython dep
        # When on Windows execute as Windows Path
        if self.settings.os == "Windows":
            python_interpreter = Path(*[f'"{p}"' if " " in p else p for p in python_interpreter.parts])

        # Create the virtual environment
        self.run(f"""{python_interpreter} -m venv {self._venv_base_path}""", env = "conanbuild")

        # Make sure there executable is named the same on all three OSes this allows it to be called with `python`
        # simplifying GH Actions steps
        if self.settings.os != "Windows":
            python_venv_interpreter = Path(self.build_folder, self._venv_bin_path, "python")
            if not python_venv_interpreter.exists():
                python_venv_interpreter.hardlink_to(Path(self.build_folder, self._venv_bin_path,
                                                              Path(sys.executable).stem + Path(sys.executable).suffix))
        else:
            python_venv_interpreter = Path(self.build_folder, self._venv_bin_path,
                                                Path(sys.executable).stem + Path(sys.executable).suffix)

        if not python_venv_interpreter.exists():
            raise ConanException(f"Virtual environment Python interpreter not found at: {python_venv_interpreter}")
        if self.settings.os == "Windows":
            python_venv_interpreter = Path(*[f'"{p}"' if " " in p else p for p in python_venv_interpreter.parts])

        buffer = StringIO()
        outer = '"' if self.settings.os == "Windows" else "'"
        inner = "'" if self.settings.os == "Windows" else '"'
        self.run(
            f"{python_venv_interpreter} -c {outer}import sysconfig; print(sysconfig.get_path({inner}purelib{inner})){outer}",
            env = "conanrun",
            output = buffer)
        pythonpath = buffer.getvalue().splitlines()[-1]

        env = VirtualRunEnv(self)
        run_env = env.environment()

        run_env.define_path("VIRTUAL_ENV", str(self._venv_base_path))
        run_env.prepend_path("PATH", str(self._venv_bin_path))
        run_env.prepend_path("PYTHONPATH", str(pythonpath))
        run_env.unset("PYTHONHOME")

        envvars = run_env.vars(self, scope = "run")

        with envvars.apply():
            # Install some base_packages
            self.run(f"""{python_venv_interpreter} -m pip install wheel setuptools""", run_environment = True, env = "run")

            # Install sip PyQt6-sip PyQt-builder in the newly created virtual python env # TODO: pin versions and make it future proof
            self.run(f"""{python_venv_interpreter} -m pip install sip \"PyQt6-sip<=13.2.1\" \"PyQt-builder<=1.12.2\" --no-binary :all: --upgrade""",
                     run_environment = True, env = "run")

            sip_install_executable = Path(self._venv_bin_path, "sip-install")
            if self.settings.os == "Windows":
                sip_install_executable = Path(*[f'"{p}"' if " " in p else p for p in sip_install_executable.parts])

            with chdir(self.folders.source_folder):
                self.run(f"""{sip_install_executable} --verbose --build-dir {self.folders.build_folder} --target-dir {self.folders.package_folder} --no-tools --qt-shared --confirm-license --no-dbus-python""",
                         run_environment = True, env = "run")

        files.rmdir(self._venv_base_path)


    def package(self):
        packager = AutoPackager(self)
        packager.run()
        # TODO: package pyd, pyi
        # TODO: should we also add the PyQt6-sip as part of this package?
        # self.copy("*", src = self._site_packages, dst = self._site_packages)
