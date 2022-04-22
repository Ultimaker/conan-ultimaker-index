import sys
import yaml
import subprocess

from pathlib import Path

if __name__ == "__main__":
    user = sys.argv[1]
    ref_name = sys.argv[2]

    changed_recipes = []
    for file in sys.argv[3:]:
        file_path = Path(file)
        if "recipes" in file_path.parts:
            changed_recipes.append(Path("/".join(file_path.parts[:file_path.parts.index("recipes") + 2])))

    if ref_name == "main":
        channel = "stable"
    elif ref_name == "dev":
        channel = "testing"
    else:
        channel = ref_name[:9] if ref_name.startswith("CURA-") and len(ref_name) >= 9 else ref_name

    for recipe_path in changed_recipes:
        recipe_name = recipe_path.parts[-1]
        conandata_path = recipe_path.joinpath("conandata.yml")
        if not conandata_path.exists():
            continue
        with open(conandata_path, "r") as f:
            parsed_yaml = yaml.safe_load(f)
            for recipe_version in parsed_yaml["sources"].keys():
                subprocess.run(f"conan export {recipe_path} {recipe_name}/{recipe_version}@{user}/{channel}", shell = True)
