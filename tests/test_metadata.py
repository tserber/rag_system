from pathlib import Path

from rag_core.metadata import ChunkMetadata, infer_sphere_and_technology


def test_infers_sphere_and_technology_from_two_level_path():
    data_root = Path("/data")
    file_path = Path("/data/databases/postgresql/indexing.md")
    sphere, technology = infer_sphere_and_technology(file_path, data_root)
    assert sphere == "databases"
    assert technology == "postgresql"


def test_infers_sphere_only_from_one_level_path():
    data_root = Path("/data")
    file_path = Path("/data/networking/dns.md")
    sphere, technology = infer_sphere_and_technology(file_path, data_root)
    assert sphere == "networking"
    assert technology is None


def test_infers_nothing_for_file_directly_in_root():
    data_root = Path("/data")
    file_path = Path("/data/notes.md")
    sphere, technology = infer_sphere_and_technology(file_path, data_root)
    assert sphere is None
    assert technology is None


def test_infers_nothing_for_path_outside_root():
    data_root = Path("/data")
    file_path = Path("/somewhere/else/notes.md")
    sphere, technology = infer_sphere_and_technology(file_path, data_root)
    assert sphere is None
    assert technology is None


def test_chunk_metadata_to_payload_round_trips():
    metadata = ChunkMetadata(
        text="Postgres uses MVCC.",
        source="databases/postgresql/mvcc.md",
        chunk_index=0,
        sphere="databases",
        technology="postgresql",
    )
    payload = metadata.to_payload()
    assert payload == {
        "text": "Postgres uses MVCC.",
        "source": "databases/postgresql/mvcc.md",
        "chunk_index": 0,
        "sphere": "databases",
        "technology": "postgresql",
    }
