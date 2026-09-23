import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.core.config import settings
from src.core.models import (
    Project,
    Transcript,
    ContentAnalysis,
    EditPlan,
    VideoMetadata,
    RenderJob
)

class DatabaseManager:
    """Manages SQLite persistence for projects, transcripts, edit decisions, and render jobs."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_video_path TEXT NOT NULL,
                status TEXT NOT NULL,
                ai_provider TEXT NOT NULL,
                ai_model TEXT NOT NULL,
                duration_seconds REAL,
                video_width INTEGER,
                video_height INTEGER,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                extra_metadata TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                project_id TEXT PRIMARY KEY,
                language TEXT,
                duration REAL,
                full_text TEXT,
                raw_json TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_analyses (
                project_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS edit_plans (
                project_id TEXT PRIMARY KEY,
                plan_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                approved_at REAL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS render_jobs (
                job_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                render_type TEXT NOT NULL,
                short_id TEXT,
                status TEXT NOT NULL,
                progress REAL DEFAULT 0.0,
                output_file TEXT,
                error TEXT,
                created_at REAL NOT NULL,
                completed_at REAL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_metadata (
                project_id TEXT PRIMARY KEY,
                metadata_json TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """)
            conn.commit()

    # --- Project Management ---

    def create_project(
        self,
        project_id: str,
        name: str,
        source_video_path: str,
        ai_provider: str = "gemini",
        ai_model: str = "gemini-2.0-flash",
        duration_seconds: Optional[float] = None,
        video_width: Optional[int] = None,
        video_height: Optional[int] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> Project:
        now = time.time()
        project = Project(
            id=project_id,
            name=name,
            source_video_path=source_video_path,
            status="created",
            ai_provider=ai_provider,
            ai_model=ai_model,
            duration_seconds=duration_seconds,
            video_width=video_width,
            video_height=video_height,
            created_at=now,
            updated_at=now,
            extra_metadata=extra_metadata or {}
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO projects (
                id, name, source_video_path, status, ai_provider, ai_model,
                duration_seconds, video_width, video_height, created_at, updated_at, extra_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.id, project.name, project.source_video_path, project.status,
                project.ai_provider, project.ai_model, project.duration_seconds,
                project.video_width, project.video_height, project.created_at,
                project.updated_at, json.dumps(project.extra_metadata)
            ))
            conn.commit()

        # Ensure project directory structure
        proj_dir = settings.projects_dir / project_id
        for sub in ["source", "audio", "transcript", "analysis", "edit_plan", "previews", "renders", "shorts", "metadata"]:
            (proj_dir / sub).mkdir(parents=True, exist_ok=True)

        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_project(row)

    def list_projects(self) -> List[Project]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_project(r) for r in rows]

    def update_project_status(
        self,
        project_id: str,
        status: str,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if extra_metadata is not None:
                cursor.execute(
                    "UPDATE projects SET status = ?, updated_at = ?, extra_metadata = ? WHERE id = ?",
                    (status, now, json.dumps(extra_metadata), project_id)
                )
            else:
                cursor.execute(
                    "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
                    (status, now, project_id)
                )
            conn.commit()

    def delete_project(self, project_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_project(self, row: sqlite3.Row) -> Project:
        extra = {}
        if row["extra_metadata"]:
            try:
                extra = json.loads(row["extra_metadata"])
            except Exception:
                pass
        return Project(
            id=row["id"],
            name=row["name"],
            source_video_path=row["source_video_path"],
            status=row["status"],
            ai_provider=row["ai_provider"],
            ai_model=row["ai_model"],
            duration_seconds=row["duration_seconds"],
            video_width=row["video_width"],
            video_height=row["video_height"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            extra_metadata=extra
        )

    # --- Transcript Persistence ---

    def save_transcript(self, project_id: str, transcript: Transcript) -> None:
        raw_json = transcript.model_dump_json()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO transcripts (project_id, language, duration, full_text, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """, (project_id, transcript.language, transcript.duration, transcript.full_text, raw_json))
            conn.commit()

        # Also write artifact file to project/transcript/transcript.json
        proj_file = settings.projects_dir / project_id / "transcript" / "transcript.json"
        proj_file.parent.mkdir(parents=True, exist_ok=True)
        with open(proj_file, "w", encoding="utf-8") as f:
            f.write(raw_json)

    def get_transcript(self, project_id: str) -> Optional[Transcript]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT raw_json FROM transcripts WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Transcript.model_validate_json(row["raw_json"])

    # --- Content Analysis ---

    def save_content_analysis(self, project_id: str, analysis: ContentAnalysis) -> None:
        data_json = analysis.model_dump_json()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO content_analyses (project_id, data_json)
            VALUES (?, ?)
            """, (project_id, data_json))
            conn.commit()

        proj_file = settings.projects_dir / project_id / "analysis" / "analysis.json"
        proj_file.parent.mkdir(parents=True, exist_ok=True)
        with open(proj_file, "w", encoding="utf-8") as f:
            f.write(data_json)

    def get_content_analysis(self, project_id: str) -> Optional[ContentAnalysis]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data_json FROM content_analyses WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return ContentAnalysis.model_validate_json(row["data_json"])

    # --- Edit Plan ---

    def save_edit_plan(self, project_id: str, edit_plan: EditPlan, status: str = "draft") -> None:
        plan_json = edit_plan.model_dump_json()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO edit_plans (project_id, plan_json, status, approved_at)
            VALUES (?, ?, ?, ?)
            """, (project_id, plan_json, status, time.time() if status == "approved" else None))
            conn.commit()

        proj_file = settings.projects_dir / project_id / "edit_plan" / "edit_plan.json"
        proj_file.parent.mkdir(parents=True, exist_ok=True)
        with open(proj_file, "w", encoding="utf-8") as f:
            f.write(plan_json)

    def get_edit_plan(self, project_id: str) -> Optional[EditPlan]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT plan_json FROM edit_plans WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return EditPlan.model_validate_json(row["plan_json"])

    # --- Render Jobs ---

    def create_render_job(self, job: RenderJob) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO render_jobs (
                job_id, project_id, render_type, short_id, status, progress, output_file, error, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.project_id, job.render_type, job.short_id,
                job.status, job.progress, job.output_file, job.error,
                job.created_at, job.completed_at
            ))
            conn.commit()

    def update_render_job(
        self,
        job_id: str,
        status: str,
        progress: float,
        output_file: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        completed = time.time() if status in ["completed", "failed"] else None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE render_jobs
            SET status = ?, progress = ?, output_file = COALESCE(?, output_file),
                error = ?, completed_at = COALESCE(?, completed_at)
            WHERE job_id = ?
            """, (status, progress, output_file, error, completed, job_id))
            conn.commit()

    def get_render_jobs(self, project_id: str) -> List[RenderJob]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM render_jobs WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
            rows = cursor.fetchall()
            return [
                RenderJob(
                    job_id=r["job_id"],
                    project_id=r["project_id"],
                    render_type=r["render_type"],
                    short_id=r["short_id"],
                    status=r["status"],
                    progress=r["progress"],
                    output_file=r["output_file"],
                    error=r["error"],
                    created_at=r["created_at"],
                    completed_at=r["completed_at"]
                )
                for r in rows
            ]

    # --- Metadata Persistence ---

    def save_metadata(self, project_id: str, metadata: VideoMetadata) -> None:
        meta_json = metadata.model_dump_json()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO video_metadata (project_id, metadata_json)
            VALUES (?, ?)
            """, (project_id, meta_json))
            conn.commit()

        proj_file = settings.projects_dir / project_id / "metadata" / "metadata.json"
        proj_file.parent.mkdir(parents=True, exist_ok=True)
        with open(proj_file, "w", encoding="utf-8") as f:
            f.write(meta_json)

    def get_metadata(self, project_id: str) -> Optional[VideoMetadata]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata_json FROM video_metadata WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return VideoMetadata.model_validate_json(row["metadata_json"])

# Global database instance
db = DatabaseManager()
