import os
import anthropic
import sys

# Get the API key from an environment variable
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("Error: Please set the ANTHROPIC_API_KEY environment variable with a valid API key.")
    print("Example: ANTHROPIC_API_KEY=your_key python visualization.py")
    sys.exit(1)

try:
    # Initialize the client with updated API format for version 0.49.0
    client = anthropic.Anthropic(api_key=api_key)

    # Use streaming for long operations
    with client.messages.stream(
        model="claude-3-7-sonnet-20250219",
        max_tokens=64000,
        temperature=1,
        system="I will provide you with a file or a content, analyze its content, and transform it into a visually appealing and well-structured webpage.\n\n### Content Requirements\n* Maintain the core information from the original file while presenting it in a clearer and more visually engaging format.\n\n### Design Style\n* Follow a modern and minimalistic design inspired by Linear App.\n* Use a clear visual hierarchy to emphasize important content.\n* Adopt a professional and harmonious color scheme that is easy on the eyes for extended reading.\n\n### Technical Specifications\n* Use HTML5, TailwindCSS 3.0+ (via CDN), and necessary JavaScript.\n* Implement a fully functional dark/light mode toggle, defaulting to the system setting.\n* Ensure clean, well-structured code with appropriate comments for easy understanding and maintenance.\n\n### Responsive Design\n* The page must be fully responsive, adapting seamlessly to mobile, tablet, and desktop screens.\n* Optimize layout and typography for different screen sizes.\n* Ensure a smooth and intuitive touch experience on mobile devices.\n\n### Icons & Visual Elements\n* Use professional icon libraries like Font Awesome or Material Icons (via CDN).\n* Integrate illustrations or charts that best represent the content.\n* Avoid using emojis as primary icons.\n* Check if any icons cannot be loaded.\n\n### User Interaction & Experience\nEnhance the user experience with subtle micro-interactions:\n* Buttons should have slight enlargement and color transitions on hover.\n* Cards should feature soft shadows and border effects on hover.\n* Implement smooth scrolling effects throughout the page.\n* Content blocks should have an elegant fade-in animation on load.\n\n### Performance Optimization\n* Ensure fast page loading by avoiding large, unnecessary resources.\n* Use modern image formats (WebP) with proper compression.\n* Implement lazy loading for content-heavy pages.\n\n### Output Requirements\n* Deliver a fully functional standalone HTML file, including all necessary CSS and JavaScript.\n* Ensure the code meets W3C standards with no errors or warnings.\n* Maintain consistent design and functionality across different browsers.\n\nCreate the most effective and visually appealing webpage based on the uploaded file's content type (document, data, images, etc.).",
        messages=[
            {
                "role": "user",
                "content": "This project focused on Post-Quantum Cryptography (PQC) companies. It is part of the course assignment for TIMG5303B: ML for Tech Entrepreneurship Problem Solving (SEM), Winter 2025, Assignment 2B. We are Group 2. Our group members include: Temuulen Turbat, Lizhao Luo, Mike Wang, Christabel Awuah-Gyasi, Babatunde Oladoja, Ye Liu, and Joe (Beiqiao) Hu. You may use the following logo for our TIM program: https://carleton.ca/tim/wp-content/uploads/sites/52/2024/07/CU_Sprott_TIMFull_Logo_Horizontal_CMYK_Red_Black_on_light-copy-scaled.jpg The official link of TIM program: https://carleton.ca/tim/. The website can first introduce our process as follows: Based on Assignment 2A, we compiled a list of 66 PQC companies and gathered a corpus of their products and solutions. We combined this data into a CSV file for analysis using Orange. After processing the data, we identified five distinct topic models: Topic 1: blockchain, design, TPM, securosys, cloudHSM, HSM, cloud, certification, ironcap, firmware. Topic 2: identity, machine, random, decrypt, encrypt, key, break, easy, certificate, number. Topic 3: platform, customer, edge, NXP, industrial, transmission, cloud, ethernet, embed, TSN. Topic 4: luxquantum, azure, resilient, kit, key, customer, launch, easy, AW, semiconductor. Topic 5: embed, key, service, firmware, discovery, secure, API, bit, design, offer. (Choosing 5 topics as it provides a better topic model fit with lower log perplexity. And ideal range in topic coherence. Topic evaluation: Log perplexity: 186.25290 Topic coherence: 0.62725). Next, we used an LLM to analyze each topic and answer specific questions. We compared different versions and selected the best responses for presentation."
            }
        ]
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

except anthropic.AuthenticationError:
    print("Authentication Error: The provided API key is invalid.")
    print("Please make sure you're using a valid Anthropic API key.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1)