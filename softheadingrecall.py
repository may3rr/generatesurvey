import os
import json
from typing import List, Dict, Tuple
import torch
from sentence_transformers import SentenceTransformer, util

# 配置
EMBEDDING_MODEL_PATH = 'BAAI/bge-large-en-v1.5'
EMBEDDING_MODEL_BATCH_SIZE = 32
EMBEDDING_MODEL_DEVICE = 'mps'

def extract_titles_from_outline(outline: List) -> List[str]:
    """从大纲中提取所有标题（包括子标题）"""
    titles = []
    for item in outline:
        if isinstance(item, str):
            titles.append(item)
        elif isinstance(item, list):
            titles.extend(item)
    return titles

def read_outlines(directory: str) -> Dict[str, List[str]]:
    """读取目录中的所有outline文件并提取标题"""
    print(f"\nReading outlines from directory: {directory}")
    outlines = {}
    if not os.path.exists(directory):
        print(f"Directory does not exist: {directory}")
        return outlines
        
    files = os.listdir(directory)
    print(f"Found {len(files)} files in directory")
    
    for filename in files:
        if filename.endswith('.json'):
            print(f"\nProcessing file: {filename}")
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    outline = json.load(f)
                    titles = extract_titles_from_outline(outline)
                    print(f"Extracted {len(titles)} titles from {filename}")
                    print("First few titles:", titles[:3])
                    outlines[filename] = titles
                except json.JSONDecodeError as e:
                    print(f"Error reading {filename}: {e}")
    return outlines

class Encoder:
    def __init__(
            self,
            path=EMBEDDING_MODEL_PATH,
            batch_size=EMBEDDING_MODEL_BATCH_SIZE,
            device=EMBEDDING_MODEL_DEVICE,
            show_progress_bar=True
    ):
        self.batch_size = batch_size
        self.show_progress_bar = show_progress_bar
        prompt = 'Represent this sentence for searching relevant passages: ' if 'bge' in path and 'en' in path else None
        print(f"\nInitializing encoder with model: {path}")
        print(f"Using device: {device}")
        self.model = SentenceTransformer(
            path,
            device=device,
            prompts={'query': prompt} if prompt else None,
            default_prompt_name='query'
        )

    def encode_docs(self, docs: list[str]):
        print(f"\nEncoding {len(docs)} documents")
        embeddings = self.model.encode(
            docs,
            batch_size=self.batch_size,
            show_progress_bar=self.show_progress_bar,
            prompt_name=None,
            normalize_embeddings=False
        )
        return embeddings

class SoftHeadingRecallEvaluator:
    def __init__(self):
        self.encoder = Encoder()

    def _card(self, titles: list[str]) -> float:
        embeddings = self.encoder.encode_docs(titles)
        similarities = util.cos_sim(embeddings, embeddings)
        count = 1 / torch.sum(similarities, dim=1)
        card = torch.sum(count).item()
        return card

    def evaluate(self, generated_titles: list[str], reference_titles: list[str]) -> float:
        print("\nEvaluating titles:")
        print(f"Number of generated titles: {len(generated_titles)}")
        print(f"Number of reference titles: {len(reference_titles)}")
        
        if not generated_titles or not reference_titles:
            print("Warning: Empty title list detected")
            return 0.
            
        union_titles = list(set(generated_titles).union(reference_titles))
        print(f"Number of unique titles in union: {len(union_titles)}")
        
        card_g = self._card(generated_titles)
        card_r = self._card(reference_titles)
        card_union = self._card(union_titles)
        
        print(f"Card_g: {card_g:.4f}")
        print(f"Card_r: {card_r:.4f}")
        print(f"Card_union: {card_union:.4f}")
        
        score = (card_r + card_g - card_union) / card_r
        return score

def compare_outlines(source_dir: str, reference_dir: str) -> Dict[str, float]:
    """比较两个目录中对应的outline文件"""
    print("\nStarting outline comparison")
    evaluator = SoftHeadingRecallEvaluator()
    
    print("\nReading source outlines")
    source_outlines = read_outlines(source_dir)
    print(f"Found {len(source_outlines)} source outlines")
    
    print("\nReading reference outlines")
    reference_outlines = read_outlines(reference_dir)
    print(f"Found {len(reference_outlines)} reference outlines")
    
    results = {}
    for filename in source_outlines:
        print(f"\nProcessing file: {filename}")
        if filename in reference_outlines:
            score = evaluator.evaluate(
                source_outlines[filename],
                reference_outlines[filename]
            )
            results[filename] = score
            print(f"Score: {score:.4f}")
        else:
            print(f"No matching reference file found for {filename}")
    
    return results

def main():
    print("Starting evaluation process...")
    
    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Current directory: {current_dir}")
    
    # 定义源目录和参考目录
    source_dir = os.path.join(current_dir, "outline")
    reference_dir = os.path.join(current_dir, "sourceoutline")
    
    print(f"\nSource directory: {source_dir}")
    print(f"Reference directory: {reference_dir}")
    
    # 检查目录是否存在
    if not os.path.exists(source_dir):
        print(f"Error: Source directory does not exist: {source_dir}")
        return
    if not os.path.exists(reference_dir):
        print(f"Error: Reference directory does not exist: {reference_dir}")
        return
    
    # 比较outlines
    results = compare_outlines(source_dir, reference_dir)
    
    # 输出结果
    print("\nEvaluation Results:")
    print("-" * 50)
    if results:
        for filename, score in results.items():
            print(f"{filename}: {score:.4f}")
        
        # 计算平均分
        average_score = sum(results.values()) / len(results)
        print("-" * 50)
        print(f"Average Score: {average_score:.4f}")
    else:
        print("No results generated. Please check if the input directories contain matching files.")

if __name__ == "__main__":
    main()