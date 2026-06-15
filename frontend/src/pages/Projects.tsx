import { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Chip, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Select, MenuItem, FormControl, InputLabel, IconButton, Tabs, Tab, CircularProgress, Alert, List, ListItem, ListItemText, Divider,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import GroupIcon from '@mui/icons-material/Group';
import DescriptionIcon from '@mui/icons-material/Description';
import ChatIcon from '@mui/icons-material/Chat';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import axios from 'axios';

const API = 'http://localhost:8000';

interface Project { id: string; name: string; description: string; status: string; owner: string; created_at: string; updated_at: string; }
interface ProjectStats { members: number; reports: number; chats: number; context_items: number; content_items: number; }
interface Report { id: string; title: string; report_type: string; content: string; created_by: string; created_at: string; }
interface Chat { id: string; title: string; messages: any[]; model_id: string; created_by: string; created_at: string; updated_at: string; }
interface ContextItem { id: string; title: string; context_type: string; content: string; url: string; tags: string[]; created_by: string; created_at: string; }

const STATUS_COLORS: Record<string, string> = { active: '#34D399', archived: '#6B7280', completed: '#60A5FA' };

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [projectStats, setProjectStats] = useState<ProjectStats | null>(null);
  const [tab, setTab] = useState(0);
  const [reports, setReports] = useState<Report[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [contextItems, setContextItems] = useState<ContextItem[]>([]);
  const [error, setError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');

  useEffect(() => { fetchProjects(); }, []);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/projects`);
      setProjects(data.projects || []);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const selectProject = async (pid: string) => {
    setSelected(pid);
    try {
      const [s, r, c, ctx] = await Promise.all([
        axios.get(`${API}/projects/${pid}/stats`),
        axios.get(`${API}/projects/${pid}/reports`),
        axios.get(`${API}/projects/${pid}/chats`),
        axios.get(`${API}/projects/${pid}/context`),
      ]);
      setProjectStats(s.data.stats);
      setReports(r.data.reports || []);
      setChats(c.data.chats || []);
      setContextItems(ctx.data.context || []);
    } catch (e: any) { setError(e.message); }
  };

  const createProject = async () => {
    if (!createName.trim()) return;
    try {
      await axios.post(`${API}/projects`, { name: createName, description: createDesc });
      setCreateOpen(false); setCreateName(''); setCreateDesc('');
      await fetchProjects();
    } catch (e: any) { setError(e.message); }
  };

  const deleteProject = async (pid: string) => {
    try {
      await axios.delete(`${API}/projects/${pid}`);
      if (selected === pid) { setSelected(null); setProjectStats(null); setReports([]); setChats([]); setContextItems([]); }
      await fetchProjects();
    } catch (e: any) { setError(e.message); }
  };

  if (loading) return <Box sx={{ display:'flex', justifyContent:'center', mt:8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb:3 }}>
        <Box>
          <Typography variant="h4">Projects</Typography>
          <Typography variant="body2" color="text.secondary">Shared project context, reports, and AI chat sessions</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>New Project</Button>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={2}>
        <Grid item xs={12} md={selected ? 4 : 12}>
          <Grid container spacing={2}>
            {projects.map(p => (
              <Grid item xs={12} sm={selected ? 12 : 6} md={selected ? 12 : 3} key={p.id}>
                <Card sx={{ cursor:'pointer', border: selected === p.id ? 2 : 0, borderColor: 'primary.main', '&:hover': { transform:'translateY(-2px)' }, transition:'transform 0.15s' }}
                  onClick={() => selectProject(p.id)}>
                  <CardContent>
                    <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                      <Box>
                        <Typography variant="h6">{p.name}</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt:0.5, display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden' }}>
                          {p.description || 'No description'}
                        </Typography>
                      </Box>
                      <IconButton size="small" onClick={(e) => { e.stopPropagation(); deleteProject(p.id); }}><DeleteIcon fontSize="small" /></IconButton>
                    </Box>
                    <Box sx={{ display:'flex', gap:0.5, mt:1.5, flexWrap:'wrap' }}>
                      <Chip label={p.status} size="small" sx={{ bgcolor: STATUS_COLORS[p.status] || '#6B7280', color:'#fff' }} />
                      <Chip label={p.owner} size="small" variant="outlined" />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            {projects.length === 0 && !loading && (
              <Grid item xs={12}><Typography color="text.secondary" textAlign="center" py={4}>No projects yet. Create your first project.</Typography></Grid>
            )}
          </Grid>
        </Grid>

        {selected && (
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb:1 }}>
                  <Typography variant="h6">{projects.find(p => p.id === selected)?.name || 'Project'}</Typography>
                  <Box sx={{ display:'flex', gap:0.5 }}>
                    <Chip label={`${projectStats?.members || 0} members`} size="small" icon={<GroupIcon />} />
                    <Chip label={`${projectStats?.reports || 0} reports`} size="small" icon={<DescriptionIcon />} />
                    <Chip label={`${projectStats?.chats || 0} chats`} size="small" icon={<ChatIcon />} />
                    <Chip label={`${projectStats?.context_items || 0} context`} size="small" icon={<BookmarkIcon />} />
                  </Box>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {projects.find(p => p.id === selected)?.description || 'No description'}
                </Typography>

                <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
                  <Tab label="Reports" />
                  <Tab label="AI Chats" />
                  <Tab label="Context" />
                </Tabs>

                {tab === 0 && (
                  <Box>
                    {reports.length === 0 ? <Typography color="text.secondary">No reports</Typography> : (
                      <List dense>
                        {reports.map(r => (
                          <ListItem key={r.id} divider>
                            <ListItemText primary={r.title} secondary={`${r.report_type} · ${r.created_by} · ${new Date(r.created_at).toLocaleDateString()}`} />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Box>
                )}

                {tab === 1 && (
                  <Box>
                    {chats.length === 0 ? <Typography color="text.secondary">No AI chats</Typography> : (
                      <List dense>
                        {chats.map(c => (
                          <ListItem key={c.id} divider>
                            <ListItemText primary={c.title} secondary={`${c.messages?.length || 0} messages · ${c.model_id || 'default model'} · ${new Date(c.updated_at).toLocaleDateString()}`} />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Box>
                )}

                {tab === 2 && (
                  <Box>
                    {contextItems.length === 0 ? <Typography color="text.secondary">No context documents</Typography> : (
                      <List dense>
                        {contextItems.map(ctx => (
                          <ListItem key={ctx.id} divider>
                            <ListItemText primary={ctx.title} secondary={`${ctx.context_type} · ${ctx.tags?.join(', ') || ''}${ctx.url ? ` · ${ctx.url}` : ''}`} />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Project</DialogTitle>
        <DialogContent>
          <TextField autoFocus fullWidth label="Project Name" value={createName} onChange={e => setCreateName(e.target.value)} sx={{ mt: 1 }} />
          <TextField fullWidth label="Description" multiline rows={3} value={createDesc} onChange={e => setCreateDesc(e.target.value)} sx={{ mt: 2 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={createProject}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
