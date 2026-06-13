import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import SessionPage from './pages/SessionPage';
import ReportPage from './pages/ReportPage';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/session/:sessionId" element={<SessionPage />} />
        <Route path="/report/:sessionId" element={<ReportPage />} />
      </Routes>
    </BrowserRouter>
  );
}
