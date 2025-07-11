// Natural Language to SQL Converter - Frontend JavaScript - Updated 2025-01-01

class SQLConverter {
    constructor() {
        this.initializeEventListeners();
        this.loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        this.historyModal = new bootstrap.Modal(document.getElementById('historyModal'));
        
        // Initialize Prism.js for syntax highlighting
        if (typeof Prism !== 'undefined') {
            Prism.highlightAll();
        }
        
        // Set up scroll restoration on page visibility change
        this.setupScrollRestoration();
    }
    
    setupScrollRestoration() {
        // Restore scroll on visibility change (tab switching)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.restoreScrolling();
            }
        });
        
        // Restore scroll on focus
        window.addEventListener('focus', () => {
            this.restoreScrolling();
        });
        
        // Add click handler to restore scrolling when clicking anywhere
        document.addEventListener('click', (e) => {
            // Only restore if not clicking on modal content
            if (!e.target.closest('.modal-content')) {
                setTimeout(() => this.restoreScrolling(), 100);
            }
        });
        
        // Add keyboard shortcut (Ctrl+Shift+S) to restore scrolling
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'S') {
                e.preventDefault();
                this.restoreScrolling();
                this.showSuccess('Scroll restored manually');
            }
        });
    }
    
    restoreScrolling() {
        try {
            // Remove modal-open class
            document.body.classList.remove('modal-open');
            
            // Remove all overflow restrictions
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');
            document.documentElement.style.removeProperty('overflow');
            
            // Explicitly set to allow scrolling
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
            
            // Remove any stuck modal backdrops
            document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                if (!backdrop.closest('.modal.show')) {
                    backdrop.remove();
                }
            });
            
            console.log('Scroll restored');
        } catch (error) {
            console.warn('Error restoring scroll:', error);
        }
    }

    initializeEventListeners() {
        // Form submission
        const form = document.getElementById('sqlConverterForm');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Example queries
        document.querySelectorAll('.example-query').forEach(button => {
            button.addEventListener('click', (e) => this.handleExampleClick(e));
        });

        // Schema selection
        const schemaSelect = document.getElementById('schemaSelect');
        if (schemaSelect) {
            schemaSelect.addEventListener('change', (e) => this.handleSchemaChange(e));
        }
    }

    async handleFormSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const data = {
            natural_language: formData.get('natural_language'),
            schema_context: formData.get('schema_context') || ''
        };

        if (!data.natural_language.trim()) {
            this.showError('Please enter a natural language description.');
            return;
        }

        this.showLoading(true);
        
        try {
            const response = await fetch('/convert', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.displaySQLResult(result);
                this.showSuccess('SQL query generated successfully!');
            } else {
                // Force hide loading immediately - multiple attempts for safety
                this.showLoading(false);
                setTimeout(() => this.showLoading(false), 50);
                setTimeout(() => this.showLoading(false), 200);
                
                this.showError(result.error || 'Failed to generate SQL query');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showLoading(false);
            this.showError('Network error occurred. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    handleExampleClick(event) {
        const query = event.target.dataset.query;
        const textarea = document.getElementById('naturalLanguageInput');
        if (textarea) {
            textarea.value = query;
            textarea.focus();
        }
    }

    async handleSchemaChange(event) {
        // Schema context is now used only for SQL generation context
        // No UI display needed
    }

    displaySQLResult(result) {
        // Ensure loading state is completely hidden
        this.showLoading(false);
        
        // Additional safety check to hide any stuck loading modals
        setTimeout(() => {
            this.showLoading(false);
        }, 100);
        
        // Show the SQL output section
        const sqlOutput = document.getElementById('sqlOutput');
        const emptyState = document.getElementById('emptyState');
        const errorState = document.getElementById('errorState');
        const outputActions = document.getElementById('outputActions');

        if (sqlOutput && emptyState && errorState && outputActions) {
            emptyState.classList.add('d-none');
            errorState.classList.add('d-none');
            sqlOutput.classList.remove('d-none');
            outputActions.classList.remove('d-none');
        }

        // Display the SQL code
        const sqlCode = document.getElementById('sqlCode');
        if (sqlCode) {
            sqlCode.textContent = result.sql;
            
            // Re-highlight syntax
            if (typeof Prism !== 'undefined') {
                Prism.highlightElement(sqlCode);
            }
        }

        // Display explanation
        const explanationText = document.getElementById('explanationText');
        if (explanationText && result.explanation) {
            explanationText.textContent = result.explanation;
        }

        // Display validation results if available
        if (result.validation) {
            this.displayValidationResults(result.validation);
        }

        // Display feedback analysis if available
        if (result.feedback) {
            this.displayFeedbackAnalysis(result.feedback);
        }

        // Store the current SQL for later use
        this.currentSQL = result.sql;
        this.currentQueryId = result.query_id;
    }

    displayValidationResults(validation) {
        const validationResults = document.getElementById('validationResults');
        const validationContent = document.getElementById('validationContent');
        
        if (!validationResults || !validationContent) return;

        let html = '';

        // Validation status
        if (validation.is_valid) {
            html += '<div class="validation-item validation-success">';
            html += '<i class="fas fa-check-circle me-2"></i>';
            html += '<strong>Valid SQL Query</strong>';
            html += '</div>';
        } else {
            html += '<div class="validation-item validation-error">';
            html += '<i class="fas fa-exclamation-circle me-2"></i>';
            html += '<strong>SQL Validation Failed</strong>';
            html += '</div>';
        }

        // Errors
        if (validation.errors && validation.errors.length > 0) {
            validation.errors.forEach(error => {
                html += '<div class="validation-item validation-error">';
                html += '<i class="fas fa-times-circle me-2"></i>';
                html += `<strong>Error:</strong> ${this.escapeHtml(error)}`;
                html += '</div>';
            });
        }

        // Warnings
        if (validation.warnings && validation.warnings.length > 0) {
            validation.warnings.forEach(warning => {
                html += '<div class="validation-item validation-warning">';
                html += '<i class="fas fa-exclamation-triangle me-2"></i>';
                html += `<strong>Warning:</strong> ${this.escapeHtml(warning)}`;
                html += '</div>';
            });
        }

        // Suggestions
        if (validation.suggestions && validation.suggestions.length > 0) {
            validation.suggestions.forEach(suggestion => {
                html += '<div class="validation-item validation-suggestion">';
                html += '<i class="fas fa-lightbulb me-2"></i>';
                html += `<strong>Suggestion:</strong> ${this.escapeHtml(suggestion)}`;
                html += '</div>';
            });
        }

        // Security issues
        if (validation.security_issues && validation.security_issues.length > 0) {
            validation.security_issues.forEach(issue => {
                html += '<div class="validation-item validation-error">';
                html += '<i class="fas fa-shield-alt me-2"></i>';
                html += `<strong>Security Issue:</strong> ${this.escapeHtml(issue)}`;
                html += '</div>';
            });
        }

        if (html) {
            validationContent.innerHTML = html;
            validationResults.classList.remove('d-none');
        } else {
            validationResults.classList.add('d-none');
        }
    }



    showLoading(show) {
        try {
            if (show) {
                this.loadingModal.show();
                // Safety timeout to auto-hide loading after 30 seconds
                this.loadingTimeout = setTimeout(() => {
                    this.showLoading(false);
                    this.showError('Request timed out. Please try again.');
                }, 30000);
            } else {
                // Clear any existing timeout
                if (this.loadingTimeout) {
                    clearTimeout(this.loadingTimeout);
                    this.loadingTimeout = null;
                }
                
                // Multiple approaches to ensure modal is hidden
                this.loadingModal.hide();
                
                // Force hide through Bootstrap's internal methods
                const modalElement = document.getElementById('loadingModal');
                if (modalElement) {
                    modalElement.classList.remove('show');
                    modalElement.style.display = 'none';
                    modalElement.setAttribute('aria-hidden', 'true');
                    modalElement.removeAttribute('aria-modal');
                }
                
                // Remove any stuck backdrops and restore scrolling
                const removeBackdrops = () => {
                    document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
                    document.body.classList.remove('modal-open');
                    document.body.style.removeProperty('padding-right');
                    document.body.style.removeProperty('overflow');
                    document.body.style.overflow = '';
                    document.documentElement.style.removeProperty('overflow');
                    document.documentElement.style.overflow = '';
                };
                
                removeBackdrops();
                setTimeout(removeBackdrops, 50);
                setTimeout(removeBackdrops, 200);
                setTimeout(removeBackdrops, 500); // Extra cleanup
            }
        } catch (error) {
            console.error('Error managing loading state:', error);
            // Emergency fallback - force remove all modal elements and restore scroll
            if (!show) {
                this.restoreScrolling();
            }
        }
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showError(message) {
        const errorState = document.getElementById('errorState');
        const errorMessage = document.getElementById('errorMessage');
        const sqlOutput = document.getElementById('sqlOutput');
        
        if (errorState && errorMessage) {
            errorMessage.textContent = message;
            errorState.classList.remove('d-none');
            
            if (sqlOutput) {
                sqlOutput.classList.add('d-none');
            }
        }
        
        this.showToast(message, 'error');
    }

    showToast(message, type) {
        // Create toast element
        const toastContainer = this.getToastContainer();
        const toastId = 'toast-' + Date.now();
        
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type === 'error' ? 'danger' : 'success'} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'} me-2"></i>
                        ${this.escapeHtml(message)}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    getToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1055';
            document.body.appendChild(container);
        }
        return container;
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Global functions for button actions
async function copyToClipboard() {
    const sqlCode = document.getElementById('sqlCode');
    if (!sqlCode || !sqlCode.textContent) {
        return;
    }

    try {
        await navigator.clipboard.writeText(sqlCode.textContent);
        
        // Visual feedback
        const copyBtn = event.target.closest('button');
        if (copyBtn) {
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
            copyBtn.classList.add('copy-success');
            
            setTimeout(() => {
                copyBtn.innerHTML = originalText;
                copyBtn.classList.remove('copy-success');
            }, 2000);
        }
        
        // Show toast
        window.sqlConverter.showSuccess('SQL query copied to clipboard!');
    } catch (err) {
        console.error('Failed to copy text: ', err);
        window.sqlConverter.showError('Failed to copy to clipboard');
    }
}

async function validateSQL() {
    const sqlCode = document.getElementById('sqlCode');
    if (!sqlCode || !sqlCode.textContent) {
        window.sqlConverter.showError('No SQL query to validate');
        return;
    }

    try {
        const response = await fetch('/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sql: sqlCode.textContent
            })
        });

        const result = await response.json();

        if (result.success) {
            window.sqlConverter.displayValidationResults(result.validation);
            window.sqlConverter.showSuccess('SQL validation completed');
        } else {
            window.sqlConverter.showError(result.error || 'Validation failed');
        }
    } catch (error) {
        console.error('Error validating SQL:', error);
        window.sqlConverter.showError('Network error during validation');
    }
}

