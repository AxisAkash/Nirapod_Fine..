"""python -m app.chain status | anchor | verify    (blockchain audit helpers)"""

import sys

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services import integrity
from app.services.chain import ChainError, get_chain
from app.services.datasets import get_active_version


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    settings = get_settings()
    print(f"blockchain enabled: {settings.blockchain_enabled}   rpc: {settings.blockchain_rpc_url}")
    if not settings.blockchain_enabled:
        sys.exit("Set BLOCKCHAIN_ENABLED=true in backend/.env first.")
    try:
        chain = get_chain()
    except ChainError as e:
        sys.exit(f"{e.code}: {e}")
    print(f"contract: {chain.address}   network: {chain.network}")
    with SessionLocal() as db:
        version = get_active_version(db)
        if version is None:
            sys.exit("No active dataset version. Run `python -m app.seed`.")
        if cmd == "anchor":
            print("anchor:", integrity.anchor_version(db, version, chain))
            db.commit()
        check = integrity.check_dataset(db, version, chain)
        print(f"dataset '{version.version_name}': {check.status}. {check.message}")
        if check.content_hash:
            print(f"  content hash {check.content_hash}")


if __name__ == "__main__":
    main()
