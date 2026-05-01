"""
Seed a batch of realistic subjects for local development.

Usage (from backend/ directory with Docker services running):
    uv run python scripts/seed_subjects.py
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.subject import Subject

SUBJECTS = [
    # Engineering — Year 1
    {"name": "Mathematics I", "code": "MATH101", "college": "Engineering", "academic_year": 1},
    {"name": "Physics I", "code": "PHY101", "college": "Engineering", "academic_year": 1},
    {"name": "Introduction to Programming", "code": "CS101", "college": "Engineering", "academic_year": 1},
    {"name": "Engineering Drawing", "code": "ENG101", "college": "Engineering", "academic_year": 1},
    # Engineering — Year 2
    {"name": "Mathematics II", "code": "MATH201", "college": "Engineering", "academic_year": 2},
    {"name": "Data Structures & Algorithms", "code": "CS201", "college": "Engineering", "academic_year": 2},
    {"name": "Digital Logic", "code": "CS202", "college": "Engineering", "academic_year": 2},
    {"name": "Thermodynamics", "code": "ME201", "college": "Engineering", "academic_year": 2},
    # Engineering — Year 3
    {"name": "Operating Systems", "code": "CS301", "college": "Engineering", "academic_year": 3},
    {"name": "Database Systems", "code": "CS302", "college": "Engineering", "academic_year": 3},
    {"name": "Computer Networks", "code": "CS303", "college": "Engineering", "academic_year": 3},
    {"name": "Software Engineering", "code": "CS304", "college": "Engineering", "academic_year": 3},
    # Medicine — Year 1
    {"name": "Anatomy I", "code": "MED101", "college": "Medicine", "academic_year": 1},
    {"name": "Physiology I", "code": "MED102", "college": "Medicine", "academic_year": 1},
    {"name": "Biochemistry", "code": "MED103", "college": "Medicine", "academic_year": 1},
    # Medicine — Year 2
    {"name": "Anatomy II", "code": "MED201", "college": "Medicine", "academic_year": 2},
    {"name": "Pathology", "code": "MED202", "college": "Medicine", "academic_year": 2},
    {"name": "Pharmacology I", "code": "MED203", "college": "Medicine", "academic_year": 2},
    # Business — Year 1
    {"name": "Microeconomics", "code": "BUS101", "college": "Business", "academic_year": 1},
    {"name": "Accounting I", "code": "BUS102", "college": "Business", "academic_year": 1},
    {"name": "Business Law", "code": "BUS103", "college": "Business", "academic_year": 1},
    # Business — Year 2
    {"name": "Macroeconomics", "code": "BUS201", "college": "Business", "academic_year": 2},
    {"name": "Marketing", "code": "BUS202", "college": "Business", "academic_year": 2},
    {"name": "Statistics for Business", "code": "BUS203", "college": "Business", "academic_year": 2},
]


async def seed() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as db:
        inserted = 0
        skipped = 0
        for data in SUBJECTS:
            existing = await db.scalar(
                select(Subject).where(
                    Subject.college == data["college"],
                    Subject.code == data["code"],
                    Subject.academic_year == data["academic_year"],
                )
            )
            if existing:
                skipped += 1
                continue
            db.add(Subject(**data))
            inserted += 1

        await db.commit()
        print(f"Seeded {inserted} subjects ({skipped} already existed)")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
