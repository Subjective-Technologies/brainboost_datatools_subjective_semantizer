from com_worktwins_languages.Language import Language


# Usage example:
if __name__ == "__main__":
    language_file = 'com_worktwins_data/languages.yml'  # Path to your YAML file
    lang = Language(language_file)

    # Find language by name
    language_name = 'C++'
    attributes = lang.get_language_attributes(language_name)
    if attributes:
        print(f"Attributes for {language_name}:")
        for key, value in attributes.items():
            print(f"{key}: {value}")

    # Find languages by file extension
    extension = '.py'
    languages_by_extension = lang.find_by_extension(extension)
    print(f"Languages with extension '{extension}': {languages_by_extension}")

    # Find languages by alias
    alias = 'python3'
    languages_by_alias = lang.find_by_alias(alias)
    print(f"Languages with alias '{alias}': {languages_by_alias}")

    # Find languages by interpreter
    interpreter = 'python3'
    languages_by_interpreter = lang.find_by_interpreter(interpreter)
    print(f"Languages with interpreter '{interpreter}': {languages_by_interpreter}")