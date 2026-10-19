"""python -m app.seed  -> load the PDF-derived dataset into the configured database."""

from app.db.session import SessionLocal
from app.services import integrity
from app.services.datasets import dataset_content_hash, seed_default_dataset


def main() -> None:
    with SessionLocal() as db:
        version = seed_default_dataset(db)
        print(f"Dataset '{version.version_name}' ({version.status}) id={version.id}")
        print(f"  source hash  {version.source_hash}")
        print(f"  content hash {dataset_content_hash(db, version)}")
        print(f"  rules {len(version.rules)}  exception rules {len(version.exceptions)}")
        status = integrity.anchor_version(db, version) if version.status == "active" else "not active"
        db.commit()
        print(f"  blockchain anchor: {status}")


if __name__ == "__main__":
    main()
