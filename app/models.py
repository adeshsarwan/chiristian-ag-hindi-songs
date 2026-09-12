from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Song(Base):
    __tablename__ = "songs"
    id: Mapped[int] = mapped_column(primary_key=True)
    song_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(50))
    title_hindi: Mapped[str] = mapped_column(Text)
    title_roman: Mapped[str | None] = mapped_column(Text)
    first_line_hindi: Mapped[str | None] = mapped_column(Text)
    first_line_roman: Mapped[str | None] = mapped_column(Text)
    lyrics: Mapped[str | None] = mapped_column(Text)
    lyrics_book_hindi: Mapped[str | None] = mapped_column(Text)
    lyrics_normalized_hindi: Mapped[str | None] = mapped_column(Text)
    lyrics_roman: Mapped[str | None] = mapped_column(Text)
    book_page: Mapped[int | None] = mapped_column(Integer)
    book_source: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="researching")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    recordings: Mapped[list["Recording"]] = relationship(back_populates="song", cascade="all, delete-orphan")
    research: Mapped[list["ResearchLog"]] = relationship(back_populates="song", cascade="all, delete-orphan")
    lyric_variants: Mapped[list["LyricVariant"]] = relationship(back_populates="song", cascade="all, delete-orphan")
    arrangements: Mapped[list["Arrangement"]] = relationship(back_populates="song", cascade="all, delete-orphan")


class Recording(Base):
    __tablename__ = "recordings"
    id: Mapped[int] = mapped_column(primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(40), default="youtube")
    url: Mapped[str] = mapped_column(Text)
    video_id: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(Text)
    channel_name: Mapped[str | None] = mapped_column(Text)
    channel_url: Mapped[str | None] = mapped_column(Text)
    publication_year: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str | None] = mapped_column(String(50))
    version_label: Mapped[str | None] = mapped_column(String(100))
    match_score: Mapped[float | None] = mapped_column(Float)
    match_reason: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(30), default="candidate")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    start_seconds: Mapped[int | None] = mapped_column(Integer)
    end_seconds: Mapped[int | None] = mapped_column(Integer)
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    song: Mapped[Song] = relationship(back_populates="recordings")
    credits: Mapped[list["RecordingArtist"]] = relationship(back_populates="recording", cascade="all, delete-orphan")


class LyricVariant(Base):
    __tablename__ = "lyric_variants"
    id: Mapped[int] = mapped_column(primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str | None] = mapped_column(String(50))
    source_title: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    lyrics_hindi: Mapped[str] = mapped_column(Text)
    difference_notes: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    song: Mapped[Song] = relationship(back_populates="lyric_variants")


class Arrangement(Base):
    __tablename__ = "arrangements"
    id: Mapped[int] = mapped_column(primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    arrangement_type: Mapped[str] = mapped_column(String(50), default="congregational")
    preferred_key: Mapped[str | None] = mapped_column(String(20))
    tempo_bpm: Mapped[int | None] = mapped_column(Integer)
    tempo_style: Mapped[str | None] = mapped_column(String(100))
    lead_instrument: Mapped[str | None] = mapped_column(String(100))
    accompaniment_notes: Mapped[str | None] = mapped_column(Text)
    vocal_notes: Mapped[str | None] = mapped_column(Text)
    production_status: Mapped[str] = mapped_column(String(30), default="planned")
    audio_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    song: Mapped[Song] = relationship(back_populates="arrangements")


class Artist(Base):
    __tablename__ = "artists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, index=True)
    type: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(Text)
    youtube_channel: Mapped[str | None] = mapped_column(Text)
    instagram: Mapped[str | None] = mapped_column(Text)
    facebook: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class RecordingArtist(Base):
    __tablename__ = "recording_artists"
    __table_args__ = (UniqueConstraint("recording_id", "artist_id", "role"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("recordings.id", ondelete="CASCADE"))
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(50))
    recording: Mapped[Recording] = relationship(back_populates="credits")
    artist: Mapped[Artist] = relationship()


class ResearchLog(Base):
    __tablename__ = "research_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str | None] = mapped_column(String(50))
    source_url: Mapped[str | None] = mapped_column(Text)
    source_title: Mapped[str | None] = mapped_column(Text)
    finding: Mapped[str] = mapped_column(Text)
    searched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    song: Mapped[Song] = relationship(back_populates="research")
