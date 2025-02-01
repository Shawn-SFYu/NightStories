import React, { useState } from 'react';
import './css/LoginPage.css';

const LoginPage = () => {
  const [accountName, setAccountName] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = (e) => {
    e.preventDefault();
    // TODO: Add your login API call or authentication logic here.
    console.log('Logging in with:', { accountName, password });
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