async function showHistory() {
    const modal = document.getElementById('historyModal');
    const historyContent = document.getElementById('historyContent');
    
    if (!modal || !historyContent) return;

    // Show loading state
    historyContent.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2 text-muted">Loading query history...</p>
        </div>
    `;

    // Show modal
    const historyModal = new bootstrap.Modal(modal);
    historyModal.show();

    try {
        const response = await fetch('/history');
        const result = await response.json();

        if (result.success && result.history) {
            displayHistoryContent(result.history);
        } else {
            historyContent.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                    <h6 class="mt-3">Failed to load history</h6>
                    <p class="text-muted">Could not retrieve query history</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading history:', error);
        historyContent.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                <h6 class="mt-3">Error loading history</h6>
                <p class="text-muted">Network error occurred</p>
            </div>
        `;
    }
}

function showSchemaUpload() {
    const modal = document.getElementById('schemaUploadModal');
    if (!modal) return;
    
    const schemaUploadModal = new bootstrap.Modal(modal);
    schemaUploadModal.show();
    
    // Add form submission handler
    const form = document.getElementById('schemaUploadForm');
    if (form) {
        form.onsubmit = handleSchemaUpload;
    }
}

async function handleSchemaUpload(event) {
    event.preventDefault();
    
    const schemaName = document.getElementById('schemaName').value.trim();
    const schemaJson = document.getElementById('schemaJson').value.trim();
    
    if (!schemaName || !schemaJson) {
        window.sqlConverter.showError('Please provide both schema name and JSON definition');
        return;
    }
    
    try {
        const tables = JSON.parse(schemaJson);
        
        const response = await fetch('/upload-schema', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                schema_name: schemaName,
                tables: tables
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.sqlConverter.showSuccess(`Schema "${schemaName}" uploaded successfully!`);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('schemaUploadModal'));
            if (modal) modal.hide();
            
            // Clear form
            document.getElementById('schemaUploadForm').reset();
            
            // Refresh schema dropdown
            location.reload();
        } else {
            window.sqlConverter.showError(result.error || 'Failed to upload schema');
        }
    } catch (error) {
        if (error instanceof SyntaxError) {
            window.sqlConverter.showError('Invalid JSON format. Please check your schema definition.');
        } else {
            console.error('Error uploading schema:', error);
            window.sqlConverter.showError('Network error occurred while uploading schema');
        }
    }
}

