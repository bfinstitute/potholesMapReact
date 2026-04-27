const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // Health check
  async healthCheck() {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }

  // Upload CSV file
  async uploadCSV(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${this.baseURL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Upload failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  }

  // Analyze CSV data
  async analyzeCSV(csvData) {
    try {
      const response = await fetch(`${this.baseURL}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ csvData }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Analysis failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Analysis failed:', error);
      throw error;
    }
  }

  // Download CSV file
  async downloadCSV(csvData, filename = 'processed_data.csv') {
    try {
      const response = await fetch(`${this.baseURL}/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ csvData, filename }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Download failed');
      }

      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      return { success: true };
    } catch (error) {
      console.error('Download failed:', error);
      throw error;
    }
  }

  // Submit feedback
  async submitFeedback(feedbackData) {
    try {
      const response = await fetch(`${this.baseURL}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedbackData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Feedback submission failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Feedback submission failed:', error);
      throw error;
    }
  }

  // Validate CSV data
  async validateCSV(csvData) {
    try {
      const response = await fetch(`${this.baseURL}/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ csvData }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Validation failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Validation failed:', error);
      throw error;
    }
  }

  // Login user
  async login(email, password) {
    try {
      const response = await fetch(`${this.baseURL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Login failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }

  // Verify token
  async verifyToken(token) {
    try {
      const response = await fetch(`${this.baseURL}/verify-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Token verification failed');
      }

      return await response.json();
    } catch (error) {
      console.error('Token verification failed:', error);
      throw error;
    }
  }

  // List uploaded files
  async listFiles() {
    try {
      const response = await fetch(`${this.baseURL}/files`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to list files');
      }
      return await response.json();
    } catch (error) {
      console.error('Failed to list files:', error);
      throw error;
    }
  }

  // Get file information
  async getFileInfo(filename) {
    try {
      const response = await fetch(`${this.baseURL}/files/${encodeURIComponent(filename)}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get file info');
      }
      return await response.json();
    } catch (error) {
      console.error('Failed to get file info:', error);
      throw error;
    }
  }
}

export default new ApiService(); 