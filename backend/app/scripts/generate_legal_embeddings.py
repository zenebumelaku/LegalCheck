import argparse
import json
from typing import Optional, Sequence
from uuid import UUID

from app.db.session import get_session_factory
from app.services.embeddings import EmbeddingProviderConfigurationError, get_embedding_provider
from app.services.legal_embedding_index import generate_embeddings_for_verified_sources


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate embeddings for verified legal sources."
    )
    parser.add_argument(
        "--source-id",
        type=UUID,
        help="Limit indexing to one verified legal source UUID.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of provision chunks per embedding request (default: 32).",
    )
    arguments = parser.parse_args(argv)
    if arguments.batch_size < 1:
        parser.error("--batch-size must be greater than zero.")

    try:
        provider = get_embedding_provider()
    except EmbeddingProviderConfigurationError as exc:
        parser.error(str(exc))
    if provider is None:
        parser.error(
            "Set EMBEDDING_PROVIDER=openai_compatible and configure "
            "EMBEDDING_API_URL before generating production embeddings."
        )

    with get_session_factory()() as db:
        results = generate_embeddings_for_verified_sources(
            db,
            provider,
            source_id=arguments.source_id,
            batch_size=arguments.batch_size,
        )
    print(
        json.dumps(
            [result.model_dump(mode="json") for result in results],
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
