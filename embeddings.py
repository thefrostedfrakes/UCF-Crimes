'''
Functions to help search for cases
Uses OpenAI to compare case title against existing embeddings

Maverick Reynolds
08.24.2023
'''

import openai
import numpy as np


def get_embedding(text: str, model='text-embedding-ada-002'):
    text = text.replace("\n", " ")
    return openai.Embedding.create(input = [text], model=model)['data'][0]['embedding']


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search_incident_titles(df, query, embeddings_dict, n=5):
    '''
    Function to search for similar incident titles using natural language
    Uses the embeddings dictionary and OpenAI Embeddings with cosine similarity
    '''
    embedding = get_embedding(query)
 
    # Apply similarity to all embeddings
    df['similarity'] = df['case_id'].apply(lambda x: cosine_similarity(embedding, embeddings_dict[x]))
 
    # Return the top n results
    return df.sort_values(by='similarity', ascending=False).head(n).drop('similarity', axis=1)

