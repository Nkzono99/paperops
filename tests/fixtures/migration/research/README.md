# Research migration fixtures

`tests/test_research_migration_adapter.py` は P1-B の合成 Research documents から、現行 legacy card と同じ front matter / heading prose 形式を一時 project に生成する。これにより approval、revision、quantity contract、provenance、gate pairing、unknown/private field、duplicate ID を外部データなしで反復検証する。
