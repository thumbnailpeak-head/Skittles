from sentence_transformers import SentenceTransformer


# Load a pre-trained model for sentence embeddings
# 384 * 1 array
model = SentenceTransformer('all-MiniLM-L6-v2')


def get_embedding(sentences):
    return model.encode(sentences)


# Example sentences
sentences = [
    "This is an example sentence for embedding.",
    "Another sentence that we want to encode.",
    "Sentence embeddings are useful for text similarity."
]

# Generate embeddings for the sentences
embeddings = get_embedding(sentences)

# Print the shape of the embeddings for each sentence
print("Embedding shape:", embeddings.shape)

# Display the embedding for each sentence
for i, sentence in enumerate(sentences):
    print(f"Sentence: {sentence}")
    print(f"Embedding: {embeddings[i]}")
    print()
