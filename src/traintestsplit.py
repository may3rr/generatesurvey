"""
Extract references and subject from JSON files and save as TXT files.
"""

import json
import os
import re

def extract_references_and_subject(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取subject
    subjects = data.get('subject', [])
    
    # 提取references
    references = []
    reference_list = data.get('reference', [])
    reference_content_list = data.get('reference_content', [])

    reference_content_dict = {
        content['reference_num']: content.get('reference_abstract', "") 
        for content in reference_content_list
    }

    for i, ref in enumerate(reference_list):
        reference_num = f"[{i+1}]"
        reference_title = ref if isinstance(ref, str) else ref.get('reference_title', "")
        reference_abstract = reference_content_dict.get(reference_num, "")

        references.append({
            "num": reference_num,
            "title": reference_title,
            "abstract": reference_abstract
        })

    return subjects, references

def save_references_and_subject_as_txt(subjects, references, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        # 首先写入subjects
        f.write("Subjects:\n")
        for subject in subjects:
            f.write(f"{subject}\n")
        f.write("\n")  # 空行分隔

        # 然后写入references
        f.write("References:\n")
        for ref in references:
            f.write(f'Number: {ref["num"]}\n')
            f.write(f'Title: {ref["title"]}\n')
            f.write(f'Abstract: {ref["abstract"]}\n')
            f.write('\n')

def process_all_json_files_and_save_txt(train_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for file_name in os.listdir(train_folder):
        if file_name.endswith('.json'):
            json_file = os.path.join(train_folder, file_name)
            subjects, references = extract_references_and_subject(json_file)

            # 使用正则表达式提取完整的数字部分 (2002.00564)
            match = re.search(r'(\d+\.\d+)', file_name)
            if match:
                paper_id = match.group(1)
                output_file = os.path.join(output_folder, f'{paper_id}.txt')
                save_references_and_subject_as_txt(subjects, references, output_file)
            else:
                print(f"Warning: Could not extract paper ID from {file_name}")

# 运行处理
process_all_json_files_and_save_txt('train', 'test')