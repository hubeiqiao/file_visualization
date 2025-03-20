# Claude 3.7 File Visualizer (v0.2.0)

A web application that uses Claude 3.7 to generate beautiful HTML visualizations from text files, PDFs, and Word documents.

## Features

- Upload files (PDF, DOCX, TXT) or paste text directly
- Real-time HTML generation with Claude 3.7
- Live preview of the generated HTML
- Copy HTML code or download as a file
- Track token usage and cost
- **New in v0.2.0**: Optimized for large content (100K+ tokens) with improved streaming

## Requirements

- Python 3.8+
- Flask
- Anthropic API key

## Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/hubeiqiao/File-Visualizer.git
   cd File-Visualizer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   ./start_server.sh
   ```
   
   Or manually:
   ```bash
   python server.py --port=5001
   ```

4. Open your browser and navigate to `http://localhost:5001`

## Usage

1. Enter your Anthropic API key
2. Upload a file or paste text
3. Adjust parameters if needed:
   - Temperature (creativity level)
   - Max tokens (output length)
   - Thinking budget (for Claude's thinking process)
4. Add custom instructions (optional)
5. Click "Generate Visualization"
6. View the result, copy the HTML, or download the file

## Technical Details

- **Frontend**: HTML, TailwindCSS, JavaScript
- **Backend**: Python, Flask
- **Claude Settings**: Uses Claude 3.7 with thinking capabilities
- **Libraries**: PyPDF2 for PDF processing, python-docx for Word documents
- **Streaming**: Optimized incremental rendering for large outputs
- **Memory Handling**: Efficient DOM updates to prevent browser crashes

## Release Notes

### v0.2.0 (March 2025)
- Improved handling of large content (100K+ tokens)
- Optimized streaming to prevent browser crashes
- Reduced chunk sizes for better browser compatibility
- Added incremental DOM updates for memory efficiency
- More aggressive checkpointing for reliable recovery

### v0.1.0 (March 2025)
- Initial release

## Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude 3.7
- [TailwindCSS](https://tailwindcss.com/) for styling
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [PyPDF2](https://pypi.org/project/PyPDF2/) for PDF processing
- [python-docx](https://python-docx.readthedocs.io/) for Word document processing 