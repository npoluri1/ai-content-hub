import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline, Box, Toolbar } from '@mui/material';
import theme from './theme';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Search from './pages/Search';
import Sources from './pages/Sources';
import Topics from './pages/Topics';
import Digest from './pages/Digest';
import Schedule from './pages/Schedule';
import Settings from './pages/Settings';

const DRAWER_WIDTH = 240;

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex' }}>
        <Navbar />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            minHeight: '100vh',
            maxWidth: `calc(100% - ${DRAWER_WIDTH}px)`,
          }}
        >
          <Toolbar />
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/search" element={<Search />} />
            <Route path="/sources" element={<Sources />} />
            <Route path="/topics" element={<Topics />} />
            <Route path="/digest" element={<Digest />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
