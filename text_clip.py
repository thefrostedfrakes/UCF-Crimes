import torch
import clip
import builtins
from typing import Union

Number = Union[builtins.int, builtins.float, builtins.bool]

def calculate_text_clip_score(query: str, text: str) -> Number:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)
    query_inputs = clip.tokenize([query]).to(device)
    text_inputs = clip.tokenize([text]).to(device)

    with torch.no_grad():
        query_features = model.encode_text(query_inputs)
        text_features = model.encode_text(text_inputs)

        query_features = query_features / query_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        similarity_score = (torch.matmul(query_features, text_features.T) * 100).item()

        print(f"{similarity_score:.2f}%")
        return similarity_score
