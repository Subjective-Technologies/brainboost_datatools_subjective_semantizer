import os
import json

class Pipe:
    """
    Base class for processing steps (pipes) in the pipeline.
    """
    def __init__(self, name, output_dir, dependencies=None):
        self.name = name
        self.output_dir = output_dir
        self.dependencies = dependencies or []  # List of dependent pipes
        self.output_file = os.path.join(output_dir, f"{self.name}.json")

    def execute(self, input_data=None):
        """
        Executes the pipe, ensuring dependencies are resolved first.
        """
        # Execute dependencies first
        for dependency in self.dependencies:
            dependency.execute(input_data)

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
        """
        raise NotImplementedError("The run method must be implemented by child classes.")

    def save_output(self, data):
        """
        Saves the output data to a JSON file.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.output_file, "w") as f:
            json.dump(data, f, indent=4)

    def load_output(self):
        """
        Loads the output data from the JSON file.
        """
        with open(self.output_file, "r") as f:
            return json.load(f)

    def save_to_txt(self,data, output_path):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(data)