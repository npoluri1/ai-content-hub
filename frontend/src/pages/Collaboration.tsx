import { useEffect, useState } from 'react';
import { Box, Typography, Grid, Card, CardContent, Chip, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, IconButton, CircularProgress, Alert } from '@mui/material';
import GroupIcon from '@mui/icons-material/Group';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import axios from 'axios';

const API = 'http://localhost:8000';

interface Workspace { id: string; name: string; description: string; owner: string; created_at: string; members?: number; items?: number; }

export default function Collaboration() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');

  useEffect(() => { fetchWorkspaces(); }, []);

  const fetchWorkspaces = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/collab/workspaces`, { params: { user: 'admin' } });
      setWorkspaces(data.workspaces || []);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const createWorkspace = async () => {
    if (!createName.trim()) return;
    try {
      await axios.post(`${API}/collab/workspaces`, { name: createName, description: createDesc, owner: 'admin' });
      setCreateOpen(false); setCreateName(''); setCreateDesc('');
      await fetchWorkspaces();
    } catch (e: any) { setError(e.message); }
  };

  const deleteWorkspace = async (wsId: string) => {
    try {
      await axios.delete(`${API}/collab/workspaces/${wsId}`);
      await fetchWorkspaces();
    } catch (e: any) { setError(e.message); }
  };

  if (loading) return <Box sx={{ display:'flex', justifyContent:'center', mt:8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb:3 }}>
        <Box>
          <Typography variant="h4">Collaboration</Typography>
          <Typography variant="body2" color="text.secondary">Workspaces, comments, and shared collections</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>New Workspace</Button>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={2}>
        {workspaces.map(ws => (
          <Grid item xs={12} sm={6} md={4} key={ws.id}>
            <Card sx={{ cursor:'pointer', '&:hover': { transform:'translateY(-2px)' }, transition:'transform 0.15s' }}>
              <CardContent>
                <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                  <Box>
                    <Typography variant="h6">{ws.name}</Typography>
                    <Typography variant="body2" color="text.secondary">{ws.description || 'No description'}</Typography>
                  </Box>
                  <Box sx={{ display:'flex', alignItems:'center', gap:0.5 }}>
                    <GroupIcon color="primary" />
                    <IconButton size="small" onClick={() => deleteWorkspace(ws.id)}><DeleteIcon fontSize="small" /></IconButton>
                  </Box>
                </Box>
                <Box sx={{ display:'flex', gap:0.5, mt: 2 }}>
                  <Chip label={ws.owner} size="small" variant="outlined" />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {workspaces.length === 0 && !loading && (
          <Grid item xs={12}><Typography color="text.secondary" textAlign="center" py={4}>No workspaces. Create one to get started.</Typography></Grid>
        )}
      </Grid>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Workspace</DialogTitle>
        <DialogContent>
          <TextField autoFocus fullWidth label="Workspace Name" value={createName} onChange={e => setCreateName(e.target.value)} sx={{ mt: 1 }} />
          <TextField fullWidth label="Description" multiline rows={3} value={createDesc} onChange={e => setCreateDesc(e.target.value)} sx={{ mt: 2 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={createWorkspace}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
