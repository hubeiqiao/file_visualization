// Process stream function for Vercel Edge Runtime using Anthropic API directly
export const config = {
  runtime: 'edge',
  regions: ['iad1'], // Force specific US region for more consistent performance
};

export default async function handler(req) {
  // Create a new ReadableStream with a controller to manage the flow
  const stream = new ReadableStream({
    async start(controller) {
      // Create TextEncoder once
      const encoder = new TextEncoder();
      
      // Function to write event to stream
      function writeEvent(eventType, data) {
        // Format in the SSE format expected by the client
        const eventString = `event: ${eventType}\ndata: ${JSON.stringify(data)}\n\n`;
        controller.enqueue(encoder.encode(eventString));
      }
      
      // Flag to track if stream has ended
      let hasEnded = false;
      
      // Function to safely end the stream
      function safeEndStream() {
        if (!hasEnded) {
          try {
            console.log('Safely ending stream');
            writeEvent('stream_end', { message: 'Stream complete' });
            controller.close();
            hasEnded = true;
          } catch (e) {
            console.error('Error ending stream:', e);
          }
        }
      }
      
      // Function to wait
      const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
      
      // Start time for tracking elapsed time
      const startTime = Date.now();
      
      // Create keep-alive timer
      let keepaliveInterval = null;
      let lastEventTime = Date.now();
      
      try {
        // Handle OPTIONS request
        if (req.method === 'OPTIONS') {
          safeEndStream();
          return;
        }
        
        // Only allow POST requests
        if (req.method !== 'POST') {
          writeEvent('error', { error: 'Method not allowed' });
          safeEndStream();
          return;
        }
        
        // Log the start of the request
        console.log('Process-stream request received');
        
        // Get content from request body
        const body = await req.json();
        const content = body.content || body.source || '';
        const apiKey = body.api_key || '';
        const maxTokens = body.max_tokens || 128000;
        const thinkingBudget = body.thinking_budget || 32000;
        const temperature = body.temperature || 0.5;
        const formatPrompt = body.format_prompt || '';
        const testMode = body.test_mode === true;
        
        console.log(`Request params: content length: ${content.length}, maxTokens: ${maxTokens}, temperature: ${temperature}, testMode: ${testMode}`);
        
        if (!content) {
          console.error('Content is required but was empty');
          writeEvent('error', { error: 'Content is required' });
          safeEndStream();
          return;
        }
        
        if (!apiKey || !apiKey.startsWith('sk-ant')) {
          console.error('Invalid API key format');
          writeEvent('error', { error: 'Valid API key required' });
          safeEndStream();
          return;
        }
        
        // Generate messageId
        const messageId = crypto.randomUUID();
        console.log(`Generated message ID: ${messageId}`);
        
        // Send start event immediately (crucial)
        writeEvent('stream_start', { message: 'Stream starting' });
        
        // Setup frequently recurring keepalive to ensure the connection stays open
        // Send initial keepalive message right away
        writeEvent('keepalive', { timestamp: Date.now() / 1000 });
        lastEventTime = Date.now();
        
        // Setup keepalive interval - frequent to prevent timeouts
        keepaliveInterval = setInterval(() => {
          try {
            if (!hasEnded) {
              const now = Date.now();
              // Only send if it's been more than 300ms since last event
              if (now - lastEventTime > 300) {
                writeEvent('keepalive', { timestamp: now / 1000 });
                lastEventTime = now;
                console.log('Sent keepalive at', new Date().toISOString());
              }
            } else {
              clearInterval(keepaliveInterval);
            }
          } catch (e) {
            console.error('Error sending keepalive:', e);
            clearInterval(keepaliveInterval);
          }
        }, 500);
        
        // System prompt - use the full prompt for best results
        const systemPrompt = "I will provide you with a file or a content, analyze its content, and transform it into a visually appealing and well-structured webpage.### Content Requirements* Maintain the core information from the original file while presenting it in a clearer and more visually engaging format.⠀Design Style* Follow a modern and minimalistic design inspired by Linear App.* Use a clear visual hierarchy to emphasize important content.* Adopt a professional and harmonious color scheme that is easy on the eyes for extended reading.⠀Technical Specifications* Use HTML5, TailwindCSS 3.0+ (via CDN), and necessary JavaScript.* Implement a fully functional dark/light mode toggle, defaulting to the system setting.* Ensure clean, well-structured code with appropriate comments for easy understanding and maintenance.⠀Responsive Design* The page must be fully responsive, adapting seamlessly to mobile, tablet, and desktop screens.* Optimize layout and typography for different screen sizes.* Ensure a smooth and intuitive touch experience on mobile devices.⠀Icons & Visual Elements* Use professional icon libraries like Font Awesome or Material Icons (via CDN).* Integrate illustrations or charts that best represent the content.* Avoid using emojis as primary icons.* Check if any icons cannot be loaded.⠀User Interaction & ExperienceEnhance the user experience with subtle micro-interactions:* Buttons should have slight enlargement and color transitions on hover.* Cards should feature soft shadows and border effects on hover.* Implement smooth scrolling effects throughout the page.* Content blocks should have an elegant fade-in animation on load.⠀Performance Optimization* Ensure fast page loading by avoiding large, unnecessary resources.* Use modern image formats (WebP) with proper compression.* Implement lazy loading for content-heavy pages.⠀Output Requirements* Deliver a fully functional standalone HTML file, including all necessary CSS and JavaScript.* Ensure the code meets W3C standards with no errors or warnings.* Maintain consistent design and functionality across different browsers.⠀Create the most effective and visually appealing webpage based on the uploaded file's content type (document, data, images, etc.).";
        
        // Format user content - use smaller chunk for Vercel and simplify
        let userContent;
        if (testMode) {
          // For test mode, use minimal content
          userContent = `This is a test mode request. Generate a simple HTML page saying "Test successful".`;
        } else {
          // For regular mode, use a smaller portion of content for Vercel
          const contentSample = content.substring(0, Math.min(content.length, 20000));
          userContent = formatPrompt ? 
            `${formatPrompt}\n\nGenerate HTML for this content: ${contentSample}` :
            `Generate HTML for this content: ${contentSample}`;
        }
        
        console.log(`User content prepared, length: ${userContent.length}`);
        
        try {
          console.log('Preparing to call Anthropic API directly...');
          
          // Add retry logic with exponential backoff
          let maxRetries = 3;
          let retryCount = 0;
          let backoffTime = 1000; // Start with 1 second (in ms)
          let success = false;
          let htmlOutput = '';
          let chunkCount = 0;
          
          // Use the correct Claude 3.7 model as requested
          const model = testMode ? 'claude-3-haiku-20240307' : 'claude-3-7-sonnet-20250219';
          const tokenLimit = testMode ? 1000 : 60000;
          
          writeEvent('status', {
            message: `Using model: ${model} with max tokens: ${tokenLimit}`
          });
          
          while (retryCount <= maxRetries && !success && !hasEnded) {
            try {
              console.log(`Attempt ${retryCount + 1}/${maxRetries + 1} to create stream`);
              
              // Create controller to abort request if needed
              const abortController = new AbortController();
              const signal = abortController.signal;
              
              // For debugging - generate a simple HTML directly instead of calling the API
              if (testMode) {
                console.log('Using test mode - generating simple HTML');
                
                // Create a simple HTML file
                htmlOutput = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated Test Visualization</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; }
    h1 { color: #3b82f6; }
  </style>
</head>
<body>
  <h1>Test Visualization Generated Successfully</h1>
  <p>This is a test HTML file generated directly from the Vercel serverless function.</p>
  <p>Your content length: ${content.length} characters</p>
  <p>Generated at: ${new Date().toISOString()}</p>
</body>
</html>`;
                
                // Send some fake chunks to simulate streaming
                for (let i = 0; i < 3; i++) {
                  await sleep(300);
                  writeEvent('content', {
                    type: 'content_block_delta',
                    chunk_id: `${messageId}_${i}`,
                    delta: {
                      text: `Chunk ${i} of test HTML...`
                    }
                  });
                  
                  writeEvent('keepalive', {
                    timestamp: Date.now() / 1000,
                    chunk_count: i
                  });
                }
                
                success = true;
                break;
              }
              
              // Send status update to client
              writeEvent('status', {
                message: `Connecting to Anthropic API...`
              });
              
              // Log the exact request we're about to make (debugging)
              const requestBody = {
                model: model,
                max_tokens: tokenLimit,
                temperature: temperature,
                system: systemPrompt,
                messages: [{ role: 'user', content: userContent }],
                stream: true
              };
              
              // Don't log the entire content, just length
              console.log(`API request: model=${model}, max_tokens=${tokenLimit}, content_length=${userContent.length}`);
              
              // Call Anthropic API with correct headers for Claude 3.7
              const response = await fetch('https://api.anthropic.com/v1/messages', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'x-api-key': apiKey,
                  'anthropic-version': '2023-06-01'
                },
                body: JSON.stringify(requestBody),
                signal
              }).catch(error => {
                console.error('Fetch API error:', error);
                throw error;
              });
              
              if (!response.ok) {
                const errorText = await response.text();
                console.error(`Anthropic API error: ${response.status}`, errorText);
                writeEvent('status', {
                  message: `API error: ${response.status} - ${errorText.substring(0, 100)}`
                });
                throw new Error(`Anthropic API error: ${response.status} ${errorText}`);
              }
              
              console.log('Stream created, processing chunks...');
              
              // Process the response as a stream
              const reader = response.body.getReader();
              const decoder = new TextDecoder();
              let buffer = ''; // Buffer to handle partial chunks
              
              // Send status update
              writeEvent('status', {
                message: 'Connected to API, receiving response...'
              });
              
              // Process chunks in a try-catch block
              try {
                // Process chunks
                while (true) {
                  const { done, value } = await reader.read();
                  
                  // Update last event time
                  lastEventTime = Date.now();
                  
                  // Skip processing if stream has ended or done
                  if (done || hasEnded) {
                    console.log('Stream ended or closed');
                    break;
                  }
                  
                  // Decode the chunk
                  const chunk = decoder.decode(value, { stream: true });
                  buffer += chunk;
                  
                  // For debugging, log raw chunk data occasionally
                  if (chunkCount % 20 === 0) {
                    console.log(`Raw chunk data (first 100 chars): ${chunk.substring(0, 100)}`);
                  }
                  
                  // Split on double newlines to get complete SSE events
                  const events = buffer.split('\n\n');
                  
                  // Process all complete events, and keep the last partial event in the buffer
                  buffer = events.pop() || '';
                  
                  for (const event of events) {
                    if (!event.trim()) continue;
                    
                    const lines = event.split('\n');
                    let eventType = '';
                    let eventData = '';
                    
                    // Extract event type and data
                    for (const line of lines) {
                      if (line.startsWith('event:')) {
                        eventType = line.slice(6).trim();
                      } else if (line.startsWith('data:')) {
                        eventData = line.slice(5).trim();
                      }
                    }
                    
                    // Skip if no data
                    if (!eventData) continue;
                    
                    // Handle ping events specially
                    if (eventType === 'ping') {
                      console.log('Received ping event');
                      continue;
                    }
                    
                    try {
                      const parsed = JSON.parse(eventData);
                      
                      // Process content block delta (the text chunks)
                      if (parsed.type === 'content_block_delta' && 
                          parsed.delta && 
                          parsed.delta.type === 'text_delta') {
                        const textChunk = parsed.delta.text;
                        htmlOutput += textChunk;
                        chunkCount++;
                        
                        // Send chunk in content_block_delta format to match server.py
                        writeEvent('content', { 
                          type: 'content_block_delta', 
                          chunk_id: `${messageId}_${chunkCount}`,
                          delta: {
                            text: textChunk
                          }
                        });
                        
                        // More frequent keepalives during processing
                        writeEvent('keepalive', { 
                          timestamp: Date.now() / 1000,
                          chunk_count: chunkCount
                        });
                        
                        // Debug logging
                        if (chunkCount % 10 === 0) {
                          console.log(`Processed ${chunkCount} chunks, current length: ${htmlOutput.length}`);
                        }
                      } else if (parsed.type === 'thinking') {
                        // Pass thinking update to client
                        writeEvent('thinking_update', {
                          thinking: parsed
                        });
                      } else if (parsed.type === 'message_start') {
                        console.log('Message start received');
                        writeEvent('keepalive', { timestamp: Date.now() / 1000 });
                      } else if (parsed.type === 'message_delta') {
                        if (parsed.delta && parsed.delta.stop_reason) {
                          console.log(`Message completion: ${parsed.delta.stop_reason}`);
                        }
                      } else if (parsed.type === 'message_stop') {
                        // Final message completion
                        console.log('Message stop received');
                        
                        // Get actual usage from the API
                        try {
                          // Make a request to get the usage from the message ID
                          const usageResponse = await fetch(`https://api.anthropic.com/v1/messages/${parsed.message.id}`, {
                            method: 'GET',
                            headers: {
                              'x-api-key': apiKey,
                              'anthropic-version': '2023-06-01'
                            }
                          });
                          
                          if (usageResponse.ok) {
                            const usageData = await usageResponse.json();
                            console.log('Got usage data from Anthropic API:', usageData.usage);
                            
                            // Send message complete event with actual usage
                            writeEvent('message_complete', {
                              message: 'Content generation complete',
                              usage: {
                                input_tokens: usageData.usage.input_tokens,
                                output_tokens: usageData.usage.output_tokens,
                                total_cost: (usageData.usage.input_tokens / 1000000) * 3.0 + 
                                           (usageData.usage.output_tokens / 1000000) * 15.0
                              }
                            });
                          } else {
                            console.error('Failed to get usage data:', await usageResponse.text());
                            // Fall back to estimation if API request fails
                            estimateAndSendUsage();
                          }
                        } catch (usageErr) {
                          console.error('Error getting usage data:', usageErr);
                          // Fall back to estimation if API request fails
                          estimateAndSendUsage();
                        }
                        
                        // Mark as successful
                        success = true;
                      } else {
                        console.log(`Other event type: ${parsed.type}`);
                      }
                    } catch (e) {
                      console.error('Error parsing event data:', e);
                      console.error('Event data:', eventData.substring(0, 200));
                    }
                  }
                }
                
                // If we've completed successfully, break the retry loop
                if (success) {
                  console.log(`HTML generation complete, length: ${htmlOutput.length} characters`);
                  break;
                }
              } catch (streamError) {
                console.error('Error during stream processing:', streamError);
                writeEvent('status', {
                  message: `Stream error: ${streamError.message}`
                });
                throw streamError; // Rethrow to be caught by the retry logic
              }
              
            } catch (requestError) {
              console.error('Error during request/streaming:', requestError);
              
              // Include more detailed error info in the status
              const errorMsg = requestError.message || 'Unknown error';
              writeEvent('status', {
                message: `API request error: ${errorMsg.substring(0, 100)}`
              });
              
              // Check if we've already tried the maximum number of times
              if (retryCount >= maxRetries) {
                writeEvent('error', { 
                  error: `Failed after ${maxRetries + 1} attempts: ${requestError.message}` 
                });
                
                // Fall back to a simple HTML if all API attempts fail
                console.log('All API attempts failed, falling back to basic HTML');
                htmlOutput = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fallback Visualization</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; }
    h1 { color: #ef4444; }
    pre { background: #f5f5f5; padding: 1rem; border-radius: 0.5rem; overflow: auto; }
  </style>
</head>
<body>
  <h1>API Connection Issue Detected</h1>
  <p>The application couldn't connect to the Anthropic API, but has generated this fallback HTML.</p>
  <p>Error details: ${requestError.message}</p>
  <p>Generated at: ${new Date().toISOString()}</p>
  <h2>Your Content Preview:</h2>
  <pre>${content.substring(0, 500)}${content.length > 500 ? '...' : ''}</pre>
</body>
</html>`;
                success = true;
                break;
              }
              
              // Increment retry count and apply exponential backoff
              retryCount++;
              const jitter = Math.random() * 500;
              backoffTime = Math.min(10000, backoffTime * 2) + jitter;
              
              console.log(`Retrying after ${backoffTime}ms...`);
              
              // Let the client know we're retrying
              writeEvent('status', { 
                message: `Request attempt ${retryCount}/${maxRetries + 1} failed, retrying in ${Math.round(backoffTime/1000)}s...` 
              });
              
              // Wait before the next retry
              await sleep(backoffTime);
            }
          }
          
          // Process the HTML output before completing
          if (htmlOutput) {
            // Create a complete HTML document if it doesn't look like one already
            let finalHtml = htmlOutput;
            if (!finalHtml.trim().toLowerCase().startsWith('<!doctype html>') && 
                !finalHtml.trim().toLowerCase().startsWith('<html')) {
              finalHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated Visualization</title>
</head>
<body>
  ${finalHtml}
</body>
</html>`;
            }
            
            // Calculate approximate token usage for analytics
            function estimateAndSendUsage() {
              const contentLength = content.length;
              const outputLength = htmlOutput.length;
              // Rough token estimates based on character count (about 4 chars per token)
              const inputTokens = Math.ceil(contentLength / 4);
              const outputTokens = Math.ceil(outputLength / 4);
              const totalCost = (inputTokens / 1000000) * 3.0 + (outputTokens / 1000000) * 15.0;
              
              // Include token usage in the event
              const usage = {
                input_tokens: inputTokens,
                output_tokens: outputTokens,
                total_cost: totalCost
              };
              
              // Send message_complete event with usage statistics
              writeEvent('message_complete', {
                message: 'Content generation complete',
                usage: usage
              });
              
              console.log('Sent estimated usage stats:', usage);
            }
            
            // Use function defined above
            estimateAndSendUsage();
            
            // Send complete content event with the full HTML
            writeEvent('content_complete', { 
              content: finalHtml,
              length: finalHtml.length,
              chunks: chunkCount
            });
            
            console.log(`Content complete sent, length: ${finalHtml.length}`);
          } else {
            // Even if we don't have HTML output, generate a simple fallback
            const fallbackHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Generated Visualization</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; }
    h1 { color: #dc2626; }
  </style>
</head>
<body>
  <h1>Error Generating Visualization</h1>
  <p>There was an error generating the visualization from the provided content.</p>
  <p>Please try again or use a different API key.</p>
</body>
</html>`;
            
            // Calculate approximate token usage for analytics
            estimateAndSendUsage();
            
            // Send complete content event with the fallback HTML
            writeEvent('content_complete', { 
              content: fallbackHtml,
              length: fallbackHtml.length,
              chunks: chunkCount
            });
          }
          
          // Complete the stream after sending all the data
          const elapsed = (Date.now() - startTime) / 1000;
          writeEvent('complete', { 
            message: 'Stream processing complete',
            elapsed: elapsed,
            html_length: htmlOutput.length || 0,
            success: true
          });
          
          console.log(`Generation complete. Elapsed time: ${elapsed}s`);
          
        } catch (error) {
          console.error('Error in stream processing:', error);
          
          writeEvent('error', { 
            error: `Stream processing error: ${error.message}` 
          });
          
          // Generate fallback HTML for error case
          const errorHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Error Visualization</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; }
    h1 { color: #dc2626; }
    .error { background: #fee2e2; padding: 1rem; border-radius: 0.5rem; }
  </style>
</head>
<body>
  <h1>Error Processing Request</h1>
  <div class="error">
    <p>Error message: ${escape(error.message || 'Unknown error')}</p>
  </div>
  <p>Please try again or check your API key.</p>
</body>
</html>`;

          // Calculate approximate token usage for analytics
          estimateAndSendUsage();
          
          // Send complete content event with the error HTML
          writeEvent('content_complete', { 
            content: errorHtml,
            length: errorHtml.length,
            error: true
          });
          
          safeEndStream();
        } finally {
          // Ensure timer is cleaned up
          if (keepaliveInterval) {
            clearInterval(keepaliveInterval);
          }
          
          // Always send a final event indicating the stream is done
          writeEvent('stream_end', { 
            message: 'Stream finished', 
            timestamp: Date.now() / 1000,
            success: success || false
          });
        }
      } catch (outerError) {
        console.error('Fatal error in request handler:', outerError);
        
        // Send error event
        writeEvent('error', {
          error: `Fatal error: ${outerError.message || 'Unknown error'}`,
          stack: outerError.stack
        });
        
        // Generate fatal error HTML
        const fatalHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fatal Error</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; }
    h1 { color: #dc2626; }
    .error { background: #fee2e2; padding: 1rem; border-radius: 0.5rem; }
  </style>
</head>
<body>
  <h1>Fatal Error</h1>
  <div class="error">
    <p>A fatal error occurred while processing your request.</p>
    <p>Error: ${escape(outerError.message || 'Unknown error')}</p>
  </div>
  <p>Please try again later.</p>
</body>
</html>`;

        // Calculate approximate token usage for analytics
        estimateAndSendUsage();
        
        // Send complete content event with the fatal error HTML
        writeEvent('content_complete', { 
          content: fatalHtml,
          length: fatalHtml.length,
          fatal_error: true
        });
        
        safeEndStream();
      }
    }
  });
  
  // Return the stream as the response
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}

// Helper to escape HTML
function escape(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
} 