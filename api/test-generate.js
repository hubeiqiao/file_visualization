// Test generate function for Vercel that uses minimal Anthropic API tokens
module.exports = async (req, res) => {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle OPTIONS request
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }
  
  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({
      error: 'Method not allowed'
    });
  }
  
  try {
    // Get content from request body
    const body = req.body || {};
    const content = body.content || body.source || '';
    const apiKey = body.api_key || '';
    
    if (!content) {
      return res.status(400).json({ 
        success: false, 
        error: 'Content is required' 
      });
    }
    
    if (!apiKey || !apiKey.startsWith('sk-ant')) {
      return res.status(400).json({ 
        success: false, 
        error: 'Valid API key is required' 
      });
    }
    
    console.log(`Got request with content length: ${content.length}`);
    
    // Truncate content to just 500 characters to minimize token usage
    const truncatedContent = content.length > 500 ? content.substring(0, 500) + '...' : content;
    
    // Start time for measuring elapsed time
    const startTime = Date.now();
    
    try {
      // Import Anthropic SDK
      const { Anthropic } = await import('@anthropic-ai/sdk');
      const anthropic = new Anthropic({
        apiKey: apiKey
      });
      
      // Brief system prompt to minimize token usage
      const systemPrompt = "Generate minimal HTML to confirm the API integration works.";
      
      // Minimal user prompt
      const userPrompt = `Generate a very simple HTML page that confirms the API works. The content is: ${truncatedContent}`;
      
      // Implement retry logic with exponential backoff
      const maxRetries = 5;
      let retryCount = 0;
      let baseDelay = 1000; // Starting delay in milliseconds
      let success = false;
      let response;
      
      while (retryCount <= maxRetries && !success) {
        try {
          console.log(`API call attempt ${retryCount + 1}/${maxRetries + 1}`);
          
          // Call Anthropic API with minimal settings
          response = await anthropic.messages.create({
            model: "claude-sonnet-4-20250514", // Use smaller model to save tokens
            max_tokens: 100, // Minimal output
            temperature: 0.5,
            system: systemPrompt,
            messages: [
              {
                role: "user",
                content: userPrompt
              }
            ]
          });
          
          // If we get here without error, the call was successful
          success = true;
          
        } catch (apiError) {
          console.error(`API error on attempt ${retryCount + 1}:`, apiError);
          
          // Check if it's an overloaded error (529)
          const isOverloaded = 
            apiError.status === 529 || 
            (apiError.response && apiError.response.status === 529) ||
            (apiError.message && apiError.message.includes('529')) ||
            (apiError.message && apiError.message.includes('Overloaded'));
          
          if (isOverloaded && retryCount < maxRetries) {
            retryCount++;
            const waitTime = baseDelay / 1000; // Convert to seconds for display
            console.log(`Anthropic API overloaded. Retrying in ${waitTime}s (attempt ${retryCount}/${maxRetries})`);
            
            // Sleep for the delay period
            await new Promise(resolve => setTimeout(resolve, baseDelay));
            
            // Exponential backoff
            baseDelay *= 2;
            
            // Continue to next attempt
            continue;
          }
          
          // For other errors or if we've exhausted retries, return an error response with HTML
          const errorHtml = `
          <html>
          <head>
            <title>Test Mode - API Error</title>
            <style>
              body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 2rem; max-width: 800px; margin: 0 auto; }
              .error { background-color: #fee; border-left: 4px solid #e53e3e; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
              pre { background-color: #f7fafc; padding: 1rem; border-radius: 4px; overflow-x: auto; }
              h1 { color: #2d3748; }
            </style>
          </head>
          <body>
            <h1>Test Mode - ${isOverloaded ? 'API Overloaded' : 'API Error'}</h1>
            <p>${isOverloaded ? 
              'The Anthropic API is currently experiencing high demand and is overloaded. We tried several times but could not get a response.' : 
              'There was an error calling the Anthropic API:'}</p>
            <div class="error">
              <pre>${apiError.message || 'Unknown error'}</pre>
            </div>
            <p>Please try again later or check your API key.</p>
          </body>
          </html>
          `;
          
          return res.status(200).json({
            success: false,
            error: apiError.message || 'Error calling Anthropic API',
            html: errorHtml,
            code: isOverloaded ? 529 : (apiError.status || 500),
            usage: {
              input_tokens: 0,
              output_tokens: 0,
              thinking_tokens: 0,
              time_elapsed: (Date.now() - startTime) / 1000,
              total_cost: 0
            },
            test_mode: true
          });
        }
      }
      
      // Process successful response
      if (success && response) {
        // Get the response content
        const htmlOutput = response.content[0].text;
        
        // Calculate token usage (estimates)
        const systemPromptTokens = Math.floor(systemPrompt.length / 3);
        const contentTokens = Math.floor(truncatedContent.length / 4);
        const outputTokens = Math.floor(htmlOutput.length / 4);
        
        // Calculate elapsed time
        const elapsedTime = (Date.now() - startTime) / 1000; // Convert to seconds
        
        // Return JSON response with HTML and usage stats
        return res.status(200).json({
          success: true,
          html: htmlOutput,
          usage: {
            input_tokens: systemPromptTokens + contentTokens,
            output_tokens: outputTokens,
            thinking_tokens: 0, // No thinking tokens used in this simplified test
            time_elapsed: elapsedTime,
            total_cost: ((systemPromptTokens + contentTokens + outputTokens) / 1000000 * 3.0)
          },
          test_mode: true,
          message: "Test completed with minimal token usage"
        });
      }
      
    } catch (error) {
      console.error('Error in test generation:', error);
      
      // Generic error fallback HTML
      const fallbackHtml = `
      <html>
      <head>
        <title>Test Mode - Server Error</title>
        <style>
          body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 2rem; max-width: 800px; margin: 0 auto; }
          .error { background-color: #fee; border-left: 4px solid #e53e3e; padding: 1rem; border-radius: 4px; margin: 1rem 0; }
          h1 { color: #2d3748; }
        </style>
      </head>
      <body>
        <h1>Test Mode - Server Error</h1>
        <p>An unexpected error occurred while processing your request:</p>
        <div class="error">
          <p>${error.message || 'Unknown error'}</p>
        </div>
        <p>Please try again later.</p>
      </body>
      </html>
      `;
      
      return res.status(200).json({
        success: false,
        error: `Error in test generation: ${error.message}`,
        html: fallbackHtml,
        usage: {
          input_tokens: 0,
          output_tokens: 0,
          thinking_tokens: 0,
          time_elapsed: (Date.now() - startTime) / 1000,
          total_cost: 0
        },
        test_mode: true
      });
    }
    
  } catch (error) {
    console.error('Unhandled error in test-generate endpoint:', error);
    return res.status(500).json({
      success: false,
      error: `Server error: ${error.message}`,
      html: `<html><body><h1>Test Mode - Server Error</h1><p>${error.message}</p></body></html>`
    });
  }
}; 