function showSchemaAnalyzer() {
    const modal = document.getElementById('schemaAnalyzerModal');
    if (!modal) return;
    
    const schemaAnalyzerModal = new bootstrap.Modal(modal);
    schemaAnalyzerModal.show();
    
    // Add form submission handler
    const form = document.getElementById('schemaAnalyzerForm');
    if (form) {
        form.onsubmit = handleSchemaAnalysis;
    }
    
    // Initialize authentication fields
    toggleAuthFields();
}

// Toggle authentication fields based on selected type
function toggleAuthFields() {
    const authType = document.getElementById('authType').value;
    const sqlAuthFields = document.getElementById('sqlAuthFields');
    const windowsAuthInfo = document.getElementById('windowsAuthInfo');
    const usernameField = document.getElementById('dbUsername');
    const passwordField = document.getElementById('dbPassword');
    
    if (authType === 'sql') {
        sqlAuthFields.style.display = 'block';
        windowsAuthInfo.style.display = 'none';
        usernameField.required = true;
        passwordField.required = true;
    } else if (authType === 'windows') {
        sqlAuthFields.style.display = 'none';
        windowsAuthInfo.style.display = 'block';
        usernameField.required = false;
        passwordField.required = false;
        usernameField.value = '';
        passwordField.value = '';
    } else {
        sqlAuthFields.style.display = 'none';
        windowsAuthInfo.style.display = 'none';
        usernameField.required = false;
        passwordField.required = false;
    }
}

