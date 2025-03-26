// DOM Elements
const $ = document.querySelector.bind(document);
const $$ = document.querySelectorAll.bind(document);

// API configuration
const API_URL = window.location.origin;
const API_KEY_STORAGE_KEY = 'claude_visualizer_api_key';

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
    thinkingTokens: $('#thinking-tokens'),
    totalCost: $('#total-cost'),
    
    // Output
    previewIframe: $('#preview-iframe'),
    htmlOutput: $('#html-output'),
    copyHtml: $('#copy-html'),
    downloadHtml: $('#download-html'),
    openPreview: $('#open-preview'),
    
    // Token Info
    tokenInfo: $('#tokenInfo'),
    testModeIndicator: $('#test-mode-indicator'),
    
    // Usage Statistics
    totalUsageTokens: $('#total-usage-tokens'),
    totalUsageCost: $('#total-usage-cost')
};

// State
let state = {
    activeTab: 'file',
    apiKey: localStorage.getItem(API_KEY_STORAGE_KEY) || '',
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

// Initialize the app
function init() {
    console.log('Initializing app...');
    
    // Set initial theme based on localStorage or system preference
    const savedTheme = localStorage.getItem('theme');
    const html = document.documentElement;
    const sunIcon = document.querySelector('.fa-sun');
    const moonIcon = document.querySelector('.fa-moon');
    
    if (savedTheme === 'dark') {
        html.classList.add('dark');
        if (sunIcon && moonIcon) {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        }
    } else if (savedTheme === 'light') {
        html.classList.remove('dark');
        if (sunIcon && moonIcon) {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        }
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        html.classList.add('dark');
        if (sunIcon && moonIcon) {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        }
        localStorage.setItem('theme', 'dark');
    } else {
        html.classList.remove('dark');
        if (sunIcon && moonIcon) {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        }
        localStorage.setItem('theme', 'light');
    }
    
    // Set API key from localStorage if available
    if (state.apiKey) {
        elements.apiKeyInput.value = state.apiKey;
    }
    
    // Set default values
    state.maxTokens = 128000;
    state.thinkingBudget = 32000;
    elements.maxTokens.value = 128000;
    elements.thinkingBudget.value = 32000;
    elements.maxTokensValue.textContent = '128,000';
    elements.thinkingBudgetValue.textContent = '32,000';
    
    // Setup event listeners
    setupEventListeners();
    
    // Check button status
    updateGenerateButtonState();
    
    // Initial token analysis for text input if there's already text entered
    if (elements.inputText && elements.inputText.value.trim()) {
        state.textContent = elements.inputText.value.trim();
        analyzeTokens(state.textContent);
    }
    
    // Initialize test mode from localStorage
    if (elements.testModeToggle) {
        const savedTestMode = localStorage.getItem('test_mode') === 'true';
        console.log("Initializing test mode from localStorage:", savedTestMode);
        if (savedTestMode) {
            elements.testModeToggle.checked = true;
            state.testMode = true;
            showTestModeIndicator();
        }
    }
    
    // Load usage statistics
    loadUsageStatistics();
    
    console.log('App initialized');
}

// Setup event listeners
function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Theme Toggle
    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', toggleTheme);
    }
    
    // API Key
    if (elements.apiKeyInput) {
        elements.apiKeyInput.addEventListener('input', handleApiKeyInput);
    }
    
    if (elements.validateKeyBtn) {
        elements.validateKeyBtn.addEventListener('click', validateApiKey);
    }
    
    // Input Tabs
    if (elements.fileTab) {
        elements.fileTab.addEventListener('click', () => {
            console.log('File tab clicked');
            switchTab('file');
        });
    }
    
    if (elements.textTab) {
        elements.textTab.addEventListener('click', () => {
            console.log('Text tab clicked');
            switchTab('text');
        });
    }
    
    // File Upload
    if (elements.dropArea) {
        elements.dropArea.addEventListener('click', () => {
            console.log('Drop area clicked');
            if (elements.fileUpload) {
                elements.fileUpload.click();
            }
        });
    }
    
    if (elements.fileUpload) {
        elements.fileUpload.addEventListener('change', (e) => {
            console.log('File selected:', e.target.files[0]);
            handleFileUpload(e);
        });
    }
    
    setupDragAndDrop();
    
    // Text Input - Ensure we analyze tokens whenever text changes
    if (elements.inputText) {
        elements.inputText.addEventListener('input', (e) => {
            console.log('Text input changed');
            handleTextInput(e);
        });
        
        // Also analyze on paste
        elements.inputText.addEventListener('paste', (e) => {
            // Wait a bit for the paste to complete before analyzing
            setTimeout(() => {
                console.log('Text pasted');
                if (elements.inputText.value.trim()) {
                    analyzeTokens(elements.inputText.value.trim());
                } else if (elements.tokenInfo) {
                    // Clear token info if text is empty
                    elements.tokenInfo.innerHTML = '';
                }
            }, 100);
        });

        // Initial analysis if there's already text in the input
        if (elements.inputText.value.trim()) {
            analyzeTokens(elements.inputText.value.trim());
        }
    }
    
    // Parameter Controls
    if (elements.temperature) {
        elements.temperature.addEventListener('input', updateTemperature);
    }
    
    if (elements.temperatureReset) {
        elements.temperatureReset.addEventListener('click', resetTemperature);
    }
    
    if (elements.maxTokens) {
        elements.maxTokens.addEventListener('input', updateMaxTokens);
    }
    
    if (elements.maxTokensReset) {
        elements.maxTokensReset.addEventListener('click', resetMaxTokens);
    }
    
    if (elements.thinkingBudget) {
        elements.thinkingBudget.addEventListener('input', updateThinkingBudget);
    }
    
    if (elements.thinkingBudgetReset) {
        elements.thinkingBudgetReset.addEventListener('click', resetThinkingBudget);
    }
    
    // Generate Button
    if (elements.generateBtn) {
        elements.generateBtn.addEventListener('click', startGeneration);
    }
    
    // Output Actions
    if (elements.copyHtml) {
        elements.copyHtml.addEventListener('click', copyHtmlToClipboard);
    }
    
    if (elements.downloadHtml) {
        elements.downloadHtml.addEventListener('click', downloadHtml);
    }
    
    if (elements.openPreview) {
        elements.openPreview.addEventListener('click', openPreviewInNewTab);
    }
    
    // Test mode toggle
    if (elements.testModeToggle) {
        console.log("Setting up test mode toggle listener");
        elements.testModeToggle.addEventListener('change', function() {
            console.log("Test mode toggle changed:", elements.testModeToggle.checked);
            state.testMode = elements.testModeToggle.checked;
            localStorage.setItem('test_mode', state.testMode);
            
            if (state.testMode) {
                showTestModeIndicator();
            } else {
                hideTestModeIndicator();
            }
        });
    } else {
        console.warn("Test mode toggle element not found");
    }
    
    console.log('Event listeners set up');
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
function handleApiKeyInput(e) {
    state.apiKey = e.target.value.trim();
    state.apiKeyValidated = false;
    updateGenerateButtonState();
}

