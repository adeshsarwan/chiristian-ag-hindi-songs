import secrets
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import Base, engine, get_db
from .models import Artist, Recording, RecordingArtist, ResearchLog, Song
from .schemas import ArtistCreate, ArtistOut, CreditCreate, RecordingCreate, RecordingOut, ResearchCreate, SongCreate, SongOut, SongUpdate

settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


def require_api_key(authorization: str | None = Header(default=None)):
    expected = f"Bearer {settings.api_key}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


@app.get("/health")
def health():
    return {"ok": True, "service": settings.app_name}


@app.get("/api/songs", response_model=list[SongOut], dependencies=[Depends(require_api_key)])
def list_songs(status: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Song).order_by(Song.id)
    if status:
        stmt = stmt.where(Song.status == status)
    if q:
        stmt = stmt.where(Song.title_hindi.ilike(f"%{q}%") | Song.title_roman.ilike(f"%{q}%") | Song.song_code.ilike(f"%{q}%"))
    return db.scalars(stmt).all()


@app.get("/api/songs/{song_code}", response_model=SongOut, dependencies=[Depends(require_api_key)])
def get_song(song_code: str, db: Session = Depends(get_db)):
    song = db.scalar(select(Song).where(Song.song_code == song_code.upper()))
    if not song:
        raise HTTPException(404, "Song not found")
    return song


@app.post("/api/songs", response_model=SongOut, dependencies=[Depends(require_api_key)])
def create_song(payload: SongCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Song).where(Song.song_code == payload.song_code.upper())):
        raise HTTPException(409, "Song code already exists")
    data = payload.model_dump()
    data["song_code"] = data["song_code"].upper()
    song = Song(**data)
    db.add(song); db.commit(); db.refresh(song)
    return song


@app.patch("/api/songs/{song_code}", response_model=SongOut, dependencies=[Depends(require_api_key)])
def update_song(song_code: str, payload: SongUpdate, db: Session = Depends(get_db)):
    song = db.scalar(select(Song).where(Song.song_code == song_code.upper()))
    if not song:
        raise HTTPException(404, "Song not found")
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(song, k, v)
    db.commit(); db.refresh(song)
    return song


@app.get("/api/songs/{song_code}/recordings", response_model=list[RecordingOut], dependencies=[Depends(require_api_key)])
def recordings(song_code: str, db: Session = Depends(get_db)):
    song = db.scalar(select(Song).where(Song.song_code == song_code.upper()))
    if not song: raise HTTPException(404, "Song not found")
    return db.scalars(select(Recording).where(Recording.song_id == song.id).order_by(Recording.id)).all()


@app.post("/api/songs/{song_code}/recordings", response_model=RecordingOut, dependencies=[Depends(require_api_key)])
def add_recording(song_code: str, payload: RecordingCreate, db: Session = Depends(get_db)):
    song = db.scalar(select(Song).where(Song.song_code == song_code.upper()))
    if not song: raise HTTPException(404, "Song not found")
    recording = Recording(song_id=song.id, **payload.model_dump())
    db.add(recording); db.commit(); db.refresh(recording)
    return recording


@app.patch("/api/recordings/{recording_id}", response_model=RecordingOut, dependencies=[Depends(require_api_key)])
def update_recording(recording_id: int, payload: RecordingCreate, db: Session = Depends(get_db)):
    recording = db.get(Recording, recording_id)
    if not recording: raise HTTPException(404, "Recording not found")
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(recording, k, v)
    db.commit(); db.refresh(recording)
    return recording


@app.post("/api/songs/{song_code}/primary-recording/{recording_id}", dependencies=[Depends(require_api_key)])
def set_primary(song_code: str, recording_id: int, db: Session = Depends(get_db)):
    song = db.scalar(select(Song).where(Song.song_code == song_code.upper()))
    recording = db.get(Recording, recording_id)
    if not song or not recording or recording.song_id != song.id: raise HTTPException(404, "Song/recording not found")
    for item in db.scalars(select(Recording).where(Recording.song_id == song.id)).all(): item.is_primary = item.id == recording_id
    db.commit()
    return {"ok": True, "song_code": song.song_code, "primary_recording_id": recording_id}


@app.post("/api/artists", response_model=ArtistOut, dependencies=[Depends(require_api_key)])
def create_artist(payload: ArtistCreate, db: Session = Depends(get_db)):
    artist = Artist(**payload.model_dump()); db.add(artist); db.commit(); db.refresh(artist); return artist


@app.get("/api/artists", response_model=list[ArtistOut], dependencies=[Depends(require_api_key)])
def list_artists(db: Session = Depends(get_db)):
    return db.scalars(select(Artist).order_by(Artist.name)).all()


@app.post("/api/recordings/{recording_id}/credits", dependencies=[Depends(require_api_key)])
def add_credit(recording_id: int, payload: CreditCreate, db: Session = Depends(get_db)):
    if not db.get(Recording, recording_id) or not db.get(Artist, payload.artist_id): raise HTTPException(404, "Recording/artist not found")
    credit = RecordingArtist(recording_id=recording_id, artist_id=payload.artist_id, role=payload.role)
    db.add(credit); db.commit(); return {"ok": True, "credit_id": credit.id}


@app.post("/api/songs/{song_code}/research", dependencies=[Depends(require_api_key)])
def add_research(song_code: str, payload: ResearchCreate, db: Session = Depends(get_db)):
    song = db.scalar(select(Song).where(Song.song_code == song_code.upper()))
    if not song: raise HTTPException(404, "Song not found")
    item = ResearchLog(song_id=song.id, **payload.model_dump()); db.add(item); db.commit(); return {"ok": True, "research_id": item.id}


@app.get("/api/songs/{song_code}/research", dependencies=[Depends(require_api_key)])
def get_research(song_code: str, db: Session = Depends(get_db)):
    song = db.scalar(select(Song).where(Song.song_code == song_code.upper()))
    if not song: raise HTTPException(404, "Song not found")
    items = db.scalars(select(ResearchLog).where(ResearchLog.song_id == song.id).order_by(ResearchLog.searched_at.desc())).all()
    return [{"id": x.id, "source_type": x.source_type, "source_url": x.source_url, "source_title": x.source_title, "finding": x.finding, "searched_at": x.searched_at} for x in items]
