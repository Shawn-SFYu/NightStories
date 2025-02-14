import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './css/DocumentsPage.css';

const DocumentsPage = () => {
    const navigate = useNavigate();
    const token = localStorage.getItem('auth-token');
    const [documents, setDocuments] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [processingDocs, setProcessingDocs] = useState(new Set());

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
                // Update processing docs set
                const stillProcessing = new Set(
                    data.documents
                        .filter(doc => doc.status === 'processing')
                        .map(doc => doc._id)
                );
                setProcessingDocs(stillProcessing);
            }
        } catch (error) {
            console.error('Error fetching documents:', error);
        }
    };

    // Poll for updates while documents are processing
    useEffect(() => {
        fetchDocuments();
        
        if (processingDocs.size > 0) {
            const interval = setInterval(fetchDocuments, 3000); // Poll every 3 seconds
            return () => clearInterval(interval);
        }
    }, [processingDocs.size]);

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
                // Add new document to processing set
                setProcessingDocs(prev => new Set(prev).add(data.document_id));
                // Fetch updated document list
                fetchDocuments();
            }
        } catch (error) {
            console.error('Error uploading document:', error);
        }
    };

    return (
        <div className="documents-container">
            <div className="documents-layout">
                <div className="documents-section">
                    <h2>Your Documents</h2>
                    <div className="documents-list">
                        {documents.map((doc) => (
                            <div key={doc._id} className="document-card">
                                <div className="document-header">
                                    <h3>{doc.filename}</h3>
                                    <span className={`status-badge ${doc.status}`}>
                                        {doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
                                    </span>
                                </div>
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
            </div>
        </div>
    );
};

export default DocumentsPage; 