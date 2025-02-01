import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import TtsPage from './pages/TtsPage';


function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/tts" element={<TtsPage />} /> 
      </Routes>
    </Router>
  );
}

export default App;