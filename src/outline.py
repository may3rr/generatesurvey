"""
Outline Generation Agent - Generates survey paper outline based on references
"""

import os
import json
import re
from typing import List, Dict, Tuple
import yaml
from config import client, model_name

class OutlineAgent:
    def __init__(self):
        """Initialize the Outline Agent"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_file = os.path.join(current_dir, 'prompts.yaml')
        self.prompt = self._load_prompt(prompt_file)
        
        # 创建outline输出目录
        self.output_dir = os.path.join(os.path.dirname(current_dir), 'outline')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt template from YAML file"""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
                if 'outline_prompt' not in prompt_data:
                    print(f"Warning: 'outline_prompt' not found in {prompt_file}")
                    return self._get_default_prompt()
                return prompt_data['outline_prompt']
        except Exception as e:
            print(f"Error loading prompt file: {e}")
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Return default prompt if YAML loading fails"""
        return """
Based on the following paper's subject and references, generate a clear and logical outline of first-level section headings for a comprehensive survey paper.

Subject: {subject}
References: {references}

Requirements:
1. Generate 6-10 first-level section headings
2. Don't include Introduction and Conclusion in the count
3. Each heading should be concise and academically appropriate
4. Focus on organizing topics logically and coherently
5. Ensure comprehensive coverage of the research area
6. Don't use bullet points or numbers

Format your response as follows:
<outline>
Introduction
[Your 6-10 section headings here, one per line]
Conclusion
</outline>
"""

    def _extract_content(self, file_content: str) -> Tuple[str, str]:
        """Extract subject and references from the file content"""
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
                elif line.startswith('Abstract:'):
                    references[-1] += f"\nAbstract: {line[9:].strip()}"

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

    def _verify_outline_format(self, outline: str) -> bool:
        """Verify if the outline format is acceptable"""
        content = outline.strip()
        # 输出包含6-10个section就可以了
        sections = [s.strip() for s in content.split('\n') if s.strip()]
        return 6 <= len(sections) <= 10

    def _get_outline_from_gpt(self, subject: str, references: str) -> str:
        """Get outline suggestion from GPT"""
        try:
            formatted_prompt = self.prompt.format(
                subject=subject,
                references=references
            )
            messages = [{"role": "user", "content": formatted_prompt}]
            
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7
            )
            outline = response.choices[0].message.content.strip()

            # 简单提取section列表
            sections = [s.strip() for s in outline.split('\n') if s.strip()]
            if not (6 <= len(sections) <= 10):
                correction_message = (
                    "Please provide between 6 and 10 sections (excluding Introduction and Conclusion). "
                    "Each section should be on a new line."
                )
                messages.extend([
                    {"role": "assistant", "content": outline},
                    {"role": "user", "content": correction_message}
                ])
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7
                )
                outline = response.choices[0].message.content.strip()
                
            return outline
                
        except Exception as e:
            print(f"Error getting GPT response: {e}")
            return ""

    def _save_outline(self, paper_id: str, outline: str):
        """Save outline to individual JSON file"""
        output_file = os.path.join(self.output_dir, f'{paper_id}.json')
        
        # Extract sections from the outline
        sections = [s.strip() for s in outline.split('\n') if s.strip()]
        
        result = {
            'paper_id': paper_id,
            'sections': sections
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    def process_folder(self) -> List[Dict[str, List[str]]]:
        """Process all txt files in the test folder"""
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        test_folder = os.path.join(current_dir, 'test')
        
        results = []
        for file_name in os.listdir(test_folder):
            if file_name.endswith('.txt'):
                file_path = os.path.join(test_folder, file_name)
                ref_data = self._read_reference_file(file_path)
                
                if ref_data and ref_data.get('subject') and ref_data.get('references'):
                    print(f"\nProcessing {ref_data['id']}...")
                    outline = self._get_outline_from_gpt(ref_data['subject'], ref_data['references'])
                    
                    # Extract sections
                    sections = [s.strip() for s in outline.split('\n') if s.strip()]
                    
                    result = {
                        'paper_id': ref_data['id'],
                        'sections': sections
                    }
                    results.append(result)
                    
                    # 保存单独的JSON文件
                    self._save_outline(ref_data['id'], outline)
                    
                    print(f"Generated outline for {ref_data['id']}:")
                    for section in sections:
                        print(f"  {section}")
                else:
                    print(f"Warning: Missing subject or references for {file_path}")

        return results

def main():
    agent = OutlineAgent()
    agent.process_folder()

if __name__ == "__main__":
    main()