# Pipe.py

import os
import json

class Pipe:
    """
    Base class for processing steps (pipes) in the pipeline.
    """
    def __init__(self, name, output_dir, pdf_name, dependencies=None):
        """
        Initializes the Pipe.

        Args:
            name (str): The name of the pipe (e.g., 'WordFrequencies').
            output_dir (str): The directory where output files will be saved.
            pdf_name (str): The base name of the PDF being processed.
            dependencies (list, optional): List of dependent Pipe instances.
        """
        self.name = name
        self.output_dir = output_dir
        self.pdf_name = pdf_name
        self.dependencies = dependencies or []  # List of dependent pipes
        self.output_file = os.path.join(
            output_dir, f"{self.pdf_name}-{self.name}.json"
        )

    def execute(self, input_data=None):
        """
        Executes the pipe, ensuring dependencies are resolved first.

        Args:
            input_data: The input data for the pipe.

        Returns:
            dict: The output data from the pipe.
        """
        # Execute dependencies first
        for dependency in self.dependencies:
            dependency.execute()

        # Run the current pipe
        if not os.path.exists(self.output_file):  # Skip if already executed
            print(f"Executing pipe: {self.name}")
            output_data = self.run(input_data)
            self.save_output(output_data)
        else:
            print(f"Skipping pipe {self.name}; output already exists.")

        # Load and return the output data
        return self.load_output()

    def run(self, input_data):
        """
        Logic for the pipe. Must be implemented by child classes.

        Args:
            input_data: The input data for processing.

        Raises:
            NotImplementedError: If not implemented in child class.
        """
        raise NotImplementedError("The run method must be implemented by child classes.")

    def save_output(self, data):
        """
        Saves the output data to a JSON file.

        Args:
            data (dict): The data to save.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load_output(self):
        """
        Loads the output data from the JSON file.

        Returns:
            dict: The loaded data.
        """
        with open(self.output_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_to_txt(self, data, output_path):
        """
        Saves data to a text file.

        Args:
            data (str): The data to save.
            output_path (str): The path to the output text file.
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(data)
