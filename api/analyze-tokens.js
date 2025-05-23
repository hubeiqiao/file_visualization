// Token analysis function for Vercel using same logic as local
module.exports = (req, res) => {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle OPTIONS request (CORS preflight)
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }
  
  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({
      success: false,
      error: 'Method not allowed. Use POST.'
    });
  }
  
  try {
    // Get content from request body
    const body = req.body || {};
    
    // Check for both 'content' and 'source' parameters for compatibility
    let content = body.content || '';
    if (!content && body.source) {
      content = body.source; // Fallback to 'source' if 'content' is empty
    }
    
    const fileType = body.file_type || 'txt';
    
    // Check if content is provided
    if (!content) {
      return res.status(400).json({
        success: false,
        error: 'Content is required'
      });
    }
    
    // Use the same system prompt as server.py
    const systemPrompt = "I will provide you with a file or a content, analyze its content, and transform it into a visually appealing and well-structured webpage.### Content Requirements* Maintain the core information from the original file while presenting it in a clearer and more visually engaging format.⠀Design Style* Follow a modern and minimalistic design inspired by Linear App.* Use a clear visual hierarchy to emphasize important content.* Adopt a professional and harmonious color scheme that is easy on the eyes for extended reading.⠀Technical Specifications* Use HTML5, TailwindCSS 3.0+ (via CDN), and necessary JavaScript.* Implement a fully functional dark/light mode toggle, defaulting to the system setting.* Ensure clean, well-structured code with appropriate comments for easy understanding and maintenance.⠀Responsive Design* The page must be fully responsive, adapting seamlessly to mobile, tablet, and desktop screens.* Optimize layout and typography for different screen sizes.* Ensure a smooth and intuitive touch experience on mobile devices.⠀Icons & Visual Elements* Use professional icon libraries like Font Awesome or Material Icons (via CDN).* Integrate illustrations or charts that best represent the content.* Avoid using emojis as primary icons.* Check if any icons cannot be loaded.⠀User Interaction & ExperienceEnhance the user experience with subtle micro-interactions:* Buttons should have slight enlargement and color transitions on hover.* Cards should feature soft shadows and border effects on hover.* Implement smooth scrolling effects throughout the page.* Content blocks should have an elegant fade-in animation on load.⠀Performance Optimization* Ensure fast page loading by avoiding large, unnecessary resources.* Use modern image formats (WebP) with proper compression.* Implement lazy loading for content-heavy pages.⠀Output Requirements* Deliver a fully functional standalone HTML file, including all necessary CSS and JavaScript.* Ensure the code meets W3C standards with no errors or warnings.* Maintain consistent design and functionality across different browsers.⠀Create the most effective and visually appealing webpage based on the uploaded file's content type (document, data, images, etc.).";
    
    // Use the same token estimation logic as in server.py
    // Tokens are calculated by character count divided by a factor
    const systemPromptTokens = Math.floor(systemPrompt.length / 3);
    const contentTokens = Math.floor(content.length / 4);
    
    // Total tokens (including message formatting overhead)
    const totalTokens = systemPromptTokens + contentTokens;
    
    // Calculate cost estimate (using the same 3.0 per million tokens pricing)
    const costEstimate = (totalTokens / 1000000 * 3.0).toFixed(6);
    
    // Calculate max safe output tokens - same as in server.py
    const maxSafeOutputTokens = Math.min(64000, 200000 - totalTokens - 5000);
    
    // Return the estimated token count with all fields needed by the frontend
    return res.status(200).json({
      success: true,
      token_count: totalTokens,
      estimated_tokens: totalTokens,
      token_count_str: formatNumberWithCommas(totalTokens),
      cost_estimate: parseFloat(costEstimate),
      estimated_cost: parseFloat(costEstimate),
      cost_estimate_str: '$' + costEstimate,
      message: 'Token count estimated for Anthropic Claude API (includes system prompt).',
      max_safe_output_tokens: maxSafeOutputTokens
    });
    
  } catch (error) {
    // Handle any errors
    console.error('Token analysis error:', error);
    return res.status(500).json({
      success: false,
      error: `Error analyzing tokens: ${error.message}`
    });
  }
};

// Helper function to format numbers with commas
function formatNumberWithCommas(number) {
  if (number === undefined || number === null) {
    return "0";
  }
  return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
} 