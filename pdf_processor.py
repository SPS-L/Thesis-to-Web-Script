"""
Thesis PDF Processor Script

This script processes PDF student thesis reports and generates entries suitable for an academic website built with Hugo Blox.
It uses the Perplexity API to analyze the content of PDFs and create markdown files with summaries, titles, authors, and keywords.

The script can be run in two modes:
1. Full Mode: Processes all PDF files in the specified folder
2. Test Mode: Processes only one PDF file (useful for testing)

Usage:
    Full Mode:
        python pdf_processor.py --api-key YOUR_API_KEY --base-folder "/path/to/folder"
    
    Test Mode:
        python pdf_processor.py --api-key YOUR_API_KEY --base-folder "/path/to/folder" --test

Arguments:
    --api-key: Your Perplexity API key (required)
    --base-folder: Path to the folder containing PDFs (required)
    --test: Optional flag to process only one PDF file for testing purposes

Example:
    # Process all PDFs
    python pdf_processor.py --api-key "your_api_key" --base-folder "/home/user/thesis_reports"
    
    # Process only one PDF (test mode)
    python pdf_processor.py --api-key "your_api_key" --base-folder "/home/user/thesis_reports" --test

Note:
    - Ensure that the Perplexity API key is valid
    - The base folder must contain PDF files to be processed
    - The script creates an 'out' directory in the base folder to store processed files
    - Each processed PDF gets its own subdirectory with the format: 2025_author_name
    - The script generates an index.md file for each processed PDF

Dependencies:
    - PyPDF2: For PDF text and metadata extraction
    - requests: For API communication
    - pathlib: For path handling

License:
    This project is licensed under the Creative Commons Attribution 4.0 International License.
"""

import os
import shutil
import PyPDF2
import requests
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import argparse

