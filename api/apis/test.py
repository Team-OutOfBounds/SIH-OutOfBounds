
# Core Python and OS modules
import os
from threading import Thread

# FastAPI and related modules
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Data and type handling
import pandas as pd
from pydantic import BaseModel
from typing import List

# Text processing and similarity
from fuzzywuzzy import process, fuzz

# PDF processing
from PyPDF2 import PdfReader

# Machine Learning and Transformers
import torch
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import silhouette_score
from transformers import TextIteratorStreamer, AutoTokenizer, AutoModel

# External library
from unsloth import FastLanguageModel

# Custom modules

# Paths
ner_data_path = "apis/resources/ner_data.csv"
pdf_directory = "apis/resources/03-09-24"
context_directory = "current_context"

# Initialize FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

df = pd.read_csv(ner_data_path)


# Configuration
embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
max_chunk_size = 100
max_seq_length = 2048
dtype = None  # None for auto detection. Float16 for Tesla T4, V100, Bfloat16 for Ampere+
load_in_4bit = True

# Paths
ner_data_path = "apis/resources/ner_data.csv"
pdf_directory = "apis/resources/03-09-24"
context_directory = "current_context"


class AIChatbot:
    def __init__(self):
        # Load the main language model
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name="unsloth/Llama-3.2-3B-Instruct",
            max_seq_length=max_seq_length,
            dtype=dtype,
            load_in_4bit=load_in_4bit
        )
        FastLanguageModel.for_inference(self.model)
        
        # Load the embedding model for semantic chunking
        self.embedding_tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
        self.embedding_model = AutoModel.from_pretrained(embedding_model_name)

    def encode_text(self, text):
        """Encode text into embeddings using a pre-trained model."""
        inputs = self.embedding_tokenizer(text, return_tensors='pt', truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.embedding_model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1).numpy()
        return embeddings
    
    def chunk_text(self, text):
        """Chunk the text into smaller pieces."""
        tokens = self.embedding_tokenizer.tokenize(text)
        token_chunks = [tokens[i:i + max_chunk_size] for i in range(0, len(tokens), max_chunk_size)]
        text_chunks = [self.embedding_tokenizer.convert_tokens_to_string(chunk) for chunk in token_chunks]
        return text_chunks
    
    def determine_optimal_clusters(self, embeddings, max_clusters=10):
        """Determine the optimal number of clusters."""
        distortions = []
        silhouette_scores = []
        K = range(2, max_clusters + 1)
        
        for k in K:
            kmeans = KMeans(n_clusters=k, n_init=10, random_state=0)
            kmeans.fit(embeddings)
            labels = kmeans.labels_
            distortions.append(kmeans.inertia_)
            if k > 1:
                silhouette_scores.append(silhouette_score(embeddings, labels))
        
        if silhouette_scores:
            optimal_clusters = K[1:][np.argmax(silhouette_scores)]
        else:
            optimal_clusters = K[0]
        
        return optimal_clusters
    
    def semantic_chunking(self, text):
        """Perform semantic chunking on the text using dynamic clustering."""
        chunks = self.chunk_text(text)
        embeddings = np.vstack([self.encode_text(chunk) for chunk in chunks])
        
        optimal_clusters = self.determine_optimal_clusters(embeddings)
        kmeans = KMeans(n_clusters=optimal_clusters, n_init=10, random_state=0)
        kmeans.fit(embeddings)
        labels = kmeans.labels_
        
        chunked_texts = {i: [] for i in range(optimal_clusters)}
        for i, label in enumerate(labels):
            chunked_texts[label].append(chunks[i])

        return chunked_texts, embeddings, chunks
    
    def retrieve_chunks(self, query, top_n=5):
        """Retrieve the most similar chunks based on a query."""
        query_embedding = self.encode_text(query)
        similarities = cosine_similarity(query_embedding, self.embeddings).flatten()
        top_indices = np.argsort(similarities)[-top_n:][::-1]
        retrieved_chunks = " ".join(self.chunks[index] for index in top_indices)
        return retrieved_chunks

    def process_text(self, file_path):
        """Read and process the input text from a file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            input_text = file.read()
        
        return self.semantic_chunking(input_text)
    
    def generate_response(self, question):
        """Generate a response to a given question."""
        context = self.retrieve_chunks(question)
        input_template = """
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>

            Cutting Knowledge Date: December 2023
            Today Date: 23 July 2024
            <|eot_id|><|start_header_id|>user<|end_header_id|>

            You are a helpful assistant that responds to the user based on the context provided, if the answer does not lie in the context, you will respond with that is not my area of expertise, I am a chatbot designed for Vidi-Lekhak, a platform to help users know and create legal documents.You will refer to Vidhi-Lekhak as "our" platform. You are the assistant for the vidhilekhak platform. If any document is mentioned by the user you will also give the steps to generate it.

            Context : {context}
            Question : {question}

            <|eot_id|><|start_header_id|>assistant<|end_header_id|>
        """
        input_text = input_template.format(context=context, question=question)
        inputs = self.tokenizer(input_text, return_tensors="pt")
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True)
        generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=256)
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        for new_text in streamer:
            yield new_text
        thread.join()

chatbot = AIChatbot()


@app.post("/ask/")
async def ask_question(request: Request):
    data = await request.json()
    uuid = data.get("uuid")
    question = data.get("question")

    # Load the NER data to get the file name
    ner_data = pd.read_csv(ner_data_path)
    file_row = ner_data[ner_data["uuid"] == uuid]

    if file_row.empty:
        return {"error": "Invalid UUID"}

    file_name = file_row.iloc[0]["file_name"]
    text_file_path = os.path.join(context_directory, f"{file_name}.txt")

    if not os.path.exists(text_file_path):
        pdf_file_path = os.path.join(pdf_directory, file_name)
        reader = PdfReader(pdf_file_path)
        text = "\n".join(page.extract_text() for page in reader.pages)
        with open(text_file_path, "w", encoding="utf-8") as text_file:
            text_file.write(text)
        chatbot.chunked_texts, chatbot.embeddings, chatbot.chunks = chatbot.semantic_chunking(text)

    return StreamingResponse(chatbot.generate_response(question), media_type="text/plain")