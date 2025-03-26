console.log("APP.JS LOADED", new Date().toISOString());

// DOM Elements
const $ = document.querySelector.bind(document);
const $$ = document.querySelectorAll.bind(document);

// API configuration - Make sure this is set correctly
const API_URL = window.location.origin;
console.log("API_URL set to:", API_URL);
const ANTHROPIC_API_KEY_STORAGE_KEY = 'claude_visualizer_api_key'; // Keep the original key name for backward compatibility
const GEMINI_API_KEY_STORAGE_KEY = 'gemini_visualizer_api_key'; // New storage key for Gemini
const API_PROVIDER_STORAGE_KEY = 'visualizer_api_provider';

// Constants for stream handling
const MAX_RECONNECT_ATTEMPTS = 10; // Increased from default
const RECONNECT_DELAY = 1000; // 1 second
const MAX_SEGMENT_SIZE = 16384; // 16KB to match server setting
const MAX_HTML_BUFFER_SIZE = 2 * 1024 * 1024; // 2MB before using incremental rendering

// Global variables
let generatedHtml = ''; // Store the generated HTML
let reconnectAttempts = 0;
let currentSessionId = null;
let lastChunkId = null;
let chunkCount = 0;

// Elements
const elements = {
    // Theme
    themeToggle: $('#theme-toggle'),
    
    // API Key
    apiKeyInput: $('#api-key'),
    validateKeyBtn: $('#validate-key'),
    keyStatus: $('#key-status'),
    
    // Input Tabs
    fileTab: $('#file-tab'),
    textTab: $('#text-tab'),
    fileInput: $('#file-input'),
    textInput: $('#text-input'),
    
    // File Upload
    dropArea: $('#drop-area'),
    fileUpload: $('#file-upload'),
    fileInfo: $('#file-info'),
    inputText: $('#input-text'),
    
    // Additional Prompt
    additionalPrompt: $('#additional-prompt'),
    
    // Model Parameters
    temperature: $('#temperature'),
    temperatureValue: $('#temperature-value'),
    temperatureReset: $('#reset-temp'),
    maxTokens: $('#max-tokens'),
    maxTokensValue: $('#max-tokens-value'),
    maxTokensReset: $('#reset-max-tokens'),
    thinkingBudget: $('#thinking-budget'),
    thinkingBudgetValue: $('#thinking-budget-value'),
    thinkingBudgetReset: $('#reset-thinking-budget'),
    
    // Test Mode
    testModeToggle: $('#test-mode'),
    testModeIndicator: $('#test-mode-indicator'),
    
    // Generate
    generateBtn: $('#generate-btn'),
    generateError: $('#generate-error'),
    
    // Processing
    processingStatus: $('#processing-status'),
    processingText: $('#processing-text'),
    processingIcon: $('#processing-icon'),
    elapsedTime: $('#elapsed-time'),
    progressBar: $('#progress-bar'),
    
    // Results
    resultSection: $('#result-section'),
    inputTokens: $('#input-tokens'),
    outputTokens: $('#output-tokens'),
    totalCost: $('#total-cost'),
    
    // Output
    previewIframe: $('#preview-iframe'),
    htmlOutput: $('#html-output'),
    copyHtml: $('#copy-html'),
    downloadHtml: $('#download-html'),
    openPreview: $('#open-preview'),
    
    // Token Info
    tokenInfo: $('#tokenInfo'),
    thinkingOutput: $('#thinking-output'),
    statusMessage: $('#status-message'),
};

// State
let state = {
    activeTab: 'file',
    apiKey: localStorage.getItem(ANTHROPIC_API_KEY_STORAGE_KEY) || '',
    apiProvider: localStorage.getItem(API_PROVIDER_STORAGE_KEY) || 'gemini', // Default to Gemini instead of Anthropic
    apiKeyValidated: false,
    file: null,
    fileContent: '',
    textContent: '',
    temperature: 1.0,
    maxTokens: 128000,
    thinkingBudget: 32000,
    processing: false,
    generatedHtml: '',
    fileName: '',
    startTime: null,
    elapsedTimeInterval: null,
    testMode: false
};

// Function to update processing text
function setProcessingText(text) {
    // Only update the in-page processing text
    if (elements.processingText) {
        elements.processingText.textContent = text;
    }
}

// Initialize the app
function init() {
    console.log("Initializing app...");
    
    // Always use light theme
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme', 'light');
    
    // Reset usage statistics to clear any previously stored values
    resetUsageStatistics();
    
    // Reset token stats display
    resetTokenStats();
    
    // Set default API provider to Gemini
    state.apiProvider = localStorage.getItem(API_PROVIDER_STORAGE_KEY) || 'gemini';
    
    // Set the radio button to match the saved provider
    const radioBtns = document.querySelectorAll('input[name="api-provider"]');
    radioBtns.forEach(btn => {
        if (btn.value === state.apiProvider) {
            btn.checked = true;
        }
    });
    
    // Update UI based on selected provider
    updateApiProviderInfo(state.apiProvider);
    updateUIForApiProvider(state.apiProvider);
    
    // Load saved API key based on the selected provider
    const storageKey = state.apiProvider === 'anthropic' ? ANTHROPIC_API_KEY_STORAGE_KEY : GEMINI_API_KEY_STORAGE_KEY;
    const savedApiKey = localStorage.getItem(storageKey) || '';
    
    if (savedApiKey && elements.apiKeyInput) {
        elements.apiKeyInput.value = savedApiKey;
        state.apiKey = savedApiKey; // Make sure we update the state
    }
    
    // Setup event listeners
    setupEventListeners();
    
    // Set text input as active
    state.activeTab = 'text';
    
    // Initialize state
    updateGenerateButtonState();
    
    // Load and display usage statistics
    loadUsageStatistics();
    
    // Ensure the generate button state is correct
    setTimeout(updateGenerateButtonState, 200);
    
    // Force enable the generate button for testing
    setTimeout(() => {
        console.log('Forcefully ensuring generate button is enabled');
        const generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            // Force visual style regardless of conditions
            generateBtn.disabled = false;
            generateBtn.classList.remove('bg-gray-300', 'text-gray-500', 'cursor-not-allowed');
            generateBtn.classList.add('bg-primary-500', 'hover:bg-primary-600', 'text-white', 'cursor-pointer');
            generateBtn.style.pointerEvents = 'auto';
            
            // Make sure event handler is attached
            if (!generateBtn._hasDirectHandler) {
                generateBtn.onclick = function(e) {
                    console.log('Generate button clicked via direct handler!');
                    e.preventDefault();
                    
                    if (typeof generateWebsite === 'function') {
                        generateWebsite();
                    } else {
                        console.error('generateWebsite function not found!');
                        alert('Error: Generation function not found. Please check the console.');
                    }
                    return false;
                };
                generateBtn._hasDirectHandler = true;
            }
        } else {
            console.error('Generate button not found in setTimeout!');
        }
    }, 500);
    
    // Force enable all buttons as a fallback
    setTimeout(() => {
        document.querySelectorAll('button').forEach(button => {
            button.style.pointerEvents = 'auto';
            button.disabled = false;
        });
        console.log("All buttons forcefully enabled as fallback");
    }, 1000);
    
    console.log("App initialized");
}

// Format cost to display either a dollar amount or dash if zero
function formatCostDisplay(cost) {
    if (!cost || cost === 0 || isNaN(cost)) {
        return '-';
    }
    return `$${cost.toFixed(4)}`;
}

// Update all cost display logic to use this helper
function loadUsageStatistics() {
    try {
        // Get stats from localStorage
        const stats = JSON.parse(localStorage.getItem('fileVisualizerStats') || '{"totalRuns":0,"totalTokens":0,"totalCost":0}');
        
        // Update the stats display
        if (document.getElementById('total-runs')) {
            document.getElementById('total-runs').textContent = stats.totalRuns.toLocaleString();
        }
        
        if (document.getElementById('total-tokens')) {
            document.getElementById('total-tokens').textContent = stats.totalTokens.toLocaleString();
        }
        
        if (document.getElementById('total-cost')) {
            document.getElementById('total-cost').textContent = formatCostDisplay(stats.totalCost);
        }
        
        return stats;
    } catch (e) {
        console.error('Error loading usage statistics:', e);
        return { totalRuns: 0, totalTokens: 0, totalCost: 0 };
    }
}

// Add a function to reset statistics (can be called for testing)
function resetUsageStatistics() {
    try {
        localStorage.setItem('fileVisualizerStats', JSON.stringify({
            totalRuns: 0,
            totalTokens: 0,
            totalCost: 0
        }));
        loadUsageStatistics(); // Reload the stats display
        console.log('Usage statistics have been reset');
    } catch (e) {
        console.error('Error resetting usage statistics:', e);
    }
}

// Event listeners
function setupEventListeners() {
    console.log("Setting up event listeners...");
    
    // API key input
    if (elements.apiKeyInput) {
        elements.apiKeyInput.addEventListener('input', handleApiKeyInput);
        elements.apiKeyInput.addEventListener('blur', validateApiKey);
    }
    
    // API key validate button
    if (elements.validateKeyBtn) {
        elements.validateKeyBtn.addEventListener('click', validateApiKey);
    }
    
    // Text input
    if (elements.inputText) {
        elements.inputText.addEventListener('input', handleTextInput);
    }
    
    // Range inputs
    if (elements.temperature) {
        elements.temperature.addEventListener('input', updateTemperature);
    }
    
    if (document.getElementById('reset-temp')) {
        document.getElementById('reset-temp').addEventListener('click', resetTemperature);
    }
    
    if (elements.maxTokens) {
        elements.maxTokens.addEventListener('input', updateMaxTokens);
    }
    
    if (document.getElementById('reset-max-tokens')) {
        document.getElementById('reset-max-tokens').addEventListener('click', resetMaxTokens);
    }
    
    if (elements.thinkingBudget) {
        elements.thinkingBudget.addEventListener('input', updateThinkingBudget);
    }
    
    if (document.getElementById('reset-thinking-budget')) {
        document.getElementById('reset-thinking-budget').addEventListener('click', resetThinkingBudget);
    }
    
    // Generate
    if (elements.generateBtn) {
        elements.generateBtn.addEventListener('click', startGeneration);
    }
    
    // Output actions
    if (elements.copyHtml) {
        elements.copyHtml.addEventListener('click', copyHtmlToClipboard);
    }
    if (elements.downloadHtml) {
        elements.downloadHtml.addEventListener('click', downloadHtmlFile);
    }
    if (elements.openPreview) {
        elements.openPreview.addEventListener('click', openPreviewInNewTab);
    }
    
    // Check for iOS Safari for special mobile handling
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    if (isIOS) {
        document.body.classList.add('ios-device');
    }
    
    console.log("Event listeners set up");
    
    // API provider selection
    const apiProviderRadios = document.querySelectorAll('input[name="api-provider"]');
    apiProviderRadios.forEach(radio => {
        radio.addEventListener('change', handleApiProviderChange);
    });
}

