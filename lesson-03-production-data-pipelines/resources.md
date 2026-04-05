# Lesson 03: Production Data Pipelines — Resources

## Text Cleaning & Normalization

- [ftfy documentation](https://ftfy.readthedocs.io/) — fixes mojibake, smart quotes, encoding issues
- [Unicode NFKC (Technical Report #15)](https://unicode.org/reports/tr15/) — canonical decomposition + compatibility composition
- [The Absolute Minimum Every Developer Must Know About Unicode](https://www.joelonsoftware.com/2003/10/08/the-absolute-minimum-every-software-developer-absolutely-positively-must-know-about-unicode-and-character-sets-no-excuses/) — Joel Spolsky

## Chunking Strategies

- [Greg Kamradt: 5 Levels of Text Splitting](https://www.youtube.com/watch?v=8OJC21T2SL4) — video + notebook
- [Chunking Strategies for RAG (Pinecone)](https://www.pinecone.io/learn/chunking-strategies/) — practical comparison
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/) — RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter, SemanticChunker
- [LlamaIndex: Ingestion Pipeline](https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/) — SentenceWindowNodeParser, ParentDocumentRetriever

## PII Detection & Data Privacy

- [Microsoft Presidio](https://microsoft.github.io/presidio/) — production PII detection/anonymization
- [Presidio: Adding Custom Recognizers](https://microsoft.github.io/presidio/analyzer/adding_recognizers/) — custom patterns for Ukrainian PII
- [GDPR Article 4](https://gdpr-info.eu/art-4-gdpr/) — definition of personal data
- [GDPR and AI](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/) — ICO guidance

## Deduplication

- [datasketch (MinHash, LSH)](https://ekzhu.com/datasketch/) — probabilistic deduplication at scale
- [Deduplication and Quality Filtering for LLM Training Data](https://arxiv.org/abs/2311.16479) — Google Research
- [SimHash (Charikar, 2002)](https://www.cs.princeton.edu/courses/archive/spring04/cos598B/bib/ChsijA-sim.pdf) — foundational paper

## Metadata & Data Lineage

- [OpenLineage](https://openlineage.io/) — open standard for data lineage
- [Pydantic v2](https://docs.pydantic.dev/) — data validation and serialization
- [Data Provenance for AI (Stanford)](https://arxiv.org/abs/2310.16787) — tracking data origins

## Feature Stores

- [Feast](https://feast.dev/) — open-source feature store
- [What is a Feature Store? (Tecton)](https://www.tecton.ai/blog/what-is-a-feature-store/) — comprehensive overview
- [Hopsworks Feature Store](https://www.hopsworks.ai/feature-store) — full platform

## Vector Databases & Embeddings

- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings) — text-embedding-3-small/large
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) — embedding model comparison
- [Qdrant](https://qdrant.tech/documentation/) — vector database

## End-to-End Pipelines

- [Unstructured.io](https://docs.unstructured.io/) — document parsing
- [LlamaIndex Ingestion Pipeline](https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/) — RAG data pipeline

## Tools Used in This Lesson

| Tool | Purpose | Install |
|------|---------|---------|
| ftfy | Fix text encoding | `pip install ftfy` |
| datasketch | MinHash dedup | `pip install datasketch` |
| langchain-text-splitters | Chunking | `pip install langchain-text-splitters` |
| scikit-learn | TF-IDF, cosine sim | `pip install scikit-learn` |
| pydantic | Data models | `pip install pydantic` |
| tiktoken | Token counting | `pip install tiktoken` |
| streamlit | Demo UI | `pip install streamlit` |
| openai | Embeddings + GPT | `pip install openai` |
