"""
Abstract Generation Agent - Generates paper abstract based on title and outline
"""

import os
import json
import re
from typing import List, Dict, Tuple
import yaml
from config import client, model_name

class AbstractAgent:
    def __init__(self):
        """Initialize the Abstract Agent"""
        print("Initializing AbstractAgent...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_file = os.path.join(current_dir, 'prompts.yaml')
        print(f"Loading prompt from: {prompt_file}")
        self.prompt = self._load_prompt(prompt_file)
        
        # 创建abstract输出目录
        self.output_dir = os.path.join(os.path.dirname(current_dir), 'abstract')
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")

    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt template from YAML file"""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
                if 'abstract_prompt' not in prompt_data:
                    raise KeyError("'abstract_prompt' not found in YAML file")
                print("Prompt loaded successfully")
                return prompt_data['abstract_prompt']
        except Exception as e:
            print(f"Error: Failed to load abstract_prompt from {prompt_file}")
            print(f"Detailed error: {str(e)}")
            raise

    def _read_subject_from_test(self, paper_id: str) -> str:
        """Read subject from test file"""
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            test_file = os.path.join(current_dir, 'test', f'{paper_id}.txt')
            
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for line in content.split('\n'):
                if line.strip() and line.strip() != "Subjects:":
                    if not line.startswith(('References:', 'Number:', 'Title:', 'Abstract:')):
                        return line.strip()
            return ""
        except Exception as e:
            print(f"Error reading subject: {e}")
            return ""

    def _read_title_from_file(self, paper_id: str) -> str:
        """Read title from title directory"""
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            title_file = os.path.join(current_dir, 'title', f'{paper_id}.json')
            
            with open(title_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                title = data.get('title', '')
                # Remove tags if present
                title = re.sub(r'<title>|</title>', '', title)
                return title.strip()
        except Exception as e:
            print(f"Error reading title: {e}")
            return ""

    def _read_outline_from_file(self, paper_id: str) -> List[str]:
        """Read outline from outline directory"""
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            outline_file = os.path.join(current_dir, 'outline', f'{paper_id}.json')
            
            with open(outline_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('sections', [])
        except Exception as e:
            print(f"Error reading outline: {e}")
            return []

    def _verify_abstract_format(self, abstract: str) -> bool:
        """Verify if the abstract is in correct format and length"""
        if not (abstract.startswith('<abstract>') and abstract.endswith('</abstract>')):
            print("Abstract format verification failed: Missing tags")
            return False
            
        # Remove tags and count words
        content = re.sub(r'<abstract>|</abstract>', '', abstract).strip()
        word_count = len(content.split())
        
        if not (200 <= word_count <= 500):
            print(f"Abstract format verification failed: Word count {word_count} not in range [200, 500]")
            return False
            
        print("Abstract format verification passed")
        return True

    def _get_abstract_from_gpt(self, subject: str, title: str, outline: List[str]) -> str:
        """Get abstract suggestion from GPT"""
        try:
            print("\nGenerating abstract using GPT...")
            outline_text = '\n'.join(outline)
            formatted_prompt = self.prompt.format(
                subject=subject,
                title=title,
                outline=outline_text
            )
            messages = [{"role": "user", "content": formatted_prompt}]
            
            while True:  # 循环直到获得正确格式的响应
                print("Sending request to GPT...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000  # Ensure enough tokens for abstract
                )
                abstract = response.choices[0].message.content.strip()
                print(f"Received response of length: {len(abstract)}")
                
                if self._verify_abstract_format(abstract):
                    return abstract
                
                # 如果格式不正确，添加纠正提示并继续对话
                correction_message = (
                    "Please format your response properly:\n"
                    "1. Wrap the abstract in <abstract> tags\n"
                    "2. Ensure length is between 200-500 words\n"
                    "3. Write as a single paragraph\n"
                    "4. Include only the abstract content"
                )
                
                messages.extend([
                    {"role": "assistant", "content": abstract},
                    {"role": "user", "content": correction_message}
                ])
                print("Incorrect format detected, requesting correction...")
                
        except Exception as e:
            print(f"Error getting GPT response: {e}")
            return ""

    def _save_abstract(self, paper_id: str, abstract: str):
        """Save abstract to individual JSON file"""
        output_file = os.path.join(self.output_dir, f'{paper_id}.json')
        result = {
            'paper_id': paper_id,
            'abstract': abstract
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Saved abstract to: {output_file}")

    def process_papers(self) -> List[Dict[str, str]]:
        """Process all papers that have both title and outline"""
        print("\nStarting abstract generation process...")
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        title_dir = os.path.join(current_dir, 'title')
        
        results = []
        for file_name in os.listdir(title_dir):
            if file_name.endswith('.json'):
                paper_id = os.path.splitext(file_name)[0]
                print(f"\nProcessing paper: {paper_id}")
                
                # Read necessary information
                subject = self._read_subject_from_test(paper_id)
                title = self._read_title_from_file(paper_id)
                outline = self._read_outline_from_file(paper_id)
                
                if subject and title and outline:
                    print(f"Found all required information for {paper_id}")
                    abstract = self._get_abstract_from_gpt(subject, title, outline)
                    
                    if abstract:
                        result = {
                            'paper_id': paper_id,
                            'abstract': abstract
                        }
                        results.append(result)
                        self._save_abstract(paper_id, abstract)
                        print(f"Generated abstract for {paper_id}")
                else:
                    print(f"Warning: Missing information for {paper_id}")
                    if not subject:
                        print("- Missing subject")
                    if not title:
                        print("- Missing title")
                    if not outline:
                        print("- Missing outline")
                
        return results

def main():
    agent = AbstractAgent()
    agent.process_papers()
    print("\nAbstract generation completed!")

if __name__ == "__main__":
    main()