// Toggle theme between light and dark
function toggleTheme() {
    console.log('Toggling theme');
    const html = document.documentElement;
    const sunIcon = document.querySelector('.fa-sun');
    const moonIcon = document.querySelector('.fa-moon');
    
    if (html.classList.contains('dark')) {
        html.classList.remove('dark');
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
        localStorage.setItem('theme', 'light');
    } else {
        html.classList.add('dark');
        sunIcon.classList.add('hidden');
        moonIcon.classList.remove('hidden');
        localStorage.setItem('theme', 'dark');
    }
}

// API Key Handling
async function validateApiKey() {
    console.log('Validating API key...');
    const apiKey = elements.apiKeyInput.value.trim();
    const apiProvider = state.apiProvider;
    
    if (!apiKey) {
        showNotification('Please enter an API key', 'error');
        return null;
    }
    
    // Show immediate feedback that validation is in progress
    showToast('Validating API key...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/api/validate-key`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                api_key: apiKey,
                api_type: apiProvider
            })
        });
        
        // Get response text once
        let responseData;
        try {
            responseData = await response.text();
            
            // Try to parse as JSON
            let data;
            try {
                data = JSON.parse(responseData);
            } catch (parseError) {
                console.error('Failed to parse response as JSON:', parseError);
                console.error('Raw response:', responseData);
                
                // Create a minimal response object for consistent handling
                data = { 
                    valid: false, 
                    message: `Server returned invalid JSON. Status: ${response.status}. Please try again or contact support.` 
                };
            }
            
            if (response.ok && data.valid) {
                console.log('API key is valid');
                // Save the API key to the appropriate storage key
                const storageKey = apiProvider === 'anthropic' ? ANTHROPIC_API_KEY_STORAGE_KEY : GEMINI_API_KEY_STORAGE_KEY;
                localStorage.setItem(storageKey, apiKey);
                state.apiKey = apiKey;
                showNotification(data.message || 'API key is valid', 'success');
                updateKeyStatus('valid');
                return apiKey;
            } else {
                console.error('API key validation failed:', data.message || 'Unknown error');
                showNotification(data.message || 'Invalid API key', 'error');
                updateKeyStatus('invalid');
                return null;
            }
        } catch (readError) {
            throw new Error(`Failed to read response: ${readError.message}`);
        }
    } catch (error) {
        console.error('Error validating API key:', error);
        showNotification('Error validating API key: ' + error.message, 'error');
        updateKeyStatus('invalid');
        return null;
    }
}

function updateKeyStatus(status) {
    if (!elements.keyStatus) return;
    
    elements.keyStatus.classList.remove('hidden');
    elements.keyStatus.innerHTML = status === 'valid' 
        ? '<span class="text-green-500">✓ Valid API Key</span>'
        : '<span class="text-red-500">✗ Invalid API Key</span>';
}

function handleApiKeyInput(e) {
    const apiKey = e.target.value.trim();
    state.apiKey = apiKey;
    
    // Save the API key to the appropriate storage key
    const storageKey = state.apiProvider === 'anthropic' ? ANTHROPIC_API_KEY_STORAGE_KEY : GEMINI_API_KEY_STORAGE_KEY;
    localStorage.setItem(storageKey, apiKey);
    
    updateGenerateButtonState();
}

