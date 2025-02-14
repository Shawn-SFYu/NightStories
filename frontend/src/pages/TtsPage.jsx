// src/pages/TTSPage.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './css/TtsPage.css';

const TTSPage = () => {
    const navigate = useNavigate();
    const token = localStorage.getItem('auth-token');
    const [activeTab, setActiveTab] = useState('text'); // 'text' or 'documents'
    const [text, setText] = useState('');
    const [audioUrl, setAudioUrl] = useState(null);
    const [documents, setDocuments] = useState([]);

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
                setDocuments(data.documents.filter(doc => doc.status === 'completed'));
            }
        } catch (error) {
            console.error('Error fetching documents:', error);
        }
    };

    // Simulate generating audio when the form is submitted.
    const handleGenerateAudio = async (e) => {
        e.preventDefault();
        
        try {
            // Submit text for conversion
            const response = await fetch('http://localhost:5000/tts/submit', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });

            const data = await response.json();
            if (data.success) {
                // Poll for audio completion
                const checkAudioStatus = setInterval(async () => {
                    const statusResponse = await fetch(`http://localhost:5000/tts/status/${data.task_id}`, {
                        headers: {
                            'Authorization': `Bearer ${token}`,
                        },
                    });
                    const statusData = await statusResponse.json();
                    
                    if (statusData.status === 'completed') {
                        clearInterval(checkAudioStatus);
                        setAudioUrl(`http://localhost:5000/tts/audio/${statusData.file_id}`);
                    } else if (statusData.status === 'failed') {
                        clearInterval(checkAudioStatus);
                        alert('Audio generation failed');
                    }
                }, 2000); // Check every 2 seconds
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error('Audio generation error:', error);
            alert('Failed to submit text for conversion');
        }
    };

    const handleTTSConvert = async (docId, chapterIndex) => {
        try {
            // Submit chapter for conversion
            const response = await fetch('http://localhost:5000/tts/convert-chapter', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    doc_id: docId,
                    chapter_index: chapterIndex 
                }),
            });

            const data = await response.json();
            if (data.success) {
                // Poll for audio completion
                const checkAudioStatus = setInterval(async () => {
                    const statusResponse = await fetch(`http://localhost:5000/tts/status/${data.task_id}`, {
                        headers: {
                            'Authorization': `Bearer ${token}`,
                        },
                    });
                    const statusData = await statusResponse.json();
                    
                    if (statusData.status === 'completed') {
                        clearInterval(checkAudioStatus);
                        setAudioUrl(`http://localhost:5000/tts/audio/${statusData.file_id}`);
                    } else if (statusData.status === 'failed') {
                        clearInterval(checkAudioStatus);
                        alert('Audio generation failed');
                    }
                }, 2000); // Check every 2 seconds
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error('Chapter conversion error:', error);
            alert('Failed to convert chapter to speech');
        }
    };

    // Play the audio file when the button is clicked.
    const handlePlayAudio = () => {
        if (audioUrl) {
        const audio = new Audio(audioUrl);
        audio.play();
        }
    };

    return (
        <div className="tts-container">
            <div className="overlay"></div>
            <div className="tts-content">
                <div className="tts-form-container">
                    <div className="tabs-container">
                        <button 
                            className={`tab-button ${activeTab === 'text' ? 'active' : ''}`}
                            onClick={() => setActiveTab('text')}
                        >
                            Direct Text
                        </button>
                        <button 
                            className={`tab-button ${activeTab === 'documents' ? 'active' : ''}`}
                            onClick={() => setActiveTab('documents')}
                        >
                            From Documents
                        </button>
                    </div>

                    {activeTab === 'text' ? (
                        <form onSubmit={handleGenerateAudio} className="tts-form">
                            <textarea
                                placeholder="Enter text to convert to speech..."
                                value={text}
                                onChange={(e) => setText(e.target.value)}
                            ></textarea>
                            <button type="submit" className="generate-button">Generate Audio</button>
                        </form>
                    ) : (
                        <div className="documents-list">
                            {documents.map((doc) => (
                                <div key={doc._id} className="document-item">
                                    <h3>{doc.filename}</h3>
                                    {doc.status === 'processing' ? (
                                        <p>Document is still being processed...</p>
                                    ) : doc.chapters && doc.chapters.length > 0 ? (
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
                                    ) : (
                                        <p>No chapters found in this document</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="right-side">
                    <h2>Previous Audio</h2>
                    {audioUrl ? (
                        <div className="audio-container">
                            <audio controls src={audioUrl}>
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                    ) : (
                        <p>No audio generated yet.</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TTSPage;
