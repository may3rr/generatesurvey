"""
Content Generation Agent - Generates detailed content for each subsection
"""

import os
import json
import re
from typing import List, Dict, Tuple
import yaml
from config import client, model_name

class ContentAgent:
    def __init__(self):
        """Initialize the Content Generation Agent"""
        print("Initializing ContentAgent...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_file = os.path.join(current_dir, 'prompts.yaml')
        print(f"Loading prompt from: {prompt_file}")
        self.prompt = self._load_prompt(prompt_file)
        
        # 创建content输出目录
        self.output_dir = os.path.join(os.path.dirname(current_dir), 'content')
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")
        
        # 设置最大重试次数
        self.max_retries = 3

    def _load_prompt(self, prompt_file: str) -> str:
        """Load prompt template from YAML file"""
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
                if 'content_prompt' not in prompt_data:
                    raise KeyError("'content_prompt' not found in YAML file")
                print("Prompt loaded successfully")
                return prompt_data['content_prompt']
        except Exception as e:
            print(f"Error loading prompt file: {e}")
            raise

    def _read_paper_info(self, paper_id: str) -> Dict:
        """Read all necessary information for a paper"""
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            paper_info = {}

            # Read subject
            test_file = os.path.join(current_dir, 'test', f'{paper_id}.txt')
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.strip() and line.strip() != "Subjects:":
                        if not line.startswith(('References:', 'Number:', 'Title:', 'Abstract:')):
                            paper_info['subject'] = line.strip()
                            break

            # Read title
            title_file = os.path.join(current_dir, 'title', f'{paper_id}.json')
            with open(title_file, 'r', encoding='utf-8') as f:
                title_data = json.load(f)
                paper_info['title'] = re.sub(r'<title>|</title>', '', title_data.get('title', '')).strip()

            # Read outline
            outline_file = os.path.join(current_dir, 'outline', f'{paper_id}.json')
            with open(outline_file, 'r', encoding='utf-8') as f:
                outline_data = json.load(f)
                sections = [s for s in outline_data.get('sections', []) 
                          if not (s.startswith('<outline>') or s.startswith('</outline>') or s == "")]
                paper_info['outline'] = sections

            # Read section references
            refs_file = os.path.join(current_dir, 'references', f'{paper_id}.json')
            with open(refs_file, 'r', encoding='utf-8') as f:
                paper_info['section_refs'] = json.load(f)

            # Read subsections
            subsections_file = os.path.join(current_dir, 'subsections', f'{paper_id}.json')
            with open(subsections_file, 'r', encoding='utf-8') as f:
                subsections_data = json.load(f)
                paper_info['subsections'] = subsections_data.get('sections', {})

            return paper_info
        except Exception as e:
            print(f"Error reading paper info: {e}")
            return {}

    def _verify_content_format(self, content: str) -> bool:
        """Verify if the content meets the requirements"""
        if not (content.startswith('<content>') and content.endswith('</content>')):
            print("Content format verification failed: Missing tags")
            return False

        # Remove tags and analyze content
        text = content[9:-10].strip()  # Remove <content> tags
        
        # Count paragraphs (separated by double newlines)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) < 3:
            print(f"Content format verification failed: Too few paragraphs ({len(paragraphs)})")
            return False
        
        # Relaxed word count check
        words = len(text.split())
        if words < 500:  # 只检查最小字数
            print(f"Content format verification failed: Word count {words} too low (min 500)")
            return False

        # Check for citation format [n]
        if not re.search(r'\[\d+\]', text):
            print("Content format verification failed: No citations found")
            return False

        print(f"Content format verification passed: {len(paragraphs)} paragraphs, {words} words")
        return True

    def _get_content(self, paper_info: Dict, section: str, subsection: str) -> str:
        """Generate content for a subsection"""
        try:
            print(f"\nGenerating content for subsection: {subsection}")
            section_refs = paper_info['section_refs'].get(section, [])
            formatted_prompt = self.prompt.format(
                subject=paper_info['subject'],
                title=paper_info['title'],
                outline='\n'.join(paper_info['outline']),
                section_heading=section,
                subsec_heading=subsection,
                section_refs='\n'.join(section_refs)
            )
            messages = [{"role": "user", "content": formatted_prompt}]
            
            retry_count = 0
            while retry_count < self.max_retries:  # 限制重试次数
                print(f"Attempt {retry_count + 1}/{self.max_retries}")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                content = response.choices[0].message.content.strip()
                print(f"Received response of length: {len(content)}")
                
                if self._verify_content_format(content):
                    return content
                
                correction_message = (
                    "Please format your response properly:\n"
                    "1. Wrap content in <content> tags\n"
                    "2. Write at least 3 paragraphs\n"
                    "3. Include at least 500 words\n"
                    "4. Use proper citations [n]\n"
                    "5. Don't include any headings\n"
                    "6. Maintain academic style"
                )
                
                messages.extend([
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": correction_message}
                ])
                print("Incorrect format detected, requesting correction...")
                retry_count += 1
            
            # 如果达到最大重试次数，返回最后一次的响应
            print("Maximum retries reached, using last response")
            return content
                
        except Exception as e:
            print(f"Error getting GPT response: {e}")
            return ""

    def _save_content(self, paper_id: str, content_data: Dict):
        """Save generated content to JSON file"""
        output_file = os.path.join(self.output_dir, f'{paper_id}.json')
        result = {
            'paper_id': paper_id,
            'sections': content_data
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Saved content to: {output_file}")

    def process_papers(self) -> None:
        """Process all papers that have complete information"""
        print("\nStarting content generation process...")
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
                
                # Process each section and subsection
                content_data = {}
                for section, subsections in paper_info['subsections'].items():
                    if section not in ['Introduction', 'Conclusion']:
                        section_content = {}
                        for subsection in subsections:
                            content = self._get_content(paper_info, section, subsection)
                            if content:
                                section_content[subsection] = content[9:-10].strip()  # Remove tags
                                print(f"Generated content for subsection: {subsection}")
                        if section_content:
                            content_data[section] = section_content
                
                # Save results
                self._save_content(paper_id, content_data)
                print(f"Completed content generation for paper: {paper_id}")

def main():
    agent = ContentAgent()
    agent.process_papers()
    print("\nContent generation completed!")

if __name__ == "__main__":
    main()