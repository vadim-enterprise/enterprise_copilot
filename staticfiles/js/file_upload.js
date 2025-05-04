class FileUpload {
    constructor() {
        this.uploadButton = document.getElementById('uploadCsvButton');
        this.fileInput = document.getElementById('csvFileInput');
        this.notificationContainer = document.getElementById('notification-container');
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.uploadButton.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
    }

    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.name.endsWith('.csv')) {
            this.showNotification('Please select a CSV file', 'error');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('http://127.0.0.1:8001/api/files/upload-csv', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.showNotification('File uploaded successfully!', 'success');
            console.log('Upload result:', result);
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Error uploading file: ' + error.message, 'error');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        this.notificationContainer.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize file upload functionality when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new FileUpload();
}); 