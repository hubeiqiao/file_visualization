# Claude File Visualizer Deployment

This repository contains a web application that visualizes files using Claude 3.7 AI. 

## Deployment Instructions for Render.com

### Prerequisites
- A Render.com account
- Git repository with this code

### Steps to Deploy

1. **Create a new Web Service on Render**
   - Connect to your Git repository
   - Select the branch to deploy

2. **Configure the Web Service**
   - **Name**: `claude-file-visualizer` (or your preferred name)
   - **Environment**: `Python`
   - **Build Command**: `pip install -r file_visualization/requirements.txt`
   - **Start Command**: `cd file_visualization && python server.py`

3. **Add Environment Variables**
   - `PORT`: `10000` (Render will override this with its own value)
   - `PYTHON_VERSION`: `3.11.0` (or your preferred Python version)

4. **Deploy**
   - Click "Create Web Service"
   - Wait for the deployment to complete

## Local Development

To run the application locally:

```bash
cd file_visualization
pip install -r requirements.txt
python server.py
```

The application will be available at http://localhost:5001

## Usage

1. Enter your Anthropic API key
2. Upload a file or enter text
3. Set model parameters
4. Generate visualization
5. View and download the generated HTML 