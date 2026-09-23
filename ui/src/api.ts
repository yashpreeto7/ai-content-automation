// API Client for the local Python backend
const API_BASE = "http://127.0.0.1:8765";

export interface Project {
  id: string;
  name: string;
  source_video_path: string;
  status: string;
  ai_provider: string;
  ai_model: string;
  duration_seconds?: number;
  video_width?: number;
  video_height?: number;
  created_at: number;
  updated_at: number;
  extra_metadata?: Record<string, any>;
}

export interface WordTiming {
  word: string;
  start: number;
  end: number;
  confidence?: number;
}

export interface TranscriptSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  words: WordTiming[];
}

export interface Transcript {
  language: string;
  duration: number;
  full_text: string;
  segments: TranscriptSegment[];
}

export interface CutSegment {
  start: number;
  end: number;
  reason: string;
  transcript_snippet?: string;
}

export interface LongFormEditPlan {
  target_duration_seconds: number;
  estimated_duration: number;
  narrative_arc: string;
  segments: CutSegment[];
}

export interface ShortCandidate {
  id: string;
  title: string;
  category: string;
  hook: string;
  hook_start: number;
  hook_end: number;
  body_start: number;
  body_end: number;
  estimated_duration: number;
  score: number;
  reason: string;
  suggested_caption: string;
  broll_suggestions: string[];
}

export interface EditPlan {
  project_id: string;
  long_form: LongFormEditPlan;
  shorts: ShortCandidate[];
  broll: any[];
  silence_cuts: any[];
  ducking_db: number;
}

export interface ShortMetadata {
  short_id: string;
  title: string;
  caption: string;
  hashtags: string[];
  thumbnail_timestamp: number;
  thumbnail_concept: string;
}

export interface VideoMetadata {
  long_form_title_options: string[];
  long_form_description: string;
  long_form_tags: string[];
  long_form_thumbnail_concept: string;
  shorts_metadata: ShortMetadata[];
}

export interface RenderJob {
  job_id: string;
  project_id: string;
  render_type: string;
  short_id?: string;
  status: string;
  progress: number;
  output_file?: string;
  error?: string;
  created_at: number;
  completed_at?: number;
}

export interface ProjectDetails {
  project: Project;
  transcript: Transcript | null;
  analysis: any | null;
  edit_plan: EditPlan | null;
  render_jobs: RenderJob[];
  metadata: VideoMetadata | null;
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.json();
  },

  async listProjects(): Promise<Project[]> {
    const res = await fetch(`${API_BASE}/api/projects`);
    return res.json();
  },

  async createProject(data: {
    name: string;
    source_video_path: string;
    ai_provider: string;
    ai_model?: string;
    target_duration_minutes?: number;
  }): Promise<Project> {
    const res = await fetch(`${API_BASE}/api/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create project");
    }
    return res.json();
  },

  async getProject(projectId: string): Promise<ProjectDetails> {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}`);
    if (!res.ok) throw new Error("Failed to fetch project");
    return res.json();
  },

  async deleteProject(projectId: string) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}`, { method: "DELETE" });
    return res.json();
  },

  async startTranscription(projectId: string) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/transcribe`, { method: "POST" });
    return res.json();
  },

  async startAnalysis(projectId: string) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/analyze`, { method: "POST" });
    return res.json();
  },

  async updateEditPlan(projectId: string, plan: EditPlan) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/edit-plan`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(plan)
    });
    return res.json();
  },

  async updateMetadata(projectId: string, metadata: VideoMetadata) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/metadata`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(metadata)
    });
    return res.json();
  },

  async renderLongForm(projectId: string) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/render/long-form`, { method: "POST" });
    return res.json();
  },

  async renderShort(projectId: string, shortId: string) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/render/short/${shortId}`, { method: "POST" });
    return res.json();
  },

  async renderAllShorts(projectId: string) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/render/all-shorts`, { method: "POST" });
    return res.json();
  },

  async publish(projectId: string, data: {
    platform: string;
    video_type: string;
    short_id?: string;
    title?: string;
    description?: string;
    privacy_status?: string;
  }) {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    return res.json();
  },

  getMediaUrl(filePath: string): string {
    return `${API_BASE}/media/file?path=${encodeURIComponent(filePath)}`;
  },

  subscribeToEvents(projectId: string, onEvent: (event: any) => void): EventSource {
    const es = new EventSource(`${API_BASE}/api/events/${projectId}`);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        onEvent(data);
      } catch (err) {
        console.error("SSE parse error", err);
      }
    };
    return es;
  }
};
