import os
from hashlib import sha256
from alive_progress import alive_bar
import torch
from com_worktwins_pipe.Pipe import Pipe  # Import the base Pipe class
from transformers import AutoTokenizer, AutoModel
import sys

sys.path.append('/home/golden/.local/lib/python3.10/site-packages')


class SemanticTreePipe(Pipe):
    """
    A Pipe subclass to generate a semantic tree from normalized paragraphs.
    """


    def __init__(self, name, output_dir, dependencies=None):
        super().__init__(name, output_dir, dependencies)
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"  # Alternative lightweight model
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
    
    def embed_text(self, text):
        """
        Generate embeddings for a given text using Hugging Face transformers.
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Mean pooling
            embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings
        

    def calculate_cosine_similarity(self,embedding1, embedding2):
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: Tensor of size [d] or [1, d].
            embedding2: Tensor of size [d] or [1, d].

        Returns:
            Cosine similarity as a scalar value.
        """
        embedding1 = torch.tensor(embedding1) if not torch.is_tensor(embedding1) else embedding1
        embedding2 = torch.tensor(embedding2) if not torch.is_tensor(embedding2) else embedding2

        # Ensure tensors have the same shape
        embedding1 = embedding1.view(1, -1)  # Reshape to [1, d] if necessary
        embedding2 = embedding2.view(1, -1)

        similarity = torch.nn.functional.cosine_similarity(embedding1, embedding2)
        return similarity.item()

    def run(self, input_data):
        """
        Generates a semantic tree using embeddings for paragraphs.
        """
        normalized_paragraphs = input_data.get("normalized_paragraphs", [])
        if not normalized_paragraphs:
            raise ValueError("Input data must contain 'normalized_paragraphs'.")

        semantic_tree = {}
        for para in normalized_paragraphs:
            para_text = para.get("text", "")
            if not para_text:
                continue

            # Example of semantic tree logic: embedding-based grouping
            embedding = self.embed_text(para_text)
            para_id = para["id"]

            semantic_tree[para_id] = {
                "id": para_id,
                "text": para_text,
                "embedding": embedding.tolist()  # Store embedding as list
            }

        return {"semantic_tree": semantic_tree}
    


    def generate_semantic_tree(self, normalized_paragraphs):
        """
        Generate a semantic tree from normalized paragraphs based on their semantic similarity.

        Args:
            normalized_paragraphs (list): List of dictionaries with normalized paragraphs.

        Returns:
            dict: A semantic tree structure with hierarchical relationships between paragraphs.
        """
        # Extract semantics and compute embeddings
        paragraph_embeddings = []
        for para in normalized_paragraphs:
            embedding = self.embedding_model.encode(para['semantics'], convert_to_tensor=True)
            paragraph_embeddings.append({
                "id": para["id"],
                "semantics": para["semantics"],
                "embedding": embedding,
                "keywords": para["keywords"],
                "text": para["text"],
            })

        # Create the semantic tree
        semantic_tree = {}
        with alive_bar(len(paragraph_embeddings), title="Building Semantic Tree") as bar:
            for para in paragraph_embeddings:
                para_id = para["id"]
                semantics = para["semantics"]
                embedding = para["embedding"]

                # Find the most similar existing node in the tree
                parent_id = None
                highest_similarity = 0.0
                for node_id, node in semantic_tree.items():
                    similarity = self.calculate_cosine_similarity(embedding, node["embedding"])
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        parent_id = node_id

                # Add as a child if a similar parent is found
                if parent_id and highest_similarity > 0.7:  # Similarity threshold
                    current_node = semantic_tree[parent_id]["children"]
                else:
                    current_node = semantic_tree

                # Create a new node
                node_id = sha256(semantics.encode()).hexdigest()[:8]
                current_node[node_id] = {
                    "id": node_id,
                    "semantics": semantics,
                    "keywords": para["keywords"],
                    "text": para["text"],
                    "children": {},
                    "embedding": embedding,  # Store embedding for further similarity checks
                }
                bar()

        # Remove embeddings before saving (to reduce size)
        def clean_tree(tree):
            for key, value in tree.items():
                value.pop("embedding", None)
                clean_tree(value["children"])

        clean_tree(semantic_tree)
        return semantic_tree