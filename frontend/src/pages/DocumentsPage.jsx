import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './css/DocumentsPage.css';

const DocumentsPage = () => {
    const navigate = useNavigate();
    const token = localStorage.getItem('auth-token');
    const [documents, setDocuments] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploadProgress, setUploadProgress] = useState(0);

    useEffect(() => {
        if (!token) {
            navigate('/');
            return;
        }
        fetchDocuments();
    }, [token, navigate]);

    const fetchDocuments = async () => {
        try {
            const response = await fetch('http://localhost:5000/documents', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });
            const data = await response.json();
            if (data.success) {
                setDocuments(data.documents);
            }
        } catch (error) {
            console.error('Error fetching documents:', error);
        }
    };

    const handleFileChange = (event) => {
        setSelectedFile(event.target.files[0]);
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const response = await fetch('http://localhost:5000/documents/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData
            });

            const data = await response.json();
            if (data.success) {
                setSelectedFile(null);
                fetchDocuments();
            }
        } catch (error) {
            console.error('Upload error:', error);
        }
    };

    return (
        <div className="documents-container">
            <div className="upload-section">
                <h2>Upload Document</h2>
                <form onSubmit={handleUpload}>
                    <input 
                        type="file" 
                        accept=".pdf"
                        onChange={handleFileChange}
                    />
                    <button type="submit" disabled={!selectedFile}>
                        Upload PDF
                    </button>
                </form>
            </div>

            <div className="documents-list">
                <h2>Your Documents</h2>
                {documents.map((doc) => (
                    <div key={doc._id} className="document-card">
                        <h3>{doc.filename}</h3>
                        <p>Status: {doc.status}</p>
                        {doc.status === 'completed' && (
                            <div className="chapters-list">
                                {doc.chapters.map((chapter, index) => (
                                    <div key={index} className="chapter-item">
                                        <span>{chapter.title}</span>
                                        <button onClick={() => handleTTSConvert(doc._id, index)}>
                                            Convert to Speech
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default DocumentsPage; 