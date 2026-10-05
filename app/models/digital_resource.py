from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class DigitalResource(Base):
    """
    Online e-books, open-access resources (Project Gutenberg, DOAB, Standard Ebooks),
    librarian-uploaded educational PDFs, and external digital library resources.
    """
    __tablename__ = "digital_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    isbn: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # resource_type: "open_access", "uploaded_pdf", "external_link"
    resource_type: Mapped[str] = mapped_column(String(50), default="open_access")

    # access_type: "free", "library_members", "external"
    access_type: Mapped[str] = mapped_column(String(50), default="free")

    # provider: "Project Gutenberg", "Standard Ebooks", "DOAB", "Book Bridge Campus", etc.
    provider: Mapped[str] = mapped_column(String(100), default="Project Gutenberg")

    library_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("libraries.id"), nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)

    subject: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(50), default="English")
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    license_name: Mapped[str] = mapped_column(String(100), default="Public Domain / CC")
    license_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    distribution_basis: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rights_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    download_allowed: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )

    library = relationship("Library")
    uploader = relationship("User", foreign_keys=[uploaded_by])
