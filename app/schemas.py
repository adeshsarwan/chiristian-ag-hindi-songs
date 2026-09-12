from pydantic import BaseModel, ConfigDict, Field, model_validator


class SongCreate(BaseModel):
    song_code: str
    category: str | None = None
    title_hindi: str
    title_roman: str | None = None
    first_line_hindi: str | None = None
    first_line_roman: str | None = None
    lyrics: str | None = None
    lyrics_book_hindi: str | None = None
    lyrics_normalized_hindi: str | None = None
    lyrics_roman: str | None = None
    book_page: int | None = None
    book_source: str | None = None
    status: str = "researching"
    notes: str | None = None


class SongUpdate(BaseModel):
    category: str | None = None
    title_hindi: str | None = None
    title_roman: str | None = None
    first_line_hindi: str | None = None
    first_line_roman: str | None = None
    lyrics: str | None = None
    lyrics_book_hindi: str | None = None
    lyrics_normalized_hindi: str | None = None
    lyrics_roman: str | None = None
    book_page: int | None = None
    book_source: str | None = None
    status: str | None = None
    notes: str | None = None


class RecordingBase(BaseModel):
    platform: str | None = None
    url: str | None = None
    video_id: str | None = None
    title: str | None = None
    channel_name: str | None = None
    channel_url: str | None = None
    publication_year: int | None = None
    language: str | None = None
    version_label: str | None = None
    match_score: float | None = Field(default=None, ge=0, le=1)
    match_reason: str | None = None
    verification_status: str | None = None
    is_primary: bool | None = None
    start_seconds: int | None = Field(default=None, ge=0)
    end_seconds: int | None = Field(default=None, ge=0)
    rejected_reason: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_segment(self):
        if self.start_seconds is not None and self.end_seconds is not None and self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


class RecordingCreate(RecordingBase):
    platform: str = "youtube"
    url: str
    verification_status: str = "candidate"
    is_primary: bool = False


class RecordingUpdate(RecordingBase):
    pass


class LyricVariantCreate(BaseModel):
    source_type: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    lyrics_hindi: str
    difference_notes: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class ArrangementCreate(BaseModel):
    arrangement_type: str = "congregational"
    preferred_key: str | None = None
    tempo_bpm: int | None = Field(default=None, gt=0, le=400)
    tempo_style: str | None = None
    lead_instrument: str | None = None
    accompaniment_notes: str | None = None
    vocal_notes: str | None = None
    production_status: str = "planned"
    audio_url: str | None = None
    notes: str | None = None


class ArrangementUpdate(BaseModel):
    arrangement_type: str | None = None
    preferred_key: str | None = None
    tempo_bpm: int | None = Field(default=None, gt=0, le=400)
    tempo_style: str | None = None
    lead_instrument: str | None = None
    accompaniment_notes: str | None = None
    vocal_notes: str | None = None
    production_status: str | None = None
    audio_url: str | None = None
    notes: str | None = None


class ArtistCreate(BaseModel):
    name: str
    type: str | None = None
    website: str | None = None
    youtube_channel: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    notes: str | None = None


class CreditCreate(BaseModel):
    artist_id: int
    role: str


class ResearchCreate(BaseModel):
    source_type: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    finding: str


class ORMOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SongOut(SongCreate, ORMOut):
    id: int


class RecordingOut(RecordingCreate, ORMOut):
    id: int
    song_id: int


class LyricVariantOut(LyricVariantCreate, ORMOut):
    id: int
    song_id: int


class ArrangementOut(ArrangementCreate, ORMOut):
    id: int
    song_id: int


class ArtistOut(ArtistCreate, ORMOut):
    id: int