// Test database connection
async function testConnection() {
    const connectionInfo = getConnectionInfo();
    if (!connectionInfo) return;
    
    const testButton = document.querySelector('button[onclick="testConnection()"]');
    const resultDiv = document.getElementById('connectionTestResult');
    
    // Show loading state
    testButton.disabled = true;
    testButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Testing...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `
        <div class="alert alert-info">
            <i class="fas fa-clock me-2"></i>Testing connection to SQL Server...
        </div>
    `;
    
    try {
        const response = await fetch('/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                connection_info: connectionInfo
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>Connection Successful!</strong><br>
                    <small>Connected to: ${result.server_info || 'SQL Server'}</small>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <strong>Connection Failed:</strong><br>
                    <small>${result.error}</small>
                </div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    } finally {
        testButton.disabled = false;
        testButton.innerHTML = '<i class="fas fa-plug me-2"></i>Test Connection';
    }
}

// Get connection info from form
function getConnectionInfo() {
    const dbType = document.getElementById('dbType').value;
    const authType = document.getElementById('authType').value;
    const dbHost = document.getElementById('dbHost').value.trim();
    const dbPort = document.getElementById('dbPort').value.trim();
    const dbDatabase = document.getElementById('dbDatabase').value.trim();
    const dbUsername = document.getElementById('dbUsername').value.trim();
    const dbPassword = document.getElementById('dbPassword').value.trim();
    
    if (!dbType || !authType || !dbHost || !dbDatabase) {
        window.sqlConverter.showError('Please fill in all required fields');
        return null;
    }
    
    if (authType === 'sql' && (!dbUsername || !dbPassword)) {
        window.sqlConverter.showError('Please provide username and password for SQL authentication');
        return null;
    }
    
    return {
        database_type: dbType,
        auth_type: authType,
        host: dbHost,
        port: dbPort || '1433',
        database: dbDatabase,
        username: dbUsername,
        password: dbPassword
    };
}

async function handleSchemaAnalysis(event) {
    event.preventDefault();
    
    const connectionInfo = getConnectionInfo();
    if (!connectionInfo) return;
    
    const resultsDiv = document.getElementById('analysisResults');
    
    // Show loading state
    resultsDiv.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Analyzing...</span>
            </div>
            <h6 class="mt-3">AI Analyzing Your Database</h6>
            <p class="text-muted">This may take a few minutes for large databases...</p>
            <small class="text-muted">
                • Connecting to database<br>
                • Extracting schema information<br>
                • Analyzing table patterns<br>
                • Generating AI descriptions
            </small>
        </div>
    `;
    
    try {
        
        const response = await fetch('/analyze-schema', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                connection_info: connectionInfo
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayAnalysisResults(result.analysis, result.suggested_descriptions, result.schema_saved, result.schema_name);
            
            // Show success message if schema was automatically saved
            if (result.schema_saved) {
                window.sqlConverter.showSuccess(`✓ Analysis complete! Schema "${result.schema_name}" automatically saved and added to dropdown.`);
            }
        } else {
            resultsDiv.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-exclamation-triangle text-warning fa-2x mb-3"></i>
                    <h6>Analysis Failed</h6>
                    <p class="text-danger">${result.error}</p>
                    <small class="text-muted">
                        Please check your database connection details and try again.
                    </small>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error analyzing schema:', error);
        resultsDiv.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-exclamation-triangle text-warning fa-2x mb-3"></i>
                <h6>Network Error</h6>
                <p class="text-danger">Failed to connect to analysis service</p>
                <small class="text-muted">Please check your network connection and try again.</small>
            </div>
        `;
    }
}

