import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import TtsPage from './pages/TtsPage';
import DocumentsPage from './pages/DocumentsPage';
import Navbar from './components/navbar/Navbar';

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar />
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/tts" element={<TtsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;