import os
import shutil
from io import StringIO

from conan import ConanFile, conan_version
from conan.errors import ConanException
from conan.tools.apple import is_apple_os
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import mkdir
from conan.tools.gnu import AutotoolsDeps
from conan.tools.microsoft import is_msvc, msvc_runtime_flag, VCVars
from conan.tools.scm import Version

conan2 = conan_version >= Version("2.0.0")

class CmakePython3Abi(object):
    def __init__(self, debug, pymalloc, unicode):
        self.debug, self.pymalloc, self.unicode = debug, pymalloc, unicode

    _cmake_lut = {
        None: "ANY",
        True: "ON",
        False: "OFF",
    }

    @property
    def suffix(self):
        suffix = ""
        if self.debug:
            suffix += "d"
        if self.pymalloc:
            suffix += "m"
        if self.unicode:
            suffix += "u"
        return suffix

    @property
    def cmake_arg(self):
        return ";".join(self._cmake_lut[a] for a in (self.debug, self.pymalloc, self.unicode))


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # The main recipe does not require CMake, but we test with it.
        # The interesting problem that arises here is if you have CMake installed
        # with your global pip, then it will fail to run in this test package.
        # To avoid that, just add a requirement on CMake.
        self.tool_requires("cmake/[>=3.15 <4]")

    def layout(self):
        cmake_layout(self)

    @property
    def _python(self):
        if conan2:
            return self.dependencies["cpython"].conf_info.get("user.cpython:python", check_type=str)
        else:
            return self.deps_user_info["cpython"].python

    @property
    def _clean_py_version(self):
        return str(self._py_version)

    @property
    def _py_version(self):
        if conan2:
            return Version(self.dependencies["cpython"].ref.version)
        else:
            return Version(self.deps_cpp_info["cpython"].version)

    @property
    def _pymalloc(self):
        if conan2:
            return bool(self.dependencies["cpython"].options.get_safe("pymalloc", False))
        else:
            return bool("pymalloc" in self.options["cpython"] and self.options["cpython"].pymalloc)

    @property
    def _cmake_abi(self):
        if self._py_version < "3.8":
            return CmakePython3Abi(debug=self.settings.build_type == "Debug", pymalloc=self._pymalloc, unicode=False)
        else:
            return CmakePython3Abi(debug=self.settings.build_type == "Debug", pymalloc=False, unicode=False)

    @property
    def _cmake_try_FindPythonX(self):
        return not is_msvc(self) or self.settings.build_type != "Debug"

    @property
    def _supports_modules(self):
        if conan2:
            return not is_msvc(self) or self.dependencies["cpython"].options.shared
        else:
            return not is_msvc(self) or self.options["cpython"].shared

    def generate(self):
        tc = CMakeToolchain(self)
        version = self._py_version
        py_major = str(version.major)
        tc.cache_variables["BUILD_MODULE"] = self._supports_modules
        tc.cache_variables["PY_VERSION_MAJOR"] = py_major
        tc.cache_variables["PY_VERSION_MAJOR_MINOR"] = f"{version.major}.{version.minor}"
        tc.cache_variables["PY_FULL_VERSION"] = str(version)
        tc.cache_variables["PY_VERSION"] = self._clean_py_version
        tc.cache_variables["PY_VERSION_SUFFIX"] = self._cmake_abi.suffix
        tc.cache_variables["PYTHON_EXECUTABLE"] = self._python
        tc.cache_variables["USE_FINDPYTHON_X".format(py_major)] = self._cmake_try_FindPythonX
        tc.cache_variables[f"Python{py_major}_EXECUTABLE"] = self._python
        tc.cache_variables[f"Python{py_major}_ROOT_DIR"] = self.dependencies["cpython"].package_folder
        tc.cache_variables[f"Python{py_major}_USE_STATIC_LIBS"] = not self.dependencies["cpython"].options.shared
        tc.cache_variables[f"Python{py_major}_FIND_FRAMEWORK"] = "NEVER"
        tc.cache_variables[f"Python{py_major}_FIND_REGISTRY"] = "NEVER"
        tc.cache_variables[f"Python{py_major}_FIND_IMPLEMENTATIONS"] = "CPython"
        tc.cache_variables[f"Python{py_major}_FIND_STRATEGY"] = "LOCATION"
        if not is_msvc(self) and self._py_version < "3.8":
            tc.cache_variables[f"Python{py_major}_FIND_ABI"] = self._cmake_abi.cmake_arg
        tc.generate()

        try:
            # CMakeToolchain might generate VCVars, but we need it
            # unconditionally for the setuptools build.
            VCVars(self).generate()
        except ConanException:
            pass

        # The build also needs access to the run environment to run the python executable
        VirtualRunEnv(self).generate(scope="run")
        VirtualRunEnv(self).generate(scope="build")
        # Just for the distutils build
        AutotoolsDeps(self).generate(scope="build")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if not cross_building(self, skip_x64_x86=True):
            if self._supports_modules:
                modsrcfolder = "py2" if self._py_version.major == 2 else "py3"
                mkdir(self, os.path.join(self.build_folder, modsrcfolder))
                for fn in os.listdir(os.path.join(self.source_folder, modsrcfolder)):
                    shutil.copy(
                        os.path.join(self.source_folder, modsrcfolder, fn),
                        os.path.join(self.build_folder, modsrcfolder, fn),
                    )
                shutil.copy(
                    os.path.join(self.source_folder, "setup.py"),
                    os.path.join(self.build_folder, "setup.py"),
                )
                os.environ["DISTUTILS_USE_SDK"] = "1"
                os.environ["MSSdk"] = "1"
                setup_args = [
                    f"{self.source_folder}/setup.py",
                    # "conan",
                    # "--install-folder", self.build_folder,
                    "build",
                    "--build-base", self.build_folder,
                    "--build-platlib", os.path.join(self.build_folder, "lib_setuptools"),
                ]
                if self.settings.build_type == "Debug":
                    setup_args.append("--debug")
                args = " ".join(f'"{a}"' for a in setup_args)
                self.run(f"{self._python} {args}")

    def _test_module(self, module, should_work):
        try:
            self.run(f"{self._python} {self.source_folder}/test_package.py -b {self.build_folder} -t {module}", env="conanrun")
        except ConanException:
            if should_work:
                self.output.warning(f"Module '{module}' does not work, but should have worked")
                raise
            self.output.info("Module failed as expected")
            return
        if not should_work:
            raise ConanException(f"Module '{module}' works, but should not have worked")
        self.output.info("Module worked as expected")

    def _cpython_option(self, name):
        if conan2:
            return self.dependencies["cpython"].options.get_safe(name, False)
        else:
            try:
                return getattr(self.options["cpython"], name, False)
            except ConanException:
                return False

    def test(self):
        if not cross_building(self, skip_x64_x86=True):
            self.run(f"{self._python} --version", env="conanrun")

            self.run(f"{self._python} -c \"print('hello world')\"", env="conanrun")

            buffer = StringIO()
            self.run(f"{self._python} -c \"import sys; print('.'.join(str(s) for s in sys.version_info[:3]))\"", buffer, env="conanrun")
            self.output.info(buffer.getvalue())
            version_detected = buffer.getvalue().splitlines()[-1].strip()
            if self._clean_py_version != version_detected:
                raise ConanException(
                    f"python reported wrong version. Expected {self._clean_py_version}. Got {version_detected}."
                )

            if self._supports_modules:
                self._test_module("gdbm", self._cpython_option("with_gdbm"))
                self._test_module("bz2", self._cpython_option("with_bz2"))
                if self._py_version.major < 3:
                    self._test_module("bsddb", self._cpython_option("with_bsddb"))
                self._test_module("lzma", self._cpython_option("with_lzma"))
                self._test_module("tkinter", self._cpython_option("with_tkinter"))
                os.environ["TERM"] = "ansi"
                self._test_module("curses", self._cpython_option("with_curses"))

                self._test_module("expat", True)
                self._test_module("sqlite3", self._cpython_option("with_sqlite3"))
                self._test_module("decimal", True)
                self._test_module("ctypes", True)
                skip_ssl_test = is_msvc(self) and self._py_version < "3.8" and self._cpython_option("shared")
                if not skip_ssl_test:
                    # Unsure cause of failure in this oddly specific combo, but these versions are EOL so not concerned with fixing.
                    self._test_module("ssl", True)

            if is_apple_os(self) and not self._cpython_option("shared"):
                self.output.info(
                    "Not testing the module, because these seem not to work on apple when cpython is built as"
                    " a static library"
                )
                # FIXME: find out why cpython on apple does not allow to use modules linked against a static python
            else:
                # FIXME: This very specific config fails to import spam for unknown reason. It also only fails in this test package.
                skip_spam_test = is_msvc(self) and self._py_version < "3.8.0" \
                    and self.settings.build_type == "Debug" and "d" in msvc_runtime_flag(self)
                if self._supports_modules and not skip_spam_test:
                    os.environ["PYTHONPATH"] = os.path.join(self.build_folder, self.cpp.build.libdirs[0])
                    self.output.info("Testing module (spam) using cmake built module")
                    self._test_module("spam", True)

                    os.environ["PYTHONPATH"] = os.path.join(self.build_folder, "lib_setuptools")
                    self.output.info("Testing module (spam) using setup.py built module")
                    self._test_module("spam", True)

                    del os.environ["PYTHONPATH"]

            # MSVC builds need PYTHONHOME set. Linux and Mac don't require it to be set if tested after building,
            # but if the package is relocated then it needs to be set.
            if conan2:
                os.environ["PYTHONHOME"] = self.dependencies["cpython"].conf_info.get("user.cpython:pythonhome", check_type=str)
            else:
                os.environ["PYTHONHOME"] = self.deps_user_info["cpython"].pythonhome
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(bin_path, env="conanrun")
