import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './css/ChatPage.css';

const ChatPage = () => {
    const navigate = useNavigate();
    const token = localStorage.getItem('auth-token');
    const [documents, setDocuments] = useState([]);
    const [selectedDocs, setSelectedDocs] = useState([]);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        if (!token) {
            navigate('/');
            return;
        }
        fetchDocuments();
    }, [token, navigate]);

    // Fetch user's documents
    const fetchDocuments = async () => {
        try {
            const response = await fetch('http://localhost:5000/documents', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            const data = await response.json();
            if (data.success) {
                setDocuments(data.documents);
            }
        } catch (error) {
            console.error('Error fetching documents:', error);
        }
    };

    // Handle document selection
    const handleDocSelect = (docId) => {
        setSelectedDocs(prev => {
            if (prev.includes(docId)) {
                return prev.filter(id => id !== docId);
            }
            return [...prev, docId];
        });
    };

    // Handle message send
    const handleSendMessage = async () => {
        if (!inputMessage.trim() || selectedDocs.length === 0) return;

        const newMessage = {
            content: inputMessage,
            sender: 'user',
            timestamp: new Date().toISOString()
        };

        setMessages(prev => [...prev, newMessage]);
        setInputMessage('');
        setIsLoading(true);

        try {
            const response = await fetch('http://localhost:5000/chat', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: inputMessage,
                    doc_ids: selectedDocs
                })
            });

            const data = await response.json();
            if (data.success) {
                setMessages(prev => [...prev, {
                    content: data.response,
                    sender: 'bot',
                    timestamp: new Date().toISOString()
                }]);
            }
        } catch (error) {
            console.error('Error sending message:', error);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-page">
            <div className="chat-content">
                <div className="document-panel">
                    <h2>Your Documents</h2>
                    <div className="document-list">
                        {documents.map(doc => (
                            <div key={doc._id} className="document-item">
                                <input
                                    type="checkbox"
                                    checked={selectedDocs.includes(doc._id)}
                                    onChange={() => handleDocSelect(doc._id)}
                                />
                                <span>{doc.filename}</span>
                            </div>
                        ))}
                    </div>
                </div>
                
                <div className="chat-panel">
                    <div className="message-history">
                        {messages.map((msg, index) => (
                            <div key={index} className={`message ${msg.sender}`}>
                                <div className="message-content">{msg.content}</div>
                                <div className="message-timestamp">
                                    {new Date(msg.timestamp).toLocaleTimeString()}
                                </div>
                            </div>
                        ))}
                        {isLoading && <div className="loading-indicator">Bot is typing...</div>}
                    </div>
                    
                    <div className="message-input">
                        <input
                            type="text"
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                            placeholder="Type your message..."
                            disabled={selectedDocs.length === 0}
                        />
                        <button 
                            onClick={handleSendMessage}
                            disabled={!inputMessage.trim() || selectedDocs.length === 0}
                        >
                            Send
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatPage; 