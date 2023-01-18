#  Copyright (c) 2023 UltiMaker.
#  Cura is released under the terms of the LGPLv3 or higher.

import argparse
import os
import subprocess
from os.path import isfile

from pathlib import Path


def extract_strings(root_path: Path, script_path: Path, translations_root_path: Path, all_strings_pot_path: Path):
    """ Extracts all strings into a pot file with empty translations.

    Strings are extracted everywhere that i18n is used in python and qml in the project. It also checks the project
    for JSON files with 'settings' in the root node and extracts these for translation as well.

    @param root_path: The root path of the project. This is the root for string searching.
    @param script_path: The location of the bash scripts used for translating.
    @param translations_root_path: The root of the translations folder (resources/i18n).
    @param all_strings_pot_path: The path of the pot file where all strings will be outputted (resources/i8n/cura.pot).
    """

    # Extract the setting strings from any json file with settings at its root
    extract_json_arguments = [
        script_path.joinpath("extract-json"),
        root_path.joinpath("resources", "definitions"),
        translations_root_path
    ]
    subprocess.run(extract_json_arguments)

    # Extract all strings from qml and py files
    extract_qml_py_arguments = [
        script_path.joinpath("extract-all"),
        root_path,
        all_strings_pot_path
    ]
    subprocess.run(extract_qml_py_arguments)

    # Extract all the name and description from all plugins
    extract_plugin_arguments = [
        script_path.joinpath("extract-plugins"),
        root_path.joinpath("plugins"),
        all_strings_pot_path
    ]
    subprocess.run(extract_plugin_arguments)

    # Convert the output file to utf-8
    convert_encoding_arguments = [
        "msgconv",
        "--to-code=UTF-8",
        all_strings_pot_path,
        "-o",
        all_strings_pot_path
    ]
    subprocess.run(convert_encoding_arguments)


def update_po_files_all_languages(translations_root_path: Path) -> None:
    """ Updates all po files in translation_root_path with new strings mapped to blank translations.

    This will take all newly generated po files in the root of the translations path (i18n/cura.pot, i18n/fdmextruder.json.def.pot)
    and merge them with the existing po files for every language. This will create new po files with empty translations
    for all new words added to the project.

    @param translation_root_path: Root of the translations folder (resources/i18n).
    """
    new_pot_files = []

    for file in os.listdir(translations_root_path):
        path = translations_root_path.joinpath(file)
        if path.suffix == ".pot":
            new_pot_files.append(path)
    print(new_pot_files)

    for directory, _, po_files in os.walk(translations_root_path):
        print(directory)
        print(po_files)
        for pot in new_pot_files:

            po_filename = pot.name.rstrip("t")
            if po_filename not in po_files:
                continue  # We only want to merge files that have matching names

            pot_file = pot
            po_file = Path(directory, po_filename).absolute()

            merge_files_arguments = [
                "msgmerge",
                "--no-wrap",
                "--no-fuzzy-matching",
                "--update",
                "--sort-by-file",  # Sort by file location, this is better than pure sorting for translators
                po_file,  # po file that will be updated
                pot_file  # source of new strings
            ]

            subprocess.run(merge_files_arguments)


def extract_strings_from_project(root_path: Path, translations_root_path: Path, translation_file_name: str) -> None:
    print(root_path)
    print(translations_root_path)
    print(translation_file_name)
    script_path = Path(__file__).parent.resolve() # Assume other scripts are in the same folder as this file

    all_strings_pot_path = translations_root_path.joinpath(translation_file_name)  # pot file containing all strings untranslated
    if os.path.exists(all_strings_pot_path):
        os.remove(all_strings_pot_path)  # Clear the output file, otherwise deleted strings will still be in the output.

    extract_strings(root_path, script_path, translations_root_path, all_strings_pot_path)

    update_po_files_all_languages(translations_root_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract strings from project into .po files")
    parser.add_argument("root_path", type=str, help="The root of the project to extract translatable strings from")
    parser.add_argument("translations_root_path", type=str, help="The path containing folders labeled by lang code (resoures/i18n)")
    parser.add_argument("translation_template_name", type=str, help="The .pot file that all extracted strings will be inserted into")
    args = parser.parse_args()

    extract_strings_from_project(Path(args.root_path), Path(args.translations_root_path), args.translation_template_name)