async function validateApiKey() {
    const key = state.apiKey;
    
    if (!key) {
        showKeyStatus(false, 'Please enter an API key');
        return false;
    }
    
    try {
        elements.validateKeyBtn.disabled = true;
        elements.validateKeyBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Validating...';
        
        const response = await fetch(`${API_URL}/api/validate-key`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ api_key: key })
        });
        
        const data = await response.json();
        
        if (data.valid) {
            showKeyStatus(true, 'API key is valid');
            localStorage.setItem(API_KEY_STORAGE_KEY, key);
            state.apiKeyValidated = true;
            return key;
        } else {
            showKeyStatus(false, data.message || 'Invalid API key');
            state.apiKeyValidated = false;
            return false;
        }
    } catch (error) {
        showKeyStatus(false, `Error: ${error.message}`);
        state.apiKeyValidated = false;
        return false;
    } finally {
        elements.validateKeyBtn.disabled = false;
        elements.validateKeyBtn.innerHTML = '<i class="fas fa-check-circle mr-2"></i>Validate Key';
        updateGenerateButtonState();
    }
}

function showKeyStatus(isValid, message) {
    if (!elements.keyStatus) return;
    
    elements.keyStatus.innerHTML = `
        <div class="flex items-center ${isValid ? 'text-green-500' : 'text-red-500'}">
            <i class="fas ${isValid ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    elements.keyStatus.classList.remove('hidden');
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
    
    if (!elements.fileTab || !elements.textTab) {
        console.error('Tab elements not found');
        return;
    }
    
    if (tab === 'file') {
        // Update tab styling
        elements.fileTab.classList.remove('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        elements.fileTab.classList.add('bg-primary-100', 'dark:bg-primary-900', 'text-primary-700', 'dark:text-primary-300');
        
        elements.textTab.classList.remove('bg-primary-100', 'dark:bg-primary-900', 'text-primary-700', 'dark:text-primary-300');
        elements.textTab.classList.add('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        
        // Show file input, hide text input
        if (elements.fileInput) elements.fileInput.classList.remove('hidden');
        if (elements.textInput) elements.textInput.classList.add('hidden');
        
        // Clear text input content when switching to file tab
        if (elements.inputText) {
            // Don't actually clear the UI element - just don't use it when generating
            state.textContent = '';
        }
    } else {
        // Update tab styling
        elements.textTab.classList.remove('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        elements.textTab.classList.add('bg-primary-100', 'dark:bg-primary-900', 'text-primary-700', 'dark:text-primary-300');
        
        elements.fileTab.classList.remove('bg-primary-100', 'dark:bg-primary-900', 'text-primary-700', 'dark:text-primary-300');
        elements.fileTab.classList.add('bg-gray-100', 'dark:bg-gray-700', 'text-gray-700', 'dark:text-gray-300');
        
        // Show text input, hide file input
        if (elements.textInput) elements.textInput.classList.remove('hidden');
        if (elements.fileInput) elements.fileInput.classList.add('hidden');
        
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
    
    // Update button state after tab switch
    updateGenerateButtonState();
}

// File Upload
function setupDragAndDrop() {
    const dropArea = elements.dropArea;
    if (!dropArea) {
        console.error('Drop area element not found');
        return;
    }
    
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
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    // Add click event to the drop area to open file dialog
    dropArea.addEventListener('click', function() {
        if (elements.fileUpload) {
            elements.fileUpload.click();
        }
    });
    
    // Add cursor pointer style
    dropArea.classList.add('cursor-pointer');
    
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
    
    // Make sure drop area has drop event listener
    dropArea.addEventListener('drop', handleDrop, false);
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
                const base64String = btoa(
                    Array.from(uint8Array)
                        .map(byte => String.fromCharCode(byte))
                        .join('')
                );
                
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
                                    <p>Maximum Safe Output Tokens: ${data.max_safe_output_tokens.toLocaleString()}</p>
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
                const base64String = btoa(
                    Array.from(uint8Array)
                        .map(byte => String.fromCharCode(byte))
                        .join('')
                );
                
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
    console.log('Handling text input...');
    const newText = e.target.value.trim();
    state.textContent = newText;
    updateGenerateButtonState();
    
    // Always analyze tokens for text input when the content changes
    if (newText) {
        analyzeTokens(newText);
    } else if (elements.tokenInfo) {
        // Clear token info if text is empty
        elements.tokenInfo.innerHTML = '';
    }
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
    if (!elements.generateBtn) {
        console.error('Generate button element not found');
        return;
    }
    
    const hasApiKey = !!state.apiKey;
    const hasContent = (state.activeTab === 'file' && !!state.fileContent) || 
                       (state.activeTab === 'text' && !!state.textContent);
    
    if (hasApiKey && hasContent) {
        elements.generateBtn.disabled = false;
        elements.generateBtn.classList.remove('bg-gray-300', 'dark:bg-gray-700', 'text-gray-500', 'dark:text-gray-400', 'cursor-not-allowed');
        elements.generateBtn.classList.add('bg-primary-500', 'hover:bg-primary-600', 'text-white', 'cursor-pointer');
        if (elements.generateError) {
            elements.generateError.classList.add('hidden');
        }
    } else {
        elements.generateBtn.disabled = true;
        elements.generateBtn.classList.add('bg-gray-300', 'dark:bg-gray-700', 'text-gray-500', 'dark:text-gray-400', 'cursor-not-allowed');
        elements.generateBtn.classList.remove('bg-primary-500', 'hover:bg-primary-600', 'text-white', 'cursor-pointer');
    }
}

// Main generation function
async function generateWebsite(content, apiKey, formatPrompt, temperature, maxTokens, thinkingBudget) {
    console.log(`Generating website with: provider=gemini, maxTokens=${maxTokens}, temperature=${temperature}, thinkingBudget=${thinkingBudget}`);
    
    // Mark as processing to prevent duplicate requests
    state.processing = true;
    disableInputsDuringGeneration(true);
    
    try {
        // Try non-streaming approach directly (skip the streaming attempt)
        await generateGeminiHTML(content, apiKey, formatPrompt, temperature, maxTokens);
    } catch (error) {
        console.error(`Failed to generate with Gemini API: ${error}`);
        showToast(`Error: ${error.message}`, "error");
        stopProcessingAnimation();
        resetGenerationUI();
    }
}

// Gemini Integration - Non-Streaming
async function generateGeminiHTML(content, apiKey, formatPrompt, temperature, maxTokens) {
    console.log("Starting Gemini HTML generation (non-streaming)...");
    
    // Estimate input tokens (approximate)
    const inputTokens = Math.ceil(content.length / 4);
    console.log(`Estimated input tokens: ${inputTokens}`);
    
    try {
        // Prepare request data
        const requestData = {
            api_key: apiKey,
            content: content,
            format_prompt: formatPrompt,
            temperature: temperature,
            max_tokens: maxTokens
        };
        
        // Determine if we're in a local development environment to handle CORS
        const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        let baseUrl = isLocalDev ? 'http://127.0.0.1:5011' : window.location.origin;
        
        console.log(`Making request to ${baseUrl}/api/process-gemini`);
        
        // Make the non-streaming request
        const response = await fetch(`${baseUrl}/api/process-gemini`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (data.html) {
            // Update the generated HTML
            state.generatedHtml = data.html;
            
            // Update the display
            updateHtmlDisplay();
            
            // Update the preview
            updatePreview();
            
            // Update usage statistics
            if (data.usage) {
                updateTokenUsage(data.usage);
                console.log("Received usage statistics from non-streaming API:", data.usage);
            }
            
            // Show success message
            console.log("Generation complete with Gemini (non-streaming)");
            showToast("Generation complete!", "success");
            
            // Reset UI
            stopProcessingAnimation();
            resetGenerationUI(true);
            
            return true;
        } else {
            throw new Error("No HTML content received from the server");
        }
    } catch (error) {
        console.error("Error generating with Gemini non-streaming:", error);
        throw error;
    }
}

function updateHtmlDisplay() {
    const htmlOutput = elements.htmlOutput;
    htmlOutput.textContent = state.generatedHtml;
    
    // Highlight with Prism.js
    if (window.Prism) {
        Prism.highlightElement(htmlOutput);
    }
}

function updatePreview() {
    const iframe = elements.previewIframe;
    const blob = new Blob([state.generatedHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    
    iframe.src = url;
}

function resetGenerationUI(success = false) {
    // Reset button and status
    if (elements.generateBtn) {
        elements.generateBtn.disabled = false;
        elements.generateBtn.innerHTML = '<i class="fas fa-magic mr-2"></i>Generate Visualization';
    }
    
    // Hide processing status if not successful
    if (!success && elements.processingStatus) {
        elements.processingStatus.classList.add('hidden');
    } else if (success && elements.resultSection) {
        // Show result section
        elements.resultSection.classList.remove('hidden');
    }
    
    // Re-enable all inputs
    disableInputsDuringGeneration(false);
    
    // Reset state
    state.processing = false;
}

// Output Actions
function copyHtmlToClipboard() {
    navigator.clipboard.writeText(state.generatedHtml)
        .then(() => showToast('HTML copied to clipboard', 'success'))
        .catch(err => showToast('Failed to copy HTML', 'error'));
}

function downloadHtml() {
    // Generate a filename
    let filename = 'visualization.html';
    
    if (state.activeTab === 'file' && state.fileName) {
        const nameWithoutExt = state.fileName.replace(/\.[^/.]+$/, "");
        filename = `${nameWithoutExt}_visualization.html`;
    } else if (state.activeTab === 'text' && state.textContent) {
        // Create a summary from the first few words of the text
        const firstWords = state.textContent.trim().split(/\s+/).slice(0, 5).join('_');
        if (firstWords.length > 0) {
            filename = `${firstWords}_visualization.html`;
        }
    }
    
    // Create download link
    const blob = new Blob([state.generatedHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    
    a.href = url;
    a.download = filename;
    a.click();
    
    // Clean up
    URL.revokeObjectURL(url);
    showToast(`Downloaded as ${filename}`, 'success');
}

function openPreviewInNewTab() {
    const blob = new Blob([state.generatedHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
}

// Toast Notification
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast fade-in';
    
    // Set color based on type
    let bgColor, textColor, icon;
    
    switch (type) {
        case 'success':
            bgColor = 'bg-green-500';
            textColor = 'text-white';
            icon = 'fa-check-circle';
            break;
        case 'error':
            bgColor = 'bg-red-500';
            textColor = 'text-white';
            icon = 'fa-exclamation-circle';
            break;
        default:
            bgColor = 'bg-primary-500';
            textColor = 'text-white';
            icon = 'fa-info-circle';
    }
    
    toast.classList.add(bgColor, textColor);
    
    // Set content
    toast.innerHTML = `<i class="fas ${icon} mr-2"></i>${message}`;
    
    // Add to document
    document.body.appendChild(toast);
    
    // Remove after animation completes
    setTimeout(() => {
        toast.remove();
    }, 5300);
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
        
        // Update token info display
        if (elements.tokenInfo) {
            elements.tokenInfo.innerHTML = `
                <div class="token-analysis">
                    <h3>Token Analysis</h3>
                    <p>Estimated Input Tokens: ${data.estimated_tokens.toLocaleString()}</p>
                    <p>Estimated Input Cost: $${data.estimated_cost.toFixed(4)}</p>
                    <p>Maximum Safe Output Tokens: ${data.max_safe_output_tokens.toLocaleString()}</p>
                </div>
            `;
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
    const tokenInfoElement = elements.tokenInfo;
    if (!tokenInfoElement) return;
    
    try {
        if (data) {
            if (data.error) {
                tokenInfoElement.innerHTML = `
                    <div class="token-analysis text-red-500">
                        <h3>Token Analysis Error</h3>
                        <p>${data.error}</p>
                    </div>
                `;
            } else {
                tokenInfoElement.innerHTML = `
                    <div class="token-analysis">
                        <h3>Token Analysis</h3>
                        <p>Estimated Input Tokens: ${data.estimated_tokens.toLocaleString()}</p>
                        <p>Estimated Input Cost: $${data.estimated_cost.toFixed(4)}</p>
                        <p>Maximum Safe Output Tokens: ${data.max_safe_output_tokens.toLocaleString()}</p>
                    </div>
                `;
            }
        } else {
            tokenInfoElement.innerHTML = `
                <div class="token-analysis text-gray-400">
                    <h3>Token Analysis</h3>
                    <p>Enter text or upload a file to see token count</p>
                </div>
            `;
        }
    } catch (err) {
        console.error("Error updating token info UI:", err);
        tokenInfoElement.innerHTML = `
            <div class="token-analysis text-red-500">
                <h3>Token Analysis Error</h3>
                <p>Failed to display token information</p>
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

// Helper function to disable/enable inputs during generation
function disableInputsDuringGeneration(disable) {
    // Disable/enable input elements
    const inputElements = [
        elements.inputText,             // Text input
        elements.fileUpload,            // File upload
        elements.additionalPrompt,      // Additional prompt
        elements.temperature,           // Temperature
        elements.maxTokens,             // Max tokens
        elements.thinkingBudget,        // Thinking budget
        elements.temperatureReset,      // Temperature reset
        elements.maxTokensReset,        // Max tokens reset
        elements.thinkingBudgetReset,   // Thinking budget reset
        elements.fileTab,               // File tab
        elements.textTab                // Text tab
    ];
    
    // Apply disabled state to all elements
    inputElements.forEach(element => {
        if (element) {
            element.disabled = disable;
            
            // Add visual indication of disabled state
            if (disable) {
                element.classList.add('opacity-50');
            } else {
                element.classList.remove('opacity-50');
            }
        }
    });
    
    // Disable droparea functionality during generation
    if (elements.dropArea) {
        if (disable) {
            elements.dropArea.classList.add('pointer-events-none', 'opacity-50');
        } else {
            elements.dropArea.classList.remove('pointer-events-none', 'opacity-50');
        }
    }
}

// Helper function to update token usage display
function updateTokenUsage(usage) {
    const inputTokens = usage.input_tokens || 0;
    const outputTokens = usage.output_tokens || 0;
    const thinkingTokens = usage.thinking_tokens || 0;
    const totalTokens = usage.total_tokens || (inputTokens + outputTokens + thinkingTokens);
    
    // Estimate cost at $3 per million tokens for Claude 3.7 Sonnet
    const estimatedCost = (totalTokens / 1000000) * 3;
    
    // Update the UI
    elements.totalCost.textContent = `$${estimatedCost.toFixed(4)}`;
}

// Helper function to safely escape HTML 
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Function to get the input content from the active tab
function getInputContent() {
    console.log("Getting input content");
    
    if (state.activeTab === 'text') {
        // Get content from text input
        if (elements.inputText && elements.inputText.value.trim()) {
            console.log("Returning text input content");
            return elements.inputText.value.trim();
        }
    } else if (state.activeTab === 'file') {
        // Get content from file upload
        if (state.fileContent) {
            console.log("Returning file content");
            return state.fileContent;
        }
    }
    
    console.log("No input content found");
    return null;
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

function hideTestModeIndicator() {
    if (elements.testModeIndicator) {
        elements.testModeIndicator.classList.add('hidden');
    }
}

function showTestModeIndicator() {
    console.log("Showing test mode indicator");
    // Create indicator if it doesn't exist
    if (!elements.testModeIndicator) {
        const indicator = document.createElement('span');
        indicator.id = 'test-mode-indicator';
        indicator.className = 'test-mode-active ml-2';
        indicator.textContent = 'Test Mode';
        
        // Add indicator next to the generate button
        if (elements.generateBtn && elements.generateBtn.parentNode) {
            elements.generateBtn.parentNode.insertBefore(indicator, elements.generateBtn.nextSibling);
            elements.testModeIndicator = indicator;
        } else {
            console.warn("Generate button not found for adding test mode indicator");
        }
    } else if (elements.testModeIndicator) {
        elements.testModeIndicator.classList.remove('hidden');
    }
}

// Load and save usage statistics
function saveUsageStatistics(usage) {
    try {
        // Get existing statistics
        const existingStats = JSON.parse(localStorage.getItem('usage_statistics') || '[]');
        
        // Add new usage data with timestamp
        const newEntry = {
            timestamp: new Date().toISOString(),
            input_tokens: usage.input_tokens || 0,
            output_tokens: usage.output_tokens || 0,
            thinking_tokens: usage.thinking_tokens || 0,
            total_cost: usage.total_cost || 0,
            test_mode: state.testMode
        };
        
        // Add to beginning of array (newest first)
        existingStats.unshift(newEntry);
        
        // Limit to last 20 entries
        const limitedStats = existingStats.slice(0, 20);
        
        // Save back to localStorage
        localStorage.setItem('usage_statistics', JSON.stringify(limitedStats));
        console.log('Usage statistics saved:', newEntry);
    } catch (error) {
        console.error('Error saving usage statistics:', error);
    }
}

function loadUsageStatistics() {
    try {
        const statistics = JSON.parse(localStorage.getItem('usage_statistics') || '[]');
        
        // Calculate totals
        let totalTokens = 0;
        let totalCost = 0;
        
        statistics.forEach(entry => {
            totalTokens += (entry.input_tokens || 0) + (entry.output_tokens || 0) + (entry.thinking_tokens || 0);
            totalCost += entry.total_cost || 0;
        });
        
        // Update UI if we have elements for it
        if (elements.totalUsageTokens) {
            elements.totalUsageTokens.textContent = totalTokens.toLocaleString();
        }
        
        if (elements.totalUsageCost) {
            elements.totalUsageCost.textContent = `$${totalCost.toFixed(4)}`;
        }
        
        console.log('Usage statistics loaded:', {
            entries: statistics.length,
            totalTokens,
            totalCost
        });
        
    } catch (error) {
        console.error('Error loading usage statistics:', error);
    }
}

// Helper function to set the processing text
function setProcessingText(text) {
    if (elements.processingText) {
        elements.processingText.textContent = text;
    }
}

// Function to update the HTML preview with error handling for null elements
function updateHtmlPreview(html) {
    try {
        if (!html) return;
        
        // Update the HTML output textarea/pre element
        if (elements.htmlOutput) {
            elements.htmlOutput.textContent = html;
            
            // Highlight with Prism.js if available
            if (window.Prism) {
                Prism.highlightElement(elements.htmlOutput);
            }
        }
        
        // Update the preview iframe if it exists
        if (elements.previewIframe) {
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            elements.previewIframe.src = url;
        }
        
        // Save the HTML to the state
        state.generatedHtml = html;
        
        // Show result section if available
        showResultSection();
    } catch (error) {
        console.error('Error updating HTML preview:', error);
    }
}

// Function to show the result section if it exists
function showResultSection() {
    if (elements.resultSection) {
        elements.resultSection.classList.remove('hidden');
    }
}

// Initialize the app
document.addEventListener('DOMContentLoaded', init); 