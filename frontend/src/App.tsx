import { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline, Box, Toolbar } from '@mui/material';
import { ThemeProvider as CustomThemeProvider, useThemePreset } from './context/ThemeContext';
import Navbar from './components/Navbar';
import ItemDetail from './components/ItemDetail';
import Dashboard from './pages/Dashboard';
import Search from './pages/Search';
import Sources from './pages/Sources';
import Topics from './pages/Topics';
import Digest from './pages/Digest';
import Schedule from './pages/Schedule';
import Settings from './pages/Settings';
import Analytics from './pages/Analytics';
import AiLab from './pages/AiLab';
import RagChat from './pages/RagChat';
import EnterpriseSearch from './pages/EnterpriseSearch';
import MlopsLab from './pages/MlopsLab';
import Integrations from './pages/Integrations';
import Compliance from './pages/Compliance';
import Collaboration from './pages/Collaboration';
import Monitoring from './pages/Monitoring';
import Workflows from './pages/Workflows';
import Notifications from './pages/Notifications';
import Processing from './pages/Processing';
import Trends from './pages/Trends';
import Forum from './pages/Forum';
import type { ContentItem } from './api/client';

const DRAWER = 260;

function AppContent() {
  const { theme } = useThemePreset();
  const [detailItem, setDetailItem] = useState<ContentItem | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const openDetail = (item: ContentItem) => {
    setDetailItem(item);
    setDetailOpen(true);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex' }}>
        <Navbar />
        <Box component="main" sx={{ flexGrow: 1, p: 3, minHeight: '100vh', maxWidth: `calc(100% - ${DRAWER}px)`, bgcolor: 'background.default' }}>
          <Toolbar />
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard onItemClick={openDetail} />} />
            <Route path="/search" element={<Search onItemClick={openDetail} />} />
            <Route path="/sources" element={<Sources onItemClick={openDetail} />} />
            <Route path="/topics" element={<Topics onItemClick={openDetail} />} />
            <Route path="/digest" element={<Digest />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="/rag-chat" element={<RagChat />} />
            <Route path="/ai-lab" element={<AiLab />} />
            <Route path="/enterprise-search" element={<EnterpriseSearch />} />
            <Route path="/mlops-lab" element={<MlopsLab />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/compliance" element={<Compliance />} />
            <Route path="/collaboration" element={<Collaboration />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/workflows" element={<Workflows />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/processing" element={<Processing />} />
            <Route path="/forum" element={<Forum />} />
          </Routes>
        </Box>
      </Box>
      <ItemDetail item={detailItem} open={detailOpen} onClose={() => setDetailOpen(false)} />
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <CustomThemeProvider>
      <AppContent />
    </CustomThemeProvider>
  );
}
