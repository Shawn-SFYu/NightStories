import React, { useState } from 'react';
import './css/LoginPage.css';
import { useNavigate } from 'react-router-dom';

const LoginPage = () => {
  const [accountName, setAccountName] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:5000/login', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email:accountName, password }),
      });

      const data = await response.json();
      console.log(data);
      if (data.success) {
        localStorage.setItem('auth-token', data.token);
        navigate('/tts');
      } else {
        alert(data.errors);
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed. Please try again.');
    }
  };

  return (
    <div className="login-container">
      <div className="login-content">
        <div className="left-side">
          <h1>{`Welcome to 'Stories Now' 
                    -- AI Storytelling`}</h1>
        <p>{`An AI-powered storytelling application 
        that is designed to serve my family initially. `}</p>
        <p>{`From text-to-speech, summarization, 
        to text-to-image ... `}</p>
        <p>{`It's fun to expand the capacity and share! `}</p>
        </div>
        <div className="right-side">
          <form onSubmit={handleLogin} className="login-form">
            <div className="form-group">
              <label htmlFor="accountName">Account Name</label>
              <input
                type="text"
                id="accountName"
                value={accountName}
                onChange={(e) => setAccountName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <button type="submit">Login</button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