function displayAnalysisResults(analysis, descriptions, schemaSaved = false, schemaName = '') {
    const resultsDiv = document.getElementById('analysisResults');
    
    let html = `
        <div class="analysis-results">
            <div class="mb-4">
                <h6 class="text-success">
                    <i class="fas fa-check-circle me-2"></i>
                    Analysis Complete
                </h6>
                <p class="text-muted mb-3">AI has analyzed your database and generated descriptions for cryptic table names.</p>
                ${schemaSaved ? `
                    <div class="alert alert-success border-0 mb-3">
                        <i class="fas fa-save me-2"></i>
                        <strong>Schema Automatically Saved!</strong><br>
                        <small>Schema "${schemaName}" has been saved to <code>services/schemas/${schemaName}.json</code> and is now available in the dropdown.</small>
                    </div>
                ` : ''}
            </div>
    `;
    
    // Show naming patterns discovered
    if (analysis.naming_conventions) {
        html += `
            <div class="mb-4">
                <h6><i class="fas fa-pattern me-2"></i>Naming Patterns Discovered</h6>
                <div class="row">
                    <div class="col-md-6">
                        <small class="text-muted">Common Prefixes:</small>
                        <div class="badge bg-secondary me-1 mb-1">${analysis.naming_conventions.common_prefixes.join('</div><div class="badge bg-secondary me-1 mb-1">')}</div>
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">Common Suffixes:</small>
                        <div class="badge bg-secondary me-1 mb-1">${analysis.naming_conventions.common_suffixes.join('</div><div class="badge bg-secondary me-1 mb-1">')}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Show table analysis results
    html += `<div class="mb-4">
        <h6><i class="fas fa-table me-2"></i>Table Analysis Results</h6>
        <div class="accordion" id="tableAnalysisAccordion">
    `;
    
    let tableIndex = 0;
    for (const [tableName, tableDesc] of Object.entries(descriptions.tables)) {
        const confidence = Math.round(tableDesc.confidence * 100);
        const confidenceColor = confidence > 70 ? 'success' : confidence > 40 ? 'warning' : 'danger';
        
        html += `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#table${tableIndex}">
                        <div class="d-flex justify-content-between align-items-center w-100">
                            <span>
                                <code class="text-primary">${tableName}</code>
                                <span class="badge bg-${confidenceColor} ms-2">${confidence}% confidence</span>
                            </span>
                            <small class="text-muted me-3">${tableDesc.purpose}</small>
                        </div>
                    </button>
                </h2>
                <div id="table${tableIndex}" class="accordion-collapse collapse" data-bs-parent="#tableAnalysisAccordion">
                    <div class="accordion-body">
                        <p><strong>AI Description:</strong> ${tableDesc.description}</p>
                        ${tableDesc.evidence.length > 0 ? `
                            <p><strong>Evidence:</strong></p>
                            <ul class="small">
                                ${tableDesc.evidence.map(ev => `<li>${ev}</li>`).join('')}
                            </ul>
                        ` : ''}
                        
                        <div class="mt-3">
                            <h6>Column Descriptions:</h6>
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Column</th>
                                            <th>AI Description</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${Object.entries(descriptions.columns[tableName] || {}).map(([colName, colDesc]) => `
                                            <tr>
                                                <td><code>${colName}</code></td>
                                                <td>${colDesc}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        tableIndex++;
    }
    
    html += `
        </div>
    </div>
    
    <div class="d-grid gap-2">
        <button class="btn btn-success" onclick="exportAnalysisToSchema()">
            <i class="fas fa-download me-2"></i>
            Export as Schema JSON
        </button>
        <button class="btn btn-primary" onclick="useAnalysisAsSchema()">
            <i class="fas fa-check me-2"></i>
            Use This Analysis as Schema
        </button>
    </div>
    </div>
    `;
    
    resultsDiv.innerHTML = html;
}

function exportAnalysisToSchema() {
    window.sqlConverter.showSuccess('Analysis export feature coming soon!');
}

function useAnalysisAsSchema() {
    window.sqlConverter.showSuccess('Schema import from analysis feature coming soon!');
}

async function showHistory() {
    const modal = document.getElementById('historyModal');
    const historyContent = document.getElementById('historyContent');
    
    if (!modal || !historyContent) return;

    // Show loading state
    historyContent.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2 text-muted">Loading query history...</p>
        </div>
    `;

    // Show modal
    const historyModal = new bootstrap.Modal(modal);
    historyModal.show();

    try {
        const response = await fetch('/history');
        const result = await response.json();

        if (result.success && result.history) {
            displayHistoryContent(result.history);
        } else {
            historyContent.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                    <h6 class="mt-3">Failed to load history</h6>
                    <p class="text-muted">${result.error || 'Unknown error occurred'}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading history:', error);
        historyContent.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-wifi text-danger" style="font-size: 2rem;"></i>
                <h6 class="mt-3">Network Error</h6>
                <p class="text-muted">Could not connect to the server</p>
            </div>
        `;
    }
}

function displayHistoryContent(history) {
    const historyContent = document.getElementById('historyContent');
    
    if (!history || history.length === 0) {
        historyContent.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-history text-muted" style="font-size: 2rem;"></i>
                <h6 class="mt-3">No query history</h6>
                <p class="text-muted">Your generated queries will appear here</p>
            </div>
        `;
        return;
    }

    let html = '';
    history.forEach((item, index) => {
        const date = new Date(item.created_at).toLocaleString();
        const isValid = item.is_valid ? 'success' : 'danger';
        const validIcon = item.is_valid ? 'check-circle' : 'exclamation-circle';
        
        html += `
            <div class="history-item" onclick="loadHistoryItem(${index})" data-history='${JSON.stringify(item)}'>
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-1">${window.sqlConverter.escapeHtml(item.natural_language.substring(0, 100))}${item.natural_language.length > 100 ? '...' : ''}</h6>
                    <div class="d-flex align-items-center">
                        <span class="badge bg-${isValid} me-2">
                            <i class="fas fa-${validIcon} me-1"></i>
                            ${item.is_valid ? 'Valid' : 'Invalid'}
                        </span>
                        <small class="text-muted">${date}</small>
                    </div>
                </div>
                <div class="history-query">
                    <code class="language-sql">${window.sqlConverter.escapeHtml(item.optimized_sql || item.generated_sql)}</code>
                </div>
            </div>
        `;
    });

    historyContent.innerHTML = html;
    
    // Re-highlight syntax for history items
    if (typeof Prism !== 'undefined') {
        Prism.highlightAll();
    }
}

function loadHistoryItem(index) {
    const historyItems = document.querySelectorAll('.history-item');
    if (historyItems[index]) {
        const historyData = JSON.parse(historyItems[index].dataset.history);
        
        // Load the query into the main interface
        const textarea = document.getElementById('naturalLanguageInput');
        const sqlCode = document.getElementById('sqlCode');
        
        if (textarea) {
            textarea.value = historyData.natural_language;
        }
        
        if (sqlCode) {
            sqlCode.textContent = historyData.optimized_sql || historyData.generated_sql;
            
            // Show the SQL output section
            const sqlOutput = document.getElementById('sqlOutput');
            const emptyState = document.getElementById('emptyState');
            const outputActions = document.getElementById('outputActions');
            
            if (sqlOutput && emptyState && outputActions) {
                emptyState.classList.add('d-none');
                sqlOutput.classList.remove('d-none');
                outputActions.classList.remove('d-none');
            }
            
            // Re-highlight syntax
            if (typeof Prism !== 'undefined') {
                Prism.highlightElement(sqlCode);
            }
        }
        
        // Close the history modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('historyModal'));
        if (modal) {
            modal.hide();
        }
        
        window.sqlConverter.showSuccess('Query loaded from history');
    }
}

// Add displayFeedbackAnalysis method to SQLConverter class
SQLConverter.prototype.displayFeedbackAnalysis = function(feedback) {
    const feedbackSection = document.getElementById('feedbackSection');
    if (!feedbackSection || !feedback) return;

    // Show feedback section
    feedbackSection.classList.remove('d-none');

    // Update overall score
    const overallScore = document.getElementById('overallScore');
    const score = Math.round(feedback.analysis.overall_score);
    if (overallScore) {
        overallScore.textContent = `${score}/100`;
        overallScore.className = `badge badge-lg ${this.getScoreBadgeClass(score)}`;
    }

    // Update score breakdown
    const scores = feedback.analysis;
    this.updateScoreDisplay('syntaxScore', scores.syntax_score);
    this.updateScoreDisplay('semanticScore', scores.semantic_score);
    this.updateScoreDisplay('performanceScore', scores.performance_score);
    this.updateScoreDisplay('securityScore', scores.security_score);

    // Update recommendations
    const recommendationsList = document.getElementById('recommendationsList');
    if (recommendationsList && feedback.recommendations) {
        recommendationsList.innerHTML = '';
        feedback.recommendations.forEach(rec => {
            const li = document.createElement('li');
            li.textContent = rec;
            recommendationsList.appendChild(li);
        });
    }

    // Store feedback for user rating
    this.currentFeedback = feedback;
};

SQLConverter.prototype.updateScoreDisplay = function(elementId, score) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = Math.round(score);
        element.className = `fw-bold ${this.getScoreColorClass(score)}`;
    }
};

SQLConverter.prototype.getScoreBadgeClass = function(score) {
    if (score >= 90) return 'bg-success';
    if (score >= 70) return 'bg-warning';
    return 'bg-danger';
};

SQLConverter.prototype.getScoreColorClass = function(score) {
    if (score >= 80) return 'text-success';
    if (score >= 60) return 'text-warning';
    return 'text-danger';
};

// Feedback-related functions
let userRating = 0;

function initializeRatingSystem() {
    const stars = document.querySelectorAll('.rating-star');
    stars.forEach(star => {
        star.addEventListener('click', function() {
            userRating = parseInt(this.dataset.rating);
            updateStarDisplay(userRating);
        });
        
        star.addEventListener('mouseover', function() {
            const rating = parseInt(this.dataset.rating);
            updateStarDisplay(rating, true);
        });
    });

    // Reset on mouse leave
    document.querySelector('.rating').addEventListener('mouseleave', function() {
        updateStarDisplay(userRating);
    });
}

function updateStarDisplay(rating, isHover = false) {
    const stars = document.querySelectorAll('.rating-star');
    stars.forEach((star, index) => {
        const starRating = index + 1;
        if (starRating <= rating) {
            star.classList.remove('far');
            star.classList.add('fas');
            star.style.color = isHover ? '#ffc107' : '#f39c12';
        } else {
            star.classList.remove('fas');
            star.classList.add('far');
            star.style.color = '#6c757d';
        }
    });
}

async function submitUserRating() {
    if (!userRating || userRating < 1 || userRating > 5) {
        window.sqlConverter.showError('Please select a rating from 1 to 5 stars');
        return;
    }

    if (!window.sqlConverter.currentQueryId) {
        window.sqlConverter.showError('No query available for rating');
        return;
    }

    try {
        const response = await fetch('/feedback/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query_id: window.sqlConverter.currentQueryId,
                rating: userRating,
                comments: '' // Could add comment input later
            })
        });

        const result = await response.json();

        if (result.success) {
            window.sqlConverter.showSuccess('Thank you for your feedback!');
            // Disable rating after submission
            document.querySelectorAll('.rating-star').forEach(star => {
                star.style.pointerEvents = 'none';
                star.style.opacity = '0.6';
            });
            document.querySelector('button[onclick="submitUserRating()"]').disabled = true;
        } else {
            window.sqlConverter.showError(result.error || 'Failed to submit rating');
        }
    } catch (error) {
        window.sqlConverter.showError('Network error while submitting rating');
    }
}

