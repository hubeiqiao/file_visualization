// Vercel API handler for the main route
module.exports = (req, res) => {
  // Set appropriate headers
  res.setHeader('Content-Type', 'text/html');
  
  // Redirect to the index.html at the root
  res.statusCode = 302;
  res.setHeader('Location', '/index.html');
  res.end();
}; 