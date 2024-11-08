"""
Reference Selection Agent - Selects relevant references for each section
"""

import os
import json
import re
from typing import List, Dict, Tuple
import yaml
from config import client, model_name

class ReferenceSelectionAgent:
    def __init__(self):
        """Initialize the Reference Selection Agent"""
        print("Initializing ReferenceSelectionAgent...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_file = os.path.join(current_dir, 'prompts.yaml')
        print(f"Loading prompt from: {prompt_file}")
        self.prompt = self._load_prompt(prompt_file)
        
        # 创建reference_selection输出目录
        self.output_dir = os.path.join(os.path.dirname(current_dir), 'references')
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")

    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt template from YAML file"""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
                if 'reference_selection_prompt' not in prompt_data:
                    raise KeyError("'reference_selection_prompt' not found in YAML file")
                print("Prompt loaded successfully")
                return prompt_data['reference_selection_prompt']
        except Exception as e:
            print(f"Error loading prompt file: {e}")
            raise

    def _read_paper_info(self, paper_id: str) -> Dict:
        """Read all necessary information for a paper"""
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Read subject and references
            test_file = os.path.join(current_dir, 'test', f'{paper_id}.txt')
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            subject = ""
            references = []
            current_section = ""
            
            for line in content.split('\n'):
                line = line.strip()
                if line == "Subjects:":
                    current_section = "subjects"
                elif line == "References:":
                    current_section = "references"
                elif line and current_section == "subjects" and line != "Subjects:":
                    if not line.startswith(('References:', 'Number:', 'Title:', 'Abstract:')):
                        subject = line
                elif line and current_section == "references":
                    if line.startswith('Title:'):
                        references.append(line[6:].strip())
            
            # Read title
            title_file = os.path.join(current_dir, 'title', f'{paper_id}.json')
            with open(title_file, 'r', encoding='utf-8') as f:
                title_data = json.load(f)
                title = re.sub(r'<title>|</title>', '', title_data.get('title', '')).strip()
            
            # Read outline and clean it
            outline_file = os.path.join(current_dir, 'outline', f'{paper_id}.json')
            with open(outline_file, 'r', encoding='utf-8') as f:
                outline_data = json.load(f)
                # 清理大纲，移除标签和非章节内容
                sections = outline_data.get('sections', [])
                cleaned_sections = []
                for section in sections:
                    if not (section.startswith('<outline>') or 
                           section.startswith('</outline>') or
                           section == ""):
                        cleaned_sections.append(section)
            
            return {
                'subject': subject,
                'title': title,
                'outline': cleaned_sections,
                'references': '\n'.join(references)
            }
        except Exception as e:
            print(f"Error reading paper info: {e}")
            return {}

    def _verify_refs_format(self, refs: str) -> bool:
        """Verify if the references are in correct format"""
        if not (refs.startswith('<refs>') and refs.endswith('</refs>')):
            print("References format verification failed: Missing tags")
            return False
            
        content = refs[6:-7].strip()  # Remove tags
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Check if each line starts with * and contains [number]
        for line in lines:
            if not (line.startswith('*') and re.search(r'\[\d+\]', line)):
                print(f"References format verification failed: Invalid line format: {line}")
                return False
        
        print("References format verification passed")
        return True

    def _get_refs_for_section(self, paper_info: Dict, section: str) -> str:
        """Get reference selection from GPT for a specific section"""
        try:
            print(f"\nSelecting references for section: {section}")
            formatted_prompt = self.prompt.format(
                subject=paper_info['subject'],
                title=paper_info['title'],
                outline='\n'.join(paper_info['outline']),
                section=section,
                references=paper_info['references']
            )
            messages = [{"role": "user", "content": formatted_prompt}]
            
            while True:  # 循环直到获得正确格式的响应
                print("Sending request to GPT...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7
                )
                refs = response.choices[0].message.content.strip()
                print("Received response")
                
                if self._verify_refs_format(refs):
                    return refs
                
                correction_message = (
                    "Please format your response properly. Each reference should:\n"
                    "1. Be wrapped in <refs> tags\n"
                    "2. Start with '*'\n"
                    "3. Include the original reference number in square brackets\n"
                    "4. Be on a new line"
                )
                
                messages.extend([
                    {"role": "assistant", "content": refs},
                    {"role": "user", "content": correction_message}
                ])
                print("Incorrect format detected, requesting correction...")
                
        except Exception as e:
            print(f"Error getting GPT response: {e}")
            return ""

    def _save_refs(self, paper_id: str, section_refs: Dict[str, List[str]]):
        """Save selected references to JSON file"""
        output_file = os.path.join(self.output_dir, f'{paper_id}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(section_refs, f, indent=2, ensure_ascii=False)
        print(f"Saved references to: {output_file}")

    def process_papers(self) -> None:
        """Process all papers that have title and outline"""
        print("\nStarting reference selection process...")
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        title_dir = os.path.join(current_dir, 'title')
        
        for file_name in os.listdir(title_dir):
            if file_name.endswith('.json'):
                paper_id = os.path.splitext(file_name)[0]
                print(f"\nProcessing paper: {paper_id}")
                
                # Read paper information
                paper_info = self._read_paper_info(paper_id)
                if not paper_info:
                    print(f"Skipping paper {paper_id} due to missing information")
                    continue
                
                # Process each section
                section_refs = {}
                for section in paper_info['outline']:
                    if section not in ['Introduction', 'Conclusion']:  # Skip intro and conclusion
                        refs = self._get_refs_for_section(paper_info, section)
                        if refs:
                            # Extract reference numbers
                            content = refs[6:-7].strip()  # Remove <refs> tags
                            ref_list = [line.strip() for line in content.split('\n') if line.strip()]
                            section_refs[section] = ref_list
                            print(f"Selected {len(ref_list)} references for section: {section}")
                
                # Save results
                self._save_refs(paper_id, section_refs)
                print(f"Completed reference selection for paper: {paper_id}")

def main():
    agent = ReferenceSelectionAgent()
    agent.process_papers()
    print("\nReference selection completed!")

if __name__ == "__main__":
    main()