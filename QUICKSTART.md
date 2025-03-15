# Claude 3.7 File Visualizer - Quick Start Guide

Get up and running with the Claude 3.7 File Visualizer in just a few minutes.

## Prerequisites

- Python 3.8 or higher
- An Anthropic API key with Claude 3.7 access

## Installation

1. Clone or download this repository
2. Run the start script:

   **On macOS/Linux:**
   ```bash
   ./start.sh
   ```

   **On Windows:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python server.py
   ```

3. Open your browser and navigate to: `http://localhost:5001`

## 5-Minute Getting Started

### Step 1: Enter Your API Key

1. Paste your Anthropic API key in the input field
2. Click "Validate Key"

### Step 2: Upload a File or Enter Text

- Either drag & drop a file into the upload area or click to select a file
- Or switch to "Enter Text" tab and paste your content

### Step 3: Customize (Optional)

- Add specific instructions in the "Additional Instructions" field
- Adjust Claude parameters if needed:
  - Temperature (creativity level)
  - Max tokens (output length)
  - Thinking budget (reasoning depth)

### Step 4: Generate

- Click the "Generate Visualization" button
- Watch as Claude transforms your content in real-time

### Step 5: View and Download

- Preview the generated HTML directly in the browser
- Click "Open in New Tab" for a full-screen view
- Use the download button to save the HTML file

## Examples of What You Can Visualize

- **Documentation**: Turn bland documentation into modern, structured web pages
- **Data**: Transform CSV/JSON data into visual dashboards with explanations
- **Code**: Generate beautifully formatted code documentation with examples
- **Articles/Papers**: Convert text documents into engaging web articles
- **Notes/Ideas**: Structure brainstorming notes into organized information

## Tips

- For best results, provide clear additional instructions
- Large files may take longer to process
- Experiment with different temperature settings based on your needs
- For complex data, increase the thinking budget to get better results
- For faster processing, reduce the thinking budget for simpler content

## Troubleshooting

- If you encounter any issues with the server, try restarting it
- Make sure your API key has access to Claude 3.7 Sonnet
- Check that you have a stable internet connection
- For large files, try splitting them into smaller chunks

For more detailed instructions, see the full [GUIDE.md](GUIDE.md). 