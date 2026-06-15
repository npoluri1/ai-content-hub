import { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Card, CardContent, Chip, Button, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Select, MenuItem, FormControl, InputLabel, IconButton, CircularProgress, Alert, LinearProgress,
  List, ListItem, ListItemText, ListItemIcon, Checkbox, Divider,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import RocketIcon from '@mui/icons-material/Rocket';
import TaskIcon from '@mui/icons-material/Task';
import GroupIcon from '@mui/icons-material/Group';
import BarChartIcon from '@mui/icons-material/BarChart';
import axios from 'axios';

const API = 'http://localhost:8000';

interface Campaign { id: string; name: string; description: string; stage: string; owner: string; project_id: string; launch_date: string; target_audience: string; goals: string[]; budget: number; created_at: string; }
interface Task { id: string; title: string; description: string; assignee: string; status: string; priority: string; due_date: string; }  // eslint-disable-line @typescript-eslint/no-unused-vars
interface CampaignStats { members: number; total_tasks: number; done_tasks: number; completion_pct: number; reports: number; content_items: number; }
interface StageSummary { stage: string; count: number; }

const STAGES = ['ideation', 'planning', 'in_progress', 'review', 'launched', 'post_launch', 'completed', 'cancelled'];
const STAGE_DISPLAY: Record<string, string> = { ideation:'Ideation', planning:'Planning', in_progress:'In Progress', review:'Review', launched:'Launched', post_launch:'Post-Launch', completed:'Completed', cancelled:'Cancelled' };
const STAGE_COLORS: Record<string, string> = { ideation:'#9CA3AF', planning:'#60A5FA', in_progress:'#FBBF24', review:'#FB923C', launched:'#34D399', post_launch:'#818CF8', completed:'#6B7280', cancelled:'#EF4444' };

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [stageSummary, setStageSummary] = useState<StageSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [campaignStats, setCampaignStats] = useState<CampaignStats | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [createBudget, setCreateBudget] = useState(0);

  useEffect(() => { fetchCampaigns(); }, []);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const [c, s] = await Promise.all([
        axios.get(`${API}/campaigns`),
        axios.get(`${API}/campaigns/stages`),
      ]);
      setCampaigns(c.data.campaigns || []);
      setStageSummary(s.data.stages || []);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const selectCampaign = async (cid: string) => {
    setSelected(cid);
    try {
      const [s, t] = await Promise.all([
        axios.get(`${API}/campaigns/${cid}/stats`),
        axios.get(`${API}/campaigns/${cid}/tasks`),
      ]);
      setCampaignStats(s.data.stats);
      setTasks(t.data.tasks || []);
    } catch (e: any) { setError(e.message); }
  };

  const createCampaign = async () => {
    if (!createName.trim()) return;
    try {
      await axios.post(`${API}/campaigns`, { name: createName, description: createDesc, budget: createBudget });
      setCreateOpen(false); setCreateName(''); setCreateDesc(''); setCreateBudget(0);
      await fetchCampaigns();
    } catch (e: any) { setError(e.message); }
  };

  const updateStage = async (cid: string, stage: string) => {
    try {
      await axios.put(`${API}/campaigns/${cid}`, { stage });
      await fetchCampaigns();
      if (selected === cid) selectCampaign(cid);
    } catch (e: any) { setError(e.message); }
  };

  const deleteCampaign = async (cid: string) => {
    try {
      await axios.delete(`${API}/campaigns/${cid}`);
      if (selected === cid) { setSelected(null); setCampaignStats(null); setTasks([]); }
      await fetchCampaigns();
    } catch (e: any) { setError(e.message); }
  };

  const toggleTask = async (tid: string, currentStatus: string) => {
    try {
      await axios.put(`${API}/campaigns/tasks/${tid}`, { status: currentStatus === 'done' ? 'todo' : 'done' });
      if (selected) selectCampaign(selected);
    } catch (e: any) { setError(e.message); }
  };

  if (loading) return <Box sx={{ display:'flex', justifyContent:'center', mt:8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'center', mb:3 }}>
        <Box>
          <Typography variant="h4">Campaigns</Typography>
          <Typography variant="body2" color="text.secondary">Launch tracker with stage-based workflow</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>New Campaign</Button>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>Pipeline Overview</Typography>
          <Grid container spacing={1}>
            {STAGES.map(stage => {
              const count = stageSummary.find(s => s.stage === stage)?.count || 0;
              return (
                <Grid item key={stage}>
                  <Chip label={`${STAGE_DISPLAY[stage]}: ${count}`} size="small" sx={{ bgcolor: STAGE_COLORS[stage], color: '#fff', fontWeight: 600 }} />
                </Grid>
              );
            })}
          </Grid>
        </CardContent>
      </Card>

      <Grid container spacing={2}>
        {campaigns.map(c => (
          <Grid item xs={12} sm={6} md={4} key={c.id}>
            <Card sx={{ cursor:'pointer', border: selected === c.id ? 2 : 0, borderColor: 'primary.main', '&:hover': { transform:'translateY(-2px)' }, transition:'transform 0.15s' }}
              onClick={() => selectCampaign(c.id)}>
              <CardContent>
                <Box sx={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start' }}>
                  <Box>
                    <Typography variant="h6">{c.name}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt:0.5, display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden' }}>
                      {c.description || 'No description'}
                    </Typography>
                  </Box>
                  <IconButton size="small" onClick={(e) => { e.stopPropagation(); deleteCampaign(c.id); }}><DeleteIcon fontSize="small" /></IconButton>
                </Box>
                <Box sx={{ display:'flex', gap:0.5, mt:1.5, flexWrap:'wrap', alignItems:'center' }}>
                  <Chip label={STAGE_DISPLAY[c.stage] || c.stage} size="small" sx={{ bgcolor: STAGE_COLORS[c.stage] || '#6B7280', color:'#fff' }} />
                  {c.budget > 0 && <Chip label={`$${c.budget.toLocaleString()}`} size="small" variant="outlined" />}
                </Box>
                <Box sx={{ display:'flex', gap:1, mt:1.5 }}>
                  <Select size="small" value={c.stage} onChange={e => updateStage(c.id, e.target.value)} sx={{ minWidth:140, '& .MuiSelect-select': { py:0.5 } }}
                    onClick={e => e.stopPropagation()}>
                    {STAGES.map(s => <MenuItem key={s} value={s}>{STAGE_DISPLAY[s]}</MenuItem>)}
                  </Select>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
        {campaigns.length === 0 && !loading && (
          <Grid item xs={12}><Typography color="text.secondary" textAlign="center" py={4}>No campaigns yet. Create your first campaign.</Typography></Grid>
        )}
      </Grid>

      {selected && (
        <Box sx={{ mt: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {campaigns.find(c => c.id === selected)?.name} — {STAGE_DISPLAY[campaigns.find(c => c.id === selected)?.stage || '']}
              </Typography>
              {campaignStats && (
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={6} sm={3}>
                    <Chip label={`${campaignStats.members} members`} icon={<GroupIcon />} variant="outlined" />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Chip label={`${campaignStats.done_tasks}/${campaignStats.total_tasks} tasks`} icon={<TaskIcon />} variant="outlined" />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Chip label={`${campaignStats.completion_pct}% done`} icon={<BarChartIcon />} variant="outlined" />
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Chip label={`${campaignStats.reports} reports`} icon={<RocketIcon />} variant="outlined" />
                  </Grid>
                  <Grid item xs={12}>
                    <LinearProgress variant="determinate" value={campaignStats.completion_pct} sx={{ height: 8, borderRadius: 4, mt: 1 }} />
                  </Grid>
                </Grid>
              )}

              <Typography variant="subtitle2" gutterBottom>Tasks</Typography>
              {tasks.length === 0 ? <Typography color="text.secondary">No tasks</Typography> : (
                <List dense>
                  {tasks.map(t => (
                    <ListItem key={t.id} divider>
                      <ListItemIcon sx={{ minWidth:36 }}>
                        <Checkbox edge="start" checked={t.status === 'done'} onChange={() => toggleTask(t.id, t.status)} />
                      </ListItemIcon>
                      <ListItemText primary={t.title} secondary={`${t.assignee || 'Unassigned'} · ${t.priority}${t.due_date ? ` · Due: ${new Date(t.due_date).toLocaleDateString()}` : ''}`}
                        sx={{ textDecoration: t.status === 'done' ? 'line-through' : 'none' }} />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Box>
      )}

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Campaign</DialogTitle>
        <DialogContent>
          <TextField autoFocus fullWidth label="Campaign Name" value={createName} onChange={e => setCreateName(e.target.value)} sx={{ mt: 1 }} />
          <TextField fullWidth label="Description" multiline rows={3} value={createDesc} onChange={e => setCreateDesc(e.target.value)} sx={{ mt: 2 }} />
          <TextField fullWidth label="Budget ($)" type="number" value={createBudget} onChange={e => setCreateBudget(Number(e.target.value))} sx={{ mt: 2 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={createCampaign}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
