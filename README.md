# Claude 3.7 File Visualizer

A web application that uses Claude 3.7 with thinking capabilities to transform files and text into visually appealing, structured web pages.

## Features

- **File Upload**: Upload text-based files (txt, md, json, csv, html, js, css, py, etc.)
- **Text Input**: Directly enter or paste text for visualization
- **Claude 3.7 Integration**: Leverages Claude 3.7 Sonnet with thinking capabilities
- **Real-time Generation**: See HTML generation as it happens
- **Preview**: View the generated HTML directly in the browser
- **Download**: Save the generated HTML file
- **Cost Tracking**: Monitor token usage and associated costs
- **Custom Parameters**: Adjust Claude's temperature, max tokens, and thinking budget

## Requirements

- Python 3.8+
- Flask
- Anthropic API key (Claude 3.7 access required)

## Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd claude-file-visualizer
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python server.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5001
   ```

## Usage

1. Enter your Anthropic API key and validate it
2. Upload a file or enter text for visualization
3. (Optional) Add additional instructions to guide Claude
4. Adjust Claude's parameters if needed
5. Click "Generate Visualization"
6. Monitor the generation process
7. Preview the result, check token usage, and download the HTML

## Technical Details

- **Frontend**: HTML, CSS (TailwindCSS), JavaScript
- **Backend**: Python with Flask
- **API**: Anthropic Claude API with batch processing and streaming
- **Features**: Dark/light mode, responsive design, token and cost tracking

## Claude Settings

- **Model**: claude-3-7-sonnet-20250219
- **Temperature**: Adjustable (0-1, default 1.0)
- **Max Tokens**: Adjustable (1,000-128,000, default 64,000)
- **Thinking Budget**: Adjustable (1,024-128,000, default 32,000)
- **Output Limit**: 128K tokens using beta feature

## License

MIT License

## Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude 3.7
- [TailwindCSS](https://tailwindcss.com/) for styling
- [Font Awesome](https://fontawesome.com/) for icons
- [Prism.js](https://prismjs.com/) for code highlighting 