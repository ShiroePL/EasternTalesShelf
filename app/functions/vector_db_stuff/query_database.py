# Imports and setup
import os
import numpy as np
import itertools
from typing import List
import voyageai
from pinecone import Pinecone, ServerlessSpec
from transformers import AutoTokenizer
from rank_bm25 import BM25Okapi  # BM25 library for lexical matching
from app.functions.sqlalchemy_fns import fetch_all_records
from app.functions.vector_db_stuff.ai_related.groq_service import send_to_groq

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENV = "us-east-1"  # change to your Pinecone environment if different

# Initialize VoyageAI, Pinecone, and Hugging Face tokenizer
vc = voyageai.Client(api_key=VOYAGE_API_KEY)
tokenizer = AutoTokenizer.from_pretrained('voyageai/voyage-3')
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "eastern-tales-shelf-test2-smaller-chunks"
index = pc.Index(index_name)

# Step 1: Search the indexed vectors using a query
def search_query(index, query: str, top_k=3):
    # Embed the query for semantic similarity search
    query_embedding = vc.embed(
        texts=[query],
        model='voyage-3',
        input_type="query",
        truncation=True
    ).embeddings[0]

    # Perform similarity search using Pinecone
    result = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)

    # Collect IDs and metadata from the top-k most similar results
    top_ids = [match['id'] for match in result['matches']]
    print("Top-k most similar document IDs from Pinecone:", top_ids)

    # Fetch the original documents from Pinecone using the IDs
    fetched_data = index.fetch(ids=top_ids)
    vectors = fetched_data['vectors']

    # Extract text from fetched vectors
    retrieved_texts = [vectors[vector_id]['metadata']['text'] for vector_id in vectors]

    return retrieved_texts

# Step 2: Use BM25 to further refine the retrieved chunks for exact matches
def refine_with_bm25(query: str, retrieved_texts: List[str], top_k=3) -> List[str]:
    # Tokenize texts for BM25 processing
    tokenized_texts = [text.split() for text in retrieved_texts]
    bm25 = BM25Okapi(tokenized_texts)

    # Perform BM25 search to refine the initial results
    bm25_scores = bm25.get_scores(query.split())
    top_indices = np.argsort(bm25_scores)[-top_k:][::-1]

    # Retrieve top-k texts based on BM25 scores
    refined_texts = [retrieved_texts[idx] for idx in top_indices]
    print("Refined top-k most similar documents using BM25:")
    for idx, text in zip(top_indices, refined_texts):
        print(f"BM25 Score: {bm25_scores[idx]:.2f}, Text: {text[:100]}...")

    return refined_texts






# Step 3: Main function to execute the search and fetch process
def main():
    # Set a query string (modify this for testing different questions)
    question = "what titles are completed on list?"

    # Step 1: Search Pinecone index for top-k results based on semantic similarity
    retrieved_texts = search_query(index, question, top_k=5)

    # Step 2: Use BM25 to refine the retrieved texts and get final top-k results
    refined_texts = refine_with_bm25(question, retrieved_texts, top_k=5)

    # Display the final top-k refined chunks
    print("\nFinal top-k retrieved documents:")
    for text in refined_texts:
        print(f"{text}")


    # Step 3: ask ai to answer the question
    
    response, prompt_tokens, completion_tokens, total_tokens = send_to_groq(retrieved_texts, question)
    print(f"total tokens count: {total_tokens}, prompt: {prompt_tokens}, completion: {completion_tokens}")
    print(f"final response from ai: {response}")
if __name__ == "__main__":
    main()