// Tab Switching
function switchTab(tab) {
    console.log('Switching to tab:', tab);
    
    // If switching tabs and there's content, confirm with the user
    if (tab === 'file' && state.textContent && state.activeTab === 'text') {
        if (!confirm('Switching tabs will clear your text input. Continue?')) {
            return;  // User cancelled the tab switch
        }
    } else if (tab === 'text' && state.fileContent && state.activeTab === 'file') {
        if (!confirm('Switching tabs will clear your file upload. Continue?')) {
            return;  // User cancelled the tab switch
        }
    }
    
    state.activeTab = tab;
    
    // Check for required tab elements using the correct element references
    if (!elements.fileTab || !elements.textTab || !elements.fileInput || !elements.textInput) {
        console.error('Tab elements not found');
        return;
    }
    
    if (tab === 'file') {
        elements.fileTab.classList.remove('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        elements.fileTab.classList.add('bg-primary-100', 'dark:bg-primary-900', 'text-primary-700', 'dark:text-primary-300');
        
        elements.textTab.classList.remove('bg-primary-100', 'dark:bg-primary-900', 'text-primary-700', 'dark:text-primary-300');
        elements.textTab.classList.add('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        
        elements.fileInput.classList.remove('hidden');
        elements.textInput.classList.add('hidden');
        
        // Clear text input content when switching to file tab
        if (elements.inputText) {
            // Don't actually clear the UI element - just don't use it when generating
            state.textContent = '';
        }
    } else {
        elements.textTab.classList.remove('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        elements.textTab.classList.add('bg-primary-100', 'dark:bg-primary-900', 'text-primary-700', 'dark:text-primary-300');
        
        elements.fileTab.classList.remove('bg-primary-100', 'dark:bg-primary-900', 'text-primary-700', 'dark:text-primary-300');
        elements.fileTab.classList.add('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        
        elements.textInput.classList.remove('hidden');
        elements.fileInput.classList.add('hidden');
        
        // Clear file data when switching to text tab
        state.file = null;
        state.fileContent = '';
        state.fileName = '';
        
        // Also clear the file upload UI
        if (elements.fileInfo) {
            elements.fileInfo.classList.add('hidden');
        }
        
        if (elements.fileUpload) {
            elements.fileUpload.value = '';
        }
        
        // Trigger token analysis when switching to text tab if there's text
        if (elements.inputText && elements.inputText.value.trim()) {
            state.textContent = elements.inputText.value.trim();
            analyzeTokens(state.textContent);
        } else if (elements.tokenInfo) {
            // Clear token info if there's no text
            elements.tokenInfo.innerHTML = '';
        }
    }
    
    updateGenerateButtonState();
}

// File Upload
function setupDragAndDrop() {
    const dropArea = elements.dropArea;
    if (!dropArea) {
        console.error('Drop area element not found');
        return;
    }
    
    // Add click event to dropArea to trigger file upload dialog
    dropArea.addEventListener('click', function() {
        if (elements.fileUpload) {
            elements.fileUpload.click();
        }
    });
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener('drop', handleDrop, false);
    });
    
    function highlight() {
        dropArea.classList.add('border-primary-500', 'dark:border-primary-400', 'bg-primary-50', 'dark:bg-primary-900/20');
    }
    
    function unhighlight() {
        dropArea.classList.remove('border-primary-500', 'dark:border-primary-400', 'bg-primary-50', 'dark:bg-primary-900/20');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        
        if (file) {
            handleFile(file);
        }
    }
}

function handleFileUpload(e) {
    console.log('Handling file upload...');
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    console.log('Processing file:', file.name);
    state.file = file;
    state.fileName = file.name;
    
    if (!elements.fileInfo) {
        console.error('File info element not found');
        return;
    }
    
    // Show file info
    elements.fileInfo.innerHTML = `
        <div class="flex items-center p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg">
            <i class="fas fa-file-alt text-primary-500 mr-3 text-xl"></i>
            <div class="flex-1">
                <p class="font-medium">${file.name}</p>
                <p class="text-sm text-gray-500 dark:text-gray-400">${formatFileSize(file.size)}</p>
            </div>
            <button class="text-red-500 hover:text-red-600 p-1" id="remove-file">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    elements.fileInfo.classList.remove('hidden');
    
    // Add event listener to remove button
    const removeButton = $('#remove-file');
    if (removeButton) {
        removeButton.addEventListener('click', removeFile);
    }
    
    // Get file extension
    const fileExt = file.name.split('.').pop().toLowerCase();
    
    // Handle different file types appropriately
    if (fileExt === 'pdf') {
        // For PDF files, we need special handling
        // Show a loading indicator while processing
        if (elements.tokenInfo) {
            elements.tokenInfo.innerHTML = `
                <div class="token-analysis loading">
                    <h3>Processing PDF</h3>
                    <p>Extracting text from PDF file...</p>
                </div>
            `;
        }
        
        // Read as array buffer for binary files
        const reader = new FileReader();
        reader.onload = function(e) {
            console.log('PDF file content loaded as array buffer');
            
            try {
                // Convert the array buffer to base64
                const uint8Array = new Uint8Array(e.target.result);
                let binary = '';
                for (let i = 0; i < uint8Array.length; i++) {
                    binary += String.fromCharCode(uint8Array[i]);
                }
                const base64String = btoa(binary);
                
                // Store the base64 string
                state.fileContent = base64String;
                
                // Send to server for analysis, including file type
                fetch('/api/analyze-tokens', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        content: base64String,
                        file_type: 'pdf'
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (elements.tokenInfo) {
                        if (data.error) {
                            elements.tokenInfo.innerHTML = `
                                <div class="token-analysis error">
                                    <h3>Error Processing PDF</h3>
                                    <p>${data.error}</p>
                                </div>
                            `;
                        } else {
                            elements.tokenInfo.innerHTML = `
                                <div class="token-analysis">
                                    <h3>Token Analysis</h3>
                                    <p>Estimated Input Tokens: ${data.estimated_tokens.toLocaleString()}</p>
                                    <p>Estimated Input Cost: $${data.estimated_cost.toFixed(4)}</p>
                                    <p>Maximum Safe Input Tokens: 200,000</p>
                                </div>
                            `;
                        }
                    }
                    updateGenerateButtonState();
                })
                .catch(err => {
                    console.error('Error analyzing PDF tokens:', err);
                    if (elements.tokenInfo) {
                        elements.tokenInfo.innerHTML = `
                            <div class="token-analysis error">
                                <h3>Error Processing PDF</h3>
                                <p>${err.message}</p>
                            </div>
                        `;
                    }
                    updateGenerateButtonState();
                });
            } catch (err) {
                console.error('Error encoding PDF as base64:', err);
                if (elements.tokenInfo) {
                    elements.tokenInfo.innerHTML = `
                        <div class="token-analysis error">
                            <h3>Error Processing PDF</h3>
                            <p>Could not encode PDF file: ${err.message}</p>
                        </div>
                    `;
                }
                updateGenerateButtonState();
            }
        };
        reader.onerror = function(err) {
            console.error('Error reading PDF file:', err);
            if (elements.tokenInfo) {
                elements.tokenInfo.innerHTML = `
                    <div class="token-analysis error">
                        <h3>Error Reading PDF</h3>
                        <p>Could not read PDF file: ${err.message || 'Unknown error'}</p>
                    </div>
                `;
            }
            updateGenerateButtonState();
        };
        reader.readAsArrayBuffer(file);
    } else if (fileExt === 'docx' || fileExt === 'doc') {
        // For Word documents, we also need to use base64 and special handling
        const reader = new FileReader();
        reader.onload = function(e) {
            console.log('Word document content loaded as array buffer');
            
            try {
                // Convert the array buffer to base64
                const uint8Array = new Uint8Array(e.target.result);
                let binary = '';
                for (let i = 0; i < uint8Array.length; i++) {
                    binary += String.fromCharCode(uint8Array[i]);
                }
                const base64String = btoa(binary);
                
                // Store the base64 string
                state.fileContent = base64String;
                
                // Request token analysis from server
                fetch('/api/analyze-tokens', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        content: base64String,
                        file_type: fileExt
                    })
                })
                .then(response => response.json())
                .then(data => {
                    updateTokenInfoUI(data);
                    updateGenerateButtonState();
                })
                .catch(err => {
                    console.error('Error analyzing Word document tokens:', err);
                    showTokenAnalysisError(err.message);
                    updateGenerateButtonState();
                });
            } catch (err) {
                console.error('Error encoding Word document as base64:', err);
                showTokenAnalysisError('Could not encode Word document: ' + err.message);
                updateGenerateButtonState();
            }
        };
        reader.readAsArrayBuffer(file);
    } else {
        // For text-based files (txt, json, etc.), read as text
        const reader = new FileReader();
        reader.onload = function(e) {
            console.log('Text file content loaded');
            state.fileContent = e.target.result;
            updateGenerateButtonState();
            analyzeTokens(state.fileContent);
        };
        reader.readAsText(file);
    }
}

function removeFile() {
    state.file = null;
    state.fileContent = '';
    state.fileName = '';
    
    if (elements.fileInfo) {
        elements.fileInfo.classList.add('hidden');
    }
    
    if (elements.fileUpload) {
        elements.fileUpload.value = '';
    }
    
    // Clear token analysis display
    if (elements.tokenInfo) {
        elements.tokenInfo.innerHTML = '';
    }
    
    updateGenerateButtonState();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Text Input
function handleTextInput(e) {
    const text = e.target.value.trim();
    state.textContent = text;
    
    console.log(`Text input updated, length: ${text.length}`);
    
    // Analyze tokens for the new text content
    if (text) {
        analyzeTokens(text);
    } else if (elements.tokenInfo) {
        elements.tokenInfo.innerHTML = '';
    }
    
    updateGenerateButtonState();
}

// Parameter Controls
function updateTemperature() {
    state.temperature = parseFloat(elements.temperature.value);
    if (elements.temperatureValue) {
        elements.temperatureValue.textContent = state.temperature.toFixed(1);
    }
}

function resetTemperature() {
    state.temperature = 1.0;
    if (elements.temperature) {
        elements.temperature.value = 1.0;
    }
    if (elements.temperatureValue) {
        elements.temperatureValue.textContent = '1.0';
    }
}

function updateMaxTokens() {
    state.maxTokens = parseInt(elements.maxTokens.value);
    if (elements.maxTokensValue) {
        elements.maxTokensValue.textContent = state.maxTokens.toLocaleString();
    }
}

function resetMaxTokens() {
    state.maxTokens = 128000;
    if (elements.maxTokens) {
        elements.maxTokens.value = 128000;
    }
    if (elements.maxTokensValue) {
        elements.maxTokensValue.textContent = '128,000';
    }
}

function updateThinkingBudget() {
    state.thinkingBudget = parseInt(elements.thinkingBudget.value);
    if (elements.thinkingBudgetValue) {
        elements.thinkingBudgetValue.textContent = state.thinkingBudget.toLocaleString();
    }
}

function resetThinkingBudget() {
    state.thinkingBudget = 32000;
    if (elements.thinkingBudget) {
        elements.thinkingBudget.value = 32000;
    }
    if (elements.thinkingBudgetValue) {
        elements.thinkingBudgetValue.textContent = '32,000';
    }
}

// Generate Button State
function updateGenerateButtonState() {
    console.log('Updating generate button state...');
    console.log('Active tab:', state.activeTab);
    
    // Make sure we have API key and content
    const hasApiKey = !!state.apiKey;
    const hasContent = state.textContent || (elements.inputText && elements.inputText.value.trim());
    
    console.log('Has API key:', hasApiKey, 'Has content:', hasContent);
    
    if (elements.generateBtn) {
        if (hasApiKey && hasContent) {
            console.log('Enabling generate button');
            elements.generateBtn.disabled = false;
            elements.generateBtn.classList.remove('bg-gray-300', 'dark:bg-gray-700', 'text-gray-500', 'dark:text-gray-400', 'cursor-not-allowed');
            elements.generateBtn.classList.add('bg-primary-500', 'hover:bg-primary-600', 'text-white', 'cursor-pointer');
            elements.generateBtn.style.pointerEvents = 'auto';
            if (elements.generateError) {
                elements.generateError.classList.add('hidden');
            }
            
            // Make sure the button has a click handler
            if (!elements.generateBtn._hasClickHandler) {
                console.log('Adding click handler to generate button');
                elements.generateBtn.addEventListener('click', function(e) {
                    console.log('Generate button clicked!');
                    e.preventDefault();
                    if (typeof generateWebsite === 'function') {
                        generateWebsite();
                    } else {
                        console.error('generateWebsite function not found!');
                    }
                });
                elements.generateBtn._hasClickHandler = true;
            }
        } else {
            console.log('Disabling generate button');
            elements.generateBtn.disabled = true;
            elements.generateBtn.classList.add('bg-gray-300', 'dark:bg-gray-700', 'text-gray-500', 'dark:text-gray-400', 'cursor-not-allowed');
        }
    } else {
        console.error('Generate button element not found!');
    }
}

// Generate Website
async function generateWebsite() {
    try {
        // Validate API key
        const apiKey = elements.apiKeyInput ? elements.apiKeyInput.value.trim() : '';
        if (!apiKey) {
            showToast('Please enter your API key', 'error');
            return;
        }
        
        // Set processing flag
        state.processing = true;
        state.userScrolledDuringGeneration = false; // Reset scroll tracking
        
        // Set up scroll tracking during generation
        const scrollHandler = () => {
            if (state.processing) {
                state.userScrolledDuringGeneration = true;
                console.log('User scrolled during generation');
            }
        };
        window.addEventListener('scroll', scrollHandler);
        
        // Disable inputs during generation
        disableInputsDuringGeneration(true);
        
        // Show processing UI
        if (elements.generateBtn) {
            elements.generateBtn.disabled = true;
            elements.generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Generating...';
        }
        
        // Show processing status
        startProcessingAnimation();
        
        // Start elapsed time counter
        startElapsedTimeCounter();
        
        // Get input content based on active tab
        const content = getInputContent();
        if (!content) {
            showToast('Please enter some text or upload a file', 'error');
            resetGenerationUI();
            window.removeEventListener('scroll', scrollHandler);
            return;
        }
        
        // Prepare settings from UI
        const formatPrompt = elements.formatPrompt ? elements.formatPrompt.value.trim() : '';
        const apiProvider = state.apiProvider;
        const maxTokens = parseInt(elements.maxTokens ? elements.maxTokens.value : DEFAULT_MAX_TOKENS);
        const temperature = parseFloat(elements.temperature ? elements.temperature.value : 0.7);
        const thinkingBudget = parseInt(elements.thinkingBudget ? elements.thinkingBudget.value : 0);
        
        console.log(`Generating website with: provider=${apiProvider}, maxTokens=${maxTokens}, temperature=${temperature}, thinkingBudget=${thinkingBudget}`);
        
        // Reset token display
        resetTokenStats();
        
        // Process with the selected API provider
        if (apiProvider === 'gemini') {
            // Use Gemini API with streaming if supported, otherwise use non-streaming
            try {
                await generateGeminiHTMLStream(
                    apiKey, content, formatPrompt, 
                    maxTokens, temperature
                );
            } catch (streamError) {
                console.warn('Gemini streaming failed, falling back to non-streaming API:', streamError);
                await generateGeminiHTML(
                    apiKey, content, formatPrompt, 
                    maxTokens, temperature
                );
            }
        } else {
            // Use Claude API with streaming
            await generateHTMLStreamWithReconnection(
                apiKey, content, formatPrompt, 
                'claude-3-7-sonnet-20240307', maxTokens, 
                temperature, thinkingBudget
            );
        }
        
        // Clean up scroll tracking
        window.removeEventListener('scroll', scrollHandler);
    } catch (error) {
        console.error('Generation error:', error);
        showToast(`Error: ${error.message}`, 'error');
        resetGenerationUI();
    }
}

// Function to update UI based on API provider
function updateUIForApiProvider(provider) {
    const generationSettings = document.querySelector('.bg-white.rounded-lg.shadow-md.p-5.transition-all.hover\\:shadow-lg:has(.fa-sliders-h)');
    const usageStatsSection = document.querySelector('#result-section .bg-white.rounded-lg.shadow-md.p-5:has(.fa-chart-line)');
    
    if (provider === 'gemini') {
        // For Gemini, hide the entire Generation Settings section
        if (generationSettings) {
            generationSettings.classList.add('hidden');
        }
        
        // Hide usage stats for Gemini
        if (usageStatsSection) {
            usageStatsSection.classList.add('hidden');
        }
    } else {
        // For Anthropic, show Generation Settings
        if (generationSettings) {
            generationSettings.classList.remove('hidden');
        }
        
        // Show usage stats for Anthropic
        if (usageStatsSection) {
            usageStatsSection.classList.remove('hidden');
        }
        
        // Make sure thinking budget is visible for Anthropic
        if (elements.thinkingBudget && elements.thinkingBudget.parentNode) {
            elements.thinkingBudget.parentNode.classList.remove('hidden');
        }
    }
}

// Add new function for Gemini streaming
async function generateGeminiHTMLStream(apiKey, source, formatPrompt, maxTokens, temperature) {
    console.log("Starting Gemini HTML generation with streaming...");
    
    // Prepare state variables for streaming
    let generatedContent = '';
    let sessionId = '';
    
    try {
        // Calculate approximate input tokens right away (1.3 tokens per word)
        const inputTokens = Math.max(1, Math.floor(source.split(' ').length * 1.3));
        console.log('Estimated input tokens:', inputTokens);
        
        // Update token stats display with input tokens immediately
        updateUsageStatistics({
            input_tokens: inputTokens,
            output_tokens: 0
        });
        
        // Create the request body
        const requestBody = {
            api_key: apiKey,
            content: source,
            format_prompt: formatPrompt,
            max_tokens: maxTokens,
            temperature: temperature
        };
        
        // Add file information for file uploads
        if (state.activeTab === 'file' && state.file) {
            console.log(`Adding file upload info: ${state.fileName} (${formatFileSize(state.file.size)})`);
            requestBody.file_name = state.fileName;
            requestBody.file_content = state.fileContent;
        }
        
        // Start the streaming request
        console.log('Making fetch request to', `${API_URL}/api/process-gemini-stream`);
        const response = await fetch(`${API_URL}/api/process-gemini-stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! Status: ${response.status}, Message: ${errorText}`);
        }
        
        // Get a reader for the stream
        const reader = response.body.getReader();
        let decoder = new TextDecoder();
        let htmlBuffer = '';
        
        // Process stream chunks
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                console.log('Stream complete');
                break;
            }
            
            // Decode the chunk
            const chunk = decoder.decode(value, { stream: true });
            
            // Process each line in the chunk
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                
                try {
                    // Extract the JSON data
                    const eventData = JSON.parse(line.substring(6));
                    
                    // Handle different event types
                    if (eventData.type === 'content_block_delta') {
                        // Add the text to our buffer
                        const text = eventData.delta?.text || '';
                        htmlBuffer += text;
                        generatedContent += text;
                        
                        // Update the UI with the HTML received so far
                        updateHtmlDisplay(htmlBuffer);
                        
                        // Save to state immediately so it's available
                        state.generatedHtml = generatedContent;
                        
                        // Update processing text
                        setProcessingText(`Gemini is generating your visualization... (${formatFileSize(htmlBuffer.length)} generated)`);
                    } else if (eventData.type === 'message_complete') {
                        // Update usage statistics if available
                        if (eventData.usage) {
                            console.log('Received usage statistics:', eventData.usage);
                            updateUsageStatistics(eventData.usage);
                        }
                    } else if (eventData.type === 'error') {
                        throw new Error(eventData.error || 'Unknown streaming error');
                    }
                } catch (parseError) {
                    console.error('Error parsing stream event:', parseError, line);
                }
            }
        }
        
        // Ensure the generated content is saved to state
        state.generatedHtml = generatedContent;
        
        // Final UI updates
        updateHtmlDisplay(generatedContent);
        updatePreview(generatedContent);
        
        // If we don't have token statistics yet, estimate them
        if (!elements.inputTokens?.textContent || elements.inputTokens.textContent === '0') {
            // Estimate input tokens based on source length (1 token ≈ 3.5 characters)
            const estimatedInputTokens = Math.max(1, Math.floor(source.length / 3.5));
            const estimatedOutputTokens = Math.max(1, Math.floor(generatedContent.length / 3.5));
            
            // Update usage statistics with our estimates
            updateUsageStatistics({
                input_tokens: estimatedInputTokens,
                output_tokens: estimatedOutputTokens
            });
            
            console.log('Updated with estimated token counts:', estimatedInputTokens, estimatedOutputTokens);
        }
        
        // Complete generation
        console.log('Generation complete with Gemini streaming');
        setProcessingText('Generation complete!');
        state.processing = false;
        stopElapsedTimeCounter();
        stopProcessingAnimation();
        disableInputsDuringGeneration(false);
        
        // Show completion toast
        showToast('Website generated successfully!', 'success');
        
        return generatedContent;
    } catch (error) {
        console.error('Gemini streaming error:', error);
        throw error;
    }
}

// Add non-streaming fallback for Gemini
async function generateGeminiHTML(apiKey, source, formatPrompt, maxTokens, temperature) {
    console.log("Starting Gemini HTML generation (non-streaming)...");
    
    try {
        // Calculate approximate input tokens right away (1.3 tokens per word)
        const inputTokens = Math.max(1, Math.floor(source.split(' ').length * 1.3));
        console.log('Estimated input tokens:', inputTokens);
        
        // Update token stats display with input tokens immediately
        updateUsageStatistics({
            input_tokens: inputTokens,
            output_tokens: 0
        });
        
        // Show processing message
        setProcessingText('Processing with Google Gemini (non-streaming)...');
        
        // Create the request body
        const requestBody = {
            api_key: apiKey,
            content: source,
            format_prompt: formatPrompt,
            max_tokens: maxTokens,
            temperature: temperature
        };
        
        // Add file information for file uploads
        if (state.activeTab === 'file' && state.file) {
            requestBody.file_name = state.fileName;
            requestBody.file_content = state.fileContent;
        }
        
        // Make the non-streaming request
        const response = await fetch(`${API_URL}/api/process-gemini`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! Status: ${response.status}, Message: ${errorText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Update UI with generated HTML
        const html = data.html;
        updateHtmlDisplay(html);
        updatePreview(html);
        
        // Update usage statistics if available
        if (data.usage) {
            console.log('Received usage statistics from non-streaming API:', data.usage);
            updateUsageStatistics(data.usage);
        } else {
            // If no usage data provided, estimate tokens
            const estimatedInputTokens = Math.max(1, Math.floor(source.length / 3.5));
            const estimatedOutputTokens = Math.max(1, Math.floor(html.length / 3.5));
            
            updateUsageStatistics({
                input_tokens: estimatedInputTokens,
                output_tokens: estimatedOutputTokens
            });
            
            console.log('Updated with estimated token counts:', estimatedInputTokens, estimatedOutputTokens);
        }
        
        // Save to state
        state.generatedHtml = html;
        
        // Complete generation
        console.log('Generation complete with Gemini (non-streaming)');
        setProcessingText('Generation complete!');
        state.processing = false;
        stopElapsedTimeCounter();
        stopProcessingAnimation();
        disableInputsDuringGeneration(false);
        
        // Show completion toast
        showToast('Website generated successfully!', 'success');
        
        return html;
    } catch (error) {
        console.error('Gemini generation error:', error);
        throw error;
    }
}

async function generateHTMLStreamWithReconnection(apiKey, source, formatPrompt, model, maxTokens, temperature, thinkingBudget) {
    console.log("Starting HTML generation with streaming and reconnection support...");
    
    // Prepare state variables for streaming
    let generatedContent = '';
    let sessionId = '';
    let reconnectAttempts = 0;
    let lastKeepAliveTime = Date.now(); // Track last keepalive
    const KEEPALIVE_TIMEOUT = 10000; // 10 seconds without keepalive would trigger reconnection
    
    // Add flags to track streaming state to prevent duplicate requests
    let isGenerationCompleted = false;
    let isCurrentlyReconnecting = false;
    let activeStream = true; // Track if we have an active stream processing
    
    try {
        // Show streaming status
        setProcessingText('Connecting to Claude...');
        
        // Create a function to handle the streaming call
        const processStreamChunk = async (isReconnect = false, lastChunkId = null) => {
            // Prevent multiple concurrent reconnects
            if (isCurrentlyReconnecting) {
                console.log('Already reconnecting, ignoring duplicate request');
                return;
            }
            
            // Don't reconnect if generation is already completed
            if (isGenerationCompleted) {
                console.log('Generation already completed, ignoring reconnect request');
                return;
            }
            
            // Set the reconnecting flag to prevent concurrent reconnects
            if (isReconnect) {
                isCurrentlyReconnecting = true;
            }
            
            console.log(`${isReconnect ? 'Reconnecting' : 'Starting'} stream${sessionId ? ' with session ID: ' + sessionId : ''}...`);
            
            // Display reconnection status if applicable
            if (isReconnect) {
                setProcessingText(`Reconnecting to continue generation... (attempt ${reconnectAttempts})`);
            }
            
            // Create the request body
            const requestBody = {
                api_key: apiKey,
                source: source,
                format_prompt: formatPrompt,
                model: model,
                max_tokens: maxTokens,
                temperature: temperature,
                thinking_budget: thinkingBudget
            };
            
            // Add file information for file uploads
            if (state.activeTab === 'file' && state.file) {
                console.log(`Adding file upload info: ${state.fileName} (${formatFileSize(state.file.size)})`);
                requestBody.file_name = state.fileName;
                requestBody.file_content = state.fileContent; // Use stored file content directly
                
                // Ensure file content is included in the source parameter too for compatibility
                if (!requestBody.source || requestBody.source.trim() === '') {
                    console.log('Setting source parameter to file content for compatibility');
                    requestBody.source = state.fileContent;
                }
            }
            
            // Add session information for reconnections
            if (sessionId) {
                requestBody.session_id = sessionId;
                requestBody.is_reconnect = true;
                
                if (lastChunkId) {
                    requestBody.last_chunk_id = lastChunkId;
                }
            }
            
            try {
                // Start the streaming request
                console.log('Making fetch request to', `${API_URL}/api/process-stream`);
                const response = await fetch(`${API_URL}/api/process-stream`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestBody)
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    
                    // Special handling for timeout errors that might contain session information
                    if ((response.status === 504 || response.status === 500) && 
                        (errorText.includes('FUNCTION_INVOCATION_TIMEOUT') || errorText.includes('timed out'))) {
                        console.log('Vercel timeout detected, will attempt reconnection');
                        
                        // Extract session ID if present in the error message
                        const sessionMatch = errorText.match(/cle\d+::[a-z0-9]+-\d+-[a-z0-9]+/);
                        if (sessionMatch && !sessionId) {
                            sessionId = sessionMatch[0];
                            console.log('Extracted session ID:', sessionId);
                        }
                        
                        // Increment reconnect attempts and try again
                        reconnectAttempts++;
                        if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS && !isGenerationCompleted) {
                            isCurrentlyReconnecting = false; // Reset reconnection flag
                            await new Promise(resolve => setTimeout(resolve, RECONNECT_DELAY));
                            return await processStreamChunk(true);
                        } else {
                            isCurrentlyReconnecting = false;
                            throw new Error('Maximum reconnection attempts reached. Please try again later.');
                        }
                    }
                    
                    isCurrentlyReconnecting = false;
                    throw new Error(`HTTP error! Status: ${response.status}, Message: ${errorText}`);
                }
                
                // Reset reconnect attempts on successful connection
                reconnectAttempts = 0;
                isCurrentlyReconnecting = false;
                
                // Get a reader for the stream
                const reader = response.body.getReader();
                let decoder = new TextDecoder();
                
                // Setup keepalive monitoring
                let isStreamActive = true;
                let keepaliveMonitor = setInterval(() => {
                    const now = Date.now();
                    if (now - lastKeepAliveTime > KEEPALIVE_TIMEOUT && isStreamActive && activeStream && !isGenerationCompleted) {
                        console.warn('No keepalive received for', (now - lastKeepAliveTime) / 1000, 'seconds. Reconnecting...');
                        clearInterval(keepaliveMonitor);
                        isStreamActive = false;
                        
                        // Force reader to stop
                        reader.cancel('No keepalive received');
                        
                        // Only try to reconnect if we haven't completed
                        if (!isGenerationCompleted) {
                            reconnectAttempts++;
                            if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
                                processStreamChunk(true, lastChunkId).catch(console.error);
                            } else {
                                console.error('Max reconnect attempts reached after keepalive timeout');
                                showToast('Connection lost. Please try again.', 'error');
                                resetGenerationUI(false);
                            }
                        }
                    }
                }, 1000);
                
                // Process the stream
                try {
                    while (true) {
                        const { value, done } = await reader.read();
                        
                        if (done) {
                            console.log('Stream complete');
                            clearInterval(keepaliveMonitor);
                            break;
                        }
                        
                        // Decode the chunk
                        const chunk = decoder.decode(value, { stream: true });
                        console.log('Received chunk:', chunk.substring(0, 50) + '...');
                        
                        // Process the chunk - look for data: lines
                        const lines = chunk.split('\n');
                        
                        for (const line of lines) {
                            // Skip empty lines
                            if (!line.trim()) continue;
                            
                            // Handle SSE format (data: {...})
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.substring(6));
                                    
                                    // Update the keepalive time for keepalive events
                                    if (line.includes('event: keepalive')) {
                                        lastKeepAliveTime = Date.now();
                                        console.log('Received keepalive at', new Date().toISOString());
                                        continue;
                                    }
                                    
                                    // Handle thinking updates
                                    if (data.type === 'thinking_update') {
                                        if (data.thinking && data.thinking.content) {
                                            setProcessingText(`Claude is thinking: ${data.thinking.content.substring(0, 100)}...`);
                                        }
                                        lastKeepAliveTime = Date.now(); // Count these as keepalives too
                                        continue;
                                    }
                                    
                                    // Handle new local streaming format (type: delta)
                                    if (data.type === 'delta' && data.content) {
                                        generatedContent += data.content;
                                        updateHtmlPreview(generatedContent);
                                        lastKeepAliveTime = Date.now(); // Count content as keepalive
                                        continue;
                                    }
                                    
                                    // Handle content block deltas (the actual generated text) - Vercel format
                                    if (data.type === 'content_block_delta' && data.delta && data.delta.text) {
                                        generatedContent += data.delta.text;
                                        updateHtmlPreview(generatedContent);
                                        lastKeepAliveTime = Date.now(); // Count content as keepalive
                                        continue;
                                    }
                                    
                                    // Handle content_complete event which should include usage statistics
                                    if (data.type === 'content_complete') {
                                        console.log('Content complete event received');
                                        
                                        // Store the content but don't stop the timer yet
                                        if (data.content) {
                                            console.log(`HTML content received in content_complete (length: ${data.content.length})`);
                                            generatedContent = data.content;
                                            state.generatedHtml = data.content;
                                            updateHtmlPreview(data.content);
                                        }
                                        
                                        // Update usage statistics if available, but don't stop the timer
                                        if (data.usage) {
                                            console.log('Updating token stats from content_complete event:', data.usage);
                                            updateTokenStats(data.usage);
                                            
                                            // Calculate cost if available
                                            const totalCost = data.usage.total_cost || 
                                                ((data.usage.input_tokens / 1000000) * 3.0 + 
                                                 (data.usage.output_tokens / 1000000) * 15.0);
                                            elements.totalCost.textContent = formatCostDisplay(totalCost);
                                            
                                            // Update storage with new usage stats
                                            try {
                                                // Get existing stats
                                                const existingStats = JSON.parse(localStorage.getItem('fileVisualizerStats') || '{"totalRuns":0,"totalTokens":0,"totalCost":0}');
                                                
                                                // Update stats
                                                existingStats.totalRuns = (existingStats.totalRuns || 0) + 1;
                                                existingStats.totalTokens = (existingStats.totalTokens || 0) + 
                                                    (data.usage.input_tokens + data.usage.output_tokens);
                                                existingStats.totalCost = (existingStats.totalCost || 0) + totalCost;
                                                
                                                // Save updated stats
                                                localStorage.setItem('fileVisualizerStats', JSON.stringify(existingStats));
                                                
                                                // Update UI if stats container exists
                                                if (document.getElementById('total-runs')) {
                                                    document.getElementById('total-runs').textContent = existingStats.totalRuns.toLocaleString();
                                                }
                                                if (document.getElementById('total-tokens')) {
                                                    document.getElementById('total-tokens').textContent = existingStats.totalTokens.toLocaleString();
                                                }
                                                if (document.getElementById('total-cost')) {
                                                    document.getElementById('total-cost').textContent = formatCostDisplay(existingStats.totalCost);
                                                }
                                            } catch (e) {
                                                console.error('Error updating usage statistics:', e);
                                            }
                                        }
                                        
                                        // Do not mark as complete yet - wait for message_complete
                                        lastKeepAliveTime = Date.now();
                                        continue;
                                    }
                                    
                                    // Save chunk ID for potential reconnection
                                    if (data.chunk_id) {
                                        lastChunkId = data.chunk_id;
                                    }
                                    
                                    // Check for the local message_complete
                                    if (data.type === 'end') {
                                        console.log('End message received from local server');
                                        // Store the generated HTML for later use
                                        state.generatedHtml = generatedContent;
                                        generatedHtml = generatedContent; // Update global variable too
                                        
                                        // Mark generation as completed to prevent further reconnects
                                        isGenerationCompleted = true;
                                        activeStream = false;
                                        
                                        // Final UI update
                                        updateHtmlDisplay();
                                        stopElapsedTimeCounter(); // Only stop the timer when the generation is actually complete
                                        clearInterval(keepaliveMonitor);
                                    }
                                    
                                    // Handle message complete from Vercel
                                    if (data.type === 'message_complete') {
                                        console.log('Message complete received');
                                        
                                        // Mark generation as completed to prevent further reconnects
                                        isGenerationCompleted = true;
                                        activeStream = false;
                                        
                                        // If html is provided directly, use it
                                        if (data.html) {
                                            console.log(`HTML content received in message_complete (length: ${data.html.length})`);
                                            generatedContent = data.html;
                                        }
                                        
                                        // Ensure we store the generated HTML
                                        state.generatedHtml = generatedContent;
                                        generatedHtml = generatedContent; // Update global variable too
                                        
                                        // Final UI update
                                        updateHtmlPreview(generatedContent);
                                        updateHtmlDisplay();
                                        stopElapsedTimeCounter(); // Only stop the timer when the message is complete
                                        clearInterval(keepaliveMonitor);
                                        
                                        // Update usage statistics
                                        if (data.usage) {
                                            updateTokenStats(data.usage);
                                            
                                            // Calculate cost if available
                                            const totalCost = data.usage.total_cost || 
                                                ((data.usage.input_tokens / 1000000) * 3.0 + 
                                                 (data.usage.output_tokens / 1000000) * 15.0);
                                            elements.totalCost.textContent = formatCostDisplay(totalCost);
                                            
                                            // Update storage with new usage stats
                                            try {
                                                // Get existing stats
                                                const existingStats = JSON.parse(localStorage.getItem('fileVisualizerStats') || '{"totalRuns":0,"totalTokens":0,"totalCost":0}');
                                                
                                                // Update stats
                                                existingStats.totalRuns = (existingStats.totalRuns || 0) + 1;
                                                existingStats.totalTokens = (existingStats.totalTokens || 0) + 
                                                    (data.usage.input_tokens + data.usage.output_tokens);
                                                existingStats.totalCost = (existingStats.totalCost || 0) + totalCost;
                                                
                                                // Save updated stats
                                                localStorage.setItem('fileVisualizerStats', JSON.stringify(existingStats));
                                                
                                                // Update UI if stats container exists
                                                if (document.getElementById('total-runs')) {
                                                    document.getElementById('total-runs').textContent = existingStats.totalRuns.toLocaleString();
                                                }
                                                if (document.getElementById('total-tokens')) {
                                                    document.getElementById('total-tokens').textContent = existingStats.totalTokens.toLocaleString();
                                                }
                                                if (document.getElementById('total-cost')) {
                                                    document.getElementById('total-cost').textContent = formatCostDisplay(existingStats.totalCost);
                                                }
                                            } catch (e) {
                                                console.error('Error updating usage statistics:', e);
                                            }
                                        }
                                    }
                                    
                                    // Handle stream_end event
                                    if (data.type === 'stream_end' || line.includes('event: stream_end')) {
                                        console.log('Stream end event received');
                                        isGenerationCompleted = true;
                                        activeStream = false;
                                    }
                                    
                                    // Handle html field if present separately
                                    if (data.html && data.type !== 'message_complete') {
                                        console.log(`HTML content received directly (length: ${data.html.length})`);
                                        generatedContent = data.html;
                                        state.generatedHtml = data.html;
                                        updateHtmlPreview(generatedContent);
                                        lastKeepAliveTime = Date.now(); // Count content as keepalive
                                    }
                                } catch (e) {
                                    console.warn('Error parsing data line:', e, line);
                                }
                            }
                        }
                    }
                } catch (streamError) {
                    console.error('Error in stream processing:', streamError);
                    clearInterval(keepaliveMonitor);
                    
                    // If the stream was deliberately cancelled for reconnection,
                    // don't throw the error (the reconnection logic will handle it)
                    if (streamError.message === 'No keepalive received') {
                        return;
                    }
                    
                    // For other errors, check if we need to reconnect
                    if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS && !isGenerationCompleted) {
                        reconnectAttempts++;
                        await new Promise(resolve => setTimeout(resolve, RECONNECT_DELAY));
                        return await processStreamChunk(true, lastChunkId);
                    } else {
                        throw streamError;
                    }
                }
                
                // Set the active stream flag to false when we're done processing
                activeStream = false;
                
                // If we got here, the stream completed successfully
                // Make sure to update the state's generatedHtml property
                if (!isGenerationCompleted) {
                    state.generatedHtml = generatedContent;
                    isGenerationCompleted = true;
                    
                    // Update the HTML display and preview with the final content
                    updateHtmlDisplay();
                    updatePreview();
                    
                    // Show the results section
                    showResultSection();
                    
                    // Complete the generation process
                    stopProcessingAnimation();
                    resetGenerationUI(true);
                    showToast('Website generation complete!', 'success');
                }
                
            } catch (error) {
                // Reset the reconnecting flag
                isCurrentlyReconnecting = false;
                
                // Check if this is a timeout error that we can recover from
                if ((error.message.includes('FUNCTION_INVOCATION_TIMEOUT') || 
                    error.message.includes('timed out') ||
                    error.message.includes('Error: 504')) && 
                    reconnectAttempts <= MAX_RECONNECT_ATTEMPTS && 
                    !isGenerationCompleted) {
                    console.log('Reconnecting due to timeout...');
                    reconnectAttempts++;
                    await new Promise(resolve => setTimeout(resolve, RECONNECT_DELAY));
                    return await processStreamChunk(true, lastChunkId);
                }
                
                // Otherwise, propagate the error
                throw error;
            }
        };
        
        // Start the streaming process
        activeStream = true;
        await processStreamChunk();
        
    } catch (error) {
        console.error('Error in generateHTMLStreamWithReconnection:', error);
        showToast(`Error: ${error.message}`, 'error');
        stopProcessingAnimation();
        resetGenerationUI(false);
        throw error; // Propagate the error
    }
}

function updateHtmlPreview(html) {
    if (!html) return;
    
    try {
        // For large content, use incremental iframe updates
        const htmlLength = html.length;
        console.log(`Updating HTML preview with content length: ${htmlLength}`);
        
        if (htmlLength > MAX_HTML_BUFFER_SIZE) {
            // Only update the preview iframe in incremental mode for large content
            console.log(`Large HTML detected (${formatFileSize(htmlLength)}), using incremental iframe update`);
            
            // Check if iframe exists
            const iframe = document.getElementById('preview-iframe');
            if (!iframe) {
                console.error('Preview iframe not found');
                return;
            }
            
            // For very large content, we'll inject incrementally using document.write
            if (!iframe.hasAttribute('data-initialized')) {
                // Initialize the iframe with base HTML structure
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                iframeDoc.open();
                iframeDoc.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head><body></body></html>');
                iframeDoc.close();
                iframe.setAttribute('data-initialized', 'true');
                iframe.setAttribute('data-content-length', '0');
            }
            
            // Get the previous content length
            const prevLength = parseInt(iframe.getAttribute('data-content-length') || '0');
            
            // Only inject the new content
            if (htmlLength > prevLength) {
                const newContent = html.substring(prevLength);
                
                try {
                    // Append to body instead of rewriting everything
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    
                    // Create temporary div to parse HTML
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = newContent;
                    
                    // Extract new nodes and append them to iframe body
                    Array.from(tempDiv.childNodes).forEach(node => {
                        iframeDoc.body.appendChild(iframeDoc.importNode(node, true));
                    });
                    
                    // Update the stored content length
                    iframe.setAttribute('data-content-length', htmlLength.toString());
                } catch (innerError) {
                    console.error('Error appending to iframe:', innerError);
                }
            }
        } else {
            // For smaller content, use normal update method
            if (elements.htmlOutput) {
                elements.htmlOutput.value = html;
            } else {
                console.warn('HTML output element not found, but continuing with iframe update');
            }
            
            // Update the preview iframe
            const iframe = document.getElementById('preview-iframe');
            if (iframe) {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    iframeDoc.open();
                    iframeDoc.write(html);
                    iframeDoc.close();
                    console.log('Preview iframe updated successfully');
                } catch (iframeError) {
                    console.error('Error updating iframe:', iframeError);
                }
            } else {
                console.error('Preview iframe element not found');
            }
        }
    } catch (error) {
        console.error('Error updating HTML preview:', error);
        showToast('Error updating preview', 'error');
    }
}

function showResultSection() {
    // Show the result section
    const resultSection = document.getElementById('result-section');
    if (resultSection) {
        resultSection.classList.remove('hidden');
        
        // Hide usage stats if Gemini is selected
        if (state.apiProvider === 'gemini') {
            const usageStatsSection = resultSection.querySelector('.bg-white.rounded-lg.shadow-md.p-5:has(.fa-chart-line)');
            if (usageStatsSection) {
                usageStatsSection.classList.add('hidden');
            }
        }
        
        // Only scroll to result section if generation is complete
        if (!state.processing) {
            // Give some time for the HTML to render before scrolling
            setTimeout(() => {
                // Only scroll if the user hasn't scrolled manually after generation started
                if (!state.userScrolledDuringGeneration) {
                    resultSection.scrollIntoView({ behavior: 'smooth' });
                    console.log('Scrolled to result section');
                }
            }, 500);
        }
    }
}

function startElapsedTimeCounter() {
    clearInterval(state.elapsedTimeInterval);
    
    // Initialize the start time properly
    state.startTime = new Date();
    
    // Update the counter immediately once
    const elapsed = Math.floor((new Date() - state.startTime) / 1000);
    elements.elapsedTime.textContent = `Elapsed: ${formatTime(elapsed)}`;
    
    // Then set up the interval for subsequent updates
    state.elapsedTimeInterval = setInterval(() => {
        const elapsed = Math.floor((new Date() - state.startTime) / 1000);
        elements.elapsedTime.textContent = `Elapsed: ${formatTime(elapsed)}`;
    }, 1000);
}

function stopElapsedTimeCounter() {
    clearInterval(state.elapsedTimeInterval);
}

function displayElapsedTime(seconds) {
    if (seconds && elements.elapsedTime) {
        elements.elapsedTime.textContent = `Completed in: ${formatTime(seconds)}`;
    }
}

function formatTime(seconds) {
    if (seconds < 0 || isNaN(seconds)) {
        seconds = 0;
    }

    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

async function processWithStreaming(data) {
    try {
        // Variables for streaming
        let chunks = 0;
        let lastChunkTime = Date.now();
        let receivedHtml = '';
        
        // Get the response
        const response = await fetch(`${API_URL}/api/process-stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        // Check for errors
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${await response.text()}`);
        }
        
        // Get a reader from the response body stream
        const reader = response.body.getReader();
        let decoder = new TextDecoder();
        
        // Flag for large content handling
        let isLargeContent = false;
        
        // Process the stream
        while (true) {
            const { value, done } = await reader.read();
            
            // If the stream is done, break the loop
            if (done) {
                console.log('Stream complete');
                break;
            }
            
            // Update last chunk time
            lastChunkTime = Date.now();
            chunks++;
            
            // Output every 10 chunks for debugging
            if (chunks % 10 === 0) {
                console.log(`Processed ${chunks} chunks so far`);
            }
            
            // Decode the chunk
            const chunkText = decoder.decode(value, { stream: true });
            
            // Split the chunk into lines
            const lines = chunkText.split('\n');
            
            // Process each line
            for (const line of lines) {
                // Skip empty lines
                if (!line.trim()) continue;
                
                // Process data lines
                if (line.startsWith('data: ')) {
                    try {
                        // Parse the JSON data
                        const jsonData = JSON.parse(line.substring(6));
                        
                        // Handle different event types
                        if (jsonData.type === 'content_block_delta' && jsonData.delta && jsonData.delta.text) {
                            // Handle content increments
                            receivedHtml += jsonData.delta.text;
                            
                            // If content is becoming large, switch to incremental mode
                            if (receivedHtml.length > MAX_HTML_BUFFER_SIZE && !isLargeContent) {
                                console.log('Switching to large content mode');
                                isLargeContent = true;
                            }
                            
                            // Update the preview (will use incremental mode if needed)
                            updateHtmlPreview(receivedHtml);
                            
                            // Show progress indicator
                            if (jsonData.segment) {
                                setProcessingText(`Processing segment ${jsonData.segment}... (${formatFileSize(receivedHtml.length)} generated)`);
                            }
                        } else if (jsonData.type === 'status') {
                            // Handle status updates
                            setProcessingText(jsonData.message || 'Processing...');
                        } else if (jsonData.type === 'message_complete') {
                            // Update UI
                            if (jsonData.usage) {
                                updateTokenStats(jsonData.usage);
                                
                                // Show time if available
                                if (jsonData.usage.time_elapsed) {
                                    elements.elapsedTime.textContent = formatTime(jsonData.usage.time_elapsed);
                                }
                            }
                            
                            // Update with final content if provided
                            if (jsonData.html) {
                                receivedHtml = jsonData.html;
                                updateHtmlPreview(receivedHtml);
                            }
                            
                            console.log('Generation complete');
                            setTimeout(() => {
                                stopProcessingAnimation();
                                showToast('Generation complete!', 'success');
                            }, 500);
                        }
                    } catch (error) {
                        console.error('Error parsing SSE data:', error, line);
                    }
                }
            }
        }
        
        // Ensure the HTML is displayed
        elements.htmlOutput.value = receivedHtml;
        
        // Return the generated HTML
        return receivedHtml;
    } catch (error) {
        console.error('Error in processWithStreaming:', error);
        stopProcessingAnimation();
        showToast(`Error: ${error.message}`, 'error');
        return null;
    }
}

function updateHtmlDisplay(directContent) {
    // Use the provided content or get from state
    const htmlContent = directContent || state.generatedHtml || '';
    
    // Set the content for the HTML output textarea if it exists
    if (elements.htmlOutput) {
        elements.htmlOutput.value = htmlContent;
    }
    
    // Set the raw HTML content for display
    const rawHtmlElement = document.getElementById('raw-html');
    if (rawHtmlElement) {
        // Escape special characters for display
        rawHtmlElement.textContent = htmlContent;
        
        // Apply syntax highlighting
        if (window.Prism) {
            Prism.highlightElement(rawHtmlElement);
        }
    }
    
    // If preview is available, update it
    updatePreview(htmlContent);
    
    // Show the result section with both preview and code
    showResultSection();
    
    // Log debug info
    console.log(`updateHtmlDisplay called with content length: ${htmlContent.length}`);
}

function updatePreview(directContent) {
    // Use the provided content or get from state
    const htmlContent = directContent || state.generatedHtml || '';
    if (!htmlContent) return;
    
    // Get the iframe
    const iframe = document.getElementById('preview-iframe');
    if (!iframe) return;
    
    try {
        // Clean HTML content if it contains markdown-style code blocks from Gemini
        let cleanedContent = htmlContent;
        if (state.apiProvider === 'gemini' && htmlContent.includes('```html')) {
            // Extract the actual HTML from between the markdown code blocks
            const htmlMatch = htmlContent.match(/```html\s*([\s\S]*?)\s*```/);
            if (htmlMatch && htmlMatch[1]) {
                cleanedContent = htmlMatch[1].trim();
                console.log('Cleaned Gemini markdown code blocks from HTML output');
                
                // Also update the state and display with the cleaned content
                state.generatedHtml = cleanedContent;
                if (elements.htmlOutput) {
                    elements.htmlOutput.value = cleanedContent;
                }
                if (document.getElementById('raw-html')) {
                    document.getElementById('raw-html').textContent = cleanedContent;
                    if (window.Prism) {
                        Prism.highlightElement(document.getElementById('raw-html'));
                    }
                }
            }
        }
        
        // Write the HTML to the iframe
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write(cleanedContent);
        iframeDoc.close();
        
        console.log('Preview updated with HTML content of length:', cleanedContent.length);
    } catch (error) {
        console.error('Error updating preview:', error);
    }
}

