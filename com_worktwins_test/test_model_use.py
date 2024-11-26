import pytest
from transformers import AutoModelForCausalLM, AutoTokenizer

@pytest.fixture
def model_path():
    """Path to the converted Hugging Face model."""
    return "/home/golden/.llama/checkpoints/Llama3.2-3B-Instruct-HF"

def test_model_load(model_path):
    """
    Test if the LLaMA model and tokenizer load correctly.
    """
    try:
        model = AutoModelForCausalLM.from_pretrained(model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        assert model is not None, "Model failed to load"
        assert tokenizer is not None, "Tokenizer failed to load"
        print("Model and tokenizer loaded successfully!")
    except Exception as e:
        pytest.fail(f"Failed to load model or tokenizer: {e}")

def test_inference(model_path):
    """
    Test if the LLaMA model can generate text given a simple prompt.
    """
    try:
        model = AutoModelForCausalLM.from_pretrained(model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        # Sample input prompt
        prompt = "Explain the importance of version control in software development."

        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt")

        # Generate output
        outputs = model.generate(**inputs, max_length=50)
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        assert len(generated_text) > 0, "Model failed to generate output"
        print(f"Generated Text: {generated_text}")
    except Exception as e:
        pytest.fail(f"Model inference failed: {e}")
