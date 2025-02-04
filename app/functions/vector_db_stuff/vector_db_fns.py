# Imports and setup
import os
import itertools
from typing import List
import voyageai
from pinecone import Pinecone, ServerlessSpec
from transformers import AutoTokenizer
from app.functions.sqlalchemy_fns import fetch_all_records

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENV = "us-east-1"  # change to your Pinecone environment if different

# Initialize VoyageAI and Hugging Face tokenizer
vc = voyageai.Client(api_key=VOYAGE_API_KEY)
tokenizer = AutoTokenizer.from_pretrained('voyageai/voyage-3')

# Step 1: Fetch all records from MariaDB
# its in sqlalchemy_fns file

# Step 2: Generate combined text for each record
def generate_combined_text(record):
    combined_text = f"""
    Titles: English - {record.title_english}, Romaji - {record.title_romaji}
    URLs: Anilist - {record.anilist_url}, MAL - {record.mal_url}, Bato - {record.bato_link}
    Status: On List - {record.on_list_status}, Media Status - {record.status}, User Progress: Started - {record.user_startedAt}, Completed - {record.user_completedAt}
    Format: {record.media_format}, Origin: {record.country_of_origin}
    Volumes/Chapters: Total - {record.all_volumes} volumes, {record.all_chapters} chapters; User Progress - {record.volumes_progress} volumes, {record.chapters_progress} chapters
    Score: User - {record.score}, Reread Times - {record.reread_times}, Favourite - {bool(record.is_favourite)}
    Dates: Start Date - {record.media_start_date}, End Date - {record.media_end_date}, Last Updated - {record.last_updated_on_site}, Entry Created At (Anilist site list) - {record.entry_createdAt}
    Additional Information: Genres - {record.genres}, Description - {record.description}, Notes - {record.notes}, External Links - {record.external_links}
    """
    return combined_text

# Step 3: Tokenize and chunk the data
def record_to_chunks(record, chunk_size=150, chunk_overlap=50) -> List[dict]:
    chunks = []
    chunk_number = 1

    # Generate the combined text for the record
    combined_text = generate_combined_text(record)

    # Tokenize the text using Hugging Face tokenizer
    tokenized = tokenizer.tokenize(combined_text)
    
    # Count tokens and print the count
    total_tokens = len(tokenizer.encode(combined_text))
    print(f"Record Title: {record.title_english} - Total Tokens: {total_tokens}")

    start_idx = 0

    # Split the tokenized text into chunks based on the chunk size
    while start_idx < len(tokenized):
        end_idx = min(start_idx + chunk_size, len(tokenized))
        
        # Create chunk with injected title for context
        chunk_title = f"Title: {record.title_english} - "
        chunk_content = tokenizer.convert_tokens_to_string(tokenized[start_idx:end_idx])
        chunk = f"{chunk_title}{chunk_content}"

        chunk_id = f"{record.title_english}:chunk{chunk_number}"
        chunks.append({"id": chunk_id, "text": chunk})

        # Move to the next chunk with overlap
        start_idx += chunk_size - chunk_overlap
        chunk_number += 1

    return chunks

# Step 4: Generate embeddings for each chunk using Voyage AI
def generate_embeddings(chunks: List[dict]) -> List[dict]:
    batch_size = 128  # Set a batch size according to your Voyage AI restrictions
    embeds = []
    num_chunks = len(chunks)

    for i in range(0, num_chunks, batch_size):
        batch = chunks[i:i + batch_size]
        texts = [chunk["text"] for chunk in batch]

        embeddings = vc.embed(
            texts=texts,
            model='voyage-3',
            input_type='document',
            truncation=True
        ).embeddings

        # Adding embeddings to chunks
        for chunk, embedding in zip(batch, embeddings):
            embeds.append({"id": chunk["id"], "embedding": embedding, "text": chunk["text"]})
    
    return embeds

# Step 5: Initialize Pinecone and index the embeddings
def initialize_pinecone():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index_name = "eastern-tales-shelf-test2-smaller-chunks"
    
    if index_name not in pc.list_indexes():
        pc.create_index(
            name=index_name,
            dimension=1024,  # Embedding dimension from Voyage AI
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            ),
            deletion_protection="disabled"
        )
    return pc.Index(index_name)

def index_embeddings(index, embeddings: List[dict]):
    to_upsert = [(embed["id"], embed["embedding"], {"text": embed["text"]}) for embed in embeddings]

    # Helper function to create batches
    def chunks(iterable, batch_size=200):
        it = iter(iterable)
        chunk = tuple(itertools.islice(it, batch_size))
        while chunk:
            yield chunk
            chunk = tuple(itertools.islice(it, batch_size))
    
    # Upsert data in batches
    for ids_vectors_chunk in chunks(to_upsert, batch_size=200):
        index.upsert(vectors=ids_vectors_chunk)

# Main execution
def main():
    all_records = fetch_all_records()
    
    # Limit the number of records to process
    limit = 5  # Adjust this variable to control how many records to fetch
    limited_records = all_records[:limit]
    
    all_chunks = []
    
    for record in limited_records:
        record_chunks = record_to_chunks(record)
        all_chunks.extend(record_chunks)
    
    # Generate embeddings
    chunk_embeddings = generate_embeddings(all_chunks)
    
    # Initialize Pinecone and index
    index = initialize_pinecone()
    index_embeddings(index, chunk_embeddings)

if __name__ == "__main__":
    main()