function resetGenerationUI(success = false) {
    if (elements.generateBtn) {
        elements.generateBtn.disabled = false;
        elements.generateBtn.innerHTML = '<i class="fas fa-magic mr-2"></i>Generate Visualization';
        updateGenerateButtonState();
    }
    
    if (elements.processingStatus) {
        if (success) {
            // Change the processing status to show completion but keep it visible
            if (elements.processingText) {
                elements.processingText.textContent = "Completed";
            }
            if (elements.processingIcon) {
                elements.processingIcon.classList.remove("fa-spinner", "fa-spin");
                elements.processingIcon.classList.add("fa-check-circle");
                elements.processingIcon.style.color = "#10B981"; // Green color
            }
            // Keep it visible permanently
            elements.processingStatus.classList.remove('hidden');
            // Only stop the time counter on successful completion
            stopElapsedTimeCounter();
        } else {
            // On error, update status but keep visible
            if (elements.processingText) {
                elements.processingText.textContent = "Failed";
            }
            if (elements.processingIcon) {
                elements.processingIcon.classList.remove("fa-spinner", "fa-spin");
                elements.processingIcon.classList.add("fa-exclamation-circle");
                elements.processingIcon.style.color = "#EF4444"; // Red color
            }
            elements.processingStatus.classList.remove('hidden');
            // Stop the timer also on error
            stopElapsedTimeCounter();
        }
    }
    
    state.processing = false;
    disableInputsDuringGeneration(false);
}

