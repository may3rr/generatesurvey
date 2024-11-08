"""
XML Paper Generator - Combines all generated content into a final XML paper
"""

import os
import json
import re
from typing import Dict, List

class XMLPaperGenerator:
    def __init__(self):
        """Initialize the XML Paper Generator"""
        print("Initializing XMLPaperGenerator...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(current_dir)
        
        # 设置输入输出目录
        self.title_dir = os.path.join(base_dir, 'title')
        self.abstract_dir = os.path.join(base_dir, 'abstract')
        self.outline_dir = os.path.join(base_dir, 'outline')
        self.subsections_dir = os.path.join(base_dir, 'subsections')
        self.content_dir = os.path.join(base_dir, 'content')
        self.train_dir = os.path.join(base_dir, 'train')  # 改为train目录
        
        # 创建final输出目录
        self.output_dir = os.path.join(base_dir, 'final')
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output directory: {self.output_dir}")

    def _read_title(self, paper_id: str) -> str:
        """Read title from json file"""
        try:
            with open(os.path.join(self.title_dir, f'{paper_id}.json'), 'r') as f:
                data = json.load(f)
                title = data.get('title', '')
                return re.sub(r'<title>|</title>', '', title).strip()
        except Exception as e:
            print(f"Error reading title: {e}")
            return ""

    def _read_abstract(self, paper_id: str) -> str:
        """Read abstract from json file"""
        try:
            with open(os.path.join(self.abstract_dir, f'{paper_id}.json'), 'r') as f:
                data = json.load(f)
                abstract = data.get('abstract', '')
                return re.sub(r'<abstract>|</abstract>', '', abstract).strip()
        except Exception as e:
            print(f"Error reading abstract: {e}")
            return ""

    def _read_sections(self, paper_id: str) -> List[str]:
        """Read main sections from outline"""
        try:
            with open(os.path.join(self.outline_dir, f'{paper_id}.json'), 'r') as f:
                data = json.load(f)
                sections = [s for s in data.get('sections', []) 
                          if not (s.startswith('<outline>') or s.startswith('</outline>'))]
                return sections
        except Exception as e:
            print(f"Error reading sections: {e}")
            return []

    def _read_subsections(self, paper_id: str) -> Dict[str, List[str]]:
        """Read subsections for each section"""
        try:
            with open(os.path.join(self.subsections_dir, f'{paper_id}.json'), 'r') as f:
                data = json.load(f)
                return data.get('sections', {})
        except Exception as e:
            print(f"Error reading subsections: {e}")
            return {}

    def _read_content(self, paper_id: str) -> Dict[str, Dict[str, str]]:
        """Read content for each subsection"""
        try:
            with open(os.path.join(self.content_dir, f'{paper_id}.json'), 'r') as f:
                data = json.load(f)
                return data.get('sections', {})
        except Exception as e:
            print(f"Error reading content: {e}")
            return {}

    def _read_references(self, paper_id: str) -> str:
        """Read references from train file"""
        try:
            # 构建完整的文件名（需要添加train前缀）
            train_file = os.path.join(self.train_dir, f'train{paper_id}.content.ref.json')
            with open(train_file, 'r') as f:
                data = json.load(f)
                
                # 提取reference和reference_content
                references = data.get('reference', [])
                reference_contents = data.get('reference_content', [])
                
                # 创建完整的参考文献列表
                ref_list = references
                
                # 如果有abstract，添加到对应的参考文献中
                if reference_contents:
                    # 创建一个映射，用于快速查找reference_content
                    content_map = {
                        item['reference_num']: item.get('reference_abstract', '')
                        for item in reference_contents
                    }
                    
                    # 对每个参考文献，如果有abstract，就添加到后面
                    ref_list_with_abstracts = []
                    for ref in references:
                        ref_num = f"[{len(ref_list_with_abstracts) + 1}]"
                        if ref_num in content_map and content_map[ref_num]:
                            ref_list_with_abstracts.append(
                                f"{ref}\nAbstract: {content_map[ref_num]}"
                            )
                        else:
                            ref_list_with_abstracts.append(ref)
                    
                    ref_list = ref_list_with_abstracts

                return '\n\n'.join(ref_list)
                
        except Exception as e:
            print(f"Error reading references: {e}")
            return ""

    def _generate_xml(self, paper_id: str) -> str:
        """Generate XML content for the paper"""
        # Read all components
        title = self._read_title(paper_id)
        abstract = self._read_abstract(paper_id)
        sections = self._read_sections(paper_id)
        subsections = self._read_subsections(paper_id)
        content = self._read_content(paper_id)
        references = self._read_references(paper_id)

        # Start building XML
        xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_content.append('<Literature>')
        
        # Add title and abstract
        xml_content.append(f'<Title>{title}</Title>')
        xml_content.append(f'<Abstract>{abstract}</Abstract>')

        # Add sections, subsections, and content
        section_num = 1
        for section in sections:
            if section not in ['Introduction', 'Conclusion']:
                # Add section title
                xml_content.append(f'<Section_{section_num}_title>{section}</Section_{section_num}_title>')
                
                # Add subsections
                if section in subsections:
                    subsection_num = 1
                    for subsection in subsections[section]:
                        # Add subsection title
                        xml_content.append(
                            f'<Section_{section_num}.{subsection_num}_title>{subsection}</Section_{section_num}.{subsection_num}_title>'
                        )
                        
                        # Add subsection content
                        if section in content and subsection in content[section]:
                            xml_content.append(
                                f'<Section_{section_num}.{subsection_num}_text>{content[section][subsection]}</Section_{section_num}.{subsection_num}_text>'
                            )
                        
                        subsection_num += 1
                        
                section_num += 1

        # Add references
        xml_content.append('<References>')
        xml_content.append(references)
        xml_content.append('</References>')
        
        # Close main tag
        xml_content.append('</Literature>')
        
        return '\n'.join(xml_content)

    def _save_xml(self, paper_id: str, xml_content: str):
        """Save XML content to file"""
        output_file = os.path.join(self.output_dir, f'{paper_id}.xml')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        print(f"Saved XML to: {output_file}")

    def process_papers(self):
        """Process all papers and generate XML files"""
        print("\nStarting XML generation process...")
        
        # Get list of paper IDs from title directory
        for file_name in os.listdir(self.title_dir):
            if file_name.endswith('.json'):
                paper_id = os.path.splitext(file_name)[0]
                print(f"\nProcessing paper: {paper_id}")
                
                # Generate and save XML
                xml_content = self._generate_xml(paper_id)
                self._save_xml(paper_id, xml_content)
                print(f"Completed XML generation for paper: {paper_id}")

def main():
    generator = XMLPaperGenerator()
    generator.process_papers()
    print("\nXML generation completed!")

if __name__ == "__main__":
    main()