async function showDetailedFeedback() {
    if (!window.sqlConverter.currentFeedback) {
        window.sqlConverter.showError('No feedback analysis available');
        return;
    }

    const feedback = window.sqlConverter.currentFeedback;
    const modalContent = `
        <div class="modal fade" id="detailedFeedbackModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Detailed Query Analysis</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${generateDetailedFeedbackHTML(feedback)}
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if present
    const existingModal = document.getElementById('detailedFeedbackModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add new modal to DOM
    document.body.insertAdjacentHTML('beforeend', modalContent);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('detailedFeedbackModal'));
    modal.show();
}

function generateDetailedFeedbackHTML(feedback) {
    let html = `
        <div class="row mb-4">
            <div class="col-md-6">
                <h6>Score Breakdown</h6>
                <ul class="list-group">
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Syntax Quality</span>
                        <span class="badge ${window.sqlConverter.getScoreBadgeClass(feedback.analysis.syntax_score)}">${Math.round(feedback.analysis.syntax_score)}/100</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Intent Matching</span>
                        <span class="badge ${window.sqlConverter.getScoreBadgeClass(feedback.analysis.semantic_score)}">${Math.round(feedback.analysis.semantic_score)}/100</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Performance</span>
                        <span class="badge ${window.sqlConverter.getScoreBadgeClass(feedback.analysis.performance_score)}">${Math.round(feedback.analysis.performance_score)}/100</span>
                    </li>
                    <li class="list-group-item d-flex justify-content-between">
                        <span>Security</span>
                        <span class="badge ${window.sqlConverter.getScoreBadgeClass(feedback.analysis.security_score)}">${Math.round(feedback.analysis.security_score)}/100</span>
                    </li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6>Overall Score</h6>
                <div class="text-center">
                    <div class="display-4 ${window.sqlConverter.getScoreColorClass(feedback.analysis.overall_score)}">${Math.round(feedback.analysis.overall_score)}</div>
                    <small class="text-muted">out of 100</small>
                </div>
            </div>
        </div>
    `;

    // Add issues and suggestions sections
    const sections = [
        { title: 'Syntax Issues', items: feedback.feedback.syntax_issues, icon: 'code', type: 'danger' },
        { title: 'Semantic Issues', items: feedback.feedback.semantic_issues, icon: 'brain', type: 'warning' },
        { title: 'Performance Suggestions', items: feedback.feedback.performance_suggestions, icon: 'tachometer-alt', type: 'info' },
        { title: 'Security Warnings', items: feedback.feedback.security_warnings, icon: 'shield-alt', type: 'danger' }
    ];

    sections.forEach(section => {
        if (section.items && section.items.length > 0) {
            html += `
                <div class="mb-3">
                    <h6><i class="fas fa-${section.icon} me-2"></i>${section.title}</h6>
                    <div class="alert alert-${section.type}">
                        <ul class="mb-0">
                            ${section.items.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `;
        }
    });

    // Add execution results if available
    if (feedback.execution_results && feedback.execution_results.success) {
        html += `
            <div class="mb-3">
                <h6><i class="fas fa-play-circle me-2"></i>Execution Results</h6>
                <div class="alert alert-success">
                    <div class="row">
                        <div class="col-md-4">
                            <strong>Execution Time:</strong> ${feedback.execution_results.execution_time}s
                        </div>
                        <div class="col-md-4">
                            <strong>Rows Returned:</strong> ${feedback.execution_results.row_count}
                        </div>
                        <div class="col-md-4">
                            <strong>Columns:</strong> ${feedback.execution_results.columns ? feedback.execution_results.columns.length : 0}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    return html;
}

// Initialize rating system when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeRatingSystem();
});