// Output Actions
function copyHtmlToClipboard() {
    const htmlContent = state.generatedHtml || '';
    if (!htmlContent) {
        showToast('No HTML content to copy', 'error');
        return;
    }
    
    try {
        navigator.clipboard.writeText(htmlContent).then(() => {
            showToast('HTML copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
            
            // Fallback copy method for browsers without clipboard API
            const textarea = document.createElement('textarea');
            textarea.value = htmlContent;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            
            showToast('HTML copied to clipboard!', 'success');
        });
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        showToast('Failed to copy HTML. Please try again.', 'error');
    }
}

function downloadHtmlFile() {
    const htmlContent = state.generatedHtml || '';
    if (!htmlContent) {
        showToast('No HTML content to download', 'error');
        return;
    }
    
    try {
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        // Create a descriptive filename that always includes "visualization"
        let filename = 'visualization.html';
        if (state.activeTab === 'text' && elements.inputText && elements.inputText.value) {
            // Extract first few words from text input to create filename
            const firstFewWords = elements.inputText.value
                .trim()
                .split(/\s+/)
                .slice(0, 4)
                .join('_')
                .replace(/[^a-zA-Z0-9_-]/g, '')
                .substring(0, 30); // Limit length
                
            if (firstFewWords) {
                filename = `${firstFewWords}_visualization.html`;
            }
        } else if (state.fileName) {
            // If a file was uploaded, base the name on that
            const baseName = state.fileName.split('.')[0];
            filename = `${baseName}_visualization.html`;
        }
        
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showToast('Website file downloaded!', 'success');
    } catch (error) {
        console.error('Error downloading file:', error);
        showToast('Failed to download file. Please try again.', 'error');
    }
}

function openPreviewInNewTab() {
    const htmlContent = state.generatedHtml || '';
    if (!htmlContent) {
        showToast('No HTML content to preview', 'error');
        return;
    }
    
    try {
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
    } catch (error) {
        console.error('Error opening preview:', error);
        showToast('Failed to open preview. Please try again.', 'error');
    }
}

// Toast Notification
function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 left-1/2 transform -translate-x-1/2 z-50 p-4 rounded-lg shadow-lg ${
        type === 'success' ? 'bg-green-500' : 
        type === 'error' ? 'bg-red-500' : 
        'bg-blue-500'
    } text-white max-w-md w-full animate-fade-in text-center`;
    
    toast.style.minWidth = '300px';
    toast.style.fontWeight = 'bold';
    
    toast.innerHTML = `
        <div class="flex items-center justify-center">
            <i class="fas ${
                type === 'success' ? 'fa-check-circle' : 
                type === 'error' ? 'fa-exclamation-circle' : 
                'fa-info-circle'
            } mr-2 text-xl"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Remove the toast after 5 seconds
    setTimeout(() => {
        toast.classList.add('opacity-0');
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 5000);
}

