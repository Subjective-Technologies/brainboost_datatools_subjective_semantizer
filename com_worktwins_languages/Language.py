import ast
import json
import pandas as pd
import re
from pygments.lexers import guess_lexer, ClassNotFound


class Language:
    @staticmethod
    def load_json_to_dataframe(json_file):
        """
        Load the JSON file into a Pandas DataFrame.
        """
        with open(json_file, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
                # Convert nested dictionaries to DataFrame
                df = pd.DataFrame.from_dict(data, orient='index')
                # Reset index to have 'name' as a column
                df.reset_index(inplace=True)
                df.rename(columns={'index': 'name'}, inplace=True)
                return df
            except json.JSONDecodeError as e:
                print(f"Error loading JSON file: {e}")
                return pd.DataFrame()

    @staticmethod
    def get_language_attributes(df, language_name):
        """
        Get attributes of a language by its name.
        """
        result = df[df['name'].str.lower() == language_name.lower()]
        if not result.empty:
            return result.to_dict(orient='records')[0]
        else:
            print(f"Language '{language_name}' not found.")
            return None

    @staticmethod
    def find_by_extension(df, extension):
        """
        Find languages by file extension.
        """
        if not extension.startswith('.'):
            extension = f'.{extension}'
        result = df[df['extensions'].apply(lambda x: extension in x if isinstance(x, list) else False)]
        return result['name'].tolist()

    @staticmethod
    def find_by_alias(df, alias):
        """
        Find languages by their aliases.
        """
        result = df[df['aliases'].apply(lambda x: alias.lower() in [a.lower() for a in x] if isinstance(x, list) else False)]
        return result['name'].tolist()

    @staticmethod
    def find_by_interpreter(df, interpreter):
        """
        Find languages by their interpreters.
        """
        result = df[df['interpreters'].apply(lambda x: interpreter.lower() in [i.lower() for i in x] if isinstance(x, list) else False)]
        return result['name'].tolist()

    @staticmethod
    def detect_programming_language(code_block):
        """
        Guess the programming language from a code block using Pygments.
        """
        try:
            lexer = guess_lexer(code_block)
            return lexer.name.lower()  # Return the detected language name in lowercase
        except ClassNotFound:
            return "unknown"  # If Pygments cannot determine the language, return "unknown"

    @staticmethod
    def code_to_ast_json(code):
        """
        Convert Python code to its AST and return as a JSON-compatible dictionary.
        """
        try:
            tree = ast.parse(code)
            return Language.ast_to_dict(tree)
        except SyntaxError as e:
            print(f"Syntax error in code block: {e}")
            return {}

    @staticmethod
    def ast_to_dict(node):
        """
        Convert an AST node to a dictionary recursively.
        """
        if isinstance(node, ast.AST):
            return {key: Language.ast_to_dict(value) for key, value in ast.iter_fields(node)}
        elif isinstance(node, list):
            return [Language.ast_to_dict(item) for item in node]
        else:
            return node

    @staticmethod
    def load_languages(file_path='com_worktwins_data/languages.json'):
        """
        Load programming languages data from a JSON file.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)