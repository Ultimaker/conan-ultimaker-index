import os

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.tools.env.environment import EnvVars, register_env_script
from conans.client.subsystems import deduce_subsystem

from conans.util.files import save

class PythonVirtualEnvironment(object):
    def __init__(self, conanfile: ConanFile):
        self._conanfile = conanfile
        self._python_interpreter = None
        self._requirements_txt = None
        self._use_env_file = None

    @property
    def _site_packages_path(self):
        if self._conanfile.settings.os == "Windows":
            return os.path.join("Lib", "site-packages")
        return os.path.join("lib", "python3.10", "site-packages")

    @property
    def _venv_path(self):
        if self._conanfile.settings.os == "Windows":
            return "Scripts"
        return "bin"

    def _create_env_file_script(self, envvars: EnvVars, filename, env_variable):
        file_path = os.path.join(self._conanfile.generators_folder, filename)
        subsystem = deduce_subsystem(self._conanfile, envvars._scope)
        result = []
        for varname, varvalues in envvars._values.items():
            value = varvalues.get_str("${name}", subsystem, pathsep = envvars._pathsep)
            value = value.replace('"', '\\"')
            if value:
                result.append('echo "{}={}" >> {}'.format(varname, value, env_variable))

        content = "\n".join(result)
        save(file_path, content)
        if envvars._scope:
            register_env_script(self._conanfile, file_path, envvars._scope)

    def configure(self, python_interpreter, requirements_txt = None, use_env_file = None):
        if not self._conanfile.should_configure:
            return
        if requirements_txt:
            self._requirements_txt = requirements_txt
        self._use_env_file = use_env_file

        self._python_interpreter = python_interpreter

    def generate(self):
        if not self._conanfile.should_build:
            return

        # install the virtual environment
        self._conanfile.output.info(f"Creating the virtual environment using {self._python_interpreter} in {self._conanfile.build_folder}")
        self._conanfile.run(f"{self._python_interpreter} -m venv {self._conanfile.build_folder}", env = "conanrun")

        # activate the virtual environment
        self._conanfile.output.info(f"Setting virtual environment variable")

        run_env = VirtualRunEnv(self._conanfile)
        env = run_env.environment()
        env.define_path("VIRTUAL_ENV", self._conanfile.build_folder)
        env.prepend_path("PATH", os.path.join(self._conanfile.build_folder, self._venv_path))
        env.prepend_path("PYTHONPATH", os.path.join(self._conanfile.build_folder, self._site_packages_path))
        env.unset("PYTHONHOME")
        env.define("PS1", f"({self._conanfile.name}) ${{PS1:-}}")
        envvars = env.vars(self._conanfile)
        envvars.save_script(f"{self._conanfile.name}")
        if self._use_env_file:
            self._create_env_file_script(envvars, f"env_{self._conanfile.name}.sh", self._use_env_file)

        # install the requirements
        if self._requirements_txt:
            if hasattr(self._requirements_txt, "__iter__") and not isinstance(self._requirements_txt, str):
                for req_txt in self._requirements_txt:
                    self._conanfile.output.info(f"Installing requirements from {req_txt}")
                    with envvars.apply():
                        self._conanfile.run(f"python -m pip install -r {os.path.join(self._conanfile.source_folder, req_txt)}", run_environment = True, env="conanrun")
            else:
                self._conanfile.output.info(f"Installing requirements from {self._requirements_txt}")
                with envvars.apply():
                    self._conanfile.run(f"python -m pip install -r {os.path.join(self._conanfile.source_folder, self._requirements_txt)}", run_environment = True, env="conanrun")



class Pkg(ConanFile):
    name = "PythonVirtualEnvironment"
    version = "0.2.1"