function getSQLServerConnectionParams() {
    const authMethod = document.getElementById('sqlServerAuth').value;
    
    const params = {
        server: document.getElementById('sqlServerHost').value.trim(),
        port: document.getElementById('sqlServerPort').value.trim() || '1433',
        database: document.getElementById('sqlServerDatabase').value.trim() || 'master',
        auth_method: authMethod,
        timeout: document.getElementById('sqlServerTimeout').value.trim() || '30',
        encrypt: document.getElementById('sqlServerEncrypt').checked ? 'yes' : 'no',
        trust_server_certificate: document.getElementById('sqlServerTrustCert').checked ? 'yes' : 'no'
    };
    
    if (authMethod === 'sql') {
        params.username = document.getElementById('sqlServerUsername').value.trim();
        params.password = document.getElementById('sqlServerPassword').value.trim();
    }
    
    return params;
}

// Theme Management
function toggleTheme() {
    const body = document.body;
    const themeToggle = document.getElementById('themeToggle');
    const icon = themeToggle.querySelector('i');
    const text = themeToggle.querySelector('span') || themeToggle.childNodes[themeToggle.childNodes.length - 1];
    
    if (body.classList.contains('light-theme')) {
        // Switch to dark theme
        body.classList.remove('light-theme');
        icon.className = 'fas fa-sun me-1';
        themeToggle.innerHTML = '<i class="fas fa-sun me-1"></i>Light';
        localStorage.setItem('theme', 'dark');
    } else {
        // Switch to light theme
        body.classList.add('light-theme');
        icon.className = 'fas fa-moon me-1';
        themeToggle.innerHTML = '<i class="fas fa-moon me-1"></i>Dark';
        localStorage.setItem('theme', 'light');
    }
}

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const themeToggle = document.getElementById('themeToggle');
    
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        if (themeToggle) {
            themeToggle.innerHTML = '<i class="fas fa-moon me-1"></i>Dark';
        }
    } else {
        if (themeToggle) {
            themeToggle.innerHTML = '<i class="fas fa-sun me-1"></i>Light';
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.sqlConverter = new SQLConverter();
    initializeTheme();
});
