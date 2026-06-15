import { Box, Typography, Card, CardContent, Grid, Select, MenuItem, FormControl, InputLabel, Switch, FormControlLabel, Divider, Chip, TextField, Button, ToggleButtonGroup, ToggleButton, Paper } from '@mui/material';
import PaletteIcon from '@mui/icons-material/Palette';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { useThemePreset } from '../context/ThemeContext';
import { useModels } from '../context/ModelContext';

export default function Settings() {
  const { preset, presets, setPreset } = useThemePreset();
  const { activeModel, activeTier, freeModels, premiumModels, switchToModel, switchToTier, globalModelId, setGlobalModelId } = useModels();

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Settings</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>Configure application theme and preferences</Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display:'flex', alignItems:'center', gap: 1, mb: 2 }}>
                <PaletteIcon color="primary" />
                <Typography variant="h6">Theme Customization</Typography>
              </Box>
              <Divider sx={{ mb: 2 }} />

              <Typography variant="body2" gutterBottom fontWeight={600}>Color Preset</Typography>
              <FormControl fullWidth size="small" sx={{ mb: 3 }}>
                <Select value={preset.name} onChange={e => setPreset(e.target.value)}>
                  {presets.map(p => (
                    <MenuItem key={p.name} value={p.name}>
                      <Box sx={{ display:'flex', alignItems:'center', gap: 1 }}>
                        <Box sx={{ width: 16, height: 16, borderRadius: '50%', background: p.gradient }} />
                        {p.label}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Typography variant="body2" gutterBottom fontWeight={600}>Preview</Typography>
              <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display:'flex', gap: 1, flexWrap:'wrap', mb: 1 }}>
                  {['Primary', 'Secondary'].map(c => (
                    <Chip key={c} label={c} sx={{ bgcolor: c === 'Primary' ? 'primary.main' : 'secondary.main', color: '#000', fontWeight: 700 }} />
                  ))}
                  <Chip label="Outlined" variant="outlined" />
                </Box>
                <Typography variant="body2" sx={{ color: 'primary.main', fontWeight: 600 }}>Primary Color Text</Typography>
                <Typography variant="body2" sx={{ color: 'secondary.main', fontWeight: 600 }}>Secondary Color Text</Typography>
                <Box sx={{ mt: 1, height: 8, borderRadius: 2, background: preset.gradient }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Application Preferences</Typography>
              <Divider sx={{ mb: 2 }} />
              <Box sx={{ display:'flex', flexDirection:'column', gap: 2 }}>
                <FormControlLabel control={<Switch defaultChecked />} label="Auto-refresh dashboard" />
                <FormControlLabel control={<Switch defaultChecked />} label="Show engagement counts" />
                <FormControlLabel control={<Switch defaultChecked />} label="Enable animations" />
                <FormControlLabel control={<Switch />} label="Compact mode" />
                <FormControlLabel control={<Switch defaultChecked />} label="Dark mode (always on)" />
              </Box>
            </CardContent>
          </Card>

          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>API Configuration</Typography>
              <Divider sx={{ mb: 2 }} />
              <TextField fullWidth size="small" label="API Base URL" defaultValue="http://localhost:8000" sx={{ mb: 2 }} />
              <Button variant="contained" size="small">Save</Button>
            </CardContent>
          </Card>

          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Box sx={{ display:'flex', alignItems:'center', gap: 1, mb: 2 }}>
                <SmartToyIcon color="primary" />
                <Typography variant="h6">Global Model Settings</Typography>
              </Box>
              <Divider sx={{ mb: 2 }} />

              <Typography variant="body2" gutterBottom fontWeight={600}>Default Tier</Typography>
              <ToggleButtonGroup value={activeTier} exclusive onChange={(_, v) => v && switchToTier(v)} size="small" sx={{ mb: 2 }}>
                <ToggleButton value="free">Free ({freeModels.length})</ToggleButton>
                <ToggleButton value="premium">Premium ({premiumModels.length})</ToggleButton>
              </ToggleButtonGroup>

              <Typography variant="body2" gutterBottom fontWeight={600}>Global Model Override</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display:'block' }}>
                {globalModelId ? `Override active: ${globalModelId}` : 'Uses backend default model per tier'}
              </Typography>
              <Select fullWidth size="small" value={globalModelId || activeModel?.id || ''} onChange={e => setGlobalModelId(e.target.value)} sx={{ mb: 1 }}>
                <MenuItem value=""><em>None (use backend default)</em></MenuItem>
                {[...freeModels, ...premiumModels].map(m => (
                  <MenuItem key={m.id} value={m.id}>
                    {m.name} · {m.provider} · {m.tier} · {m.context_window.toLocaleString()} ctx
                  </MenuItem>
                ))}
              </Select>
              {globalModelId && (
                <Button size="small" color="warning" onClick={() => setGlobalModelId('')}>Clear override</Button>
              )}

              <Box sx={{ mt: 2, p: 1.5, borderRadius: 1, bgcolor: 'action.hover' }}>
                <Typography variant="caption" display="block">
                  <strong>Active Model:</strong> {activeModel?.name || 'N/A'}
                </Typography>
                <Typography variant="caption" display="block">
                  <strong>Provider:</strong> {activeModel?.provider || 'N/A'}
                </Typography>
                <Typography variant="caption" display="block">
                  <strong>Context Window:</strong> {activeModel?.context_window?.toLocaleString() || 'N/A'}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
