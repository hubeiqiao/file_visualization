# Claude & Gemini File Visualizer v0.4.5

A web application that uses both Claude 3.7 and Google Gemini 2.5 Pro to generate beautiful HTML visualizations from text files, PDFs, and Word documents.

## Features

- Upload files (PDF, DOCX, TXT) or paste text directly
- Real-time HTML generation with Claude 3.7 or Google Gemini 2.5 Pro
- Live preview of the generated HTML
- Copy HTML code or download as a file
- Track token usage and cost
- Dark/Light mode for the UI
- Progress tracking with elapsed time
- Fallback mechanisms for more reliable generation

## Requirements

- Python 3.8+
- Flask
- Anthropic API key or Google Gemini API key

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

1. Choose your AI provider (Claude or Gemini)
2. Enter your API key
3. Upload a file or paste text
4. Adjust parameters if needed:
   - Temperature (creativity level)
   - Max tokens (output length)
   - Thinking budget (for Claude's thinking process)
5. Add custom instructions (optional)
6. Click "Generate Visualization"
7. View the result, copy the HTML, or download the file

## Technical Details

- **Frontend**: HTML, TailwindCSS, JavaScript
- **Backend**: Python, Flask
- **AI Providers**: 
  - Claude 3.7 with thinking capabilities
  - Google Gemini 2.5 Pro for alternative generation
- **Libraries**: PyPDF2 for PDF processing, python-docx for Word documents

## Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude 3.7
- [Google](https://ai.google.dev/) for Gemini 2.5 Pro
- [TailwindCSS](https://tailwindcss.com/) for styling
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [PyPDF2](https://pypi.org/project/PyPDF2/) for PDF processing
- [python-docx](https://python-docx.readthedocs.io/) for Word document processing

## Vercel Deployment

This project can be deployed on Vercel. The serverless function configuration has been optimized to handle streaming responses and prevent timeouts during the HTML generation process.

### Recent Fixes and Updates (v0.4.5):
- Added Google Gemini 2.5 Pro as an alternative AI provider
- Fixed timer functionality to accurately track generation time
- Improved button state management during generation
- Enhanced error handling for more reliable operation
- Added fallback mechanisms to ensure content delivery even with API issues
- Fixed ThemeManager compatibility issues in generated content
- Added version API endpoint (/api/version) 