// Add token analysis function
async function analyzeTokens(content) {
    if (!content) {
        if (elements.tokenInfo) {
            elements.tokenInfo.innerHTML = '';
        }
        return;
    }
    
    try {
        // Show loading indicator
        if (elements.tokenInfo) {
            elements.tokenInfo.innerHTML = `
                <div class="token-analysis loading">
                    <h3>Token Analysis</h3>
                    <p>Analyzing tokens...</p>
                </div>
            `;
        }
        
        const response = await fetch('/api/analyze-tokens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                content,
                file_type: state.activeTab === 'file' && state.file ? state.file.name.split('.').pop().toLowerCase() : 'txt'
            })
        });
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Update token info display based on API provider
        if (elements.tokenInfo) {
            if (state.apiProvider === 'gemini') {
                // For Gemini, only show estimated tokens without cost
                elements.tokenInfo.innerHTML = `
                    <div class="token-analysis">
                        <h3>Token Analysis</h3>
                        <p>Estimated Input Tokens: ${data.estimated_tokens.toLocaleString()}</p>
                    </div>
                `;
            } else {
                // For Anthropic, show full token analysis with cost
                elements.tokenInfo.innerHTML = `
                    <div class="token-analysis">
                        <h3>Token Analysis</h3>
                        <p>Estimated Input Tokens: ${data.estimated_tokens.toLocaleString()}</p>
                        <p>Estimated Input Cost: $${data.estimated_cost.toFixed(4)}</p>
                        <p>Maximum Safe Input Tokens: 200,000</p>
                    </div>
                `;
            }
        }
        
        return data;
    } catch (error) {
        console.error('Error analyzing tokens:', error);
        if (elements.tokenInfo) {
            elements.tokenInfo.innerHTML = `
                <div class="token-analysis error">
                    <p>Error analyzing tokens: ${error.message}</p>
                </div>
            `;
        }
        return null;
    }
}

