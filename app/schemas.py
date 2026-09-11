from pydantic import BaseModel, ConfigDict, Field


class SongCreate(BaseModel):
    song_code: str
    category: str | None = None
    title_hindi: str
    title_roman: str | None = None
    first_line_hindi: str | None = None
    first_line_roman: str | None = None
    lyrics: str | None = None
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
    book_page: int | None = None
    book_source: str | None = None
    status: str | None = None
    notes: str | None = None


class RecordingCreate(BaseModel):
    platform: str = "youtube"
    url: str
    video_id: str | None = None
    title: str | None = None
    channel_name: str | None = None
    channel_url: str | None = None
    publication_year: int | None = None
    language: str | None = None
    version_label: str | None = None
    match_score: float | None = Field(default=None, ge=0, le=1)
    match_reason: str | None = None
    verification_status: str = "candidate"
    is_primary: bool = False
    rejected_reason: str | None = None
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


class ArtistOut(ArtistCreate, ORMOut):
    id: int
