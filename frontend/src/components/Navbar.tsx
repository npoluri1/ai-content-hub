import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Drawer, List, ListItemButton, ListItemIcon, ListItemText, Toolbar,
  Typography, Box, Collapse, Select, MenuItem, FormControl, Divider,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SearchIcon from '@mui/icons-material/Search';
import RssFeedIcon from '@mui/icons-material/RssFeed';
import TopicIcon from '@mui/icons-material/Topic';
import ArticleIcon from '@mui/icons-material/Article';
import ScheduleIcon from '@mui/icons-material/Schedule';
import SettingsIcon from '@mui/icons-material/Settings';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import HubIcon from '@mui/icons-material/Hub';
import AppsIcon from '@mui/icons-material/Apps';
import GavelIcon from '@mui/icons-material/Gavel';
import GroupIcon from '@mui/icons-material/Group';
import NotificationsIcon from '@mui/icons-material/Notifications';
import CachedIcon from '@mui/icons-material/Cached';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import PaletteIcon from '@mui/icons-material/Palette';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import ChatIcon from '@mui/icons-material/Chat';
import ScienceIcon from '@mui/icons-material/Science';
import ForumIcon from '@mui/icons-material/Forum';
import FolderIcon from '@mui/icons-material/Folder';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import { useThemePreset } from '../context/ThemeContext';

const DRAWER = 260;

const NAV = [
  { category: 'Core', items: [
    { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
    { label: 'Search', path: '/search', icon: <SearchIcon /> },
    { label: 'Sources', path: '/sources', icon: <RssFeedIcon /> },
    { label: 'Topics', path: '/topics', icon: <TopicIcon /> },
    { label: 'Digest', path: '/digest', icon: <ArticleIcon /> },
    { label: 'Schedule', path: '/schedule', icon: <ScheduleIcon /> },
  ]},
  { category: 'Analytics', items: [
    { label: 'Analytics', path: '/analytics', icon: <AnalyticsIcon /> },
    { label: 'Trends', path: '/trends', icon: <AutoAwesomeIcon /> },
  ]},
  { category: 'AI Lab', items: [
    { label: 'RAG Chat', path: '/rag-chat', icon: <ChatIcon /> },
    { label: 'AI Lab', path: '/ai-lab', icon: <SmartToyIcon /> },
    { label: 'Enterprise Search', path: '/enterprise-search', icon: <HubIcon /> },
    { label: 'MLOps Lab', path: '/mlops-lab', icon: <ScienceIcon /> },
  ]},
  { category: 'Enterprise', items: [
    { label: 'Projects', path: '/projects', icon: <FolderIcon /> },
    { label: 'Campaigns', path: '/campaigns', icon: <RocketLaunchIcon /> },
    { label: 'Integrations', path: '/integrations', icon: <AppsIcon /> },
    { label: 'Compliance', path: '/compliance', icon: <GavelIcon /> },
    { label: 'Collaboration', path: '/collaboration', icon: <GroupIcon /> },
    { label: 'Monitoring', path: '/monitoring', icon: <MonitorHeartIcon /> },
    { label: 'Workflows', path: '/workflows', icon: <AccountTreeIcon /> },
  ]},
  { category: 'System', items: [
    { label: 'Notifications', path: '/notifications', icon: <NotificationsIcon /> },
    { label: 'Processing', path: '/processing', icon: <CachedIcon /> },
    { label: 'Forum', path: '/forum', icon: <ForumIcon /> },
    { label: 'Settings', path: '/settings', icon: <SettingsIcon /> },
  ]},
];

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { preset, presets, setPreset } = useThemePreset();
  const [openCats, setOpenCats] = useState<Record<string,boolean>>(() => {
    const cats: Record<string,boolean> = {};
    NAV.forEach(g => { cats[g.category] = g.items.some(i => location.pathname === i.path); });
    return cats;
  });

  const toggleCat = (cat: string) => setOpenCats(p => ({ ...p, [cat]: !p[cat] }));

  return (
    <Drawer variant="permanent" sx={{
      width: DRAWER, flexShrink: 0,
      '& .MuiDrawer-paper': { width: DRAWER, boxSizing: 'border-box', backgroundColor: 'background.paper' },
    }}>
      <Toolbar sx={{ px: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{
            width: 36, height: 36, borderRadius: 2,
            background: preset.gradient,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#000', fontWeight: 800, fontSize: 18,
          }}>AI</Box>
          <Box>
            <Typography variant="subtitle1" fontWeight={800} lineHeight={1.1}>Content Hub</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ opacity: 0.7 }}>Enterprise</Typography>
          </Box>
        </Box>
      </Toolbar>

      <Box sx={{ px: 2, mb: 1 }}>
        <FormControl fullWidth size="small">
          <Select
            value={preset.name}
            onChange={e => setPreset(e.target.value)}
            variant="outlined"
            sx={{
              fontSize: 12, borderRadius: 2,
              '& .MuiSelect-select': { py: 0.8 },
            }}
            startAdornment={<PaletteIcon sx={{ mr: 0.5, fontSize: 16, color: preset.primary }} />}
          >
            {presets.map(p => (
              <MenuItem key={p.name} value={p.name}>
                <Box sx={{ display:'flex', alignItems:'center', gap:1 }}>
                  <Box sx={{ width:14, height:14, borderRadius:'50%', background:p.gradient }} />
                  {p.label}
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Divider sx={{ mx: 2, mb: 1 }} />

      <Box sx={{ flex:1, overflow:'auto', px: 1 }}>
        {NAV.map(group => (
          <Box key={group.category} sx={{ mb: 0.5 }}>
            <ListItemButton onClick={() => toggleCat(group.category)} sx={{ borderRadius: 2, py: 0.6 }}>
              <ListItemText primary={group.category} primaryTypographyProps={{ variant:'caption', fontWeight:700, color:'text.secondary', sx:{ letterSpacing:1 } }} />
              {openCats[group.category] ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
            </ListItemButton>
            <Collapse in={openCats[group.category]}>
              {group.items.map(item => {
                const sel = location.pathname === item.path;
                return (
                  <ListItemButton
                    key={item.path}
                    selected={sel}
                    onClick={() => navigate(item.path)}
                    sx={{
                      borderRadius: 2, py: 0.6, pl: 2, mb: 0.3,
                      '&.Mui-selected': {
                        backgroundColor: 'primary.main', color: '#000',
                        '&:hover': { backgroundColor: 'primary.light' },
                        '& .MuiListItemIcon-root': { color: '#000' },
                        '& .MuiListItemText-primary': { color: '#000', fontWeight: 700 },
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36, fontSize: 20 }}>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.label} primaryTypographyProps={{ variant: 'body2', fontWeight: sel ? 700 : 500 }} />
                  </ListItemButton>
                );
              })}
            </Collapse>
          </Box>
        ))}
      </Box>

      <Box sx={{ px: 2, py: 1.5, borderTop: 1, borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary" sx={{ opacity: 0.5 }}>
          AI Content Hub v1.0
        </Typography>
      </Box>
    </Drawer>
  );
}