class PDFProcessor:
    def __init__(self, api_key: str, base_folder: str):
        """
        Initialize the PDF processor with Perplexity API key and base folder path.

        Args:
            api_key (str): Perplexity API key
            base_folder (str): Path to the folder containing PDFs
        """
        self.api_key = api_key
        self.base_folder = Path(base_folder)
        self.api_url = "https://api.perplexity.ai/chat/completions"

    def find_pdf_files(self) -> List[Path]:
        """
        Recursively find all PDF files in the base folder and subfolders.

        Returns:
            List[Path]: List of paths to PDF files
        """
        pdf_files = []
        for root, dirs, files in os.walk(self.base_folder):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(Path(root) / file)
        return pdf_files

    def extract_pdf_text(self, pdf_path: Path) -> str:
        """
        Extract text content from PDF file.

        Args:
            pdf_path (Path): Path to the PDF file

        Returns:
            str: Extracted text content
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""

                # Extract text from first few pages (limit for API efficiency)
                max_pages = min(5, len(pdf_reader.pages))
                for page_num in range(max_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"

                return text[:160000]  # Limit text length for API
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""

    def get_pdf_metadata(self, pdf_path: Path) -> Dict[str, str]:
        """
        Extract basic metadata from PDF file.

        Args:
            pdf_path (Path): Path to the PDF file

        Returns:
            Dict[str, str]: PDF metadata
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata = pdf_reader.metadata

                return {
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', '')
                }
        except Exception as e:
            print(f"Error extracting metadata from {pdf_path}: {e}")
            return {}

    def analyze_with_perplexity(self, pdf_text: str, pdf_metadata: Dict[str, str]) -> Dict[str, str]:
        """
        Use Perplexity API to analyze PDF content and extract required information.

        Args:
            pdf_text (str): Extracted PDF text
            pdf_metadata (Dict[str, str]): PDF metadata

        Returns:
            Dict[str, str]: Analyzed information (title, author, keywords, summary)
        """
        # Prepare the prompt for Perplexity API
        prompt = f"""
        Analyze this PDF content and metadata to extract the following information:

        PDF Metadata:
        - Title: {pdf_metadata.get('title', 'Not available')}
        - Author: {pdf_metadata.get('author', 'Not available')}
        - Subject: {pdf_metadata.get('subject', 'Not available')}

        PDF Text Content (first few pages):
        {pdf_text}

        Please provide:
        1. TITLE: The main title of the document
        2. AUTHOR: The primary author's name
        3. KEYWORDS: 3-4 relevant keywords, comma-separated, WITH QUOTES around multi-word keywords
        4. SUMMARY: A comprehensive markdown summary. The summary should be 500 words and should include three sections Overview, Key Contributions, Impact and Relevance.

        Format your response as JSON:
        {{
            "title": "extracted title",
            "author": "extracted author",
            "keywords": "keyword1, \"multi word keyword\", keyword3, keyword4",
            "summary": "markdown formatted summary..."
        }}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "You are addressing an expert audience. The defence date is May 2025 for all theses (ignore the date in the metadata or text). Do not include any references, citations or extra comments in any of the answers."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Try to parse JSON response
            try:
                # Extract JSON from response if it's wrapped in text
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_content = json_match.group()
                    parsed_data = json.loads(json_content)
                else:
                    # Fallback: create structured data from text response
                    parsed_data = self._parse_text_response(content)

                return parsed_data

            except json.JSONDecodeError:
                # Fallback parsing
                return self._parse_text_response(content)

        except Exception as e:
            print(f"Error calling Perplexity API: {e}")
            # Return fallback data
            return {
                "title": pdf_metadata.get('title', 'Unknown Title'),
                "author": pdf_metadata.get('author', 'Unknown Author'),
                "keywords": '"academic paper", "research", "analysis"',
                "summary": "This document requires manual review for proper summarization."
            }

    def _parse_text_response(self, content: str) -> Dict[str, str]:
        """
        Parse text response when JSON parsing fails.

        Args:
            content (str): API response content

        Returns:
            Dict[str, str]: Parsed information
        """
        # Simple text parsing as fallback
        lines = content.split('\n')
        result = {
            "title": "Unknown Title",
            "author": "Unknown Author", 
            "keywords": '"document", "analysis"',
            "summary": "Summary extraction failed. Manual review required."
        }

        for line in lines:
            if 'title' in line.lower() and ':' in line:
                result['title'] = line.split(':', 1)[1].strip().strip('"')
            elif 'author' in line.lower() and ':' in line:
                result['author'] = line.split(':', 1)[1].strip().strip('"')
            elif 'keyword' in line.lower() and ':' in line:
                result['keywords'] = line.split(':', 1)[1].strip()
            elif 'summary' in line.lower() and ':' in line:
                result['summary'] = line.split(':', 1)[1].strip()

        return result

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string to be used as a filename/folder name.

        Args:
            name (str): Original name

        Returns:
            str: Sanitized name
        """
        # Replace spaces with underscores and remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        sanitized = sanitized.replace(' ', '_')
        sanitized = re.sub(r'_+', '_', sanitized)  # Remove multiple underscores
        return sanitized.strip('_')

    def create_markdown_file(self, folder_path: Path, analyzed_data: Dict[str, str]) -> None:
        """
        Create the index.md file with the specified template.

        Args:
            folder_path (Path): Path to the folder where to create the file
            analyzed_data (Dict[str, str]): Analyzed data from Perplexity API
        """
        template_content = '''+++
title = "{}"
date = "2025-06-01"
authors = ["{}"]
tags = [{}]
publication_types = ["thesis"]
publication = "_Cyprus University of Technology_"
publication_short = ""
abstract = ""
summary = ""
featured = false
projects = []
slides = ""
url_code = ""
url_dataset = ""
url_poster = ""
url_slides = ""
url_source = ""
url_video = ""
math = true
highlight = true
[image]
image = ""
caption = ""
+++

{}'''.format(
            analyzed_data['title'],
            analyzed_data['author'], 
            analyzed_data['keywords'],
            analyzed_data['summary']
        )

        index_path = folder_path / "index.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(template_content)

    def process_pdf(self, pdf_path: Path) -> bool:
        """
        Process a single PDF file: extract info, create folder, copy file, create markdown.

        Args:
            pdf_path (Path): Path to the PDF file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Processing: {pdf_path.name}")

            # Extract PDF content and metadata
            pdf_text = self.extract_pdf_text(pdf_path)
            pdf_metadata = self.get_pdf_metadata(pdf_path)

            # Analyze with Perplexity API
            analyzed_data = self.analyze_with_perplexity(pdf_text, pdf_metadata)

            # Create folder name
            author_name = self.sanitize_filename(analyzed_data['author'])
            folder_name = f"2025_{author_name}"
            
            # Create 'out' directory under base_folder
            out_dir = self.base_folder / "out"
            out_dir.mkdir(exist_ok=True)
            
            # Place output folder inside 'out'
            folder_path = out_dir / folder_name

            # Create folder if it doesn't exist
            folder_path.mkdir(exist_ok=True)

            # Copy and rename PDF
            new_pdf_name = f"{folder_name}.pdf"
            new_pdf_path = folder_path / new_pdf_name
            shutil.copy2(pdf_path, new_pdf_path)

            # Create markdown file
            self.create_markdown_file(folder_path, analyzed_data)

            print(f"Successfully processed: {pdf_path.name} -> out/{folder_name}/")
            return True

        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
            return False

    def process_all_pdfs(self, test: bool = False) -> None:
        """
        Process all PDF files in the base folder and subfolders.
        If test is True, only process one PDF and stop.

        Args:
            test (bool): If True, only process one PDF file. Default is False.
        """
        pdf_files = self.find_pdf_files()

        if not pdf_files:
            print("No PDF files found in the specified folder.")
            return

        if test:
            print("Running in TEST mode - will process only one PDF file.")
            pdf_files = pdf_files[:1]
        else:
            print(f"Running in FULL mode - will process all {len(pdf_files)} PDF files.")

        successful = 0
        failed = 0

        for i, pdf_path in enumerate(pdf_files):
            if self.process_pdf(pdf_path):
                successful += 1
            else:
                failed += 1

        print(f"\nProcessing complete!")
        print(f"Successfully processed: {successful}")
        print(f"Failed: {failed}")


def main():
    """
    Main function to run the PDF processor.
    """
    parser = argparse.ArgumentParser(description="Process PDF files and generate markdown summaries.")
    parser.add_argument('--api-key', type=str, required=True, help='Perplexity API key')
    parser.add_argument('--base-folder', type=str, required=True, help='Path to the folder containing PDFs')
    parser.add_argument('--test', action='store_true', default=False, help='Process only one PDF and stop (for testing)')
    args = parser.parse_args()

    API_KEY = args.api_key
    BASE_FOLDER = args.base_folder
    TEST = args.test

    # Validate inputs
    if API_KEY == "your_perplexity_api_key_here":
        print("Please set your Perplexity API key in the API_KEY variable.")
        return

    if not os.path.exists(BASE_FOLDER):
        print(f"Folder {BASE_FOLDER} does not exist. Please check the path.")
        return

    # Initialize and run processor
    processor = PDFProcessor(API_KEY, BASE_FOLDER)
    processor.process_all_pdfs(test=TEST)


if __name__ == "__main__":
    main()