// Helper function to start processing animation
function startProcessingAnimation() {
    // Initialize progress bar animation
    if (elements.progressBar) {
        elements.progressBar.style.width = '0%';
        elements.progressBar.classList.add('animate-progress');
        
        // Animate the progress bar to 90% (reserve last 10% for completion)
        setTimeout(() => {
            elements.progressBar.style.width = '90%';
        }, 100);
    }
    
    // Show processing status
    if (elements.processingStatus) {
        elements.processingStatus.classList.remove('hidden');
        elements.processingStatus.classList.remove('processing-complete');
    }
    
    // Update processing text
    setProcessingText('Processing with Claude...');
    
    console.log('Processing animation started');
}

// Helper function to fully stop processing animation
function stopProcessingAnimation() {
    // Stop progress bar animation
    if (elements.progressBar) {
        // Ensure the progress bar is set to 100% to indicate completion
        elements.progressBar.style.width = '100%';
        elements.progressBar.classList.remove('animate-progress');
    }
    
    // Mark processing container as complete (for CSS targeting)
    if (elements.processingStatus) {
        elements.processingStatus.classList.add('processing-complete');
    }
    
    // Update the processing text to show completion instead of hiding it
    if (elements.processingText) {
        elements.processingText.textContent = 'Generation complete! ✓';
    }
    
    // Keep the processing status visible instead of hiding it
    // Comment out the code that hides it
    /*
    if (elements.processingStatus) {
        setTimeout(() => {
            elements.processingStatus.classList.add('hidden');
        }, 2000); // Hide after 2 seconds to allow user to see completion
    }
    */
    
    // Update elapsed time if it exists
    if (elements.elapsedTime) {
        // Get current elapsed time if not already set
        const currentTime = state.startTime ? 
            Math.floor((new Date() - state.startTime) / 1000) : 0;
        
        // Set to "Completed" if not already set
        if (elements.elapsedTime.textContent.startsWith('Elapsed:')) {
            elements.elapsedTime.textContent = `Completed in: ${formatTime(currentTime)}`;
        }
    }
    
    // Ensure timer stops
    stopElapsedTimeCounter();
    
    // Reset processing status if needed
    state.processing = false;
    
    console.log('Processing animation fully stopped');
}

