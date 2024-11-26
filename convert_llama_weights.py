import torch
import os
import json
from transformers import LlamaConfig, LlamaForCausalLM

def convert_to_hf_format(input_dir, output_dir):
    # Load model parameters
    with open(os.path.join(input_dir, "params.json"), "r") as config_file:
        config_data = json.load(config_file)

    # Set up configuration
    config = LlamaConfig(
        vocab_size=config_data["vocab_size"],
        hidden_size=config_data["dim"],
        num_hidden_layers=config_data["n_layers"],
        num_attention_heads=config_data["n_heads"],
        intermediate_size=4 * config_data["dim"],
        max_position_embeddings=config_data.get("max_seq_len", 2048),  # Default to 2048 if not present
    )

    # Load weights
    weights_path = os.path.join(input_dir, "consolidated.00.pth")
    device_gpu = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device_cpu = torch.device("cpu")

    print(f"Loading weights. GPU: {device_gpu}, CPU: {device_cpu}...")
    state_dict = torch.load(weights_path, map_location=device_cpu)

    # Load the model structure
    model = LlamaForCausalLM(config)
    
    # Move parts to GPU as needed
    print("Loading model weights and transferring parts to GPU...")
    for name, param in state_dict.items():
        if param.numel() > 1e6:  # Large tensors to GPU
            state_dict[name] = param.to(device_gpu)
        else:  # Smaller tensors to CPU
            state_dict[name] = param.to(device_cpu)

    model.load_state_dict(state_dict, strict=False)

    # Save in Hugging Face format
    print(f"Saving converted model to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    model.save_pretrained(output_dir)

    # Save tokenizer
    tokenizer_path = os.path.join(input_dir, "tokenizer.model")
    os.symlink(tokenizer_path, os.path.join(output_dir, "tokenizer.model"))

    print(f"Model successfully converted and saved to {output_dir}")

if __name__ == "__main__":
    input_directory = "/home/golden/.llama/checkpoints/Llama3.2-3B-Instruct"
    output_directory = "/home/golden/.llama/checkpoints/Llama3.2-3B-Instruct-HF"
    convert_to_hf_format(input_directory, output_directory)
