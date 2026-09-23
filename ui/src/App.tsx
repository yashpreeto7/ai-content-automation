import React, { useState, useEffect } from 'react';
import type {
  Project,
  ProjectDetails
} from './api';
import { api } from './api';
import {
  Video,
  Play,
  Film,
  Sparkles,
  FileText,
  Share2,
  Trash2,
  Plus,
  ArrowLeft,
  CheckCircle2,
  Cpu,
  RefreshCw,
  Download,
  Upload,
  AlertCircle
} from 'lucide-react';

function YoutubeIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2.5 17a24.12 24.12 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.56 49.56 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.12 24.12 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.55 49.55 0 0 1-16.2 0A2 2 0 0 1 2.5 17" />
      <polygon points="10 15 15 12 10 9 10 15" />
    </svg>
  );
}

function InstagramIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
    </svg>
  );
}

export default function App() {
  const [view, setView] = useState<'dashboard' | 'studio'>('dashboard');
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [projectDetails, setProjectDetails] = useState<ProjectDetails | null>(null);
  const [activeTab, setActiveTab] = useState<'long_form' | 'shorts' | 'transcript' | 'metadata' | 'publish'>('long_form');
  const [showNewModal, setShowNewModal] = useState(false);
  const [systemHealth, setSystemHealth] = useState<any>(null);

  // New Project Form State
  const [newProjName, setNewProjName] = useState('');
  const [newProjVideoPath, setNewProjVideoPath] = useState('');
  const [newProjProvider, setNewProjProvider] = useState<'gemini' | 'ollama'>('ollama');
  const [newProjDuration, setNewProjDuration] = useState<number>(12);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [createError, setCreateError] = useState('');
  const [browseResults, setBrowseResults] = useState<{
    current_path: string;
    parent_path?: string;
    directories: { name: string; path: string }[];
    videos: { name: string; path: string; size_mb: number }[];
  } | null>(null);
  const [isBrowsing, setIsBrowsing] = useState(false);

  async function triggerBrowse(path: string) {
    if (!path.trim()) {
      setBrowseResults(null);
      return;
    }
    setIsBrowsing(true);
    try {
      const res = await api.browseFiles(path.trim());
      if (res.videos?.length || res.directories?.length) {
        setBrowseResults(res);
      } else {
        setBrowseResults(null);
      }
    } catch {
      setBrowseResults(null);
    } finally {
      setIsBrowsing(false);
    }
  }

  // Live SSE Event State
  const [liveEvent, setLiveEvent] = useState<{ stage: string; progress: number; message: string } | null>(null);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError('');
    try {
      const res = await api.uploadVideo(file);
      setNewProjVideoPath(res.saved_path);
      if (!newProjName) {
        const defaultName = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
        setNewProjName(defaultName);
      }
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload video');
    } finally {
      setIsUploading(false);
    }
  }

  useEffect(() => {
    loadProjects();
    loadHealth();
  }, []);

  useEffect(() => {
    if (activeProjectId) {
      loadProjectDetails(activeProjectId);
      const es = api.subscribeToEvents(activeProjectId, (evt) => {
        if (evt.stage) {
          setLiveEvent({
            stage: evt.stage,
            progress: evt.progress || 0,
            message: evt.message || ''
          });
          if (evt.stage.includes('completed') || evt.stage.includes('ready') || evt.stage === 'transcribed') {
            loadProjectDetails(activeProjectId);
          }
        }
      });
      return () => {
        es.close();
      };
    }
  }, [activeProjectId]);

  async function loadProjects() {
    try {
      const list = await api.listProjects();
      setProjects(list);
    } catch (e) {
      console.error('Failed to load projects', e);
    }
  }

  async function loadHealth() {
    try {
      const h = await api.getHealth();
      setSystemHealth(h);
    } catch (e) {
      console.error('Failed to load health diagnostics', e);
    }
  }

  async function loadProjectDetails(id: string) {
    try {
      const details = await api.getProject(id);
      setProjectDetails(details);
    } catch (e) {
      console.error('Failed to load project details', e);
    }
  }

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!newProjName || !newProjVideoPath) return;

    setIsSubmitting(true);
    setCreateError('');
    try {
      const created = await api.createProject({
        name: newProjName,
        source_video_path: newProjVideoPath,
        ai_provider: newProjProvider,
        target_duration_minutes: newProjDuration
      });
      setShowNewModal(false);
      setNewProjName('');
      setNewProjVideoPath('');
      setBrowseResults(null);
      await loadProjects();
      openStudio(created.id);
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  }

  function openStudio(projectId: string) {
    setActiveProjectId(projectId);
    setView('studio');
    setActiveTab('long_form');
    setLiveEvent(null);
  }

  async function handleDeleteProject(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (confirm('Delete this project and all its artifacts?')) {
      await api.deleteProject(id);
      if (activeProjectId === id) {
        setView('dashboard');
        setActiveProjectId(null);
      }
      loadProjects();
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Application Navigation Bar */}
      <header style={{
        height: '64px',
        borderBottom: '1px solid var(--border-color)',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(7, 9, 14, 0.95)',
        backdropFilter: 'blur(12px)',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {view === 'studio' && (
            <button
              onClick={() => { setView('dashboard'); setActiveProjectId(null); }}
              className="btn-secondary"
              style={{ padding: '6px 12px', fontSize: '13px' }}
            >
              <ArrowLeft size={16} /> Back
            </button>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #00F0FF 0%, #8B5CF6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(0, 240, 255, 0.4)'
            }}>
              <Film size={18} color="#07090E" />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '15px', letterSpacing: '-0.3px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                AURA STUDIO
                <span className="badge badge-cyan" style={{ fontSize: '9px', padding: '2px 6px' }}>DESKTOP</span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                Hinglish Video Engine (10-15m + 4-5 Shorts)
              </div>
            </div>
          </div>
        </div>

        {/* System Diagnostics Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {systemHealth && (
            <>
              <div className="badge badge-emerald" title="Local Python Backend Running">
                <CheckCircle2 size={12} /> Backend :8765
              </div>
              <div className="badge badge-purple" title={`FFmpeg: ${systemHealth.ffmpeg}`}>
                <Cpu size={12} /> FFmpeg Ready
              </div>
              <div
                className={`badge ${systemHealth.providers?.gemini?.status === 'healthy' ? 'badge-cyan' : 'badge-amber'}`}
                title="Gemini Multimodal Cloud Provider"
              >
                Gemini 2.0 Flash
              </div>
              <div
                className={`badge ${systemHealth.providers?.ollama?.status === 'healthy' ? 'badge-emerald' : 'badge-rose'}`}
                title={`Ollama Local Provider: ${systemHealth.providers?.ollama?.status}`}
              >
                Ollama Local
              </div>
            </>
          )}

          {view === 'dashboard' && (
            <button onClick={() => setShowNewModal(true)} className="btn-primary">
              <Plus size={16} /> New Production
            </button>
          )}
        </div>
      </header>

      {/* Main View Switcher */}
      <main style={{ flex: 1, padding: '28px 36px', maxWidth: '1600px', width: '100%', margin: '0 auto' }}>
        {view === 'dashboard' ? (
          <DashboardView
            projects={projects}
            onOpenProject={openStudio}
            onDeleteProject={handleDeleteProject}
            onNewProject={() => setShowNewModal(true)}
          />
        ) : (
          <StudioView
            details={projectDetails}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            liveEvent={liveEvent}
            onRefresh={() => activeProjectId && loadProjectDetails(activeProjectId)}
          />
        )}
      </main>

      {/* New Project Modal */}
      {showNewModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '20px'
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '640px', padding: '32px', position: 'relative' }}>
            <h2 style={{ fontSize: '20px', fontWeight: 800, marginBottom: '8px' }}>
              Create New Video Production
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '24px' }}>
              Input your raw conversational Hindi/Hinglish recording. The engine will inspect the video, transcribe it, analyze narrative structure, curate a 10–15 min cut, and discover 4–5 hook-driven Shorts.
            </p>

            <form onSubmit={handleCreateProject}>
              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                  Project Name
                </label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. AI Agents & State Management Masterclass"
                  value={newProjName}
                  onChange={(e) => setNewProjName(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                  Video Source (Upload or Enter Local Path)
                </label>

                <div style={{
                  border: '2px dashed var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px',
                  textAlign: 'center',
                  marginBottom: '10px',
                  background: 'rgba(0,0,0,0.2)'
                }}>
                  <input
                    type="file"
                    id="video-file-picker"
                    accept="video/mp4,video/mkv,video/quicktime,video/webm"
                    onChange={handleFileUpload}
                    style={{ display: 'none' }}
                  />
                  <label htmlFor="video-file-picker" className="btn-secondary" style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer', marginBottom: '8px' }}>
                    <Upload size={15} style={{ marginRight: '6px' }} />
                    {isUploading ? 'Uploading Video...' : '📁 Browse / Select Video File from PC'}
                  </label>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Select any MP4, MKV, or MOV from your computer, or paste the file path below
                  </div>
                  {uploadError && (
                    <div style={{ color: '#EF4444', fontSize: '12px', marginTop: '6px' }}>{uploadError}</div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    className="input-field mono-text"
                    placeholder="e.g. C:\Users\Yashpreet_o7\Videos\recording.mp4 or G:\movies"
                    value={newProjVideoPath}
                    onChange={(e) => {
                      setNewProjVideoPath(e.target.value);
                      if (e.target.value.length > 3) triggerBrowse(e.target.value);
                    }}
                    required
                    style={{ flex: 1 }}
                  />
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => triggerBrowse(newProjVideoPath)}
                    style={{ padding: '0 14px', whiteSpace: 'nowrap' }}
                    title="Explore directory for video files"
                  >
                    {isBrowsing ? 'Scanning...' : '🔍 Browse'}
                  </button>
                </div>

                {browseResults && (browseResults.directories.length > 0 || browseResults.videos.length > 0) && (
                  <div style={{
                    background: 'rgba(0,0,0,0.5)',
                    border: '1px solid var(--accent-cyan)',
                    borderRadius: '8px',
                    padding: '12px',
                    marginTop: '8px',
                    maxHeight: '220px',
                    overflowY: 'auto'
                  }}>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--accent-cyan)', fontWeight: 700, marginBottom: '8px' }}>
                      📁 Found in: {browseResults.current_path}
                    </div>

                    {browseResults.directories.length > 0 && (
                      <div style={{ marginBottom: '8px' }}>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Subfolders:</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {browseResults.directories.map((d) => (
                            <button
                              key={d.path}
                              type="button"
                              className="badge"
                              style={{ cursor: 'pointer', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                              onClick={() => {
                                setNewProjVideoPath(d.path);
                                triggerBrowse(d.path);
                              }}
                            >
                              📁 {d.name}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {browseResults.videos.length > 0 && (
                      <div>
                        <div style={{ fontSize: '11px', color: '#10B981', fontWeight: 600, marginBottom: '6px' }}>Available Video Files (Click to select):</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {browseResults.videos.map((v) => (
                            <div
                              key={v.path}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '6px 10px',
                                borderRadius: '6px',
                                background: 'rgba(16, 185, 129, 0.08)',
                                border: '1px solid rgba(16, 185, 129, 0.2)'
                              }}
                            >
                              <div style={{ fontSize: '12px', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '360px' }}>
                                🎬 {v.name} <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>({v.size_mb} MB)</span>
                              </div>
                              <button
                                type="button"
                                className="btn-primary"
                                style={{ padding: '4px 10px', fontSize: '11px' }}
                                onClick={() => {
                                  setNewProjVideoPath(v.path);
                                  if (!newProjName) {
                                    const cleanName = v.name.replace(/\.[^/.]+$/, '').replace(/[._-]/g, ' ');
                                    setNewProjName(cleanName);
                                  }
                                  setBrowseResults(null);
                                }}
                              >
                                Select Video
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                  AI Provider Selection
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div
                    onClick={() => setNewProjProvider('gemini')}
                    style={{
                      border: newProjProvider === 'gemini' ? '2px solid var(--accent-cyan)' : '1px solid var(--border-color)',
                      background: newProjProvider === 'gemini' ? 'var(--accent-cyan-dim)' : 'rgba(0,0,0,0.2)',
                      padding: '16px',
                      borderRadius: '10px',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: '14px', color: '#00F0FF', marginBottom: '4px' }}>
                      Google Gemini 2.0 Flash
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Cloud multimodal analysis. Highest speed and nuanced conversational reasoning.
                    </div>
                  </div>

                  <div
                    onClick={() => setNewProjProvider('ollama')}
                    style={{
                      border: newProjProvider === 'ollama' ? '2px solid var(--accent-emerald)' : '1px solid var(--border-color)',
                      background: newProjProvider === 'ollama' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(0,0,0,0.2)',
                      padding: '16px',
                      borderRadius: '10px',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: '14px', color: '#10B981', marginBottom: '4px' }}>
                      Local Ollama (Ready)
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      100% offline & privacy-first. Runs faster-whisper + llama3.2 on your GPU.
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '24px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
                  Target Long-Form YouTube Duration: <span style={{ color: 'var(--accent-cyan)' }}>{newProjDuration} Minutes</span>
                </label>
                <input
                  type="range"
                  min="8"
                  max="18"
                  step="1"
                  value={newProjDuration}
                  onChange={(e) => setNewProjDuration(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
                />
              </div>

              {createError && (
                <div style={{
                  color: '#EF4444',
                  background: 'rgba(239, 68, 68, 0.12)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  fontSize: '13px',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <AlertCircle size={16} />
                  <span>{createError}</span>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="btn-secondary"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Creating Project...' : 'Create & Open Studio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// --- DASHBOARD VIEW ---

function DashboardView({
  projects,
  onOpenProject,
  onDeleteProject,
  onNewProject
}: {
  projects: Project[];
  onOpenProject: (id: string) => void;
  onDeleteProject: (id: string, e: React.MouseEvent) => void;
  onNewProject: () => void;
}) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 800, letterSpacing: '-0.5px', marginBottom: '6px' }}>
            Production Projects
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            Manage raw conversational tech videos, review AI-curated long-form cuts, and render 9:16 Shorts with Roman-Hinglish karaoke captions.
          </p>
        </div>
        <button onClick={onNewProject} className="btn-primary">
          <Plus size={16} /> New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="glass-panel" style={{ padding: '64px 32px', textAlign: 'center' }}>
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '16px',
            background: 'rgba(0, 240, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            color: 'var(--accent-cyan)'
          }}>
            <Video size={32} />
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px' }}>
            No Video Projects Yet
          </h3>
          <p style={{ color: 'var(--text-muted)', maxWidth: '480px', margin: '0 auto 24px', fontSize: '14px' }}>
            Start by creating a new project. Select your raw Hindi/Hinglish recording and let the autonomous engine transcribe, analyze, and render your long-form & Shorts content.
          </p>
          <button onClick={onNewProject} className="btn-primary">
            <Plus size={16} /> Create Your First Project
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
          {projects.map((p) => (
            <div
              key={p.id}
              onClick={() => onOpenProject(p.id)}
              className="glass-panel-interactive"
              style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <span className={`badge ${
                    p.status === 'completed' ? 'badge-emerald' :
                    p.status === 'edit_plan_ready' ? 'badge-cyan' :
                    p.status === 'transcribed' ? 'badge-purple' : 'badge-amber'
                  }`}>
                    {p.status.replace('_', ' ')}
                  </span>

                  <span className={`badge ${p.ai_provider === 'gemini' ? 'badge-cyan' : 'badge-emerald'}`} style={{ fontSize: '10px' }}>
                    {p.ai_provider.toUpperCase()}
                  </span>
                </div>

                <h3 style={{ fontSize: '17px', fontWeight: 700, lineHeight: 1.4, marginBottom: '8px' }}>
                  {p.name}
                </h3>

                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  📁 {p.source_video_path}
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-dim)', borderTop: '1px solid var(--border-color)', paddingTop: '12px', marginBottom: '16px' }}>
                  <span>⏱ {p.duration_seconds ? `${Math.round(p.duration_seconds / 60)} mins raw` : 'Analyzing...'}</span>
                  <span>{new Date(p.created_at * 1000).toLocaleDateString()}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <button className="btn-primary" style={{ padding: '8px 14px', fontSize: '13px' }}>
                    Open Studio
                  </button>
                  <button
                    onClick={(e) => onDeleteProject(p.id, e)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', padding: '8px' }}
                    title="Delete project"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- STUDIO VIEW ---

function StudioView({
  details,
  activeTab,
  setActiveTab,
  liveEvent,
  onRefresh
}: {
  details: ProjectDetails | null;
  activeTab: 'long_form' | 'shorts' | 'transcript' | 'metadata' | 'publish';
  setActiveTab: (t: 'long_form' | 'shorts' | 'transcript' | 'metadata' | 'publish') => void;
  liveEvent: { stage: string; progress: number; message: string } | null;
  onRefresh: () => void;
}) {
  if (!details) {
    return <div style={{ textAlign: 'center', padding: '80px', color: 'var(--text-muted)' }}>Loading Project Studio...</div>;
  }

  const { project, transcript, edit_plan } = details;

  async function handleTranscribe() {
    await api.startTranscription(project.id);
  }

  async function handleAnalyze() {
    await api.startAnalysis(project.id);
  }

  async function handleRenderLongForm() {
    await api.renderLongForm(project.id);
  }

  async function handleRenderShort(shortId: string) {
    await api.renderShort(project.id, shortId);
  }

  async function handleRenderAllShorts() {
    await api.renderAllShorts(project.id);
  }

  return (
    <div>
      {/* Studio Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 800 }}>{project.name}</h1>
            <span className={`badge ${
              project.status === 'completed' ? 'badge-emerald' :
              project.status === 'edit_plan_ready' ? 'badge-cyan' :
              project.status === 'transcribed' ? 'badge-purple' : 'badge-amber'
            }`}>
              {project.status.replace('_', ' ')}
            </span>
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
            Source: <span className="mono-text">{project.source_video_path}</span> ({project.duration_seconds ? `${Math.round(project.duration_seconds / 60)} mins` : '—'}) | Provider: <b>{project.ai_provider.toUpperCase()}</b>
          </div>
        </div>

        {/* Action Trigger Buttons */}
        <div style={{ display: 'flex', gap: '10px' }}>
          {!transcript && (
            <button onClick={handleTranscribe} className="btn-primary">
              <FileText size={16} /> 1. Transcribe Hinglish
            </button>
          )}

          {transcript && !edit_plan && (
            <button onClick={handleAnalyze} className="btn-primary">
              <Sparkles size={16} /> 2. Analyze & Generate Edit Plan
            </button>
          )}

          {edit_plan && (
            <>
              <button onClick={handleRenderLongForm} className="btn-secondary">
                <Play size={15} /> Render Long-Form (16:9)
              </button>
              <button onClick={handleRenderAllShorts} className="btn-primary">
                <Film size={15} /> Render All 4–5 Shorts (9:16)
              </button>
            </>
          )}

          <button onClick={onRefresh} className="btn-secondary" title="Refresh state">
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Live SSE Progress Stepper */}
      {liveEvent && (
        <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '24px', borderColor: 'var(--accent-cyan)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontWeight: 700, fontSize: '13px', color: 'var(--accent-cyan)' }}>
              ⚡ LIVE PIPELINE EXECUTION: {liveEvent.stage.toUpperCase()}
            </span>
            <span style={{ fontWeight: 800, fontSize: '14px' }}>
              {liveEvent.progress}%
            </span>
          </div>
          <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden', marginBottom: '8px' }}>
            <div style={{
              height: '100%',
              width: `${liveEvent.progress}%`,
              background: 'linear-gradient(90deg, #00F0FF, #8B5CF6)',
              transition: 'width 0.3s ease'
            }} />
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            {liveEvent.message}
          </div>
        </div>
      )}

      {/* Studio Navigation Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', marginBottom: '24px' }}>
        {[
          { id: 'long_form', label: '1. Long-Form YouTube (10–15 Min)', icon: Play },
          { id: 'shorts', label: '2. 4–5 Shorts / Reels (9:16)', icon: Film },
          { id: 'transcript', label: '3. Spoken Hinglish Transcript', icon: FileText },
          { id: 'metadata', label: '4. Titles & SEO Metadata', icon: Sparkles },
          { id: 'publish', label: '5. Export & Publishing', icon: Share2 },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 20px',
                border: 'none',
                background: 'transparent',
                color: isActive ? 'var(--accent-cyan)' : 'var(--text-muted)',
                fontWeight: isActive ? 700 : 500,
                fontSize: '14px',
                borderBottom: isActive ? '2px solid var(--accent-cyan)' : '2px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      <div>
        {activeTab === 'long_form' && (
          <LongFormPanel
            details={details}
            onRender={handleRenderLongForm}
          />
        )}

        {activeTab === 'shorts' && (
          <ShortsPanel
            details={details}
            onRenderShort={handleRenderShort}
          />
        )}

        {activeTab === 'transcript' && (
          <TranscriptPanel details={details} />
        )}

        {activeTab === 'metadata' && (
          <MetadataPanel details={details} />
        )}

        {activeTab === 'publish' && (
          <PublishPanel details={details} />
        )}
      </div>
    </div>
  );
}

// --- TAB 1: LONG FORM PANEL ---

function LongFormPanel({ details, onRender }: { details: ProjectDetails; onRender: () => void }) {
  const { edit_plan, render_jobs } = details;
  const longFormRender = render_jobs.find((j) => j.render_type === 'long_form');

  if (!edit_plan) {
    return (
      <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px' }}>Edit Plan Not Generated Yet</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '20px' }}>
          Click "Analyze & Generate Edit Plan" above to allow the AI to curate the 10–15 minute narrative segments.
        </p>
      </div>
    );
  }

  const { long_form } = edit_plan;

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px' }}>
        {/* Left: Narrative Arc & Cut Segments */}
        <div>
          <div className="glass-panel" style={{ padding: '20px', marginBottom: '20px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '8px' }}>
              NARRATIVE 3-ACT ARC
            </h4>
            <p style={{ fontSize: '14px', lineHeight: 1.6 }}>
              {long_form.narrative_arc}
            </p>
            <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
              Target Duration: ~{Math.round(long_form.target_duration_seconds / 60)} mins | Estimated Cut Duration: <b>{Math.round(long_form.estimated_duration / 60 * 10) / 10} mins</b>
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '20px' }}>
            <h4 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '16px' }}>
              Curated Narrative Segments ({long_form.segments.length})
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {long_form.segments.map((seg, idx) => (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '14px 18px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                      <span className="badge badge-cyan" style={{ fontSize: '10px' }}>
                        #{idx + 1}
                      </span>
                      <span className="mono-text" style={{ fontSize: '13px', fontWeight: 600 }}>
                        {formatTime(seg.start)} ➔ {formatTime(seg.end)} ({Math.round(seg.end - seg.start)}s)
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-main)', marginBottom: '4px' }}>
                      {seg.reason}
                    </div>
                    {seg.transcript_snippet && (
                      <div style={{ fontSize: '12px', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                        "{seg.transcript_snippet}"
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Render Preview Player & Controls */}
        <div>
          <div className="glass-panel" style={{ padding: '20px', position: 'sticky', top: '88px' }}>
            <h4 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '14px' }}>
              Long-Form Video Output (16:9)
            </h4>

            {longFormRender && longFormRender.status === 'completed' && longFormRender.output_file ? (
              <div>
                <video
                  controls
                  src={api.getMediaUrl(longFormRender.output_file)}
                  style={{ width: '100%', borderRadius: '8px', marginBottom: '14px', background: '#000' }}
                />
                <div className="badge badge-emerald" style={{ marginBottom: '12px', width: '100%', justifyContent: 'center' }}>
                  <CheckCircle2 size={13} /> Render Ready
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', wordBreak: 'break-all' }}>
                  📁 {longFormRender.output_file}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '36px 16px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', marginBottom: '16px' }}>
                <Film size={36} color="var(--text-dim)" style={{ marginBottom: '12px' }} />
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
                  {longFormRender?.status === 'rendering'
                    ? 'Rendering in progress...'
                    : '10–15 min video not rendered yet'}
                </div>
                <button
                  onClick={onRender}
                  className="btn-primary"
                  disabled={longFormRender?.status === 'rendering'}
                  style={{ width: '100%', justifyContent: 'center' }}
                >
                  <Play size={16} /> Render Long-Form Video
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- TAB 2: SHORTS PANEL ---

function ShortsPanel({ details, onRenderShort }: { details: ProjectDetails; onRenderShort: (id: string) => void }) {
  const { edit_plan, render_jobs } = details;

  if (!edit_plan || edit_plan.shorts.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px' }}>Shorts Not Selected Yet</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
          Generate the edit plan to automatically select 4–5 viral hook-driven Shorts candidates.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 800 }}>4–5 Standalone Shorts / Reels Candidates (9:16)</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
            Each Short is standalone, hook-driven, framed in 9:16 with face tracking, and features animated Roman-Hinglish karaoke captions.
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(480px, 1fr))', gap: '20px' }}>
        {edit_plan.shorts.map((short) => {
          const renderJob = render_jobs.find((j) => j.short_id === short.id && j.render_type === 'short');
          const isRendered = renderJob && renderJob.status === 'completed' && renderJob.output_file;

          return (
            <div key={short.id} className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                {/* Short Category & Score */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span className={`badge ${
                    short.category === 'hot_take' ? 'badge-amber' :
                    short.category === 'story' ? 'badge-emerald' :
                    short.category === 'contrarian' ? 'badge-rose' : 'badge-cyan'
                  }`}>
                    {short.category.replace('_', ' ')}
                  </span>

                  <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent-amber)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    ★ {short.score} / 10 Score
                  </span>
                </div>

                <h4 style={{ fontSize: '17px', fontWeight: 800, marginBottom: '8px', lineHeight: 1.3 }}>
                  {short.title}
                </h4>

                {/* Opening Hook Quote */}
                <div style={{
                  background: 'rgba(0, 240, 255, 0.06)',
                  borderLeft: '3px solid var(--accent-cyan)',
                  padding: '10px 14px',
                  borderRadius: '0 8px 8px 0',
                  marginBottom: '14px',
                  fontSize: '13px'
                }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-cyan)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    OPENING HOOK (0–3s)
                  </div>
                  "{short.hook}"
                </div>

                <div style={{ display: 'flex', gap: '14px', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '14px' }}>
                  <span>⏱ Body: <b className="mono-text">{formatTime(short.body_start)} - {formatTime(short.body_end)}</b> ({Math.round(short.estimated_duration)}s)</span>
                  <span>⚡ Hook Cut: <b className="mono-text">{formatTime(short.hook_start)} - {formatTime(short.hook_end)}</b></span>
                </div>

                {/* Roman-Hinglish Suggested Caption */}
                <div style={{ fontSize: '12px', color: 'var(--text-main)', marginBottom: '14px' }}>
                  <b>Roman-Hinglish Caption:</b> {short.suggested_caption}
                </div>

                {/* B-roll Suggestions */}
                {short.broll_suggestions && short.broll_suggestions.length > 0 && (
                  <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginBottom: '16px' }}>
                    <b>B-Roll Visuals:</b> {short.broll_suggestions.join(', ')}
                  </div>
                )}
              </div>

              {/* Video Player or Render Trigger */}
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                {isRendered ? (
                  <div>
                    <video
                      controls
                      src={api.getMediaUrl(renderJob.output_file!)}
                      style={{
                        width: '100%',
                        maxHeight: '360px',
                        borderRadius: '8px',
                        background: '#000',
                        marginBottom: '10px'
                      }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="badge badge-emerald" style={{ fontSize: '11px' }}>
                        <CheckCircle2 size={12} /> 9:16 Rendered
                      </span>
                      <button
                        onClick={() => onRenderShort(short.id)}
                        className="btn-secondary"
                        style={{ padding: '6px 12px', fontSize: '12px' }}
                      >
                        <RefreshCw size={13} /> Re-render
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => onRenderShort(short.id)}
                    className="btn-primary"
                    style={{ width: '100%', justifyContent: 'center' }}
                    disabled={renderJob?.status === 'rendering'}
                  >
                    {renderJob?.status === 'rendering' ? (
                      'Rendering 9:16 Short...'
                    ) : (
                      <>
                        <Film size={15} /> Render This Short (9:16)
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- TAB 3: TRANSCRIPT PANEL ---

function TranscriptPanel({ details }: { details: ProjectDetails }) {
  const { transcript } = details;
  const [search, setSearch] = useState('');

  if (!transcript) {
    return (
      <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px' }}>Transcription Pending</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
          Click "Transcribe Hinglish" to run faster-whisper on the extracted audio.
        </p>
      </div>
    );
  }

  const filtered = transcript.segments.filter((s) =>
    s.text.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="glass-panel" style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 800 }}>
            Spoken Hinglish Transcript ({transcript.segments.length} segments)
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
            Word-level timestamps preserved. Technical English keywords retained verbatim.
          </p>
        </div>

        <input
          type="text"
          className="input-field"
          placeholder="Search spoken words or tech terms..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: '280px' }}
        />
      </div>

      <div style={{ maxHeight: '600px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filtered.map((seg) => (
          <div
            key={seg.id}
            style={{
              padding: '10px 14px',
              borderRadius: '6px',
              background: 'rgba(0,0,0,0.25)',
              border: '1px solid var(--border-color)',
              display: 'flex',
              gap: '16px',
              alignItems: 'baseline'
            }}
          >
            <span className="mono-text" style={{ fontSize: '12px', color: 'var(--accent-cyan)', minWidth: '95px' }}>
              {formatTime(seg.start)} - {formatTime(seg.end)}
            </span>
            <span style={{ fontSize: '14px', color: 'var(--text-main)', lineHeight: 1.5 }}>
              {seg.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- TAB 4: METADATA PANEL ---

function MetadataPanel({ details }: { details: ProjectDetails }) {
  const { metadata } = details;
  const [desc, setDesc] = useState(metadata?.long_form_description || '');

  if (!metadata) {
    return (
      <div className="glass-panel" style={{ padding: '48px', textAlign: 'center' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '8px' }}>Metadata Not Generated Yet</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
          Run AI content analysis to generate title options, description chapters, hashtags, and thumbnail concepts.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
      {/* Left: Long-Form YouTube Metadata */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 800, marginBottom: '16px', color: 'var(--accent-cyan)' }}>
          YouTube Long-Form Metadata
        </h3>

        <div style={{ marginBottom: '18px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
            High-CTR Hinglish Title Variations
          </label>
          {metadata.long_form_title_options.map((title, i) => (
            <div
              key={i}
              style={{
                padding: '10px 14px',
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                marginBottom: '8px',
                fontSize: '13px',
                fontWeight: 600
              }}
            >
              Option {i + 1}: {title}
            </div>
          ))}
        </div>

        <div style={{ marginBottom: '18px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
            Description with Chapters & Timestamps
          </label>
          <textarea
            className="input-field mono-text"
            rows={8}
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>
            Thumbnail Concept
          </label>
          <div style={{ padding: '12px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>
            🎨 {metadata.long_form_thumbnail_concept}
          </div>
        </div>
      </div>

      {/* Right: Shorts Metadata List */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 800, marginBottom: '16px', color: 'var(--accent-purple)' }}>
          Shorts / Reels Metadata ({metadata.shorts_metadata.length})
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '560px', overflowY: 'auto' }}>
          {metadata.shorts_metadata.map((sm, idx) => (
            <div
              key={idx}
              style={{
                padding: '14px',
                borderRadius: '8px',
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid var(--border-color)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span className="badge badge-purple" style={{ fontSize: '10px' }}>{sm.short_id}</span>
                <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Thumb at {formatTime(sm.thumbnail_timestamp)}</span>
              </div>
              <div style={{ fontWeight: 700, fontSize: '14px', marginBottom: '6px' }}>{sm.title}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>{sm.caption}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {sm.hashtags.map((h, i) => (
                  <span key={i} style={{ fontSize: '11px', color: 'var(--accent-cyan)' }}>{h}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// --- TAB 5: PUBLISH & EXPORT PANEL ---

function PublishPanel({ details }: { details: ProjectDetails }) {
  const { project, render_jobs } = details;
  const [selectedPlatform, setSelectedPlatform] = useState<'youtube' | 'instagram'>('youtube');
  const [publishStatus, setPublishStatus] = useState<string | null>(null);

  async function handlePublish() {
    setPublishStatus('Connecting to publishing service...');
    try {
      const res = await api.publish(project.id, {
        platform: selectedPlatform,
        video_type: 'long_form',
        privacy_status: 'private'
      });
      setPublishStatus(`Dispatch status: ${res.status} (${res.note || res.error || 'Ready'})`);
    } catch (e: any) {
      setPublishStatus(`Publish error: ${e.message}`);
    }
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <div className="glass-panel" style={{ padding: '32px' }}>
        <h3 style={{ fontSize: '20px', fontWeight: 800, marginBottom: '8px' }}>
          Export & Direct Publishing
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '24px' }}>
          All videos are deterministically rendered locally on your machine. You can export them to your filesystem or publish directly with explicit user approval.
        </p>

        {/* Local Filesystem Paths */}
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '10px' }}>
            Rendered Files on Disk
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {render_jobs.filter((j) => j.status === 'completed' && j.output_file).map((j, i) => (
              <div
                key={i}
                style={{
                  padding: '10px 14px',
                  background: 'rgba(0,0,0,0.3)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <span className="badge badge-cyan" style={{ fontSize: '10px', marginRight: '8px' }}>
                    {j.render_type === 'long_form' ? '16:9 Long-Form' : `9:16 Short (${j.short_id})`}
                  </span>
                  <span className="mono-text" style={{ fontSize: '12px' }}>
                    {j.output_file}
                  </span>
                </div>
                <a
                  href={api.getMediaUrl(j.output_file!)}
                  download
                  className="btn-secondary"
                  style={{ padding: '4px 10px', fontSize: '12px' }}
                >
                  <Download size={13} />
                </a>
              </div>
            ))}
          </div>
        </div>

        {/* Social Publishing Form */}
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '24px' }}>
          <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>
            Direct Social Media Dispatch
          </h4>

          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
            <button
              onClick={() => setSelectedPlatform('youtube')}
              className={`btn-secondary ${selectedPlatform === 'youtube' ? 'btn-primary' : ''}`}
            >
              <YoutubeIcon size={16} /> YouTube
            </button>
            <button
              onClick={() => setSelectedPlatform('instagram')}
              className={`btn-secondary ${selectedPlatform === 'instagram' ? 'btn-primary' : ''}`}
            >
              <InstagramIcon size={16} /> Instagram Reels
            </button>
          </div>

          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Requires credentials in your <span className="mono-text">.env</span> file (never hard-coded). Explicit confirmation is required before any media is dispatched.
          </p>

          <button onClick={handlePublish} className="btn-primary">
            Publish to {selectedPlatform === 'youtube' ? 'YouTube' : 'Instagram Reels'}
          </button>

          {publishStatus && (
            <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(0,0,0,0.4)', borderRadius: '6px', fontSize: '13px', color: 'var(--accent-cyan)' }}>
              {publishStatus}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}