// Helper function to update token info UI
function updateTokenInfoUI(data) {
    if (!elements.tokenInfo) return;
    
    if (data.error) {
        elements.tokenInfo.innerHTML = `
            <div class="token-analysis error">
                <h3>Error Processing File</h3>
                <p>${data.error}</p>
            </div>
        `;
    } else {
        elements.tokenInfo.innerHTML = `
            <div class="token-analysis">
                <h3>Token Analysis</h3>
                <p>Estimated Input Tokens: ${data.estimated_tokens.toLocaleString()}</p>
                <p>Estimated Input Cost: $${data.estimated_cost.toFixed(4)}</p>
                <p>Maximum Safe Input Tokens: 200,000</p>
            </div>
        `;
    }
}

// Helper function to show token analysis errors
function showTokenAnalysisError(message) {
    if (!elements.tokenInfo) return;
    
    elements.tokenInfo.innerHTML = `
        <div class="token-analysis error">
            <h3>Error Processing File</h3>
            <p>${message}</p>
        </div>
    `;
}

// Helper function to disable inputs during generation
function disableInputsDuringGeneration(disable) {
    // Disable/enable input elements during generation
    const inputElements = [
        elements.apiKeyInput,
        elements.fileInput,
        elements.inputText,
        elements.additionalPrompt,
        elements.temperature,
        elements.maxTokens,
        elements.thinkingBudget,
        elements.model
    ];
    
    for (const element of inputElements) {
        if (element) {
            element.disabled = disable;
            
            // Add visual indication of disabled state
            if (disable) {
                element.classList.add('opacity-50');
            } else {
                element.classList.remove('opacity-50');
            }
        }
    }
    
    // Disable droparea functionality during generation
    if (elements.dropArea) {
        if (disable) {
            elements.dropArea.classList.add('pointer-events-none', 'opacity-50');
        } else {
            elements.dropArea.classList.remove('pointer-events-none', 'opacity-50');
        }
    }
}

// Helper function to connect to the streaming API
async function connectToStream(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
        const { value, done } = await reader.read();
        
        if (done) {
            break;
        }
        
        buffer += decoder.decode(value, { stream: true });
        
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // Keep the last incomplete chunk in the buffer
        
        for (const event of events) {
            if (event.trim() && event.startsWith('data: ')) {
                try {
                    const jsonStr = event.substring(6); // Remove 'data: ' prefix
                    const data = JSON.parse(jsonStr);
                    handleStreamEvent(data);
                } catch (e) {
                    console.error('Failed to parse event:', e);
                    // If we can't parse an event, make sure the UI is still updated
                    stopProcessingAnimation();
                }
            }
        }
    }
}

// Helper function to safely escape HTML 
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Function to get input content based on active tab
function getInputContent() {
    console.log("Getting input content for active tab:", state.activeTab);
    
    if (state.activeTab === 'file') {
        console.log("File content:", state.fileContent ? `${state.fileContent.substring(0, 50)}...` : "none");
        return state.fileContent;
    } else if (state.activeTab === 'text') {
        console.log("Text content:", state.textContent ? `${state.textContent.substring(0, 50)}...` : "none");
        return state.textContent;
    }
    
    return '';
}

// Helper function to show notifications
function showNotification(message, type = 'info') {
    // Implementation is similar to showToast function
    console.log(`NOTIFICATION (${type}): ${message}`);
    showToast(message, type);
}

// Toggle test mode state
function toggleTestMode() {
    state.testMode = elements.testModeToggle.checked;
    
    // Save test mode preference to localStorage
    localStorage.setItem('test_mode', state.testMode);
    
    // Update UI to reflect test mode state
    if (state.testMode) {
        showTestModeIndicator();
    } else {
        hideTestModeIndicator();
    }
    
    console.log(`Test mode ${state.testMode ? 'enabled' : 'disabled'}`);
}

function showTestModeIndicator() {
    // Create indicator if it doesn't exist
    if (!elements.testModeIndicator) {
        const indicator = document.createElement('span');
        indicator.id = 'test-mode-indicator';
        indicator.className = 'test-mode-active ml-2';
        indicator.textContent = 'Test Mode';
        
        // Add indicator next to the generate button
        elements.generateBtn.parentNode.insertBefore(indicator, elements.generateBtn.nextSibling);
        elements.testModeIndicator = indicator;
        
    } else if (elements.testModeIndicator) {
        elements.testModeIndicator.classList.remove('hidden');
    }
}

function hideTestModeIndicator() {
    if (elements.testModeIndicator) {
        elements.testModeIndicator.classList.add('hidden');
    }
}

// Modified function to more aggressively clear the local storage on page load
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Initialize the app
        init();
        
        // Check URL parameters for reset flag
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('reset')) {
            console.log('Reset flag detected in URL, clearing localStorage');
            resetUsageStatistics();
        }
        
        console.log('App loaded and ready!');
    } catch (e) {
        console.error('Error during initialization:', e);
    }
});

// Ensure the app initializes
if (document.readyState === 'loading') {
    console.log('Document still loading, waiting for DOMContentLoaded event');
} else {
    console.log('Document already loaded, initializing immediately');
    init();
}

// A wrapper function for compatibility in case someone calls startGeneration instead of generateWebsite
function startGeneration() {
    console.log('startGeneration called, forwarding to generateWebsite');
    if (typeof generateWebsite === 'function') {
        generateWebsite();
    } else {
        console.error('generateWebsite function not found in startGeneration!');
    }
}

// Reset output stats
function resetTokenStats() {
    elements.inputTokens.textContent = '0';
    elements.outputTokens.textContent = '0';
    // The thinking tokens element might exist in the DOM but should not be used
    elements.totalCost.textContent = '-';
}

// Update the UI with token usage data
function updateTokenStats(usage) {
    if (!usage) return;
    
    elements.inputTokens.textContent = usage.input_tokens.toLocaleString();
    elements.outputTokens.textContent = usage.output_tokens.toLocaleString();
    elements.totalCost.textContent = formatCostDisplay(usage.total_cost);
}

// Wrapper for updateTokenStats to handle Gemini usage data
function updateUsageStatistics(usage) {
    if (!usage) return;
    
    // For Gemini, we don't calculate cost since it's free
    if (state.apiProvider === 'gemini') {
        if (elements.inputTokens) {
            elements.inputTokens.textContent = usage.input_tokens.toLocaleString();
        }
        if (elements.outputTokens) {
            elements.outputTokens.textContent = usage.output_tokens.toLocaleString();
        }
        if (elements.totalCost) {
            elements.totalCost.textContent = '-'; // Always display as free for Gemini
        }
    } else {
        // For Anthropic, calculate cost if not provided
        if (!usage.total_cost) {
            // Claude 3 pricing: $3/M input tokens, $15/M output tokens
            usage.total_cost = (usage.input_tokens / 1000000) * 3.0 + (usage.output_tokens / 1000000) * 15.0;
        }
        
        // Update the token stats display
        updateTokenStats(usage);
    }
}

// Function to handle API provider change
function handleApiProviderChange(e) {
    const oldProvider = state.apiProvider;
    const newProvider = e.target.value;
    
    // Save the current API key to the appropriate storage
    const currentApiKey = elements.apiKeyInput.value.trim();
    if (currentApiKey) {
        const oldStorageKey = oldProvider === 'anthropic' ? ANTHROPIC_API_KEY_STORAGE_KEY : GEMINI_API_KEY_STORAGE_KEY;
        localStorage.setItem(oldStorageKey, currentApiKey);
    }
    
    // Update the state with the new provider
    state.apiProvider = newProvider;
    localStorage.setItem(API_PROVIDER_STORAGE_KEY, newProvider);
    
    // Load the API key for the new provider
    const newStorageKey = newProvider === 'anthropic' ? ANTHROPIC_API_KEY_STORAGE_KEY : GEMINI_API_KEY_STORAGE_KEY;
    const savedApiKey = localStorage.getItem(newStorageKey) || '';
    
    // Update the input field with the saved API key for the new provider
    if (elements.apiKeyInput) {
        elements.apiKeyInput.value = savedApiKey;
        state.apiKey = savedApiKey;
    }
    
    // Update the UI to show relevant API key info
    updateApiProviderInfo(newProvider);
    
    // Clear validation status when switching providers
    if (elements.keyStatus) {
        elements.keyStatus.classList.add('hidden');
    }
    
    // Update UI elements based on API provider
    updateUIForApiProvider(newProvider);
}

// Function to update API provider info in the UI
function updateApiProviderInfo(provider) {
    const anthropicInfo = document.getElementById('anthropic-info');
    const geminiInfo = document.getElementById('gemini-info');
    
    if (anthropicInfo && geminiInfo) {
        if (provider === 'anthropic') {
            anthropicInfo.classList.remove('hidden');
            geminiInfo.classList.add('hidden');
            elements.apiKeyInput.placeholder = "Enter your Anthropic API key";
        } else {
            anthropicInfo.classList.add('hidden');
            geminiInfo.classList.remove('hidden');
            elements.apiKeyInput.placeholder = "Enter your Google Gemini API key";
        }
    }
} 