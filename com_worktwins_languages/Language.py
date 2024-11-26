import yaml
import pandas as pd

class Language:
    def __init__(self, yaml_file):
        self.yaml_file = yaml_file
        self.df = self._load_yaml_to_dataframe()

    def _load_yaml_to_dataframe(self):
        with open(self.yaml_file, 'r', encoding='utf-8') as file:
            try:
                data = yaml.safe_load(file)
                # Convert nested dictionaries to DataFrame
                df = pd.DataFrame.from_dict(data, orient='index')
                # Reset index to have 'name' as a column
                df.reset_index(inplace=True)
                df.rename(columns={'index': 'name'}, inplace=True)
                return df
            except yaml.YAMLError as e:
                print(f"Error loading YAML file: {e}")
                return pd.DataFrame()

    def get_language_attributes(self, language_name):
        result = self.df[self.df['name'].str.lower() == language_name.lower()]
        if not result.empty:
            return result.to_dict(orient='records')[0]
        else:
            print(f"Language '{language_name}' not found.")
            return None

    def find_by_extension(self, extension):
        if not extension.startswith('.'):
            extension = f'.{extension}'
        result = self.df[self.df['extensions'].apply(lambda x: extension in x if isinstance(x, list) else False)]
        return result['name'].tolist()

    def find_by_alias(self, alias):
        result = self.df[self.df['aliases'].apply(lambda x: alias.lower() in [a.lower() for a in x] if isinstance(x, list) else False)]
        return result['name'].tolist()

    def find_by_interpreter(self, interpreter):
        result = self.df[self.df['interpreters'].apply(lambda x: interpreter.lower() in [i.lower() for i in x] if isinstance(x, list) else False)]
        return result['name'].tolist()
