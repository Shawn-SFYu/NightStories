import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import '../css/Navbar.css';

const Navbar = () => {
    const navigate = useNavigate();
    const token = localStorage.getItem('auth-token');

    const handleLogout = () => {
        localStorage.removeItem('auth-token');
        navigate('/');
    };

    return (
        <nav className="navbar">
            <div className="nav-brand">Stories Now</div>
            {token && (
                <div className="nav-links">
                    <Link to="/tts">Text to Speech</Link>
                    <Link to="/documents">Documents</Link>
                    <button onClick={handleLogout}>Logout</button>
                </div>
            )}
        </nav>
    );
};

export default Navbar; 