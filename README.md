# Thesis PDF Processor Script

This script is designed to process PDF student thesis reports, extract relevant information, and generate entries suitable for an academic website built with Hugo Blox. It uses the Perplexity API to analyze the content of PDFs and create markdown files with summaries, titles, authors, and keywords.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Functionality

- Recursively finds all PDF files in a specified base folder.
- Extracts text and metadata from each PDF.
- Analyzes the content using the Perplexity API to generate a summary, title, author, and keywords.
- Creates a structured markdown file for each PDF, which can be used to populate an academic website.

## Usage

```bash
python pdf_processor.py --api-key YOUR_API_KEY --base-folder "/path/to/folder" [--test]
```

### Arguments

- `--api-key`: Your Perplexity API key (required).
- `--base-folder`: Path to the folder containing PDFs (required).
- `--test`: Optional flag to process only one PDF for testing purposes.

### Example

```bash
python pdf_processor.py --api-key "your_api_key" --base-folder "/home/user/thesis_reports" --test
```

## Note

Ensure that the Perplexity API key is valid and that the base folder contains PDF files to be processed.

## License

This project is licensed under the Creative Commons Attribution 4.0 International License. See the [LICENSE](LICENSE) file for details. 