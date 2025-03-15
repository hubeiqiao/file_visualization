import os
import anthropic

# Get the API key from an environment variable
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("Please set the ANTHROPIC_API_KEY environment variable.")

client = anthropic.Anthropic(
    api_key=api_key,
)

# Use streaming for long operations
with client.messages.stream(
    model="claude-3-7-sonnet-20250219",
    max_tokens=64000,
    temperature=1,
    system="I will provide you with a file or a content, analyze its content, and transform it into a visually appealing and well-structured webpage.\n\n### Content Requirements\n* Maintain the core information from the original file while presenting it in a clearer and more visually engaging format.\n\n### Design Style\n* Follow a modern and minimalistic design inspired by Linear App.\n* Use a clear visual hierarchy to emphasize important content.\n* Adopt a professional and harmonious color scheme that is easy on the eyes for extended reading.\n\n### Technical Specifications\n* Use HTML5, TailwindCSS 3.0+ (via CDN), and necessary JavaScript.\n* Implement a fully functional dark/light mode toggle, defaulting to the system setting.\n* Ensure clean, well-structured code with appropriate comments for easy understanding and maintenance.\n\n### Responsive Design\n* The page must be fully responsive, adapting seamlessly to mobile, tablet, and desktop screens.\n* Optimize layout and typography for different screen sizes.\n* Ensure a smooth and intuitive touch experience on mobile devices.\n\n### Icons & Visual Elements\n* Use professional icon libraries like Font Awesome or Material Icons (via CDN).\n* Integrate illustrations or charts that best represent the content.\n* Avoid using emojis as primary icons.\n* Check if any icons cannot be loaded.\n\n### User Interaction & Experience\nEnhance the user experience with subtle micro-interactions:\n* Buttons should have slight enlargement and color transitions on hover.\n* Cards should feature soft shadows and border effects on hover.\n* Implement smooth scrolling effects throughout the page.\n* Content blocks should have an elegant fade-in animation on load.\n\n### Performance Optimization\n* Ensure fast page loading by avoiding large, unnecessary resources.\n* Use modern image formats (WebP) with proper compression.\n* Implement lazy loading for content-heavy pages.\n\n### Output Requirements\n* Deliver a fully functional standalone HTML file, including all necessary CSS and JavaScript.\n* Ensure the code meets W3C standards with no errors or warnings.\n* Maintain consistent design and functionality across different browsers.\n\nCreate the most effective and visually appealing webpage based on the uploaded file's content type (document, data, images, etc.).",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": '''Here is my notes of Explanation of Structured Handwritten Notes.“””# Explanation of Structured Handwritten Notes## Create DateMarch 9, 2025## Tag#Technology#NoteTaking#HandwritingToDigital## LocationLeeds House, Carleton University## Source/## SummaryDescribes how to convert handwritten notes into structured digital content through automatic titling, tagging, summarization, and hierarchical organization. It also explains enriching notes with research, linking related content, and generating mind maps while using time, location, and resources for better organization.## Content### InputHandwriting(raw data)+Resource: Youtube Video+Time, data, location### Output**Help ogranzie documents**① Automatically title the note.② Pre-populate tags.③ Summary the note.⑩ Time, location, resource for organize**Enrich the note**④ Organize the note hierarchically.- Heading- Bullet points- Font size and bold⑤ Enrich the note based on video content.⑥ Attach key images from video to match the note information.⑦ Suggest related readings or resources.⑧ Connect to previous notes.⑨ Create a mind map.### Related notesDynamicland Notes: https://www.figma.com/design/uJ23IJBqCQ09f66MeZktBM/Context-Aware-Handwritten-prototype?node-id=70-19&t=EiH5QTMd0OmGsQzP-1See the original handwriting transcript: [Figma](https://www.figma.com/design/uJ23IJBqCQ09f66MeZktBM/Context-Aware-Handwritten-prototype?node-id=93-142&t=EiH5QTMd0OmGsQzP-1)“””'''
                }
            ]
        }
    ],
        thinking={
        "type": "enabled",
        "budget_tokens": 16000
    }
) as stream:
    # Process the streaming response
    full_response = ""
    for text in stream.text_stream:
        full_response += text
        print(text, end="", flush=True)  # Print each chunk as it arrives
    
    print("\n\n--- Complete response ---")
    print(full_response)
    # Write the full response to an HTML file in the Downloads folder
    output_path = "/Users/joehu/Downloads/output.html"
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(full_response)
    print(f"HTML output saved to {output_path}")