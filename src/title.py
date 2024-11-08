"""
Title Generation Agent - Generates paper title based on references and subject
"""

import os
import json
import re
from typing import List, Dict, Tuple
import yaml
from config import client, model_name

class TitleAgent:
    def __init__(self):
        """Initialize the Title Agent"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_file = os.path.join(current_dir, 'prompts.yaml')
        self.prompt = self._load_prompt(prompt_file)
        
        # 创建title输出目录
        self.output_dir = os.path.join(os.path.dirname(current_dir), 'title')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt template from YAML file"""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
                return prompt_data['title_prompt']
        except Exception as e:
            print(f"Error loading prompt file: {e}")
            return ""

    def _extract_content(self, file_content: str) -> Tuple[str, str]:
        """
        Extract subject and references from the file content
        Returns:
            Tuple[str, str]: (subject, references)
        """
        lines = file_content.split('\n')
        subject = ""
        references = []
        current_section = ""

        for line in lines:
            line = line.strip()
            if line == "Subjects:":
                current_section = "subjects"
            elif line == "References:":
                current_section = "references"
            elif line and current_section == "subjects" and line != "Subjects:":
                subject = line
            elif line and current_section == "references":
                if line.startswith('Title:'):
                    references.append(line[6:].strip())

        return subject, '\n'.join(references)


    def _read_reference_file(self, file_path: str) -> Dict:
        """Read and parse a single reference file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            subject, references = self._extract_content(content)
            return {
                'id': os.path.splitext(os.path.basename(file_path))[0],
                'subject': subject,
                'references': references
            }
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return {}

    def _verify_title_format(self, title: str) -> bool:
        """Verify if the title is in correct format: <title>text</title>"""
        pattern = r'^<title>.*</title>$'
        return bool(re.match(pattern, title.strip()))

    def _get_title_from_gpt(self, subject: str, references: str) -> str:
        """Get title suggestion from GPT"""
        try:
            formatted_prompt = self.prompt.format(
                subject=subject,
                references=references
            )
            messages = [{"role": "user", "content": formatted_prompt}]
            
            while True:  # 循环直到获得正确格式的响应
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7
                )
                title = response.choices[0].message.content.strip()
                
                if self._verify_title_format(title):
                    return title
                
                # 如果格式不正确，添加纠正提示并继续对话
                correction_message = (
                    "The response format is incorrect. Please wrap your title in <title> tags. "
                    "For example: <title>Your Title Here</title>"
                )
                
                messages.extend([
                    {"role": "assistant", "content": title},
                    {"role": "user", "content": correction_message}
                ])
                print(f"Incorrect format detected, requesting correction...")
                
        except Exception as e:
            print(f"Error getting GPT response: {e}")
            return ""

    def _save_title(self, paper_id: str, title: str):
        """Save title to individual JSON file"""
        output_file = os.path.join(self.output_dir, f'{paper_id}.json')
        result = {
            'paper_id': paper_id,
            'title': title
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    def process_folder(self) -> List[Dict[str, str]]:
        """Process all txt files in the test folder"""
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        test_folder = os.path.join(current_dir, 'test')
        
        results = []
        for file_name in os.listdir(test_folder):
            if file_name.endswith('.txt'):
                file_path = os.path.join(test_folder, file_name)
                ref_data = self._read_reference_file(file_path)
                
                if ref_data and ref_data.get('subject') and ref_data.get('references'):
                    title = self._get_title_from_gpt(ref_data['subject'], ref_data['references'])
                    result = {
                        'paper_id': ref_data['id'],
                        'title': title
                    }
                    results.append(result)
                    
                    # 保存单独的JSON文件
                    self._save_title(ref_data['id'], title)
                    
                    print(f"Generated title for {ref_data['id']}: {title}")
                else:
                    print(f"Warning: Missing subject or references for {file_path}")

        return results

def main():
    agent = TitleAgent()
    agent.process_folder()

if __name__ == "__main__":
    main()