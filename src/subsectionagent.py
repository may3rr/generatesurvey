"""
Subsection Generation Agent - Generates subsection headings for each section
"""

import os
import json
import re
from typing import List, Dict, Tuple
import yaml
from config import client, model_name

class SubsectionAgent:
    def __init__(self):
        """Initialize the Subsection Agent"""
        print("Initializing SubsectionAgent...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_file = os.path.join(current_dir, 'prompts.yaml')
        print(f"Loading prompt from: {prompt_file}")
        self.prompt = self._load_prompt(prompt_file)
        
        # 创建subsections输出目录
        self.output_dir = os.path.join(os.path.dirname(current_dir), 'subsections')
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")

    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt template from YAML file"""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
                if 'subsection_prompt' not in prompt_data:
                    raise KeyError("'subsection_prompt' not found in YAML file")
                print("Prompt loaded successfully")
                return prompt_data['subsection_prompt']
        except Exception as e:
            print(f"Error loading prompt file: {e}")
            raise

    def _read_paper_info(self, paper_id: str) -> Dict:
        """Read all necessary information for a paper"""
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Read subject from test file
            test_file = os.path.join(current_dir, 'test', f'{paper_id}.txt')
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.strip() and line.strip() != "Subjects:":
                        if not line.startswith(('References:', 'Number:', 'Title:', 'Abstract:')):
                            subject = line.strip()
                            break
            
            # Read title
            title_file = os.path.join(current_dir, 'title', f'{paper_id}.json')
            with open(title_file, 'r', encoding='utf-8') as f:
                title_data = json.load(f)
                title = re.sub(r'<title>|</title>', '', title_data.get('title', '')).strip()
            
            # Read outline
            outline_file = os.path.join(current_dir, 'outline', f'{paper_id}.json')
            with open(outline_file, 'r', encoding='utf-8') as f:
                outline_data = json.load(f)
                sections = outline_data.get('sections', [])
                cleaned_sections = []
                for section in sections:
                    if not (section.startswith('<outline>') or 
                           section.startswith('</outline>') or
                           section == ""):
                        cleaned_sections.append(section)
            
            # Read section references
            refs_file = os.path.join(current_dir, 'references', f'{paper_id}.json')
            with open(refs_file, 'r', encoding='utf-8') as f:
                section_refs = json.load(f)
            
            return {
                'subject': subject,
                'title': title,
                'outline': cleaned_sections,
                'section_refs': section_refs
            }
        except Exception as e:
            print(f"Error reading paper info: {e}")
            return {}

    def _verify_subsections_format(self, subsections: str) -> bool:
        """Verify if the subsections are in correct format"""
        if not (subsections.startswith('<subsections>') and subsections.endswith('</subsections>')):
            print("Subsections format verification failed: Missing tags")
            return False
            
        content = subsections[13:-14].strip()  # Remove tags
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if not (3 <= len(lines) <= 5):
            print(f"Subsections format verification failed: Wrong number of subsections ({len(lines)})")
            return False
            
        if not all(line.startswith('* ') for line in lines):
            print("Subsections format verification failed: Missing asterisks")
            return False
        
        print("Subsections format verification passed")
        return True

    def _get_subsections_for_section(self, paper_info: Dict, section: str, section_refs: List[str]) -> str:
        """Get subsection suggestions from GPT for a specific section"""
        try:
            print(f"\nGenerating subsections for section: {section}")
            formatted_prompt = self.prompt.format(
                subject=paper_info['subject'],
                title=paper_info['title'],
                outline='\n'.join(paper_info['outline']),
                section=section,
                section_refs='\n'.join(section_refs)
            )
            messages = [{"role": "user", "content": formatted_prompt}]
            
            while True:  # 循环直到获得正确格式的响应
                print("Sending request to GPT...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7
                )
                subsections = response.choices[0].message.content.strip()
                print("Received response")
                
                if self._verify_subsections_format(subsections):
                    return subsections
                
                correction_message = (
                    "Please format your response properly:\n"
                    "1. Wrap subsections in <subsections> tags\n"
                    "2. Include 3-5 subsections\n"
                    "3. Start each subsection with '* '\n"
                    "4. Put each subsection on a new line"
                )
                
                messages.extend([
                    {"role": "assistant", "content": subsections},
                    {"role": "user", "content": correction_message}
                ])
                print("Incorrect format detected, requesting correction...")
                
        except Exception as e:
            print(f"Error getting GPT response: {e}")
            return ""

    def _save_subsections(self, paper_id: str, section_subsections: Dict):
        """Save subsections to JSON file"""
        output_file = os.path.join(self.output_dir, f'{paper_id}.json')
        # Save as a nested structure with sections and their subsections
        result = {
            'paper_id': paper_id,
            'sections': section_subsections
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Saved subsections to: {output_file}")

    def process_papers(self) -> None:
        """Process all papers that have title, outline, and references"""
        print("\nStarting subsection generation process...")
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
                section_subsections = {}
                for section in paper_info['outline']:
                    if section not in ['Introduction', 'Conclusion']:  # Skip intro and conclusion
                        section_refs = paper_info['section_refs'].get(section, [])
                        if section_refs:
                            subsections = self._get_subsections_for_section(
                                paper_info, section, section_refs
                            )
                            if subsections:
                                # Extract subsection list
                                content = subsections[13:-14].strip()  # Remove tags
                                subsection_list = [
                                    line.strip()[2:].strip()  # Remove '* ' prefix
                                    for line in content.split('\n')
                                    if line.strip()
                                ]
                                section_subsections[section] = subsection_list
                                print(f"Generated {len(subsection_list)} subsections for: {section}")
                
                # Save results
                self._save_subsections(paper_id, section_subsections)
                print(f"Completed subsection generation for paper: {paper_id}")

def main():
    agent = SubsectionAgent()
    agent.process_papers()
    print("\nSubsection generation completed!")

if __name__ == "__main__":
    main()