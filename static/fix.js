// Add click event to drop area and fix updateHtmlPreview function
document.addEventListener('DOMContentLoaded', function() {
  // Make drop area clickable
  const dropArea = document.getElementById('drop-area');
  if (dropArea) {
    dropArea.addEventListener('click', function() {
      const fileUpload = document.getElementById('file-upload');
      if (fileUpload) {
        fileUpload.click();
      }
    });
    dropArea.classList.add('cursor-pointer');
    console.log('Drop area click handler added');
  }

  // Fix tab switching
  const fileTab = document.getElementById('file-tab');
  const textTab = document.getElementById('text-tab');
  if (fileTab && textTab) {
    // Add additional safety checks to the tab switching logic
    const safeShowHide = function(showElement, hideElement) {
      if (showElement) showElement.classList.remove('hidden');
      if (hideElement) hideElement.classList.add('hidden');
    };
    
    fileTab.addEventListener('click', function() {
      const fileInput = document.getElementById('file-input');
      const textInput = document.getElementById('text-input');
      safeShowHide(fileInput, textInput);
    });
    
    textTab.addEventListener('click', function() {
      const fileInput = document.getElementById('file-input');
      const textInput = document.getElementById('text-input');
      safeShowHide(textInput, fileInput);
    });
  }

  // Fix updateHtmlPreview function
  const originalUpdateHtmlPreview = window.updateHtmlPreview;
  if (typeof originalUpdateHtmlPreview === 'function') {
    window.updateHtmlPreview = function(html) {
      try {
        if (!html) return;
        
        // Update the HTML output element
        const htmlOutput = document.getElementById('html-output');
        if (htmlOutput) {
          htmlOutput.textContent = html;
          
          // Highlight with Prism.js if available
          if (window.Prism) {
            Prism.highlightElement(htmlOutput);
          }
        }
        
        // Update the preview iframe if it exists
        const previewIframe = document.getElementById('preview-iframe');
        if (previewIframe) {
          const blob = new Blob([html], { type: 'text/html' });
          const url = URL.createObjectURL(blob);
          previewIframe.src = url;
        }
        
        // Show result section if available
        const resultSection = document.getElementById('result-section');
        if (resultSection) {
          resultSection.classList.remove('hidden');
        }
      } catch (error) {
        console.error('Error updating HTML preview:', error);
      }
    };
    console.log('updateHtmlPreview function patched');
  }
}); 