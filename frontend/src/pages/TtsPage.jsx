// src/pages/TTSPage.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './css/TtsPage.css';

const TTSPage = () => {
    const token = localStorage.getItem('auth-token');
    if (!token) {
        const navigate = useNavigate();
        navigate('/');
        return;
    }

    // State for the text input and the generated audio file URL.
    const [text, setText] = useState('');
    const [audioUrl, setAudioUrl] = useState(null);

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

    // Play the audio file when the button is clicked.
    const handlePlayAudio = () => {
        if (audioUrl) {
        const audio = new Audio(audioUrl);
        audio.play();
        }
    };

    return (
        <div className="tts-container">
        {/* The semi-transparent overlay */}
        <div className="overlay"></div>
        <div className="tts-content">
            <div className="left-side">
            <form onSubmit={handleGenerateAudio}>
                <textarea
                placeholder="Enter text to convert to speech..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                ></textarea>
                <button type="submit">Generate Audio</button>
            </form>
            </div>
            <div className="right-side">
            <h2>Previous Audio</h2>
            {audioUrl ? (
                <div className="audio-container">
                {/* You can use the <audio> element with controls */}
                <audio controls src={audioUrl}>
                    Your browser does not support the audio element.
                </audio>
                {/*<button onClick={handlePlayAudio}>Play Audio</button>*/}
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
