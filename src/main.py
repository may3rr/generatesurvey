"""
Main script for generating survey papers
This script coordinates all the steps in the survey generation process
"""

import os
import time
from typing import List, Dict
import json

# Import all agents
from traintestsplit import process_all_json_files_and_save_txt
from title import TitleAgent
from outline import OutlineAgent
from abstract import AbstractAgent
from referenceselection import ReferenceSelectionAgent
from subsectionagent import SubsectionAgent
from content import ContentAgent
from outputxml import XMLPaperGenerator

class SurveyGenerator:
    def __init__(self):
        """Initialize the Survey Generator"""
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.dirname(self.current_dir)
        
        # 确保所有必需的目录存在
        self.required_dirs = [
            'test', 'title', 'outline', 'abstract', 'references', 
            'subsections', 'content', 'final'
        ]
        self._create_directories()
        
    def _create_directories(self):
        """Create all required directories"""
        for dir_name in self.required_dirs:
            dir_path = os.path.join(self.base_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            
    def _log_step(self, step_name: str, start_time: float):
        """Log the completion of a step and return time taken"""
        end_time = time.time()
        time_taken = end_time - start_time
        print(f"✓ {step_name} completed in {time_taken:.2f} seconds")
        return end_time

    def generate_survey(self):
        """Run the complete survey generation process"""
        total_start_time = time.time()
        
        try:
            # Step 1: Process train files
            print("\n1. Processing training files...")
            start_time = time.time()
            process_all_json_files_and_save_txt('train', 'test')
            start_time = self._log_step("Train file processing", start_time)

            # Step 2: Generate titles
            print("\n2. Generating titles...")
            title_agent = TitleAgent()
            title_agent.process_folder()
            start_time = self._log_step("Title generation", start_time)

            # Step 3: Generate outlines
            print("\n3. Generating outlines...")
            outline_agent = OutlineAgent()
            outline_agent.process_folder()
            start_time = self._log_step("Outline generation", start_time)

            # Step 4: Generate abstracts
            print("\n4. Generating abstracts...")
            abstract_agent = AbstractAgent()
            abstract_agent.process_papers()
            start_time = self._log_step("Abstract generation", start_time)

            # Step 5: Select references
            print("\n5. Selecting references...")
            reference_agent = ReferenceSelectionAgent()
            reference_agent.process_papers()
            start_time = self._log_step("Reference selection", start_time)

            # Step 6: Generate subsections
            print("\n6. Generating subsections...")
            subsection_agent = SubsectionAgent()
            subsection_agent.process_papers()
            start_time = self._log_step("Subsection generation", start_time)

            # Step 7: Generate content
            print("\n7. Generating content...")
            content_agent = ContentAgent()
            content_agent.process_papers()
            start_time = self._log_step("Content generation", start_time)

            # Step 8: Generate final XML
            print("\n8. Generating final XML...")
            xml_generator = XMLPaperGenerator()
            xml_generator.process_papers()
            final_time = self._log_step("XML generation", start_time)

            # Print summary
            total_time = final_time - total_start_time
            print(f"\n✨ Survey generation completed in {total_time:.2f} seconds!")
            print(f"Generated files can be found in the following directories:")
            for dir_name in self.required_dirs:
                dir_path = os.path.join(self.base_dir, dir_name)
                file_count = len([f for f in os.listdir(dir_path) if not f.startswith('.')])
                print(f"  - {dir_name}/: {file_count} files")

        except Exception as e:
            print(f"\n❌ Error during survey generation: {str(e)}")
            raise

def main():
    print("Starting survey generation process...")
    generator = SurveyGenerator()
    generator.generate_survey()

if __name__ == "__main__":
    main()